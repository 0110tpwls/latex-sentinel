#!/usr/bin/env python
# bib-integrity.py - offline structural/field integrity checks for .bib files.
#
# The JabRef "Check Integrity" + "Check Consistency" dimension that cite-check
# previously lacked. Pure stdlib, NO network: parse-level and field-level rules
# only. Network validation (CrossRef/OpenAlex/DBLP/retraction) lives in the
# companion bib-resolve.py.
#
# Usage:
#   python bib-integrity.py refs.bib [more.bib ...]
#   python bib-integrity.py --json refs.bib
#
# On systems whose binary is python3, substitute python3.
#
# Severity:
#   ERROR  - will mis-render or silently lose data (dup key, missing required
#            field, broken DOI/ISBN/ISSN checksum, unbalanced braces).
#   WARN   - very likely wrong (single-hyphen page range, et al. in author,
#            implausible year, HTML entity, duplicate DOI across keys).
#   STYLE  - cosmetic / convention (unprotected title casing, url scheme).

import sys
import re
import json

# --------------------------------------------------------------------------
# Minimal brace-aware BibTeX parser (tracks line numbers).
# --------------------------------------------------------------------------

ENTRY_RE = re.compile(r"@(\w+)\s*\{", re.IGNORECASE)
SKIP_TYPES = {"comment", "string", "preamble", "preference"}


def parse_bib(text):
    """Return list of entries: {type, key, fields:{name:value}, line, raw,
    brace_ok}. Best-effort, resilient to messy input."""
    entries = []
    i, n = 0, len(text)
    line_starts = [0]
    for idx, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(idx + 1)

    def line_of(pos):
        # binary-ish search
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    for m in ENTRY_RE.finditer(text):
        etype = m.group(1).lower()
        if etype in SKIP_TYPES:
            continue
        start = m.end()  # just after '{'
        # Walk to the matching closing brace.
        depth = 1
        j = start
        while j < n and depth > 0:
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            j += 1
        brace_ok = depth == 0
        body = text[start:j - 1] if brace_ok else text[start:j]
        raw = text[m.start():j]
        entry = parse_entry_body(body)
        entry["type"] = etype
        entry["line"] = line_of(m.start())
        entry["raw"] = raw
        entry["brace_ok"] = brace_ok
        entries.append(entry)
    return entries


def parse_entry_body(body):
    """Split '<key>, field = value, ...' respecting braces/quotes."""
    # key = up to first top-level comma
    key = ""
    fields = {}
    field_order = []
    # Tokenise top-level by comma.
    parts = split_top_level(body)
    if parts:
        key = parts[0].strip()
    for part in parts[1:]:
        if "=" not in part:
            continue
        name, _, value = part.partition("=")
        name = name.strip().lower()
        value = value.strip()
        if not name:
            continue
        fields[name] = strip_value(value)
        field_order.append(name)
    return {"key": key, "fields": fields, "field_order": field_order}


def split_top_level(s):
    out, buf, depth, q = [], [], 0, False
    i = 0
    while i < len(s):
        c = s[i]
        if c == '"' and depth == 0:
            q = not q
            buf.append(c)
        elif c == "{":
            depth += 1
            buf.append(c)
        elif c == "}":
            depth = max(0, depth - 1)
            buf.append(c)
        elif c == "," and depth == 0 and not q:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    out.append("".join(buf))
    return out


def strip_value(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == "{" and v[-1] == "}":
        return v[1:-1].strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1].strip()
    return v


# --------------------------------------------------------------------------
# Required fields per entry type (biblatex-friendly: alternatives are OR-sets).
# Each requirement is a tuple of acceptable field names; satisfied if ANY present.
# --------------------------------------------------------------------------

REQUIRED = {
    "article": [("author",), ("title",), ("journal", "journaltitle"), ("year", "date")],
    "inproceedings": [("author",), ("title",), ("booktitle",), ("year", "date")],
    "conference": [("author",), ("title",), ("booktitle",), ("year", "date")],
    "incollection": [("author",), ("title",), ("booktitle",), ("publisher",), ("year", "date")],
    "book": [("author", "editor"), ("title",), ("publisher",), ("year", "date")],
    "inbook": [("author", "editor"), ("title",), ("publisher",), ("year", "date")],
    "proceedings": [("title",), ("year", "date")],
    "phdthesis": [("author",), ("title",), ("school", "institution"), ("year", "date")],
    "mastersthesis": [("author",), ("title",), ("school", "institution"), ("year", "date")],
    "thesis": [("author",), ("title",), ("institution", "school"), ("type",), ("year", "date")],
    "techreport": [("author",), ("title",), ("institution",), ("year", "date")],
    "report": [("author",), ("title",), ("institution",), ("year", "date")],
    "manual": [("title",)],
    "unpublished": [("author",), ("title",), ("note",)],
    "misc": [],          # nothing strictly required
    "online": [("title",), ("url",)],
    "electronic": [("title",), ("url",)],
    "patent": [("author",), ("title",), ("number",), ("year", "date")],
}


