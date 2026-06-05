#!/usr/bin/env python
# page-count.py - report a paper's total page count and a per-section breakdown.
#
# Borrowed in spirit from TexGuardian's /page_count. Total pages come from
# pdfinfo (Poppler) when available, with a pure-stdlib PDF fallback. The
# per-section breakdown is parsed from the .toc LaTeX writes when the document
# uses \tableofcontents; without a .toc only the total is reported.
#
# Usage:
#   python page-count.py paper.pdf [--limit N] [--toc paper.toc]
#   python page-count.py paper.pdf --json
#
# Exit codes: 0 ok (even if over limit — the overage is reported, not fatal),
# 2 the PDF could not be found or its page count could not be determined.
# On systems whose binary is python3, substitute python3. Stdlib only.

import argparse
import json
import os
import re
import shutil
import subprocess
import sys


def total_pages_pdfinfo(pdf):
    """Authoritative total via pdfinfo; None if pdfinfo is unavailable/failed."""
    exe = shutil.which("pdfinfo")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, pdf], capture_output=True, text=True,
                             timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"^Pages:\s*(\d+)", out.stdout, re.MULTILINE)
    return int(m.group(1)) if m else None


def total_pages_fallback(pdf):
    """Best-effort count without Poppler. Counts /Type/Page objects in the raw
    bytes — accurate for uncompressed PDFs; may undercount when pages live in
    object streams, so it is only a fallback and is flagged as approximate."""
    try:
        with open(pdf, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    # /Count in the page tree root is most reliable when present.
    counts = [int(m) for m in re.findall(rb"/Count\s+(\d+)", data)]
    if counts:
        return max(counts)
    pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
    return pages or None


_LEVEL_ORDER = {"part": 0, "chapter": 1, "section": 2, "subsection": 3,
                "subsubsection": 4, "paragraph": 5, "subparagraph": 6}

# \contentsline {section}{\numberline {1}Introduction}{1}{section.1}%
_TOC_RE = re.compile(
    r"\\contentsline\s*\{([^}]+)\}\{(.*)\}\{([^{}]+)\}\{[^{}]*\}\s*%?\s*$")


def clean_title(raw):
    raw = re.sub(r"\\numberline\s*\{([^}]*)\}", r"\1 ", raw)
    raw = re.sub(r"\\[a-zA-Z]+\s*", "", raw)      # drop other latex commands
    raw = raw.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", raw).strip()


def parse_toc(toc_path):
    """Return [{level, title, start, depth}] for section-level entries."""
    entries = []
    try:
        with open(toc_path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return entries
    for line in lines:
        m = _TOC_RE.match(line.strip())
        if not m:
            continue
        level, title, page = m.group(1), m.group(2), m.group(3).strip()
        if not page.isdigit():
            continue  # roman front-matter pages etc.; skip from the span math
        entries.append({"level": level, "title": clean_title(title),
                        "start": int(page), "depth": _LEVEL_ORDER.get(level, 9)})
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--limit", type=int, default=None,
                    help="venue page limit; reports overage if exceeded")
    ap.add_argument("--toc", default=None,
                    help="path to the .toc (default: sibling of the PDF)")
    ap.add_argument("--max-depth", type=int, default=3,
                    help="deepest toc level to show (2=section, 3=subsection)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.pdf):
        print("page-count: PDF not found: %s" % args.pdf, file=sys.stderr)
        return 2

    total = total_pages_pdfinfo(args.pdf)
    approximate = False
    if total is None:
        total = total_pages_fallback(args.pdf)
        approximate = total is not None
    if total is None:
        print("page-count: could not determine page count (install Poppler's "
              "pdfinfo for a reliable count).", file=sys.stderr)
        return 2

    toc_path = args.toc or os.path.splitext(args.pdf)[0] + ".toc"
    entries = parse_toc(toc_path) if os.path.isfile(toc_path) else []

    # Compute per-section spans from consecutive start pages (top-level only for
    # the span math; nested entries show their start page).
    sections = []
    top = [e for e in entries if e["depth"] <= args.max_depth]
    for i, e in enumerate(top):
        nxt = top[i + 1]["start"] if i + 1 < len(top) else total + 1
        span = max(0, nxt - e["start"])
        sections.append({**e, "pages": span})

    if args.json:
        print(json.dumps({"total": total, "approximate": approximate,
                          "limit": args.limit, "sections": sections}, indent=2))
        return 0

    tag = " (approximate — pdfinfo not found)" if approximate else ""
    print("Page count: %d page%s%s" % (total, "" if total == 1 else "s", tag))
    if args.limit is not None:
        if total > args.limit:
            print("  OVER the %d-page limit by %d." % (args.limit, total - args.limit))
        else:
            print("  within the %d-page limit (%d to spare)."
                  % (args.limit, args.limit - total))

    if sections:
        print("\nBy section:")
        width = max(len(s["title"]) for s in sections) if sections else 0
        width = min(width, 50)
        for s in sections:
            indent = "  " * (s["depth"] - min(x["depth"] for x in sections))
            title = (s["title"][:47] + "...") if len(s["title"]) > 50 else s["title"]
            print("  p.%-4d %s%-*s %d pp." % (s["start"], indent, width, title, s["pages"]))
    elif os.path.isfile(toc_path):
        print("\n(.toc found but no section entries parsed.)")
    else:
        print("\n(No .toc — add \\tableofcontents and recompile for a per-section "
              "breakdown, or this class doesn't emit one.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
