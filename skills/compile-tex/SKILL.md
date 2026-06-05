---
name: compile-tex
description: Compile a LaTeX paper with latexmk and surface errors clearly. Use when the user invokes /latex-sentinel:compile-tex, asks to "compile the paper", "build the PDF", or as step 1 of the review pipeline. Parses the .log for the meaningful error and warning lines instead of dumping everything.
argument-hint: "[path-to-main.tex]"
allowed-tools: Bash Read Glob
---

# Compile LaTeX

## Locate the main file

If `$ARGUMENTS` is a path to a `.tex` file, use it. Otherwise find it: `Glob` for `**/*.tex`, then `Grep` for `\documentclass` and pick the file that has it. If multiple candidates, ask the user.

## Pre-flight

Verify the toolchain:
```bash
command -v latexmk >/dev/null 2>&1 || command -v pdflatex >/dev/null 2>&1 || {
  echo "No LaTeX toolchain on PATH. Run /latex-sentinel:set-up to check your toolchain"
  echo "and see how to install one (TinyTeX is the lightweight, no-sudo option; TeX Live"
  echo "is the full distribution), then restart Claude Code."
  exit 2
}
```

If this fails, don't try to compile — tell the user to run `/latex-sentinel:set-up`, which checks the toolchain, shows how to install what's missing (TinyTeX or TeX Live), and records the engine choice in `.latex-sentinel.json`.

## Read the project config

If the project was set up with `/latex-sentinel:set-up`, a `.latex-sentinel.json` records exactly how to build this paper (engine + command). Prefer it over guessing:

```bash
PAPER_DIR=$(dirname "$MAIN_TEX")
CFG_CMD="$(python "${CLAUDE_PLUGIN_ROOT}/skills/set-up/scripts/read-config.py" \
            --field compileCommand --dir "$PAPER_DIR" 2>/dev/null)"
# (substitute python3 where that's the binary; read-config.py searches parent dirs too)
```

If `CFG_CMD` is non-empty, run **that** command with the `.tex` path appended instead of the default below. If it's empty (no config), fall back to auto-detecting `latexmk`/`pdflatex` as before — the config is an optimisation, not a requirement.

**Run the configured command through `sh -c`, not as a bare `$CFG_CMD`.** `compileCommand` is a multi-word string (`latexmk -pdf …`); under `zsh` (the default macOS shell) an unquoted `$CFG_CMD` is **not** word-split, so `$CFG_CMD "$MAIN_TEX"` tries to exec a binary literally named "latexmk -pdf …" and fails with "command not found". Use a POSIX shell to split it:

## Compile

Prefer the configured command, else `latexmk` (handles bibtex/biber/rerun automatically):

```bash
# configured (zsh-safe — sh -c performs the word-splitting):
sh -c "$CFG_CMD \"$MAIN_TEX\""
# default when there is no config:
latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error "$MAIN_TEX"
```

Fallback to manual passes if neither a config command nor `latexmk` is available. **Do not use bash's `${VAR%.tex}` parameter expansion** — it breaks under PowerShell, `dash`, and plain `sh`. Use `basename`/`dirname` instead:

```bash
PAPER_DIR=$(dirname "$MAIN_TEX")
BASENAME=$(basename "$MAIN_TEX" .tex)
(
  cd "$PAPER_DIR" || exit 1
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$BASENAME.tex"
  bibtex   "$BASENAME"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$BASENAME.tex"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$BASENAME.tex"
)
```

Capture the exit code.

## Parse errors

On failure, read the `.log` file (compute its path the same portable way: `LOG="$PAPER_DIR/$BASENAME.log"`) and extract:

- Lines starting with `!` (TeX error markers).
- The next 3 lines after each `!` (TeX context).
- Lines containing `LaTeX Error:` or `Undefined control sequence`.
- Lines with `l.\d+` (line numbers).
- `Overfull \hbox` / `Underfull \hbox` warnings (collect counts; show top 5).
- Missing reference / citation warnings: `Reference '...' on page ... undefined` and `Citation '...' on page ... undefined`.

Surface these to the user in a compact, scannable form:

```
COMPILE FAILED  (exit 1)

errors:
  paper.tex:142  ! Undefined control sequence  \citepp
  paper.tex:267  ! LaTeX Error: \begin{align} on input line 264 ended by \end{equation}.

undefined refs:    3   (fig:overview, tab:results-2, sec:appendix-b)
undefined cites:   2   (smith2024, jones2023)
overfull hboxes:   7   (worst: 18.4pt on page 5)
```

Then propose `Edit` calls for fixable errors (typos in `\cite` keys, missing `\end{...}`). Don't propose blind fixes for `Undefined control sequence` errors — those usually mean a missing `\usepackage`. Tell the user which package is likely.

## Success

On success, print:
```
COMPILE OK  paper.pdf  (N pages, M warnings)
```

And summarise warnings if any.
