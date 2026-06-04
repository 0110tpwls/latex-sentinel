#!/usr/bin/env python
# ai-metrics.py - stylometric AI-signal metrics for LaTeX prose.
#
# Computes the distributional ("structure, not vocabulary") signals that the
# phrase catalog cannot see. Adapted from the 7-metric scheme popularised by
# PasqualePillitteri/humanAIzer, but RE-TUNED for academic prose (which is
# legitimately more formal and less "bursty" than the blog text those
# thresholds were calibrated on) and given a transparent composite formula
# (neither humanAIzer nor Aboudjem/humanizer-skill published one).
#
# Usage:
#   python ai-metrics.py file1.tex [file2.tex ...]
#   python ai-metrics.py --json file1.tex      # machine-readable
#
# Stdlib only (re, math, gzip, sys, json, statistics, collections) so it runs
# anywhere a TeX distribution's Python is present, same constraint as
# cite-check. On systems whose binary is python3, substitute python3.
#
# IMPORTANT: every metric is a STYLE SMELL, not a verdict. A high score means
# "reads structurally like AI", which a careful human can also produce. Always
# report the raw value next to the flag so the author can judge.

import sys
import re
import math
import gzip
import json
import statistics
from collections import Counter

# --------------------------------------------------------------------------
# LaTeX -> prose (best-effort; good enough for word/sentence statistics)
# --------------------------------------------------------------------------

# Environments whose *contents* are not prose and must be removed wholesale.
NON_PROSE_ENVS = (
    "equation", "align", "alignat", "gather", "multline", "displaymath",
    "math", "eqnarray", "figure", "figure*", "table", "table*", "tabular",
    "tabularx", "lstlisting", "verbatim", "Verbatim", "minted", "tikzpicture",
    "algorithm", "algorithmic", "array", "bmatrix", "pmatrix", "matrix",
)

# Commands that carry NO prose payload (drop the whole call, braces included).
DROP_COMMANDS = (
    "cite", "citep", "citet", "citeauthor", "citeyear", "citealp", "citealt",
    "parencite", "textcite", "footcite", "autocite", "nocite", "Cite",
    "ref", "eqref", "cref", "Cref", "autoref", "pageref", "label",
    "includegraphics", "input", "include", "bibliography", "bibliographystyle",
    "usepackage", "documentclass", "url", "href",
)


def strip_latex(text):
    """Reduce a .tex source to readable prose for statistical analysis."""
    # 1. Strip line comments (% not preceded by a backslash).
    text = re.sub(r"(?<!\\)%.*", "", text)

    # 2. Remove non-prose environments and everything inside them.
    for env in NON_PROSE_ENVS:
        e = re.escape(env)
        text = re.sub(
            r"\\begin\{" + e + r"\}.*?\\end\{" + e + r"\}",
            " ",
            text,
            flags=re.DOTALL,
        )

    # 3. Remove inline / display math.
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.DOTALL)
    text = re.sub(r"\$.*?\$", " ", text, flags=re.DOTALL)
    text = re.sub(r"\\\[.*?\\\]", " ", text, flags=re.DOTALL)
    text = re.sub(r"\\\(.*?\\\)", " ", text, flags=re.DOTALL)

    # 4. Drop payload-free commands together with their {...} / [...] args.
    for cmd in DROP_COMMANDS:
        text = re.sub(r"\\" + cmd + r"\*?\s*(\[[^\]]*\])?\s*(\{[^{}]*\})?", " ", text)

    # 5. Remove remaining \begin{...}/\end{...} markers (keep the body text).
    text = re.sub(r"\\(begin|end)\s*\{[^{}]*\}", " ", text)

    # 6. Strip remaining control sequences but KEEP the text inside their
    #    braces (so \textbf{word} -> word). Iterate to handle nesting.
    for _ in range(3):
        text = re.sub(r"\\[a-zA-Z]+\*?\s*(\[[^\]]*\])?", " ", text)
    text = text.replace("{", " ").replace("}", " ")

    # 7. Collapse whitespace.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*", "\n\n", text)
    return text.strip()


# --------------------------------------------------------------------------
# Tokenisation
# --------------------------------------------------------------------------

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")
# Sentence terminator followed by whitespace + a capital/quote/EOL, so that
# "e.g." and decimals like "0.85" don't split.
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])[\"')\]]?\s+(?=[A-Z(\"'\[])")


def words(text):
    return WORD_RE.findall(text)


def sentences(text):
    parts = [s.strip() for s in SENT_SPLIT_RE.split(text)]
    return [s for s in parts if len(words(s)) >= 1]


# --------------------------------------------------------------------------
# The seven metrics
# --------------------------------------------------------------------------

CONNECTIVES = {
    "however", "moreover", "furthermore", "additionally", "consequently",
    "therefore", "thus", "hence", "nevertheless", "nonetheless", "accordingly",
    "subsequently", "meanwhile", "likewise", "similarly", "conversely",
    "indeed", "notably", "importantly", "ultimately", "overall", "firstly",
    "secondly", "thirdly", "finally", "essentially", "specifically",
}
# Multiword connectives matched separately.
CONNECTIVE_PHRASES = (
    "in addition", "in conclusion", "in summary", "on the other hand",
    "as a result", "for instance", "for example", "in particular",
    "in other words", "that being said", "by contrast", "in contrast",
)

STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "and", "or", "for", "on", "with",
    "as", "by", "at", "from", "that", "this", "is", "are", "was", "were",
    "be", "it", "its", "we", "our", "their", "these", "those", "which",
}


def m_burstiness(sents):
    """Coefficient of variation of sentence length. AI -> low (uniform)."""
    lens = [len(words(s)) for s in sents]
    lens = [n for n in lens if n > 0]
    if len(lens) < 2:
        return None, None, None
    mean = statistics.mean(lens)
    sd = statistics.pstdev(lens)
    cv = sd / mean if mean else 0.0
    return cv, mean, sd


def m_ttr(wlist):
    """Mean type-token ratio over 100-word windows."""
    if not wlist:
        return None
    lower = [w.lower() for w in wlist]
    ratios = []
    for i in range(0, len(lower), 100):
        win = lower[i:i + 100]
        if len(win) >= 30:  # ignore a tiny trailing window
            ratios.append(len(set(win)) / len(win))
    if not ratios:
        return len(set(lower)) / len(lower)
    return statistics.mean(ratios)


def m_bigram_repetition(wlist):
    """Content-word bigrams repeated >= 3 times. Returns (count, examples)."""
    content = [w.lower() for w in wlist if w.lower() not in STOPWORDS]
    bigrams = Counter(zip(content, content[1:]))
    repeated = [(bg, c) for bg, c in bigrams.items() if c >= 3]
    repeated.sort(key=lambda x: -x[1])
    examples = [(" ".join(bg), c) for bg, c in repeated[:5]]
    return len(repeated), examples


def m_connective_density(text, wlist):
    """Connectives per 100 words."""
    n = len(wlist)
    if n == 0:
        return None
    lower = " " + text.lower() + " "
    count = 0
    for w in (x.lower() for x in wlist):
        if w in CONNECTIVES:
            count += 1
    for phrase in CONNECTIVE_PHRASES:
        count += lower.count(" " + phrase + " ")
    return 100.0 * count / n


def m_opener_diversity(sents):
    """Opener repetition signals.

    Returns (first2_ratio, top_first_word, top_first_word_share):
    - first2_ratio: fraction of sentences with a unique first-two-words opener
      (humanAIzer's metric). Lenient: "The X" / "The Y" count as distinct.
    - top_first_word_share: fraction of sentences opening with the single most
      common first word. Catches the "The...The...The..." monotony that the
      first-two-words ratio misses.
    """
    first2 = []
    firsts = []
    for s in sents:
        w = words(s)
        if not w:
            continue
        firsts.append(w[0].lower())
        first2.append((w[0].lower(), w[1].lower()) if len(w) >= 2 else (w[0].lower(),))
    if not first2:
        return None, None, None
    ratio = len(set(first2)) / len(first2)
    top_word, top_count = Counter(firsts).most_common(1)[0]
    return ratio, top_word, top_count / len(firsts)


PUNCT_CLASSES = {
    ".": ".", "!": ".", "?": "?", ",": ",", ";": ";", ":": ":",
    "(": "()", ")": "()", "[": "()", "]": "()",
    "—": "-", "–": "-", "-": "-",
}


def m_punct_entropy(text):
    """Shannon entropy (bits) of the punctuation-class distribution."""
    counts = Counter()
    for ch in text:
        cls = PUNCT_CLASSES.get(ch)
        if cls:
            counts[cls] += 1
    total = sum(counts.values())
    if total == 0:
        return None
    h = 0.0
    for c in counts.values():
        p = c / total
        h -= p * math.log2(p)
    return h


def m_compressibility(text):
    """gzip ratio = compressed/original. Low -> repetitive/formulaic (AI)."""
    raw = text.encode("utf-8", "ignore")
    if len(raw) < 200:
        return None
    comp = gzip.compress(raw, 9)
    return len(comp) / len(raw)


# --------------------------------------------------------------------------
# Composite (academic-tuned). Each sub-score is 0 (human) .. 1 (AI-like).
# We fold only the four ROBUST metrics into the headline; the rest are
# reported as informational because they are noisy on short / formal text.
# --------------------------------------------------------------------------

def _lin(x, human, ai):
    """Map x to 0..1 where x>=human -> 0 and x<=ai -> 1 (or reversed)."""
    if x is None:
        return None
    if human < ai:  # higher x = more AI
        if x <= human:
            return 0.0
        if x >= ai:
            return 1.0
        return (x - human) / (ai - human)
    else:  # higher x = more human
        if x >= human:
            return 0.0
        if x <= ai:
            return 1.0
        return (human - x) / (human - ai)


