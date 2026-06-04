---
name: visual-polish
description: Visual polish loop for LaTeX papers. Renders the compiled PDF page-by-page and uses the vision model to find layout problems that text-only analysis can't see — overfull boxes that overflow, figures floating to the wrong section, broken page breaks, equation overflow into the margin, orphaned headings, citation rendering artefacts ([?] / ??). Use when the user invokes /latex-sentinel:visual-polish, asks to "check the rendered PDF", or as step 6 of the review pipeline.
argument-hint: "[path-to-pdf]"
allowed-tools: Bash Read Edit Glob
---

# Visual Polish Loop

This skill is the eyes of the pipeline. The text-based checks have already run; now we look at the actual rendered output and catch problems that only show up in the PDF.

## Setup

Resolve the PDF:
1. If `$ARGUMENTS` is a path, use it.
2. Otherwise look for `*.pdf` in the current directory that has a matching `*.tex`. If multiple candidates, prefer the one whose `.tex` contains `\documentclass`.
3. If no PDF exists, compile first (`latexmk -pdf -interaction=nonstopmode "$MAIN_TEX"`).

Set `PDF=<resolved-path>`.

## Render pages

Run the helper script. Reference it through `${CLAUDE_PLUGIN_ROOT}` — the variable Claude Code expands to this plugin's actual install directory, wherever it landed (a local dev folder or the marketplace cache). Do **not** hardcode `$HOME/.claude/plugins/...`; that only happens to work for a manual dev install and breaks for marketplace installs:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/visual-polish/scripts/render-pdf.sh" \
     "$PDF" .latex-sentinel/pages 150 30
```

If `${CLAUDE_PLUGIN_ROOT}` is somehow unset in your shell, fall back to the canonical absolute path shown on the skill's `Base directory:` line when this skill is loaded.

Arguments: `<pdf> <out-dir> <dpi> <max-pages>`. Defaults: dpi=150, max-pages=30.

The script writes `page-001.png`, `page-002.png`, ... in the output directory and prints the final list of files on stdout. If `pdftoppm` is not installed, the script exits with code 2 and a hint — surface that to the user (install Poppler; see the plugin README) and stop.

**Non-standard `pdftoppm` location.** If the project's `.latex-sentinel.json` (written by `/latex-sentinel:setup-tex`) records a `tools.pdftoppm` path, prepend its directory to `PATH` before calling the renderer so the script finds it:

```bash
PP="$(python "${CLAUDE_PLUGIN_ROOT}/skills/setup-tex/scripts/read-config.py" --field tools.pdftoppm --dir "$(dirname "$PDF")" 2>/dev/null)"
[ -n "$PP" ] && PATH="$(dirname "$PP"):$PATH"
# (substitute python3 where that's the binary)
```

## Inspect each page

For each PNG produced, use the `Read` tool to load it as an image. The Read tool returns the image to you visually. For each page, look for:

1. **Overfull hbox overflow** — text running into the right margin, words spilling past the textblock.
2. **Underfull vbox** — large vertical gaps inside a column or page, usually before a forced page break.
3. **Misplaced floats** — a figure or table that appears far from its first reference, in the wrong section, or on a page by itself when it shouldn't be.
4. **Broken page breaks** — paragraph splits mid-equation, mid-table, mid-listing.
5. **Equation overflow** — math expression extending past the margin.
6. **Orphan / widow headings** — section heading at the very bottom of a page with body text starting on the next.
7. **Citation rendering bugs** — visible `[?]` `[??]` `??` or `\cite{key}` rendered literally, indicating a missing bib entry or compile order issue.
8. **Caption placement** — caption above a figure (TeX style usually wants below) or below a table (usually above), unless the document class explicitly overrides this.
9. **Cropping / clipping** — figure clipped at the page edge.
10. **Inconsistent typography** — a heading or paragraph in an obviously different size/weight/font from its peers.

For each finding, record: page number, what you saw, where in the source it likely originates, and a proposed fix.

## Propose fixes

For each finding, propose an `Edit` to the relevant `.tex` source. Common patches:

- **Overfull hbox** — break the line, add `\sloppy` locally, or rephrase. Often a long URL or compound noun. `\usepackage{microtype}` helps if not already loaded.
- **Misplaced float** — change `\begin{figure}[H]` placement specifier, or move the environment closer to its first `\ref`. Adding `\usepackage{float}` and using `[H]` forces here-placement.
- **Equation overflow** — add line breaks with `\\` and `\begin{split}` (amsmath), or switch to `multline`.
- **Citation `[?]`** — re-run `latexmk` (forgotten `bibtex`/`biber` pass) or fix the missing bib key. Surface to user — don't blindly patch.
- **Caption order** — move `\caption{}` above or below `\includegraphics` per the class's convention.

**Every change goes through `Edit`** so the unified diff is visible.

## Output

End with a structured report:

```
Visual polish: <N> pages inspected
  page 4: overfull hbox in §3.2 (line ~210 of methods.tex) → propose \sloppy + rephrase
  page 7: figure 3 floated to next page → propose [H] placement
  page 12: missing bib key 'smith2024' rendering as [?] → ACTION REQUIRED
  ...

Summary: <K> findings, <K_auto> auto-patched, <K_manual> need user input.
```

## Cleanup

After the loop, if the user is done, optionally remove the render directory:
```bash
rm -rf .latex-sentinel/pages
```

Ask first — don't delete silently.
