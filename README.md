# latex-sentinel

A Claude Code plugin that helps prepare LaTeX academic papers for submission — compile, verify, validate citations, audit figures/tables, check for AI-writing tells, count pages, and visually polish the rendered PDF, all as native Claude Code skills with diff-based, checkpointed edits.

## Installation

This repo is a self-hosting Claude Code plugin marketplace. On any device:

```
/plugin marketplace add 0110tpwls/latex-sentinel
/plugin install latex-sentinel@latex-sentinel
```

Then restart Claude Code (or run `/plugin`) so the commands appear. Update later with `/plugin marketplace update latex-sentinel`.

Invoke any command from any project; the skills operate on the `.tex`/`.bib` files in the current working directory. Bundled helper scripts are resolved through `${CLAUDE_PLUGIN_ROOT}`, so they work wherever the plugin is installed.

### Quick start

```
/latex-sentinel:set-up      # check your toolchain; get install instructions if anything's missing
/latex-sentinel:review      # run the full pre-submission pass
```

New to LaTeX on this machine? Run `/latex-sentinel:set-up` first — it tells you exactly what to install (see **Setting up LaTeX** below), then `/latex-sentinel:review` runs compile → verify → cite-check → figure audit → visual polish.

## Setting up LaTeX

The text-only skills (`verify`, `cite-check`'s offline lint, `ai-writing-check`) work with nothing extra. Compiling and visual checks need a TeX toolchain. Run:

```
/latex-sentinel:set-up
```

It's a **doctor**: it checks what's installed (`latexmk`, a PDF engine, `bibtex`/`biber`, `pdftoppm`, `python`) and, for anything missing, prints the exact commands to install it — then asks you to **restart Claude Code** so the new binaries land on `PATH`. It never installs anything itself (a full TeX distribution needs `sudo`), and it writes a project-level `.latex-sentinel.json` recording how to build your paper once the toolchain is ready.

For LaTeX you get two clear choices:

| Option | Size | sudo? | Best for |
| --- | --- | --- | --- |
| **TinyTeX** (recommended) | ~200 MB | no | most users; installs to your home dir, pulls extra packages on demand |
| **Full TeX Live / MacTeX** | multi-GB | yes | heavy or unusual document classes; no missing-package surprises |

```bash
# TinyTeX (lightweight, no sudo)
curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"   # macOS
export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"              # Linux
tlmgr install latexmk booktabs natbib hyperref pgfplots xcolor float \
              geometry amsmath amssymb graphicx tikz caption subcaption microtype

# Full TeX Live (needs sudo)
brew install --cask mactex-no-gui     # macOS
sudo apt install texlive-full         # Debian/Ubuntu
sudo dnf install texlive-scheme-full  # Fedora
# Windows: install MiKTeX or TeX Live from their installers
```

Add the `export PATH=...` line to your `~/.zshrc` / `~/.bashrc` so it persists, and **restart Claude Code after installing**.

For `visual-polish` you also need `pdftoppm` (from [Poppler](https://poppler.freedesktop.org/)): `brew install poppler` (macOS), `sudo apt-get install poppler-utils` (Debian), or `winget install --id=oschwartz10612.Poppler` (Windows).

## Commands

| Command | What it does |
| --- | --- |
| `/latex-sentinel:set-up` | Check the LaTeX toolchain (a "doctor"), show how to install anything missing (TinyTeX or TeX Live), and write the project's compile config. Run this first. |
| `/latex-sentinel:review` | Run the full 7-step review pipeline (compile → verify → fix → cite-check → figure/table audit → visual polish → diff & checkpoint). |
| `/latex-sentinel:verify` | Fast regex-based checks on `.tex` files; no compilation needed. |
| `/latex-sentinel:compile-tex` | Compile the paper (using your configured engine) and surface errors. |
| `/latex-sentinel:cite-check` | Validate `\cite{}` keys against the `.bib` file, then reconcile each entry across CrossRef, OpenAlex, DBLP, and Semantic Scholar to flag fabricated and retracted references. |
| `/latex-sentinel:ai-writing-check` | Detect ChatGPT-style phrasing (phrase catalog + structural heuristics + stylometric metrics) and propose human-researcher-style rewrites. |
| `/latex-sentinel:page-count` | Report total pages and a per-section breakdown, and check against a venue page limit. |
| `/latex-sentinel:visual-polish` | Render the PDF and inspect each page visually for layout problems text analysis can't see. |

## Requirements

The plugin itself is pure Claude Code skills — no install step beyond adding the plugin. External tools are only needed by some skills; `/latex-sentinel:set-up` checks for them and tells you what's missing.

| Feature | Requires | How to get it |
| --- | --- | --- |
| `verify`, `cite-check` (offline lint), `ai-writing-check` | nothing extra | — |
| `compile-tex`, `review` | a TeX engine — ideally `latexmk` plus a distribution (TinyTeX, TeX Live, MacTeX, MiKTeX) | run `/latex-sentinel:set-up` (see **Setting up LaTeX**) |
| `visual-polish` | `pdftoppm` (ships with Poppler) | `brew install poppler` · `apt-get install poppler-utils` · `winget install --id=oschwartz10612.Poppler` |
| `page-count` | `pdfinfo` (Poppler) for an exact count; degrades to an approximate stdlib count otherwise | same as Poppler above |
| `cite-check` online, `ai-writing-check` stylometry | `python` 3.x (stdlib only — no `pip install`) and, for cite-check, network access | bundled with macOS/Linux; Windows: python.org |

On systems whose Python binary is `python3` rather than `python`, the skills substitute it automatically. No third-party Python packages are needed anywhere.

## Project config — `.latex-sentinel.json`

`set-up` writes a small JSON file in your project root recording **how this paper builds**. `compile-tex`, `review`, `page-count`, and `visual-polish` read it; if it's absent they fall back to auto-detecting `latexmk`/`pdflatex`, so the config is an optimisation, not a hard dependency. You can also write it by hand or commit it with the paper.

```json
{
  "version": 1,
  "engine": "latexmk",
  "compileCommand": "latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error",
  "distribution": "tinytex",
  "tools": { "pdftoppm": "pdftoppm" }
}
```

| Field | Meaning |
| --- | --- |
| `engine` | which engine the config selects: `latexmk`, `latexmk-xelatex`, `latexmk-lualatex`, `pdflatex`, `xelatex`, `lualatex`, or `tectonic`. |
| `compileCommand` | the exact command run to build the paper; the main `.tex` path is appended to it. Override it to add flags like `-shell-escape`. |
| `distribution` | informational — how TeX was installed (`tinytex`, `texlive`, `mactex`, `miktex`). |
| `tools.pdftoppm` | optional path to `pdftoppm` if it isn't on `PATH`; `visual-polish` uses it. |

The file is resolved by walking up from the working directory, so a config in the project root applies to `.tex` files in subfolders too. The helper scripts that read and write it live in `skills/set-up/scripts/` and are pure-stdlib Python.

## Core guarantees

- **Unified diff patches.** Every edit is proposed through the `Edit` tool so you see a unified diff before it lands.
- **Automatic checkpoints.** Before any batch of fixes, the pipeline creates a `git` commit (or stash) so changes are reversible.
- **Instant verification.** Verification runs as `ripgrep`/`Grep` passes over the source; no LaTeX run required.
- **Visual polish loop.** The pipeline renders each page of the compiled PDF to PNG and reads it with the vision model to catch overflows, broken page breaks, and figure-placement issues that pure text checks miss.
- **7-step review pipeline.** See `skills/review-pipeline/SKILL.md` for the orchestration.

## Local development

To hack on the plugin without going through a marketplace, clone it and point Claude Code at the working copy:

```
/plugin marketplace add /absolute/path/to/latex-sentinel
/plugin install latex-sentinel@latex-sentinel
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Special thanks

- **[TexGuardian](https://github.com/arcAman07/TexGuardian)** by [@arcAman07](https://github.com/arcAman07) — the project that inspired latex-sentinel. Its review pipeline, vision-model visual checks, citation validation, toolchain `doctor`, and page-count features shaped this plugin's design; latex-sentinel is an independent reimplementation as native Claude Code skills. If you want the original CLI, go give it a star.