# --------------------------------------------------------------------------
# Identifier checksums
# --------------------------------------------------------------------------

def isbn_valid(s):
    digits = re.sub(r"[\s-]", "", s)
    if re.fullmatch(r"\d{9}[\dXx]", digits):           # ISBN-10
        total = 0
        for idx, ch in enumerate(digits):
            v = 10 if ch in "Xx" else int(ch)
            total += (10 - idx) * v
        return total % 11 == 0
    if re.fullmatch(r"\d{13}", digits):                # ISBN-13
        total = sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(digits))
        return total % 10 == 0
    return None  # not an ISBN shape -> can't judge


def issn_valid(s):
    digits = re.sub(r"[\s-]", "", s)
    if not re.fullmatch(r"\d{7}[\dXx]", digits):
        return None
    total = 0
    for idx, ch in enumerate(digits):
        v = 10 if ch in "Xx" else int(ch)
        total += (8 - idx) * v
    return total % 11 == 0


DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
CUR_YEAR = 2026


def normalize_doi(s):
    s = s.strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^doi:\s*", "", s, flags=re.IGNORECASE)
    return s


def normalize_title(s):
    s = re.sub(r"[{}\\]", "", s).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------
# Per-entry checks
# --------------------------------------------------------------------------

def check_entry(e):
    """Return list of (severity, code, message)."""
    out = []
    t, f = e["type"], e["fields"]

    if not e["brace_ok"]:
        out.append(("ERROR", "brace", "unbalanced braces - entry may swallow following entries"))
    if not e["key"]:
        out.append(("ERROR", "key", "missing citation key"))

    # Required fields.
    reqs = REQUIRED.get(t)
    if reqs is None:
        out.append(("STYLE", "type", "unknown entry type @%s (not validated for required fields)" % t))
    else:
        for alt in reqs:
            if not any(a in f and f[a].strip() for a in alt):
                label = "/".join(alt)
                out.append(("ERROR", "required", "missing required field: %s" % label))

    # Empty fields present but blank.
    for name, val in f.items():
        if val == "":
            out.append(("WARN", "empty", "field '%s' is present but empty" % name))

    # DOI.
    if "doi" in f and f["doi"]:
        doi = normalize_doi(f["doi"])
        if not DOI_RE.match(doi):
            out.append(("ERROR", "doi", "malformed DOI: %r" % f["doi"]))

    # ISBN / ISSN checksums.
    if "isbn" in f and f["isbn"]:
        v = isbn_valid(f["isbn"])
        if v is False:
            out.append(("ERROR", "isbn", "ISBN checksum fails: %r" % f["isbn"]))
        elif v is None:
            out.append(("WARN", "isbn", "ISBN not a valid 10/13-digit shape: %r" % f["isbn"]))
    if "issn" in f and f["issn"]:
        v = issn_valid(f["issn"])
        if v is False:
            out.append(("ERROR", "issn", "ISSN checksum fails: %r" % f["issn"]))
        elif v is None:
            out.append(("WARN", "issn", "ISSN not a valid 8-digit shape: %r" % f["issn"]))

    # Year plausibility.
    yr = f.get("year") or f.get("date", "")
    ym = re.search(r"\d{4}", yr)
    if yr and not ym:
        out.append(("WARN", "year", "year/date has no 4-digit year: %r" % yr))
    elif ym:
        y = int(ym.group(0))
        if y < 1500 or y > CUR_YEAR + 1:
            out.append(("WARN", "year", "implausible year: %d" % y))

    # Page range: single hyphen between numbers -> should be '--'.
    if "pages" in f and f["pages"]:
        p = f["pages"]
        if re.search(r"\d\s*-\s*\d", p) and "--" not in p and "–" not in p:
            out.append(("WARN", "pages", "page range uses single hyphen; BibTeX wants '--': %r" % p))

    # Author format.
    au = f.get("author", "")
    if au:
        if re.search(r"\bet\s+al\.?", au, re.IGNORECASE):
            out.append(("WARN", "author", "literal 'et al.' in author field - list authors or it will print verbatim"))
        if " and " not in au and (";" in au or " & " in au):
            out.append(("WARN", "author", "authors not separated by ' and ' (found ';' or '&')"))

    # URL scheme.
    if "url" in f and f["url"] and not re.match(r"^(https?|ftp)://", f["url"], re.IGNORECASE):
        out.append(("STYLE", "url", "url has no http(s)/ftp scheme: %r" % f["url"][:40]))

    # HTML entities / tags leaking into any field.
    for name, val in f.items():
        if re.search(r"&(amp|lt|gt|quot|#\d+);", val) or re.search(r"</?(i|b|sub|sup|em)>", val):
            out.append(("WARN", "html", "HTML markup/entity in field '%s'" % name))
            break

    # Title-case protection (heuristic, STYLE): acronym / internal-caps word not
    # wrapped in braces gets lowercased by many .bst styles.
    title = f.get("title", "")
    if title:
        # Remove already-protected {...} spans.
        unprotected = re.sub(r"\{[^{}]*\}", " ", title)
        words = unprotected.split()
        risky = []
        for w in words[1:]:  # skip first word (sentence-initial cap is fine)
            core = re.sub(r"[^A-Za-z0-9]", "", w)
            if len(core) >= 2 and (core.isupper() or re.search(r"[a-z][A-Z]", core) or re.match(r"[A-Z]+[0-9]", core)):
                risky.append(core)
        if risky:
            out.append(("STYLE", "casing", "unprotected caps/acronyms in title (wrap in {}): %s" % ", ".join(risky[:4])))

    return out


