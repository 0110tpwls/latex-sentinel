---
name: page-count
description: Report a LaTeX paper's total page count and a per-section breakdown, and check it against a venue page limit. Counts pages from the compiled PDF (pdfinfo, with a stdlib fallback) and maps pages to sections from the .toc. Use when the user invokes /latex-sentinel:page-count, asks "how many pages is this", "am I over the page limit", "which section is longest", or wants a length check before submission.
argument-hint: "[path-to-pdf | page-limit-number]"
allowed-tools: Bash Read Glob
---

# Page count & section breakdown

Length is a hard submission constraint — most venues reject over-limit papers without review. This skill answers "how long is it, where do the pages go, and am I under the limit?"

## Resolve inputs

Parse `$ARGUMENTS`:
- A `.pdf` path → use it.
- A bare number (e.g. `8`) → treat it as the **page limit**; still resolve the PDF automatically.
- Empty → find the PDF: a `*.pdf` in the current directory whose sibling `*.tex` contains `\documentclass`. If none exists, compile first with `/latex-sentinel:compile-tex` (a count needs a built PDF).

The per-section breakdown reads the `*.toc` next to the PDF (LaTeX writes it when the document uses `\tableofcontents`). No `.toc` → only the total is reported, which is fine.

## Run

Resolve the script through `${CLAUDE_PLUGIN_ROOT}` (never a hardcoded path):

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/page-count/scripts/page-count.py" "$PDF" [--limit N]
# (substitute python3 where that's the binary; add --json for machine output,
#  --max-depth 2 to show only top-level sections)
```

- **Total pages** come from `pdfinfo` (Poppler). If `pdfinfo` isn't installed, the script falls back to a pure-stdlib PDF read and labels the number *approximate* — suggest running `/latex-sentinel:set-up` to install Poppler for an exact count.
- **`--limit N`** reports whether the paper is over/under by how many pages. Pass the venue's limit when the user mentions one.
- **Section spans** are computed from consecutive `\contentsline` start pages in the `.toc`.

## Report

Surface the script's output directly, leading with the total and the limit verdict:

```
Page count: 9 pages
  OVER the 8-page limit by 1.

By section:
  p.1   Introduction        2 pp.
  p.3   Related Work        1 pp.
  p.4   Method              3 pp.
  p.7   Experiments         1 pp.
  p.8   Conclusion          1 pp.
```

When over the limit, suggest concrete, non-destructive levers (don't apply them silently): tighten figures (`width`), trim an overfull section flagged by the breakdown, move material to an appendix or supplement, adjust `\vspace`/float placement, or check the class's allowed margin/font options. Point at the longest section as the first place to look. Leave the actual cuts to the author — length trimming is a content decision.
