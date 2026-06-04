#!/usr/bin/env python
# bib-resolve.py - multi-source online validation for .bib entries.
#
# Strengthens cite-check beyond the old single-source (CrossRef-or-S2) path:
#   * Queries CrossRef, OpenAlex, DBLP, and (optionally) Semantic Scholar and
#     RECONCILES them - a reference is "real" when independent sources agree.
#   * Checks RETRACTION status via CrossRef's Retraction Watch data
#     (work['updated-by'][*].type == 'retraction', or a 'RETRACTED:' title).
#   * Emits a FABRICATION verdict (REAL / UNCERTAIN / LIKELY-FABRICATED /
#     UNVERIFIED) instead of a soft "no-match".
#
# Network errors are distinguished from genuine "not found": if sources are
# unreachable the verdict is UNVERIFIED, never LIKELY-FABRICATED. A fabrication
# call requires at least two sources that DEFINITIVELY return no match.
#
# Usage:
#   python bib-resolve.py --doi 10.1038/nature14539
#   python bib-resolve.py --title "Attention is all you need" --author Vaswani --year 2017
#   python bib-resolve.py refs.bib
#   add --json for machine output, --no-s2 to skip Semantic Scholar,
#   --sleep N to override the inter-request delay.
#
# Stdlib only (urllib). On systems whose binary is python3, substitute python3.

import os
import sys
import re
import json
import time
import difflib
import urllib.request
import urllib.parse
import urllib.error

UA = "latex-sentinel/0.2 (mailto:nobody@example.com)"
MAILTO = "nobody@example.com"
TIMEOUT = 20
SLEEP = 0.34          # polite gap for CrossRef/OpenAlex/DBLP
SIM_OK = 0.82         # title similarity threshold to call a match
USE_S2 = True

# Semantic Scholar: an API key raises the quota a lot. With a key we can poll
# faster and tolerate more consecutive rate-limits before tripping the breaker.
S2_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
S2_SLEEP = 0.3 if S2_KEY else 1.5
S2_BREAK_AT = 10 if S2_KEY else 3

# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

def http_json(url, headers=None):
    """Return ('ok', obj) | ('notfound', None) | ('error', reason)."""
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return "ok", json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return "notfound", None
        if e.code == 429:
            return "ratelimited", None
        return "error", "HTTP %s" % e.code
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        return "error", str(e)


# --------------------------------------------------------------------------
# Normalisation / similarity
# --------------------------------------------------------------------------

