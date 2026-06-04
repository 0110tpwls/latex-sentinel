#!/usr/bin/env bash
# render-pdf.sh — render a PDF to per-page PNGs for the visual-polish skill.
#
# Usage: render-pdf.sh <input.pdf> <output-dir> [dpi=150] [max-pages=30]
#
# Requires pdftoppm (from Poppler). Exits 2 with a hint if not installed.

set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "usage: render-pdf.sh <input.pdf> <output-dir> [dpi=150] [max-pages=30]" >&2
  exit 64
fi

INPUT="$1"
OUTDIR="$2"
DPI="${3:-150}"
MAX_PAGES="${4:-30}"

if [ ! -f "$INPUT" ]; then
  echo "render-pdf: input not found: $INPUT" >&2
  exit 66
fi

if ! command -v pdftoppm >/dev/null 2>&1; then
  echo "render-pdf: pdftoppm not found on PATH." >&2
  echo "  Install Poppler:" >&2
  echo "    Windows : winget install --id=oschwartz10612.Poppler   (or grab a release zip)" >&2
  echo "    macOS   : brew install poppler" >&2
  echo "    Debian  : sudo apt-get install poppler-utils" >&2
  exit 2
fi

mkdir -p "$OUTDIR"
# Wipe stale renders so page count is accurate.
rm -f "$OUTDIR"/page-*.png

# pdftoppm: -r DPI, -png, -f first, -l last. Use -f 1 -l MAX_PAGES; pdftoppm
# silently caps at the document length so we don't need to count pages first.
pdftoppm -r "$DPI" -png -f 1 -l "$MAX_PAGES" "$INPUT" "$OUTDIR/page" >/dev/null

# pdftoppm produces page-1.png, page-2.png, ... — rename to zero-padded so
# the lexical sort matches page order for the >=10-page case.
for f in "$OUTDIR"/page-*.png; do
  base="$(basename "$f")"
  num="${base#page-}"
  num="${num%.png}"
  # Force base-10: "08"/"09" are invalid octal literals, causing printf to fail.
  printf -v padded "%03d" "$((10#$num))"
  mv -f "$f" "$OUTDIR/page-${padded}.png"
done

# Final listing for the skill to consume.
ls "$OUTDIR"/page-*.png | sort
