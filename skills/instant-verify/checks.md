# Instant-verify regex catalog

Reference patterns for the `instant-verify` skill. Each pattern is written for ripgrep / the `Grep` tool. Severity tags: `error`, `warning`, `style`.

## error

| ID | Pattern | Description |
| --- | --- | --- |
| E1 | `\\cite\{\s*\}` | Empty `\cite{}`. |
| E2 | `\\(ref|eqref|autoref|cref|Cref)\{\s*\}` | Empty cross-reference. |
| E3 | `(?<!\\)\?\?` | Unresolved `??` (LaTeX's "unknown ref" rendering, sometimes leaks into source). |
| E4 | `\\begin\{([a-zA-Z*]+)\}` vs `\\end\{\1\}` | Environment mismatch (count per file). **Strip TeX comments before counting** — a `\begin{}` inside a `%` comment must not count. |
| E5 | line-level: odd count of single `$` and zero `$$` | Mismatched inline-math delimiter. |

## warning

| ID | Pattern | Description |
| --- | --- | --- |
| W1 | `(?i)\b(TODO\|FIXME\|XXX\|HACK)\b` | Leftover marker. |
| W2 | `\\includegraphics\[[^\]]*width=\d+(\.\d+)?\s*(cm\|in\|pt\|mm)` | Hardcoded figure dimension; prefer `\linewidth`. |
| W3 | `\\cite\{[^}]+\}\s+[.,;]` | Period/comma after cite, separated by a space. Often wrong. |
| W4 | env-level: `\begin{figure}` without `\caption{` | Figure missing caption. |
| W5 | env-level: `\begin{figure}` without `\label{fig:` | Figure missing label. |
| W6 | cross-file: `\label{X}` with no `\(ref\|cref\|eqref\|autoref\|Cref)\{X\}` | Orphan label. |
| W7 | cross-file: `\cite{K}` where K not in any `@type{K,` of `**/*.bib` | Cite key not in bibliography. |
| W8 | `\\caption\{[^}]*\b(TODO\|FIXME)\b` | TODO inside caption. |
| W9 | `\\caption\{[^}]*[^.}\s]\s*\}` | Caption doesn't end with a period. |

## style

| ID | Pattern | Description |
| --- | --- | --- |
| S1 | `  ` (two spaces) | Double space. **Exclude lines inside `tabular`, `array`, `align`, `align*`, `aligned`, `equation`, `eqnarray`, `matrix`, `pmatrix`, `bmatrix`, `verbatim`, `lstlisting`, `minted` environments** — column alignment legitimately uses runs of spaces and dominates the false-positive count otherwise. |
| S2 | `,,\|,\.\|\.\.[^.]` | Double comma / `,.` / `..` (excluding `...`). |
| S3 | `[\x{2018}\x{2019}\x{201A}\x{201B}\x{201C}\x{201D}\x{201E}\x{201F}]` — i.e. only Unicode codepoints U+2018–U+201F (curly single/double quotes and their low/high variants). | Smart/curly quotes in source. **Do not flag ASCII backtick `` ` `` or apostrophe `'`** — those are LaTeX's correct opening/closing quote primitives (`` `` ``…`` '' ``). |
| S4 | `\\footnote\{[^}]+\}\s*[.,;]` | Footnote before punctuation. |
| S5 | `\w \\(cite\|ref\|autoref\|cref\|Cref)\{` | Missing `~` before cross-reference. |
| S6 | `\\eqref\{X\}` where label X is in a non-equation env | `\eqref` to non-equation. |
| S7 | `et\.al\.\|et al\b(?!\.)` | "et al" punctuation inconsistent (use `et al.\` with thin space if your style guide demands). |
| S8 | `(?m)^.{121,}$` | Source line longer than 120 chars (style only; some projects enforce wrap). |

## Notes

- Exclude `build/`, `out/`, `_minted-*`, `.texpadtmp` from the scan.
- A line is "inside a TeX comment" if `%` appears before the match without an escaping `\`. Detection heuristic: drop everything after the first un-escaped `%` on each line before applying patterns where comment context matters.
- For cross-file checks (W6, W7, W12) build the full set first, then diff. Don't rely on a single `Grep` call.