# --------------------------------------------------------------------------
# Cross-entry checks (duplicates)
# --------------------------------------------------------------------------

def cross_checks(entries):
    out = []  # (severity, code, message)
    by_key = {}
    by_doi = {}
    by_title = {}
    for e in entries:
        k = e["key"].lower()
        if k:
            by_key.setdefault(k, []).append(e)
        doi = e["fields"].get("doi")
        if doi:
            by_doi.setdefault(normalize_doi(doi).lower(), []).append(e)
        title = e["fields"].get("title")
        if title:
            nt = normalize_title(title)
            if len(nt) > 10:
                by_title.setdefault(nt, []).append(e)
    for k, es in by_key.items():
        if len(es) > 1:
            lines = ", ".join("L%d" % e["line"] for e in es)
            out.append(("ERROR", "dupkey", "duplicate key '%s' (%s) - BibTeX silently keeps the first" % (es[0]["key"], lines)))
    for doi, es in by_doi.items():
        if len(es) > 1:
            keys = ", ".join(e["key"] for e in es)
            out.append(("WARN", "dupdoi", "same DOI under %d keys: %s" % (len(es), keys)))
    for nt, es in by_title.items():
        keys = {e["key"] for e in es}
        if len(keys) > 1:
            out.append(("WARN", "duptitle", "near-identical title under keys: %s" % ", ".join(sorted(keys))))
    return out


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def analyse(paths):
    all_entries = []
    file_findings = []
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            file_findings.append((path, None, [("ERROR", "io", "cannot read: %s" % exc)]))
            continue
        entries = parse_bib(text)
        for e in entries:
            e["file"] = path
        all_entries.extend(entries)
        for e in entries:
            findings = check_entry(e)
            if findings:
                file_findings.append((path, e, findings))
    cross = cross_checks(all_entries)
    return all_entries, file_findings, cross


def severity_counts(file_findings, cross):
    c = {"ERROR": 0, "WARN": 0, "STYLE": 0}
    for _, _, fs in file_findings:
        for sev, _, _ in fs:
            c[sev] = c.get(sev, 0) + 1
    for sev, _, _ in cross:
        c[sev] = c.get(sev, 0) + 1
    return c


def print_human(entries, file_findings, cross):
    print("BibTeX integrity  (%d entries across %d file(s))" % (
        len(entries), len({e.get("file") for e in entries})))
    if cross:
        print("\nCross-entry")
        for sev, code, msg in cross:
            print("  [%-5s] %-9s %s" % (sev, code, msg))
    cur = None
    for path, e, findings in file_findings:
        if e is None:
            print("\n%s" % path)
            for sev, code, msg in findings:
                print("  [%-5s] %-9s %s" % (sev, code, msg))
            continue
        head = "%s  @%s{%s}  (L%d)" % (path, e["type"], e["key"] or "?", e["line"])
        if head != cur:
            print("\n" + head)
            cur = head
        for sev, code, msg in findings:
            print("  [%-5s] %-9s %s" % (sev, code, msg))
    c = severity_counts(file_findings, cross)
    print("\nbib-integrity: %d errors, %d warnings, %d style across %d entries"
          % (c["ERROR"], c["WARN"], c["STYLE"], len(entries)))


def main(argv):
    paths = [a for a in argv if not a.startswith("--")]
    as_json = "--json" in argv
    if not paths:
        sys.stderr.write("usage: python bib-integrity.py [--json] file1.bib [file2.bib ...]\n")
        return 64
    entries, file_findings, cross = analyse(paths)
    if as_json:
        payload = {
            "n_entries": len(entries),
            "cross": [{"severity": s, "code": c, "message": m} for s, c, m in cross],
            "entries": [
                {
                    "file": e.get("file") if e else p,
                    "key": e["key"] if e else None,
                    "type": e["type"] if e else None,
                    "line": e["line"] if e else None,
                    "findings": [{"severity": s, "code": c, "message": m} for s, c, m in fs],
                }
                for p, e, fs in file_findings
            ],
            "counts": severity_counts(file_findings, cross),
        }
        print(json.dumps(payload, indent=2))
    else:
        print_human(entries, file_findings, cross)
    c = severity_counts(file_findings, cross)
    return 1 if c["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
