---
name: instant-verify
description: Fast regex-based verification of LaTeX source. Runs in seconds, no compilation required. Use when the user invokes /latex-sentinel:verify, asks to "check the .tex files", "find issues without compiling", or as part of the review pipeline. Reports malformed citations, leftover TODO markers, suspicious figure dimensions, missing labels, and other text-detectable issues.
argument-hint: "[glob, defaults to **/*.tex]"
allowed-tools: Bash Read Grep Glob
---

# Instant Verification

Run a fast pass over the LaTeX source files looking for issues that don't need compilation to detect. Output a grouped list of findings ready for the user (or the review pipeline) to act on.

## What to scan

If `$ARGUMENTS` is a glob, use it. Otherwise scan `**/*.tex` from the current directory. Always **exclude** common build directories: `build/`, `out/`, `_minted-*/`, `.texpadtmp/`.

## How to run

Use the `Grep` tool for every check below. Run all of them — they are cheap. Aggregate the hits into a single structured report.

The full catalog of regex checks with examples lives in [checks.md](checks.md). Read that file once at the start of the run if you need the exact patterns; the summary below covers the categories.

**Grep usage (Windows-safe).** Pass the search root as the absolute `path:` and the pattern as a leading-`**` `glob:` — for example `path: "C:/Users/PC/proj/paper", glob: "**/*.tex"`. Do **not** embed a relative subdirectory in the glob (e.g. `glob: "paper/**/*.tex"` will silently return no matches on Windows). To scope to a subdirectory, change `path:`, not `glob:`.

## Checks (run all)

### Severity: error

1. **Empty `\cite{}`** — pattern `\\cite\{\s*\}` — citation with no key.
2. **Empty `\ref{}` / `\eqref{}` / `\autoref{}`** — same shape.
3. **Unresolved `??` placeholders** — pattern `\?\?` outside comments.
4. **Mismatched math delimiters** — odd number of `$` on a line that isn't `$$`. Heuristic: flag lines with `$` count that is odd and `$$` count zero.
5. **`\begin{X}` without matching `\end{X}`** — count `\begin{(\w+)}` vs `\end{\1}` per file. **Strip TeX comments first** (drop everything after the first un-escaped `%` on each line) so a `\begin{...}` that lives inside a comment doesn't produce a false mismatch.

### Severity: warning

6. **TODO/FIXME/XXX markers** — `(?i)\b(TODO|FIXME|XXX|HACK)\b`. Exclude lines that are entirely inside `%` comments only if the marker is *outside* a TeX comment; otherwise still report (authors leave them on purpose, but submission shouldn't have them).
7. **Hardcoded figure dimensions** — `\\includegraphics\[[^\]]*width=\d+(\.\d+)?\s*(cm|in|pt|mm)` — prefer `width=...\linewidth`.
8. **`\cite{}` followed by a space then punctuation** — pattern `\\cite\{[^}]+\}\s+[.,;]` — usually the period should precede the cite.
9. **Figures without `\caption`** — for each `figure` environment, check the body contains `\caption{`. (You may need to read the file to confirm; grep gets you candidates.)
10. **Figures without `\label`** — same as above but for `\label{fig:`.
11. **Orphan labels** — `\label{X}` that no `\ref`/`\eqref`/`\autoref`/`\cref`/`\Cref` references. Cross-check across files.
12. **`\cite` of a key not present in any `.bib` file in the project** — collect bib keys with `Grep` over `**/*.bib` (`@\w+\{([^,]+),`), collect cited keys, diff.

### Severity: style

13. **Double spaces** — `  ` (two spaces) outside verbatim/listing blocks.
14. **Double commas / `,.` / `..` (not ellipsis)** — `,,|,\.| {2,}\.|\.\.[^.]`.
15. **Smart quotes / curly quotes in source** — `[‘’“”]` — TeX wants `` ` `` `'` `` `` `` `` `` for opening/closing.
16. **Footnote before punctuation** — pattern `\\footnote\{[^}]+\}\s*[.,;]` — usually footnote marks go after the punctuation.
17. **Non-breaking space missing before `\cite`/`\ref`** — pattern `\w \\(cite|ref|autoref|cref|Cref)\{` — convention is `~\cite{...}`.
18. **`\eqref` to a non-equation label** — heuristic only: `\eqref{X}` where `\label{X}` is inside `figure`/`table`.

## Output format

Print a structured summary, grouped by severity, like:

```
LaTeX-Sentinel instant verification

ERROR (3)
  paper.tex:142  empty \cite{} — cite key missing
  paper.tex:201  \begin{figure} with no matching \end{figure}
  intro.tex:88   unresolved ?? placeholder

WARNING (7)
  ...

STYLE (12)
  ...

Bib coverage: 47 cite keys, 49 .bib entries, 2 unused, 0 missing.
```

Always finish with a one-line summary the pipeline can parse: `verify: <E> errors, <W> warnings, <S> style`.

## When called from the review pipeline

Return the findings list as your final tool result (not file output). The pipeline will iterate over each finding and propose `Edit`s for the ones it can fix automatically.

## When called directly by the user

After the report, ask: "Want me to fix the auto-fixable ones (style + most warnings)? I'll propose each as a diff for your approval."
