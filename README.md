# latex-sentinel

A Claude Code plugin that helps prepare LaTeX academic papers for submission. Inspired by [TexGuardian](https://github.com/arcAman07/TexGuardian) but reimplemented as native Claude Code skills.

## Commands

| Command | What it does |
| --- | --- |
| `/latex-sentinel:setup-tex` | Detect installed TeX engines, list the install options for your OS, install the one you pick, and record it in `.latex-sentinel.json`. Run this first if you don't have LaTeX yet. |
| `/latex-sentinel:review` | Run the full 7-step review pipeline (compile → verify → fix → cite-check → figure/table audit → visual polish → diff & checkpoint). |
| `/latex-sentinel:verify` | Fast regex-based checks on `.tex` files; no compilation needed. |
| `/latex-sentinel:visual-polish` | Render the PDF and inspect each page visually for layout problems text analysis can't see. |
| `/latex-sentinel:compile-tex` | Compile the paper (using your configured engine) and surface errors. |
| `/latex-sentinel:cite-check` | Validate `\cite{}` keys against the `.bib` file, then reconcile each entry across CrossRef, OpenAlex, DBLP, and Semantic Scholar to flag fabricated and retracted references. |
| `/latex-sentinel:ai-writing-check` | Detect ChatGPT-style phrasing (phrase catalog + structural heuristics + stylometric metrics) and propose human-researcher-style rewrites. |

## Requirements

The plugin itself is pure Claude Code skills — no install step beyond adding the plugin. The skills that **read and rewrite text** work with nothing extra:

| Always available (no external tools) |
| --- |
| `verify`, `cite-check` (offline integrity lint), `ai-writing-check` |

Some skills shell out to external tools. The plugin tells you which one is missing if a command fails, and `setup-tex` can install the LaTeX side for you.

| Feature | Requires | How to get it |
| --- | --- | --- |
| `compile-tex`, `review` | a TeX engine — ideally `latexmk` plus a TeX distribution (TeX Live, MacTeX, MiKTeX, TinyTeX) **or** the single-binary `tectonic` | run `/latex-sentinel:setup-tex`, or see **Installing LaTeX** below |
| `visual-polish` | `pdftoppm` (ships with [Poppler](https://poppler.freedesktop.org/)) | macOS `brew install poppler` · Debian `sudo apt-get install poppler-utils` · Windows `winget install --id=oschwartz10612.Poppler` |
| `cite-check` online resolution | `python` (3.x, stdlib only — no `pip install`) and network access for CrossRef/OpenAlex/DBLP/S2 | bundled with macOS/Linux; on Windows install from python.org |
| `ai-writing-check` stylometry | `python` (3.x, stdlib only) | same as above |

On systems whose Python binary is `python3` rather than `python`, the skills substitute it automatically. No third-party Python packages are needed anywhere.

## Installing LaTeX

`compile-tex` and the review pipeline need a TeX engine on your `PATH`. The easiest path is to let the plugin do it:

```
/latex-sentinel:setup-tex
```

This **detects** any engine you already have, **lists** the options for your OS, **asks** which to use, **installs** it on your behalf, and **writes** the choice to `.latex-sentinel.json` so future compiles are deterministic. It never installs anything without you picking a specific option first.

If you'd rather install by hand, pick one:

| OS | Full distribution (includes `latexmk`) | Minimal / single-binary |
| --- | --- | --- |
| **macOS** | `brew install --cask mactex` | `brew install --cask basictex` then `sudo tlmgr install latexmk`, or `brew install tectonic` |
| **Debian/Ubuntu** | `sudo apt-get install texlive-full` (or lighter: `texlive-latex-extra latexmk`) | `tectonic` from your package manager / release binary |
| **Fedora** | `sudo dnf install texlive-scheme-full` | `sudo dnf install tectonic` |
| **Arch** | `sudo pacman -S texlive-most texlive-bin` | `sudo pacman -S tectonic` |
| **Windows** | `winget install MiKTeX.MiKTeX` or `winget install TeXLive.TeXLive` | `winget install tectonic.tectonic` / `scoop install tectonic` |
| **Any Unix, no sudo** | TinyTeX: `curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" \| sh` then `"$HOME/.TinyTeX/bin/"*/tlmgr install latexmk` | — |

**Which should I choose?**

- **MacTeX / TeX Live + `latexmk`** — the "it just works" option. Largest download (multi-GB for the full scheme), but every package is present and `latexmk` reruns bibtex/biber for you. Pick this if you have the disk and want zero surprises.
- **BasicTeX / TinyTeX** — a few hundred MB; installs `latexmk` and pulls remaining packages on demand with `tlmgr`. Pick this for a smaller footprint.
- **Tectonic** — a single self-contained binary that downloads exactly the packages your document uses on first build and caches them. No `tlmgr`, very reproducible. Pick this for CI or a minimal, modern setup. (It drives its own engine, so there's no separate `latexmk`.)

`latexmk` is an orchestrator that can drive `pdflatex`, `xelatex`, or `lualatex` — so "which distribution" and "which PDF engine" are separate choices. Use `xelatex`/`lualatex` if your paper uses system/Unicode fonts via `fontspec`; `pdflatex` otherwise. `setup-tex` asks you which engine the config should call.

## Project config — `.latex-sentinel.json`

`setup-tex` writes a small JSON file in your project root that records **how this paper builds**. `compile-tex`, `review`, and `visual-polish` read it; if it's absent they fall back to auto-detecting `latexmk`/`pdflatex`, so the config is an optimisation, not a hard dependency. You can also write it by hand or commit it with the paper.

```json
{
  "version": 1,
  "engine": "latexmk",
  "compileCommand": "latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error",
  "distribution": "mactex",
  "tools": { "pdftoppm": "pdftoppm" }
}
```

| Field | Meaning |
| --- | --- |
| `engine` | which engine the config selects: `latexmk`, `latexmk-xelatex`, `latexmk-lualatex`, `pdflatex`, `xelatex`, `lualatex`, or `tectonic`. |
| `compileCommand` | the exact command run to build the paper; the main `.tex` path is appended to it. Override it to add flags like `-shell-escape`. |
| `distribution` | informational — how TeX was installed (`mactex`, `texlive`, `tinytex`, `miktex`, `tectonic`). |
| `tools.pdftoppm` | optional path to `pdftoppm` if it isn't on `PATH`; `visual-polish` uses it. |

The file is resolved by walking up from the working directory, so a config in the project root applies to `.tex` files in subfolders too. The helper scripts that read and write it live in `skills/setup-tex/scripts/` and are pure-stdlib Python.

## Core guarantees

- **Unified diff patches.** Every edit is proposed through the `Edit` tool so you see a unified diff before it lands.
- **Automatic checkpoints.** Before any batch of fixes, the pipeline creates a `git` commit (or stash) so changes are reversible.
- **Instant verification.** Verification runs as `ripgrep`/`Grep` passes over the source; no LaTeX run required.
- **Visual polish loop.** The pipeline renders each page of the compiled PDF to PNG and reads it with the vision model to catch overflows, broken page breaks, and figure-placement issues that pure text checks miss.
- **7-step review pipeline.** See `skills/review-pipeline/SKILL.md` for the orchestration.

## Install

This repo is a self-hosting Claude Code plugin marketplace. On any device:

```
/plugin marketplace add 0110tpwls/latex-sentinel
/plugin install latex-sentinel@latex-sentinel
```

Then restart Claude Code (or run `/plugin`) so the commands appear. Update later with `/plugin marketplace update latex-sentinel`.

Invoke any command from any project; the skills operate on the `.tex`/`.bib` files in the current working directory. Bundled helper scripts are resolved through `${CLAUDE_PLUGIN_ROOT}`, so they work regardless of where the plugin is installed.

New to LaTeX on this machine? Run `/latex-sentinel:setup-tex` once to install an engine and write the project config, then `/latex-sentinel:review` to run the full pass.

### Local development

To hack on the plugin without going through a marketplace, clone it and point Claude Code at the working copy:

```
/plugin marketplace add /absolute/path/to/latex-sentinel
/plugin install latex-sentinel@latex-sentinel
```
