---
name: set-up
description: Check the LaTeX toolchain for this project and report what's installed vs missing — a "doctor" for latex-sentinel. Detects latexmk, the PDF engines (pdflatex/xelatex/lualatex), bibtex/biber, pdftoppm (Poppler), and python; for anything missing it prints the exact, copy-pasteable setup instructions (TinyTeX for a no-sudo lightweight install, or full TeX Live) and asks you to restart Claude Code so the new tools land on PATH. When the toolchain is present it writes a project-level .latex-sentinel.json so compile-tex and the review pipeline know how to build the paper. It never installs anything itself (installing TeX Live/MacTeX needs sudo) — it tells you how. Use when the user invokes /latex-sentinel:set-up, asks to "set up", "check my latex setup", "what do I need to install", "doctor", "is my toolchain ready", or when compile-tex reports no toolchain on PATH.
argument-hint: "[engine, e.g. latexmk | xelatex | tectonic]"
allowed-tools: Bash Read Edit AskUserQuestion Glob
---

# Set up / check the LaTeX toolchain

This skill is the **doctor** for latex-sentinel. It does **not** install anything — installing a full TeX distribution needs `sudo`, and silently running privileged installers is the wrong default. Instead it: **checks → advises → (you install + restart) → writes config.**

## Step 1 — Check what's installed

Run the detector (resolve it through `${CLAUDE_PLUGIN_ROOT}`, never a hardcoded path):

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/set-up/scripts/detect-tex.sh"
```

It prints one JSON object: the OS, every tool's `{present, path, version}`, and which package managers exist. Parse it and present a compact **doctor report** with a check or cross per tool, grouped by what each unlocks:

```
latex-sentinel set-up — toolchain check (macOS)

Compile (compile-tex, review)
  ✓ latexmk      4.88
  ✓ pdflatex     TeX Live 2026
  ✓ bibtex / biber
Visual polish
  ✓ pdftoppm     Poppler 24.x
Scripts (cite-check online, ai stylometry, page-count)
  ✓ python3      3.11

All tools found — you're good to go.   (or:  Missing: pdftoppm)
```

Classify the result:
- **Everything needed is present** → skip to Step 3 (write config). Say the toolchain is ready.
- **Something is missing** → go to Step 2 and advise. The minimum to compile is *one* PDF engine (latexmk is strongly preferred because it reruns bibtex/biber). `pdftoppm` is only needed for `visual-polish`; `python`/`python3` only for the helper scripts.

## Step 2 — Advise what to install (do NOT install it yourself)

For each missing piece, print the exact commands and let the **user** run them. Never run `sudo`, `brew install --cask`, or a curl-pipe-sh installer on the user's behalf — show it, explain it, and stop.

### LaTeX is missing — offer two clear choices

Use **AskUserQuestion** to let the user pick, then print the matching commands. The two options (mirroring TexGuardian's guidance):

- **TinyTeX — lightweight, no sudo (recommended for most).** ~200 MB, installs to the home dir, pulls extra packages on demand. Best when the user can't or won't use `sudo`.
- **Full TeX Live / MacTeX — everything, needs sudo.** Multi-GB; no missing-package surprises. Best for heavy or unusual document classes.

```bash
# Option A — TinyTeX (no sudo)
curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh
# add it to PATH for this and future shells:
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"   # macOS
export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"              # Linux
# install latexmk + the packages a typical paper needs:
tlmgr install latexmk booktabs natbib hyperref pgfplots xcolor float \
              geometry amsmath amssymb graphicx tikz caption subcaption microtype

# Option B — full TeX Live (needs sudo)
brew install --cask mactex-no-gui     # macOS  (GUI-less MacTeX)
sudo apt install texlive-full         # Debian/Ubuntu
sudo dnf install texlive-scheme-full  # Fedora
# Windows: install MiKTeX or TeX Live from their installers (then restart CC)
```

Tell the user to add the `export PATH=...` line to their shell profile (`~/.zshrc` / `~/.bashrc`) so it persists.

### Poppler is missing (only blocks `visual-polish`)

```bash
brew install poppler                  # macOS
sudo apt-get install poppler-utils    # Debian/Ubuntu
winget install --id=oschwartz10612.Poppler   # Windows
```

### python is missing (only blocks the helper scripts)

`python3` ships with macOS and most Linux. On Windows, install from python.org. No `pip install` is ever needed — the scripts are stdlib-only.

### Then: prompt to restart Claude Code

Newly installed tools won't be on the PATH of the **already-running** Claude Code process. After the user installs, tell them clearly:

> Installed something? **Restart Claude Code** (quit and reopen, or start a new session) so the new binaries are picked up, then run `/latex-sentinel:set-up` again to confirm and write the config.

Do not try to compile in the same session right after advising an install — the PATH won't have updated.

## Step 3 — Write the project config (when the toolchain is ready)

Once an engine is present, record how this paper builds in `.latex-sentinel.json`. If `$ARGUMENTS` names an engine, use it; otherwise default to `latexmk` (or, if latexmk is absent but a raw engine exists, that engine). For papers using system/Unicode fonts (`fontspec`), prefer `latexmk-xelatex` or `latexmk-lualatex`.

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/set-up/scripts/write-config.py" \
  --engine latexmk \
  --distribution tinytex \
  --dir "$PROJECT_DIR"
# (substitute python3 where that's the binary; pass --pdftoppm <path> if it's off PATH)
```

`--engine` accepts: `latexmk`, `latexmk-xelatex`, `latexmk-lualatex`, `pdflatex`, `xelatex`, `lualatex`, `tectonic`. The script fills in a sensible `compileCommand`; pass `--command "<full command>"` to override (the `.tex` path is appended by compile-tex). Show the resulting file (run with `--print` or `Read` it):

```json
{
  "version": 1,
  "engine": "latexmk",
  "compileCommand": "latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error",
  "distribution": "tinytex",
  "tools": { "pdftoppm": "pdftoppm" }
}
```

`compile-tex` and `visual-polish` read this via `scripts/read-config.py`; if it's absent they fall back to auto-detecting `latexmk`/`pdflatex`, so the config is an optimisation, not a hard dependency.

## Step 4 — Confirm

If the toolchain was already complete, finish by offering to run `/latex-sentinel:compile-tex` to prove it builds. Print a one-line summary:

```
set-up: latexmk + pdftoppm + python3 present · config=.latex-sentinel.json · ready
```

If something is still missing, end with exactly what to install and the reminder to restart Claude Code afterward.

## Operating principles

- **Check and advise; never install.** Detection is free and safe. Installation can need `sudo` and is the user's call — print the commands, don't run them.
- **Two LaTeX paths, clearly framed.** TinyTeX (lightweight, no sudo) vs full TeX Live (complete, needs sudo). Recommend TinyTeX unless the user wants the full distribution.
- **Always prompt a restart after an install.** A running Claude Code session won't see newly-PATHed binaries until it restarts.
- **The config is portable.** It records intent (engine + command), not machine paths, so it can be committed with the paper. Only embed an absolute path when a binary isn't on `PATH`.
