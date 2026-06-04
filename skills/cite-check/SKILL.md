---
name: cite-check
description: Validate LaTeX citations and detect fabricated or retracted references. Parses \cite{} keys from the .tex source, cross-references them against the project .bib file(s), lints every entry offline for malformed fields and bad ISBN/ISSN/DOI checksums, then validates each entry online by RECONCILING multiple authoritative sources (CrossRef, OpenAlex, DBLP, Semantic Scholar). Emits a fabrication verdict (REAL / UNCERTAIN / LIKELY-FABRICATED / UNVERIFIED), flags retracted papers, and reports missing keys, unused entries, DOI mismatches, title typos, and outdated years. Use when the user invokes /latex-sentinel:cite-check, asks to "verify the bibliography", "check the citations", "find fake references", or as step 4 of the review pipeline.
argument-hint: "[path-to-main.tex]"
allowed-tools: Bash Read Edit Grep Glob
---

# Citation Check

Validate the bibliography against the source, an offline integrity linter, and several authoritative metadata services that are **reconciled against each other** — a reference is trustworthy when independent sources agree, suspect when they all disagree, and *unknown* (never "fake") when the network is down.

**Grep usage (Windows-safe).** Pass the project root as an absolute `path:` and use `glob: "**/*.tex"` / `glob: "**/*.bib"`. Do **not** embed a subdirectory in the glob string — set `path:` to the subdirectory instead.

**Two helper scripts do the heavy lifting** (both stdlib-only Python, no pip installs):

| Script | Network? | Purpose |
| --- | --- | --- |
| `scripts/bib-integrity.py` | no | Offline linter: structure, required fields, ISBN/ISSN/DOI checksums, duplicates, casing. |
| `scripts/bib-resolve.py` | yes | Multi-source online reconciliation, fabrication verdict, retraction check. |

On Windows, prefix script runs with `PYTHONIOENCODING=utf-8` if a `.bib` contains non-ASCII so console printing of titles can't crash. On systems whose binary is `python3`, substitute `python3`.

## Step 1 — Collect cited keys

Use `Grep` over `**/*.tex` (excluding `build/`, `out/`, `_minted-*`) to find every cite key. Patterns:

- `\\cite\{[^}]+\}`
- `\\(citep|citet|citeauthor|citeyear|citealp|citealt)\{[^}]+\}`
- `\\(parencite|textcite|footcite|autocite|cites|Cite)\{[^}]+\}` (biblatex)
- `\\nocite\{[^}]+\}`

A cite call can contain comma-separated keys: `\cite{a,b,c}`. Split on `,` and trim whitespace. Build `CITED = set of keys`.

## Step 2 — Collect .bib entries

`Glob` `**/*.bib`. For each file, parse top-level entries with the pattern `@(\w+)\{([^,]+),`. Build `BIB = { key → { type, raw_entry, doi, title, year, author } }`.

DOI extraction: `doi\s*=\s*[{"]([^}"]+)[}"]` (case-insensitive). Strip leading `https://doi.org/` if present. Title and year extraction: same shape, fields `title` and `year`.

## Step 3 — Source/bibliography diff

- `MISSING = CITED - BIB.keys()` — keys cited but no entry.
- `UNUSED  = BIB.keys() - CITED` — entries in `.bib` not cited. (Warning, not error — `\nocite{*}` users will see false positives.)

Report counts.

## Step 4 — Offline integrity lint (no network)

Run this **first** — it is free, instant, and catches a whole class of problems the metadata services can't (a missing `publisher`, a transposed ISBN digit, a single-hyphen page range, duplicate keys). It also never produces false "this paper doesn't exist" noise, so it's the safe baseline even when offline.

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/cite-check/scripts/bib-integrity.py" <refs.bib> [more.bib ...]
# add --json for machine-readable output
```

What it checks per entry, and how to read each:

| Severity | Example finding | Meaning |
| --- | --- | --- |
| **ERROR** | duplicate entry key, malformed `@type{...}`, missing required field, bad ISBN/ISSN checksum, malformed DOI | will break compilation or is provably wrong; fix before anything else |
| **WARN** | duplicate DOI/title across entries, `et al.` literal in `author`, implausible year, non-`https` URL, HTML entity in a field | very likely a mistake; review |
| **STYLE** | single-hyphen page range (`436-444` → `436--444`), unprotected acronym casing (`BERT` → `{BERT}`) | cosmetic / BibTeX convention |

The script exits non-zero if any ERROR is present and prints a summary line: `bib-integrity: N errors, M warnings, K style across E entries`. Fold its findings into the Step 6 report. Required-field checks are biblatex-friendly (e.g. an entry may carry `date` instead of `year`, `journaltitle` instead of `journal`).

## Step 5 — Online multi-source validation (reconciled)

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/cite-check/scripts/bib-resolve.py" <refs.bib>
# or validate one reference directly:
python ".../bib-resolve.py" --doi 10.1038/nature14539
python ".../bib-resolve.py" --title "Attention is all you need" --author Vaswani --year 2017
# flags: --json  --no-s2 (skip Semantic Scholar)  --sleep N (override polite delay)
```

### How reconciliation works

