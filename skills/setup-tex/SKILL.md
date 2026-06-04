---
name: setup-tex
description: Set up the LaTeX toolchain for this project. Detects which TeX engines are already installed (latexmk, pdflatex, xelatex, lualatex, tectonic), lists the install options for the current OS, asks the user which engine/distribution to use, installs it on their behalf, and writes a project-level .latex-sentinel.json so compile-tex and the review pipeline know exactly how to build the paper. Use when the user invokes /latex-sentinel:setup-tex, asks to "install LaTeX", "set up tex", "which compiler should I use", "configure the compiler", or when compile-tex reports no toolchain on PATH.
argument-hint: "[engine, e.g. latexmk | xelatex | tectonic]"
allowed-tools: Bash Read Edit AskUserQuestion Glob
---

# Set up the LaTeX toolchain

Goal: end with a working compiler **and** a `.latex-sentinel.json` in the project that records how to build it, so `/latex-sentinel:compile-tex` never has to guess again. Do the four steps in order: **detect → choose → install → write config**. Never install anything without the user's explicit approval of a specific option.

## Step 1 — Detect what already exists

Run the detector (resolve it through `${CLAUDE_PLUGIN_ROOT}`, never a hardcoded path):

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/setup-tex/scripts/detect-tex.sh"
```

It prints one JSON object: the OS, every engine's `{present, path, version}`, which install/package managers exist (`brew`, `apt-get`, `winget`, `tlmgr`, …), and a `recommend` route. Parse it.

- **If an engine is already present** (`latexmk` or any of `pdflatex`/`xelatex`/`lualatex`/`tectonic` is `present: true`): the toolchain exists. Do **not** install anything. Jump to Step 2 and ask only *which* of the installed engines to use (plus "install something else" as an option). If exactly one engine exists and it's `latexmk`, you may confirm-and-proceed in one question.
- **If nothing is present**: go to Step 2 to offer install options for this OS.

On Windows the script runs under Git Bash/MSYS; if the user's shell is PowerShell and `detect-tex.sh` can't run, fall back to checking `where latexmk` / `where pdflatex` yourself and read the manager list from "what's installed" knowledge.

## Step 2 — Ask the user which engine/distribution

Use the **AskUserQuestion** tool — this is a decision only the user can make. Build the option list from Step 1's findings and the OS. If `$ARGUMENTS` already names an engine (e.g. `xelatex`), treat that as the user's choice and skip straight to confirming the matching install/config.

**When engines already exist**, ask which to *use* (no install):

> Question: "Which LaTeX engine should latex-sentinel use to compile this paper?"
> Options drawn from what's present, e.g.:
> - `latexmk (recommended)` — auto-runs bibtex/biber and reruns until refs resolve
> - `pdflatex` — single engine, fastest, ASCII/Type1 fonts
> - `xelatex` — system/Unicode fonts (fontspec)
> - `lualatex` — Lua-extended, Unicode, modern font handling
> - `tectonic` — self-contained, downloads packages on demand
> (only list engines that are actually present, plus "Install a different distribution")

**When nothing exists**, ask which to *install*. Offer the routes that match the detected OS and available managers:

| OS | Offer (in this order) |
| --- | --- |
| macOS (`brew` present) | **MacTeX** (`brew install --cask mactex`, full, ~4 GB) · **BasicTeX** (`brew install --cask basictex`, ~100 MB, add packages with `tlmgr`) · **TinyTeX** (script, ~200 MB) · **Tectonic** (`brew install tectonic`, single binary) |
| macOS (no brew) | **TinyTeX** (curl script) · **Tectonic** (download binary) · or install Homebrew first |
| Linux (`apt-get`) | **TeX Live** (`sudo apt-get install texlive-full` or the lighter `texlive-latex-extra latexmk`) · **TinyTeX** · **Tectonic** |
| Linux (`dnf`/`pacman`/`zypper`) | distro TeX Live package (`texlive-scheme-full` / `texlive-most` / pattern) · **TinyTeX** · **Tectonic** |
| Windows (`winget`) | **MiKTeX** (`winget install MiKTeX.MiKTeX`) · **TeX Live** · **TinyTeX** · **Tectonic** (`winget install tectonic.tectonic` / `scoop install tectonic`) |

Always include a short trade-off in each option's description (size, on-demand package download, whether `latexmk` is included). Recommend **MacTeX/TeX Live + latexmk** for "I want it to just work" and **Tectonic** for "small, reproducible, no `tlmgr`". Note that latexmk drives any of pdflatex/xelatex/lualatex, so the engine and the distribution are separate choices: with TeX Live/MiKTeX the user still picks which PDF engine the config should call.

## Step 3 — Install on the user's behalf

Only after the user picks an install option, run the matching command. Echo the exact command first. Use the commands below verbatim (these are the canonical install lines):

```bash
# macOS — Homebrew
brew install --cask mactex          # full
brew install --cask basictex        # minimal; then: sudo tlmgr install latexmk <pkgs>
brew install tectonic               # single-binary engine