def norm_title(s):
    s = re.sub(r"[{}\\]", "", s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_sim(a, b):
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return 0.0
    ratio = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return max(ratio, jac)


def surname(name):
    if not name:
        return ""
    name = name.strip()
    if "," in name:
        return name.split(",")[0].strip().lower()
    return name.split()[-1].lower() if name.split() else ""


def norm_doi(s):
    s = (s or "").strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    s = re.sub(r"^doi:\s*", "", s, flags=re.I)
    return s.lower()


def year_of(s):
    m = re.search(r"\d{4}", str(s or ""))
    return int(m.group(0)) if m else None


# --------------------------------------------------------------------------
# Source adapters -> uniform record {title, year, doi, first_author, source}
# --------------------------------------------------------------------------

def rec(title, year, doi, first_author, source):
    return {"title": title or "", "year": year_of(year), "doi": norm_doi(doi),
            "first_author": first_author or "", "source": source}


def crossref_by_doi(doi):
    st, obj = http_json("https://api.crossref.org/works/" + urllib.parse.quote(doi),
                        headers={"User-Agent": UA})
    if st != "ok":
        return st, None
    m = obj["message"]
    auth = m.get("author") or []
    fa = ""
    if auth:
        fa = (auth[0].get("family") or auth[0].get("name") or "")
    record = rec(m.get("title", [""])[0] if m.get("title") else "",
                 (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
                 m.get("DOI", ""), fa, "crossref")
    record["retracted"] = _crossref_retracted(m)
    return "ok", record


def _crossref_retracted(m):
    title = (m.get("title", [""]) or [""])[0]
    if re.match(r"\s*(RETRACTED|WITHDRAWN)\b", title, re.I):
        return "retracted"
    for u in m.get("updated-by", []) or []:
        t = (u.get("type") or "").lower()
        if t == "retraction":
            return "retracted"
        if t in ("expression_of_concern", "expression-of-concern"):
            return "concern"
    return None


def crossref_query(title):
    q = urllib.parse.urlencode({"query.bibliographic": title, "rows": 3})
    st, obj = http_json("https://api.crossref.org/works?" + q, headers={"User-Agent": UA})
    if st != "ok":
        return st, []
    out = []
    for m in obj.get("message", {}).get("items", []):
        auth = m.get("author") or []
        fa = (auth[0].get("family") or auth[0].get("name") or "") if auth else ""
        out.append(rec(m.get("title", [""])[0] if m.get("title") else "",
                       (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
                       m.get("DOI", ""), fa, "crossref"))
    return "ok", out


def openalex_by_title(title):
    q = urllib.parse.urlencode({"search": title, "per-page": 3, "mailto": MAILTO})
    st, obj = http_json("https://api.openalex.org/works?" + q)
    if st != "ok":
        return st, []
    out = []
    for w in obj.get("results", []):
        au = w.get("authorships") or []
        fa = au[0]["author"]["display_name"] if au else ""
        out.append(rec(w.get("title", ""), w.get("publication_year"),
                       w.get("doi", ""), fa, "openalex"))
    return "ok", out


def dblp_by_title(title):
    q = urllib.parse.urlencode({"q": title, "format": "json", "h": 3})
    st, obj = http_json("https://dblp.org/search/publ/api?" + q)
    if st != "ok":
        return st, []
    out = []
    hits = (obj.get("result", {}).get("hits", {}) or {}).get("hit", []) or []
    for h in hits:
        info = h.get("info", {})
        authors = info.get("authors", {}).get("author", [])
        if isinstance(authors, dict):
            authors = [authors]
        fa = ""
        if authors:
            first = authors[0]
            fa = first.get("text", "") if isinstance(first, dict) else str(first)
        out.append(rec(info.get("title", ""), info.get("year"),
                       info.get("doi", ""), fa, "dblp"))
    return "ok", out


def s2_by_title(title):
    q = urllib.parse.urlencode({"query": title, "limit": 3,
                                "fields": "title,year,authors,externalIds"})
    headers = {"User-Agent": UA}
    if S2_KEY:
        headers["x-api-key"] = S2_KEY
    st, obj = http_json("https://api.semanticscholar.org/graph/v1/paper/search?" + q,
                        headers=headers)
    if st != "ok":
        return st, []
    out = []
    for p in obj.get("data", []) or []:
        au = p.get("authors") or []
        fa = au[0].get("name", "") if au else ""
        doi = (p.get("externalIds") or {}).get("DOI", "")
        out.append(rec(p.get("title", ""), p.get("year"), doi, fa, "s2"))
    return "ok", out


# --------------------------------------------------------------------------
# Reconciliation
# --------------------------------------------------------------------------

def best_match(records, title, year=None, author=None):
    """Return (record, sim) for the best title match, or (None, 0).

    Existence is judged on TITLE similarity. When several records tie on title
    (the same title can belong to several distinct works), year and first
    author act ONLY as tie-breakers to pick the most plausible canonical
    record - they never lower a title score, so a wrong year cannot make a
    real paper look fabricated. The returned `sim` is always the raw title
    similarity, so the caller's SIM_OK threshold stays year-agnostic.
    """
    best, best_key, best_sim = None, (-1.0, -1.0), 0.0
    for r in records:
        s = title_sim(title, r["title"])
        bonus = 0.0
        if author and r.get("first_author") and surname(author) \
                and surname(author) == surname(r["first_author"]):
            bonus += 0.10
        if year and r.get("year") and r["year"] == year:
            bonus += 0.05
        key = (round(s, 4), bonus)
        if key > best_key:
            best, best_key, best_sim = r, key, s
    return best, best_sim


class Breaker:
    """Semantic Scholar circuit breaker (mirrors SKILL.md spec)."""
    def __init__(self):
        self.consecutive = 0
        self.open = False

    def call(self, title):
        if self.open:
            return "skipped", []
        for attempt in range(3):
            st, hits = s2_by_title(title)
            if st == "ratelimited":
                time.sleep(min(5 * (2 ** attempt), 60))
                continue
            self.consecutive = 0
            return st, hits
        self.consecutive += 1
        if self.consecutive >= S2_BREAK_AT:
            self.open = True
        return "ratelimited", []


def resolve(title, author=None, year=None, doi=None, breaker=None):
    """Core reconciliation. Returns a verdict dict."""
    breaker = breaker or Breaker()
    result = {
        "title": title, "given_doi": doi, "verdict": None, "retracted": None,
        "resolved_doi": None, "confirmations": 0, "definitive_misses": 0,
        "sources": {}, "mismatches": [], "note": "",
    }

    # --- DOI path: CrossRef is authoritative -------------------------------
    if doi:
        st, r = crossref_by_doi(doi)
        result["sources"]["crossref(doi)"] = st
        time.sleep(SLEEP)
        if st == "ok":
            result["verdict"] = "REAL"
            result["resolved_doi"] = r["doi"]
            result["retracted"] = r.get("retracted")
            if title:
                _compare(result, r, title, author, year)
            return result
        if st == "error":
            result["note"] = "CrossRef unreachable for DOI; falling back to title search"
        elif st == "notfound":
            result["note"] = "DOI does not resolve on CrossRef"
        # fall through to title reconciliation to classify dead-DOI vs fabricated

    if not title:
        result["verdict"] = "UNVERIFIED"
        result["note"] = "no title to search and DOI did not resolve"
        return result

    # --- Title path: gather candidates from independent sources ------------
    sources = [("crossref", crossref_query), ("openalex", openalex_by_title),
               ("dblp", dblp_by_title)]
    confirmations, definitive_misses = 0, 0
    confirming = []   # (record, sim) for sources that passed SIM_OK

    def consume(name, st, hits):
        nonlocal confirmations, definitive_misses
        m, sim = best_match(hits, title, year, author) if st == "ok" else (None, 0.0)
        if st == "ok" and m and sim >= SIM_OK:
            confirmations += 1
            result["sources"][name] = "match(%.2f)" % sim
            confirming.append((m, sim))
        elif st == "ok":
            definitive_misses += 1
            result["sources"][name] = "no-match"
        elif st == "notfound":
            definitive_misses += 1
            result["sources"][name] = "not-found"
        else:
            result["sources"][name] = st  # error/ratelimited

    for name, fn in sources:
        st, hits = fn(title)
        time.sleep(SLEEP)
        consume(name, st, hits)

    if USE_S2:
        st, hits = breaker.call(title)
        time.sleep(S2_SLEEP if st != "skipped" else 0)
        consume("s2", st, hits)

    result["confirmations"] = confirmations
    result["definitive_misses"] = definitive_misses

    # Pick the canonical confirming record: prefer one whose author and year
    # agree with the bib entry, then highest title similarity, then has a DOI.
    canonical = None
    if confirming:
        def agree_key(item):
            m, sim = item
            a = 0
            if author and m.get("first_author") and surname(author) \
                    and surname(author) == surname(m["first_author"]):
                a += 2
            if year and m.get("year") and m["year"] == year:
                a += 1
            return (a, round(sim, 4), 1 if m.get("doi") else 0)
        canonical = max(confirming, key=agree_key)[0]
        if canonical.get("doi"):
            result["resolved_doi"] = canonical["doi"]

    # --- DOI cross-confirmation -------------------------------------------
    # Keyword search has poor recall on some titles: a famous paper can be
    # absent from CrossRef/OpenAlex free-text results yet sit in DBLP/S2 with
    # a correct DOI. Resolving the canonical record's DOI on CrossRef is
    # authoritative - a registered DOI whose title matches proves the work
    # exists (and reveals retraction status). We verify ONLY the canonical
    # record's DOI (the one already preferred on author/year), so this can
    # neither rescue a fabricated reference nor grab a same-titled other work.
    doi_verified = False
    if canonical and canonical.get("doi"):
        st, r = crossref_by_doi(canonical["doi"])
        time.sleep(SLEEP)
        if st == "ok":
            xtitle = r.get("title", "")
            # Some registrants (e.g. ACL Anthology) deposit no title in the
            # CrossRef record. The DOI still resolving proves the work is
            # registered, and the title was already matched by the source that
            # supplied this DOI - so accept resolution as verification, but
            # require a title match when CrossRef does provide one.
            if not xtitle or title_sim(title, xtitle) >= SIM_OK:
                doi_verified = True
                if not xtitle:
                    r["title"] = canonical.get("title") or title
                canonical = r
                result["resolved_doi"] = r["doi"]
                result["retracted"] = r.get("retracted")
                result["sources"]["crossref(doi)"] = (
                    "verified(%.2f)" % title_sim(title, xtitle) if xtitle else "verified(doi-ok)")

    if canonical:
        _compare(result, canonical, title, author, year)

    # --- Verdict -----------------------------------------------------------
    # A DOI-verified match is sufficient on its own; otherwise require two
    # independent title confirmations.
    if doi_verified or confirmations >= 2:
        result["verdict"] = "REAL"
    elif confirmations == 1:
        result["verdict"] = "UNCERTAIN"
    else:
        if definitive_misses >= 2:
            result["verdict"] = "LIKELY-FABRICATED"
        elif definitive_misses == 1:
            result["verdict"] = "UNCERTAIN"
        else:
            result["verdict"] = "UNVERIFIED"

    # DOI was given but did not resolve, yet the paper IS real elsewhere.
    if doi and result["verdict"] == "REAL":
        result["mismatches"].append("given DOI does not resolve but paper found elsewhere -> fix DOI")
        result["verdict"] = "REAL (bad DOI)"

    # Retraction backstop: if we have a DOI but didn't learn status above.
    if result.get("resolved_doi") and result["retracted"] is None:
        st, r = crossref_by_doi(result["resolved_doi"])
        time.sleep(SLEEP)
        if st == "ok":
            result["retracted"] = r.get("retracted")

    return result


def _compare(result, r, title, author, year):
    if title and r.get("title"):
        s = title_sim(title, r["title"])
        if s < SIM_OK:
            result["mismatches"].append("title differs (sim %.2f): canonical %r" % (s, r["title"][:70]))
    if year and r.get("year") and abs(r["year"] - year) > 0:
        result["mismatches"].append("year: bib %s vs source %s" % (year, r["year"]))
    if author and r.get("first_author"):
        if surname(author) and surname(author) != surname(r["first_author"]):
            result["mismatches"].append("first author: bib %r vs source %r" % (author, r["first_author"]))


# --------------------------------------------------------------------------
# .bib parsing (minimal - just enough to drive the resolver)
# --------------------------------------------------------------------------

ENTRY_RE = re.compile(r"@(\w+)\s*\{([^,]+),", re.IGNORECASE)
FIELD_RE = re.compile(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|[^,\n]+)", re.IGNORECASE)


def parse_bib_min(text):
    entries = []
    for m in ENTRY_RE.finditer(text):
        etype, key = m.group(1).lower(), m.group(2).strip()
        if etype in ("comment", "string", "preamble"):
            continue
        # body = from after key-comma to a reasonable bound (next @ or EOF)
        start = m.end()
        nxt = text.find("\n@", start)
        body = text[start: nxt if nxt != -1 else len(text)]
        fields = {}
        for fm in FIELD_RE.finditer(body):
            val = fm.group(2).strip()
            if val and val[0] in "{\"" and val[-1] in "}\"":
                val = val[1:-1].strip()
            fields[fm.group(1).lower()] = val
        entries.append({"type": etype, "key": key, "fields": fields})
    return entries


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def verdict_mark(v):
    return {
        "REAL": "OK", "REAL (bad DOI)": "!!", "UNCERTAIN": "? ",
        "LIKELY-FABRICATED": "XX", "UNVERIFIED": ".."
    }.get(v, "? ")


def print_one(key, res):
    head = "%-22s %s %s" % (key or res.get("title", "")[:22], verdict_mark(res["verdict"]), res["verdict"])
    if res.get("retracted") == "retracted":
        head += "   *** RETRACTED ***"
    elif res.get("retracted") == "concern":
        head += "   (expression of concern)"
    print(head)
    srcs = "  ".join("%s=%s" % (k, v) for k, v in res["sources"].items())
    if srcs:
        print("    sources: " + srcs)
    if res.get("resolved_doi"):
        print("    resolved DOI: " + res["resolved_doi"])
    for mm in res["mismatches"]:
        print("    ! " + mm)
    if res.get("note"):
        print("    note: " + res["note"])


def main(argv):
    global USE_S2, SLEEP
    args = [a for a in argv if not a.startswith("--")]
    flags = [a for a in argv if a.startswith("--")]
    as_json = "--json" in flags
    if "--no-s2" in flags:
        USE_S2 = False

    def flagval(name, default=None):
        for i, a in enumerate(argv):
            if a == name and i + 1 < len(argv):
                return argv[i + 1]
        return default

    if "--sleep" in flags:
        try:
            SLEEP = float(flagval("--sleep", SLEEP))
        except (TypeError, ValueError):
            pass

    breaker = Breaker()
    results = []

    if "--doi" in flags or "--title" in flags:
        res = resolve(
            title=flagval("--title", ""),
            author=flagval("--author"),
            year=year_of(flagval("--year")),
            doi=flagval("--doi"),
            breaker=breaker,
        )
        results.append((flagval("--doi") or flagval("--title", "")[:22], res))
    else:
        bibs = [a for a in args if a not in (flagval("--title"), flagval("--author"),
                                             flagval("--year"), flagval("--doi"))]
        if not bibs:
            sys.stderr.write("usage: python bib-resolve.py [--json] (--doi D | --title T [--author A] [--year Y] | file.bib)\n")
            return 64
        for path in bibs:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError as e:
                sys.stderr.write("cannot read %s: %s\n" % (path, e))
                continue
            for ent in parse_bib_min(text):
                f = ent["fields"]
                res = resolve(title=f.get("title", ""), author=f.get("author", ""),
                              year=year_of(f.get("year") or f.get("date")),
                              doi=(norm_doi(f["doi"]) if f.get("doi") else None),
                              breaker=breaker)
                results.append((ent["key"], res))

    if as_json:
        print(json.dumps([{"key": k, **r} for k, r in results], indent=2, default=str))
    else:
        for k, r in results:
            print_one(k, r)
        n = len(results)
        real = sum(1 for _, r in results if r["verdict"].startswith("REAL"))
        unc = sum(1 for _, r in results if r["verdict"] == "UNCERTAIN")
        fab = sum(1 for _, r in results if r["verdict"] == "LIKELY-FABRICATED")
        ret = sum(1 for _, r in results if r.get("retracted") == "retracted")
        print("\nbib-resolve: %d real, %d uncertain, %d likely-fabricated, %d retracted of %d"
              % (real, unc, fab, ret, n))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
