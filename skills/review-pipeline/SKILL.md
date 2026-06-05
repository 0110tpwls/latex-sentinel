---
name: review-pipeline
description: Run the 7-step LaTeX review pipeline on the paper in the current directory. Use when the user asks to "review the paper", "run the full review", "prep for submission", or invokes /latex-sentinel:review. Orchestrates compile, instant verification, LLM fixes, citation validation, figure/table audit, visual polish, and final diff approval with a git checkpoint.
argument-hint: "[path-to-main.tex]"
allowed-tools: Bash Read Edit Grep Glob
---

# 7-Step Review Pipeline

You are running the LaTeX-Sentinel review pipeline. The user is preparing a paper for submission and wants a thorough, reviewable pass. Every change must be proposed as a unified diff (via the `Edit` tool) and a `git` checkpoint must exist before each batch of fixes.

## Setup

If `$ARGUMENTS` is provided, treat it as the path to the main `.tex` file. Otherwise, find it: run `Glob` for `**/*.tex` and pick the file that contains `\documentclass`. Set `MAIN_TEX` to that path and `PAPER_DIR` to its directory. If you can't determine it, ask the user.

**Grep usage convention (Windows-safe).** Throughout this pipeline and its sub-skills, when you call the Grep tool, pass the project root as an absolute `path:` and the file pattern as `glob: "**/*.tex"` (or `"**/*.bib"`). Don't combine them — `glob: "<subdir>/**/*.tex"` silently returns no matches on Windows. To narrow scope, change `path:` to the absolute subdirectory path.

Before you start, check git status:
- `git rev-parse --is-inside-work-tree` — if this fails, ask the user whether to proceed without checkpoints or `git init` first.
- `git status --porcelain` — if there are uncommitted changes, stop and tell the user. They should commit/stash before the pipeline runs so the checkpoint is meaningful.

Print a one-line summary of what you'll do and proceed.

## Step 1 — Compile

Invoke the compile-tex skill (or run the equivalent yourself). It first reads the project's `.latex-sentinel.json` (written by `/latex-sentinel:set-up`) for the configured engine/command, and otherwise defaults to:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error "$MAIN_TEX"
```

If **no LaTeX toolchain is on `PATH`**, stop and tell the user to run `/latex-sentinel:set-up` first — it checks the toolchain, shows how to install what's missing (TinyTeX or TeX Live; restart Claude Code afterward), and records the engine in `.latex-sentinel.json` so this step builds reliably. Don't attempt later steps without a compiler.

Capture exit code and the last 80 lines of the log. If compilation fails, surface the errors to the user, propose fixes as `Edit` calls, and re-run until it compiles. Do **not** proceed to later steps with a paper that doesn't build.

## Step 2 — Instant verification

Invoke the instant-verify skill. Collect the issue list. Group findings by severity (`error`, `warning`, `style`). Show the user.

## Step 3 — Apply LLM-generated fixes

For each finding from Step 2 that you're confident about:
1. Read the file with line context.
2. Propose the fix as an `Edit` call. The Edit tool shows the unified diff; the user approves or rejects.
3. Track which fixes were applied so the final summary is accurate.

Before this batch, create a checkpoint:
```bash
git add -A && git commit -m "checkpoint: pre-fix (latex-sentinel)" --allow-empty
```

Skip fixes that need human judgement — list them for the user instead.

## Step 4 — Citation validation

Invoke the cite-check skill. Report:
- Keys cited but missing from `.bib`.
- `.bib` entries that don't resolve on CrossRef (when a DOI is present).
- `.bib` entries that don't match a Semantic Scholar record (when no DOI).
- Title/year mismatches between `.bib` and the canonical record.

Apply fixes via `Edit` (e.g., correcting a DOI, fixing a title typo) only after showing the user the canonical source.

## Step 5 — Figure & table audit

Read every `figure` and `table` environment in the paper. Check:
- Every figure has a `\caption{}` **and** a `\label{}`.
- `\includegraphics` uses relative paths and `width=...\linewidth` (not absolute `cm`/`in`).
- Every `\label{fig:...}` / `\label{tab:...}` is `\ref`'d at least once.
- Captions end with a period and don't contain TODO/FIXME.

Propose fixes as `Edit` calls.

## Step 6 — Visual polish loop

Invoke the visual-polish skill. It renders the compiled PDF page-by-page and uses the vision model to find:
- Overfull/underfull hboxes that produced visible overflow.
- Figures or tables that broke across pages or float to the wrong section.
- Equation overflow into the margin.
- Orphaned section headings at the bottom of a page.
- Citation `[?]` or `??` rendering artefacts.

Propose fixes as `Edit` calls.

## Step 7 — Final diff & checkpoint

Run `git diff --stat HEAD~1..HEAD` (or compare to the pre-pipeline state) and present a summary:
- Files touched.
- Issues fixed by step.
- Issues *not* fixed (listed for the user with a reason).
- Final checkpoint commit:
  ```bash
  git add -A && git commit -m "latex-sentinel review: <N> fixes across <M> files" --allow-empty
  ```

End with: paper is/isn't ready for submission, and what the human still needs to look at.

## Operating principles

- **Never overwrite files without showing the diff.** Always use `Edit`, never `Write` for existing files.
- **One issue per Edit.** Small, reviewable patches beat large rewrites.
- **Stop on red.** If the paper stops compiling mid-pipeline, halt and fix before continuing.
- **Defer judgement calls.** Phrasing, structure, and content questions go to the user — don't rewrite the author's voice silently.
