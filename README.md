# latex-sentinel

A Claude Code plugin that helps prepare LaTeX academic papers for submission. Inspired by [TexGuardian](https://github.com/arcAman07/TexGuardian) but reimplemented as native Claude Code skills.

## Commands

| Command | What it does |
| --- | --- |
| `/latex-sentinel:review` | Run the full 7-step review pipeline (compile → verify → fix → cite-check → figure/table audit → visual polish → diff & checkpoint). |
| `/latex-sentinel:verify` | Fast regex-based checks on `.tex` files; no compilation needed. |
| `/latex-sentinel:visual-polish` | Render the PDF and inspect each page visually for layout problems text analysis can't see. |
| `/latex-sentinel:compile-tex` | Compile the paper with `latexmk` and surface errors. |
| `/latex-sentinel:cite-check` | Validate `\cite{}` keys against the `.bib` file, then reconcile each entry across CrossRef, OpenAlex, DBLP, and Semantic Scholar to flag fabricated and retracted references. |
| `/latex-sentinel:ai-writing-check` | Detect ChatGPT-style phrasing (phrase catalog + structural heuristics + stylometric metrics) and propose human-researcher-style rewrites. |

## Core guarantees

- **Unified diff patches.** Every edit is proposed through the `Edit` tool so you see a unified diff before it lands.
- **Automatic checkpoints.** Before any batch of fixes, the pipeline creates a `git` commit (or stash) so changes are reversible.
- **Instant verification.** Verification runs as `ripgrep`/`Grep` passes over the source; no LaTeX run required.
- **Visual polish loop.** The pipeline renders each page of the compiled PDF to PNG and reads it with the vision model to catch overflows, broken page breaks, and figure-placement issues that pure text checks miss.
- **7-step review pipeline.** See `skills/review-pipeline/SKILL.md` for the orchestration.

## Requirements

These external tools must be on `PATH`. The plugin will tell you which one is missing if a command fails.

| Feature | Requires |
| --- | --- |
| `compile-tex`, `review` | `latexmk` and a TeX distribution (TeX Live, MiKTeX, or TinyTeX). |
| `visual-polish` | `pdftoppm` (ships with [Poppler](https://github.com/oschwartz10612/poppler-windows/releases)). |
| `cite-check` | `curl` (built into Windows 10+ and every modern Unix). |

On Windows, install Poppler with `winget install --id=oschwartz10612.Poppler` or extract a release zip and add its `bin/` to `PATH`.

## Install

This repo is a self-hosting Claude Code plugin marketplace. On any device:

```
/plugin marketplace add 0110tpwls/latex-sentinel
/plugin install latex-sentinel@latex-sentinel
```

Then restart Claude Code (or run `/plugin`) so the commands appear. Update later with `/plugin marketplace update latex-sentinel`.

Invoke any command from any project; the skills operate on the `.tex`/`.bib` files in the current working directory. Bundled helper scripts are resolved through `${CLAUDE_PLUGIN_ROOT}`, so they work regardless of where the plugin is installed.

### Local development

To hack on the plugin without going through a marketplace, clone it and point Claude Code at the working copy:

```
/plugin marketplace add /absolute/path/to/latex-sentinel
/plugin install latex-sentinel@latex-sentinel
```