- **If a DOI is present**, CrossRef is authoritative: resolving it confirms the work exists and returns the canonical title/year/author **and retraction status**. A DOI that 404s is *not* itself proof of fabrication — the script falls through to a title search to tell "dead/typo'd DOI on a real paper" apart from "invented reference".
- **If no DOI (or the DOI is dead)**, the script queries CrossRef, OpenAlex, and DBLP (and Semantic Scholar unless `--no-s2`) by title, and counts how many **independently confirm** the title (similarity ≥ 0.82). Year and author are reconciled too, but only as **mismatch flags** — a wrong year never makes a real paper look fabricated.
- **DOI cross-confirmation**: keyword search has poor recall on some famous titles (e.g. a paper may be absent from CrossRef's free-text results yet sit in DBLP with its real DOI). When a confirming record carries a DOI, the script resolves it on CrossRef — a registered DOI whose title matches is decisive existence proof.

### The verdict (the headline output)

| Mark | Verdict | What it means | What to do |
| --- | --- | --- | --- |
| `OK` | **REAL** | DOI verified, or ≥2 sources agree | trust it; still surface any year/author mismatch flags |
| `!!` | **REAL (bad DOI)** | paper is real but the given DOI doesn't resolve | offer to fix the DOI |
| `? ` | **UNCERTAIN** | exactly one source confirms, or only one source could even be reached | report honestly as unverified; suggest adding a DOI |
| `XX` | **LIKELY-FABRICATED** | ≥2 sources were reachable and **definitively** returned no match | **flag prominently and ask the user** — do not delete anything yourself |
| `..` | **UNVERIFIED** | sources were unreachable (network/rate-limit), so existence is unknown | not a failure; re-run later |

**Crucial distinction the script enforces:** a fabrication call requires sources that *definitively* answered "no such work" (an HTTP 200 with zero matches, or a 404). A network error, timeout, or rate-limit yields **UNVERIFIED**, never LIKELY-FABRICATED. Never accuse a reference of being fake on the strength of a failed connection.

### Retraction

Any entry whose CrossRef record carries an `update-to`/`updated-by` of type `retraction` (Retraction Watch data), or whose title is prefixed `RETRACTED:`/`WITHDRAWN:`, is marked `*** RETRACTED ***`. An expression of concern is marked too. **A retracted reference that is otherwise perfectly real is one of the most important things this skill can catch** — surface it at the top of the report regardless of the fabrication verdict.

### Semantic Scholar rate limits (handled by the script)

The script implements the polite/backoff/circuit-breaker policy so you don't have to orchestrate `curl`:

- Polite gap of ~1.5 s between S2 calls (0.3 s if a key is set).
- On HTTP 429, exponential backoff with 3 retries per entry (5 s → 20 s → 45 s).
- **Circuit breaker**: after 3 consecutive entries exhaust their retries (10 with a key), S2 calls stop for the rest of the run; affected entries simply show `s2=ratelimited` and are validated by the other three sources. A single intermittent 429 does not trip it.
- If `SEMANTIC_SCHOLAR_API_KEY` is set in the environment, the script sends it as `x-api-key`, shortens the delay, and raises the breaker threshold automatically.

S2 being unavailable never turns a REAL into a fabrication — the verdict only counts *definitive misses*, and a rate-limit is not a miss. Use `--no-s2` to skip S2 entirely for a faster, CrossRef+OpenAlex+DBLP-only run.

### Manual fallback (no Python)

If Python is genuinely unavailable, you can still validate a single DOI by hand — but you lose reconciliation, the fabrication verdict, and the retraction check, so prefer the script:

```bash
curl -sf -A "latex-sentinel/0.2 (mailto:nobody@example.com)" \
  "https://api.crossref.org/works/$(printf '%s' "$DOI" | sed 's/ /%20/g')"
```

## Step 6 — Report

Lead with the things that matter most — retractions and likely fabrications — then integrity, then the softer mismatches.

```
Citation check

CITED keys: 47        .bib entries: 49
  Missing from .bib:  2   ← cited but no entry  (smith2024, jones2023)
  Unused in .bib:     2   ← entries not cited (informational)

⚠ RETRACTED              1   wakefield1998  (10.1016/S0140-6736(97)11096-0)
⚠ LIKELY FABRICATED      1   ghost2023  (no match in CrossRef/OpenAlex/DBLP)

Integrity (offline):  0 errors, 2 warnings, 1 style
  ! lecun2015deep   pages '436-444' → '436--444'
  ! vaswani2017     literal 'et al.' in author field

Online resolution (47 entries):
  ✓ REAL                 41
  !! REAL (bad DOI)        1   chen2024  → suggested 10.1234/correct.doi
  ?  UNCERTAIN             2   doe2022 (only DBLP), kim2021 (S2 only)
  XX LIKELY FABRICATED     1   ghost2023
  .. UNVERIFIED            1   patel2020 (network/rate-limit — re-run later)
  ! year mismatch          1   liu2019 (bib 2019 vs source 2018)
```

Do **not** count `UNVERIFIED` entries as failures — they are unknown, not wrong.

## Step 7 — Propose fixes

For each flagged entry, propose an `Edit` to the `.bib` file (so each change is a unified diff the user approves):

- **Retracted** → do not silently edit. Tell the user prominently; offer to add a note or remove the citation only if they ask. This is an authorship/integrity decision, not a typo.
- **LIKELY-FABRICATED** → present the evidence (which sources were queried and definitively missed) and **ask the user**; never invent a replacement or delete the entry yourself.
- **REAL (bad DOI)** → offer to patch `doi = {...}` with the resolved DOI.
- **Year mismatch** → patch `year = {...}` after confirming.
- **Title typo** → patch `title = {...}` to the canonical title, preserving `{`-protected casing (canonical titles are sometimes cased differently; wrap acronyms in braces).
- **Integrity ERROR/WARN** → fix malformed structure, checksums, page ranges, and acronym casing per the linter's suggestion.

For `MISSING` keys, ask the user — you can't invent bibliography entries from nothing, but you can offer to search by guessing the topic from the cite context (read the sentence around `\cite{key}`).