def composite(metrics):
    # Academic-tuned breakpoints (human-tolerant end first, AI end second).
    burst = _lin(metrics["burstiness"], 0.55, 0.30)        # CV: <0.30 very uniform
    punct = _lin(metrics["punct_entropy"], 1.55, 0.85)     # bits: <0.85 only . and ,
    # Opener AI-ness = worse of (low first-2-word diversity) and (one first
    # word dominating openings, e.g. "The...The...The...").
    opener_a = _lin(metrics["opener_diversity"], 0.70, 0.40)   # frac unique openers
    opener_b = _lin(metrics.get("opener_top_share"), 0.30, 0.60)  # dominant first word
    opener = max(v for v in (opener_a, opener_b) if v is not None) \
        if (opener_a is not None or opener_b is not None) else None
    conn = _lin(metrics["connective_density"], 0.70, 2.00) # per 100 words

    parts = [(burst, 0.35), (punct, 0.25), (opener, 0.20), (conn, 0.20)]
    parts = [(v, w) for v, w in parts if v is not None]
    if not parts:
        return None
    wsum = sum(w for _, w in parts)
    score = sum(v * w for v, w in parts) / wsum
    return round(100 * score)


def band(score):
    if score is None:
        return "n/a"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


# --------------------------------------------------------------------------
# Per-file analysis
# --------------------------------------------------------------------------

def analyse(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    prose = strip_latex(raw)
    wlist = words(prose)
    sents = sentences(prose)

    cv, mean_len, sd_len = m_burstiness(sents)
    od_ratio, od_topword, od_topshare = m_opener_diversity(sents)
    m = {
        "file": path,
        "n_words": len(wlist),
        "n_sentences": len(sents),
        "burstiness": cv,
        "mean_sentence_len": mean_len,
        "sd_sentence_len": sd_len,
        "ttr": m_ttr(wlist),
        "connective_density": m_connective_density(prose, wlist),
        "opener_diversity": od_ratio,
        "opener_top_word": od_topword,
        "opener_top_share": od_topshare,
        "punct_entropy": m_punct_entropy(prose),
        "compressibility": m_compressibility(prose),
    }
    rep_count, rep_examples = m_bigram_repetition(wlist)
    m["bigram_repeats"] = rep_count
    m["bigram_examples"] = rep_examples
    m["score"] = composite(m)
    m["band"] = band(m["score"])
    m["reliable"] = m["n_sentences"] >= 8 and m["n_words"] >= 200
    return m


def fmt(x, nd=2):
    return "n/a" if x is None else ("%.*f" % (nd, x))


def print_human(results):
    for m in results:
        print("=" * 64)
        print("%s   (%d words, %d sentences)" % (m["file"], m["n_words"], m["n_sentences"]))
        if not m["reliable"]:
            print("  ! too little prose for reliable stylometry (need >=8 sentences, >=200 words)")
        print("  Stylometric AI-signal: %s / 100   [%s]" % (fmt(m["score"], 0), m["band"]))
        print("  --- metrics (raw value : reading) ---")
        cv = m["burstiness"]
        print("  burstiness (sent-len CV) : %s   %s" % (
            fmt(cv), "uniform/AI-like" if cv is not None and cv < 0.35 else "ok"))
        print("     mean sent len %s words (sd %s)" % (fmt(m["mean_sentence_len"], 1), fmt(m["sd_sentence_len"], 1)))
        pe = m["punct_entropy"]
        print("  punctuation entropy      : %s b %s" % (
            fmt(pe), "  (only . and , -> AI-like)" if pe is not None and pe < 0.9 else ""))
        od = m["opener_diversity"]
        share = m.get("opener_top_share")
        share_note = ""
        if share is not None and share >= 0.4 and m.get("opener_top_word"):
            share_note = "  ('%s' opens %d%% of sentences)" % (
                m["opener_top_word"], round(100 * share))
        print("  opener diversity         : %s%s" % (fmt(od), share_note))
        cd = m["connective_density"]
        print("  connective density       : %s /100w %s" % (
            fmt(cd), "(transition overuse)" if cd is not None and cd > 1.3 else ""))
        print("  type-token ratio (100w)  : %s   (informational)" % fmt(m["ttr"]))
        print("  gzip compressibility     : %s   (informational; low=repetitive)" % fmt(m["compressibility"], 3))
        print("  repeated content bigrams : %d" % m["bigram_repeats"])
        for bg, c in m["bigram_examples"]:
            print("       '%s' x%d" % (bg, c))
    print("=" * 64)
    # One parseable summary line per the skill's convention.
    hi = sum(1 for m in results if m["band"] == "HIGH")
    md = sum(1 for m in results if m["band"] == "MEDIUM")
    print("ai-metrics: %d HIGH, %d MEDIUM, %d files" % (hi, md, len(results)))


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    as_json = "--json" in argv
    if not args:
        sys.stderr.write("usage: python ai-metrics.py [--json] file1.tex [file2.tex ...]\n")
        return 64
    results = []
    for path in args:
        try:
            results.append(analyse(path))
        except OSError as e:
            sys.stderr.write("ai-metrics: cannot read %s: %s\n" % (path, e))
    if not results:
        return 66
    if as_json:
        print(json.dumps(results, indent=2))
    else:
        print_human(results)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