# TinyTeX (any Unix) — installs to ~/.TinyTeX, no sudo
curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh
# then add latexmk + common packages:
"$HOME/.TinyTeX/bin/"*/tlmgr install latexmk

# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y texlive-latex-extra latexmk
# Fedora
sudo dnf install -y texlive-scheme-medium latexmk
# Arch
sudo pacman -S --noconfirm texlive-most texlive-bin

# Windows (PowerShell, not this bash skill — print these for the user to run)
winget install MiKTeX.MiKTeX
winget install tectonic.tectonic
```

Notes:
- **`sudo` and `brew --cask`** can prompt for a password or take several minutes (MacTeX is multi-GB). Tell the user it may prompt and that the install runs in the foreground. Don't background a `sudo` install.
- **BasicTeX/TinyTeX** ship a tiny package set; after install, run `tlmgr install latexmk` and let the first real compile pull missing packages (or pre-install common ones: `tlmgr install collection-fontsrecommended microtype`).
- If a command isn't available because a manager is missing (e.g. no `brew`), say so and offer the next route (TinyTeX needs only `curl`).
- After installing, **re-run `detect-tex.sh`** to confirm the engine now resolves. If a freshly installed binary isn't on `PATH` yet (common with TinyTeX/BasicTeX), tell the user the exact line to add to their shell profile, e.g. `export PATH="$HOME/.TinyTeX/bin/universal-darwin:$PATH"`, or use the absolute path in the config command.

## Step 4 — Write the project config

Write (or update) `.latex-sentinel.json` in the project root with the chosen engine. Use the helper so the JSON is well-formed and existing keys survive:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/setup-tex/scripts/write-config.py" \
  --engine latexmk \
  --distribution mactex \
  --dir "$PROJECT_DIR"
# (substitute python3 where that's the binary)
```

`--engine` accepts: `latexmk`, `latexmk-xelatex`, `latexmk-lualatex`, `pdflatex`, `xelatex`, `lualatex`, `tectonic`. The script fills in a sensible `compileCommand` for each; pass `--command "<full command>"` to override (the `.tex` path is appended by compile-tex). If you detected `pdftoppm` at a non-standard path, pass `--pdftoppm <path>` so visual-polish uses it.

Show the resulting file to the user (run with `--print`, or `Read` it back). It looks like:

```json
{
  "version": 1,
  "engine": "latexmk",
  "compileCommand": "latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error",
  "distribution": "mactex",
  "tools": { "pdftoppm": "pdftoppm" }
}
```

`compile-tex` and `visual-polish` read this via `scripts/read-config.py`; if it's absent they fall back to auto-detecting `latexmk`/`pdflatex`, so the config is an optimisation, not a hard dependency.

## Step 5 — Verify

Confirm the loop closes:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/setup-tex/scripts/detect-tex.sh"   # engine now present?
python "${CLAUDE_PLUGIN_ROOT}/skills/setup-tex/scripts/read-config.py" --json --dir "$PROJECT_DIR"
```

Then offer to run `/latex-sentinel:compile-tex` on the user's main `.tex` to prove the toolchain builds end-to-end. Report a one-line summary:

```
setup-tex: engine=latexmk (TeX Live 2024) · config=.latex-sentinel.json · ready
```

## Operating principles

- **Never install without an explicit pick.** Detection and listing are free; installation changes the user's machine — gate it behind AskUserQuestion approval of a specific option.
- **Respect an existing toolchain.** If a compiler is already there, default to *using* it; only install when the user asks for a different one.
- **Foreground long installs.** MacTeX/TeX Live are large and may need `sudo`; don't background them, and warn about the password prompt and download size.
- **The config is portable.** It records intent (engine + command), not absolute machine paths, so it can be committed with the paper. Only embed an absolute path when a binary isn't on `PATH`.
