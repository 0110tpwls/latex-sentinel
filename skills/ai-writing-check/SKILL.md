---
name: ai-writing-check
description: Detect signs of AI-generated writing in LaTeX prose and propose human-researcher-style rewrites. Combines three detection layers — (1) a catalog of overused ChatGPT phrases (ETBI library aisigns page + "ChatGPT Overused Words and Phrases"), (2) structural heuristics (em-dash overuse, hedge density, rule-of-three, negative parallelism, synonym cycling), and (3) stylometric metrics computed by scripts/ai-metrics.py (sentence-length burstiness, punctuation entropy, opener diversity, connective density) plus near-certain provenance "smoking guns" (chatbot reference markup, utm_source=chatgpt.com, knowledge-cutoff disclaimers, unfilled placeholders). Use when the user invokes /latex-sentinel:ai-writing-check, asks to "check for AI writing", "make this sound more human", or "find ChatGPT-isms".
argument-hint: "[glob, defaults to **/*.tex]"
allowed-tools: Bash Read Edit Grep Glob
---

# AI-Writing Check

The goal is two-fold:
1. Surface every place the prose looks AI-generated.
2. For each hit, propose a more natural, researcher-voice alternative — and apply it as an `Edit` (unified diff) if the user agrees.

Detection runs in **three complementary layers**, because no single one is sufficient:

| Layer | Catches | Blind spot it covers |
| --- | --- | --- |
| **A. Phrase catalog** (Step 1) | known overused words/phrases | — (but defeated by paraphrase) |
| **B. Structural heuristics** (Step 2) | AI sentence *shapes* (triads, parallelisms, em-dash habit) | survives synonym swaps |
| **C. Stylometric metrics** (Step 2b) | AI *distribution* — uniform sentence length, flat punctuation, repeated openers | catches AI even when it uses no banned word |

Layers B and C are what distinguish this from a grep-for-clichés tool: an AI draft that carefully avoids every catalog phrase still betrays itself through low burstiness and a `.`/`,`-only punctuation profile. Separately, a small set of **provenance "smoking guns"** (Step 1, group G) are near-certain tells with near-zero false positives — report these first.

This is **not** a binary "is this AI" classifier. Many flagged phrases and shapes are also used by careful human writers. Treat findings as suggestions, not accusations. The catalog source is in [phrases.md](phrases.md); read it once at the start of a run.

**Why these layers (provenance note).** The phrase catalog and structural heuristics were extended after studying how existing humanizer skills detect AI — `Aboudjem/humanizer-skill` (43-pattern taxonomy), `PasqualePillitteri/humanAIzer` (7 statistical metrics), and `blader/humanizer` (post-rewrite audit pass). Their patterns are tuned for blog/marketing copy; the versions here are re-tuned for academic prose, which is legitimately more formal and less bursty than the text those thresholds assumed. Do **not** treat a flag as a verdict.

## Scope

Default to `**/*.tex` from the current directory, excluding `build/`, `out/`, `_minted-*`. If `$ARGUMENTS` is a glob, use that. Strip TeX comments (`% ...` to end of line, where `%` is not escaped) before phrase matching — comments don't count.

**Grep usage (Windows-safe).** When invoking the Grep tool, pass the project root as an absolute `path:` (e.g. `path: "C:/Users/PC/proj/paper"`) and the file pattern as `glob: "**/*.tex"`. Do **not** put the subdirectory inside the glob (e.g. `glob: "paper/**/*.tex"` silently returns no results on Windows). To narrow scope, change `path:`, not `glob:`.

## Step 1 — Phrase matches

Read `phrases.md`. It contains category-grouped phrases with severity and the kind of alternative to suggest. For each phrase, run `Grep` (case-insensitive) over the scoped files. Use word-boundary matching where appropriate (`\b...\b`) so `delve` doesn't match `delved into` only in the wrong direction.

For each hit collect: `file`, `line`, `phrase`, `category`, `severity`, surrounding sentence (~80 chars before and after).

### Group G — provenance "smoking guns" (run these FIRST)

Unlike the rest of the catalog, these are **near-certain** that text was pasted from a chatbot — near-zero false-positive rate. A single G-hit outweighs any number of style smells. Grep for each (case-insensitive) and report at the very top of the output, above HIGH.

| ID | Pattern (regex) | What it means |
| --- | --- | --- |
| G1 | `cite[\s]*turn\d+search\d+`, `turn\d+(search\|news\|image)\d+` | ChatGPT inline reference / search-result markup leaked into the text |
| G2 | `utm_source=chatgpt\.com` | A URL copied straight out of a ChatGPT answer |
| G3 | `as of (my last\|my knowledge\|the last) (update\|cutoff)`, `as an AI language model`, `I (cannot\|can't) browse`, `knowledge cutoff` | Knowledge-cutoff / assistant disclaimer |
| G4 | `\[(your name\|your title\|insert [^\]]+\|client name\|company name)\]`, `\bTODO\b.*\[.*\]` placeholder brackets left unfilled | Mad-libs placeholder never filled in |
| G5 | `\b(I hope this helps\|great question\|certainly!\|here'?s a (revised\|rewritten)\|let me know if)\b`, `^(Sure\|Certainly)[,!]` | Chatbot conversational artifact / sycophancy |
| G6 | a literal `“...”` curly-quote pair **and** an em-dash **and** no `\usepackage` for csquotes, in a doc otherwise using straight quotes | Pasted rich text retaining smart punctuation |

G1–G5 are plain regex — fast and reliable. G6 needs a judgement call; flag it for review rather than asserting. Report G-hits as `SMOKING GUN` severity.

## Step 2 — Structural heuristics

These are patterns no single phrase catches but humans can spot:

| ID | Heuristic | Detection |
| --- | --- | --- |
| H1 | **Em-dash overuse** | Count `—` (U+2014) per 1000 words. > 3 / 1000 → flag. Show density and list every line that has more than one em-dash. |
| H2 | **Hedge density** | Count hedge words (from the "hedge words and qualifiers" category) per 100 words. > 4 / 100 → flag. List the densest paragraph. |
| H3 | **Rule of three** | Pattern: `(\w+, ){2}\w+\b` (three coordinated adjectives/nouns/short phrases). Flag sentences with three or more such triads. |
| H4 | **"Not only X but Y"** | Pattern `\bnot only\b[^.]*?\bbut\b`. Flag and propose collapsing into a single declarative sentence. |
| H5 | **Vague closing -ing participle** | Sentences ending in `, [v]ing\s+\w+.*\.` where the participle adds editorial commentary rather than substance. Detection heuristic: sentence ends with `, \w+ing\b[^.]*\.` Flag for review. |
| H6 | **Outline-like conclusion** | Paragraph starting with `In summary` / `In conclusion` / `To conclude` / `Ultimately` / `In a nutshell` / `All in all` (already in catalog, but the *paragraph-initial* position is the strongest signal). |
| H7 | **Generic question opening** | Section or paragraph starting with `Have you ever wondered`, `What is the significance of`, `What if`, `Imagine`. |
| H8 | **Excessive boldface** | Count `\textbf{` per section. > 6 per page-equivalent (≈ 500 words) → flag. |
| H9 | **Editorialising adverbs cluster** | Two or more of {`absolutely`, `clearly`, `indeed`, `essentially`, `basically`, `arguably`} within 50 words of each other. |
| H10 | **False range** | `\bfrom\b [^.]{2,40} \bto\b` where the items aren't a real continuum. Detection is approximate — flag for human review rather than auto-rewrite. |
| H11 | **Negative parallelism** | `\bnot just\b[^.]*?\b(but\|it'?s)\b`, `\bit'?s not (just\|only)\b[^.]*?\bit'?s\b`. The "It's not just X, it's Y" cadence. Distinct from H4's "not only X but Y"; collapse to one clause. |
| H12 | **Synonym cycling / elegant variation** | The same entity referred to by rotating epithets to avoid repetition (e.g. "the model" → "the architecture" → "the system" → "the framework" for one thing). Detection is approximate: list candidate near-synonym noun clusters that co-refer within a paragraph; flag for human review. A *human* researcher repeats the precise term; AI varies it for "flow". |
| H13 | **"Whether…" paragraph closer** | Sentence (esp. paragraph-final) matching `\bwhether you (prefer\|are\|want\|need\|choose)\b[^.]*\bor\b`. Marketing cadence; rare in real papers. |
| H14 | **Structured-list syndrome** | Inline `\textbf{Header:}` / `\textbf{Header} --` openers repeated across ≥3 consecutive paragraphs or `\item`s (the `**Header:** description` shape, LaTeX form). Flag the run; suggest prose or a real `description` list. |
| H15 | **Symbolic gloss** | `\b(represents\|symboli[sz]es\|serves as a (reminder\|testament\|symbol)\|stands as a)\b` used to editorialise meaning rather than state a fact. Flag for review. |

Run these as a second pass after phrase matching. H1–H10 are deterministic regex; H11, H13, H14 are regex with a judgement check; H12 and H15 are judgement calls — surface them, don't auto-rewrite.

## Step 2b — Stylometric metrics (layer C)

Phrase and shape matching are lexical: an AI draft that avoids every catalog word still has an AI *distribution*. Run the metrics engine to measure it:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/ai-writing-check/scripts/ai-metrics.py" <file1.tex> [file2.tex ...]
# On systems where the binary is python3, substitute python3.
# Add --json for machine-readable output you can fold into the report.
```

The script strips LaTeX (comments, math, non-prose environments, citation/label commands) and reports, per file, a 0–100 **stylometric AI-signal** plus the raw metrics:

| Metric | AI-like reading | Academic-tuned breakpoint |
| --- | --- | --- |
| **Burstiness** (sentence-length CV) | uniform 15–20 word sentences → low CV | CV < 0.35 suspicious; the single strongest signal (weight 0.35) |
| **Punctuation entropy** (Shannon, bits) | only `.` and `,` | < 0.9 bits suspicious (weight 0.25) |
| **Opener diversity** | "The… The… This…" repeated openings | one first word opening > 40% of sentences, or < 70% unique first-two-words (weight 0.20) |
| **Connective density** (per 100 words) | however/moreover/furthermore overuse | > 1.3 / 100 words suspicious (weight 0.20) |
| **Type-token ratio**, **gzip compressibility**, **bigram repetition** | repetition signals | informational only — reported, not scored (too noisy on short/formal text) |

**How to use the number.** The composite is a *style smell*, not a verdict — it folds only the four robust metrics and is tuned so that formal-but-human academic prose lands LOW. Treat HIGH (≥60) as "look closely", MEDIUM (30–59) as "one or two structural tics", LOW (<30) as "reads human". The script prints `! too little prose for reliable stylometry` when a file has < 8 sentences or < 200 words — don't over-read the score there.

**Compare against the document's own baseline, not an absolute.** If one section scores 70 while the rest of the same paper sits at 25, that section is the suspect — relative spikes within one author's paper are more telling than the absolute value, which varies by subfield.

## Step 3 — Score and report

Group findings. Lead with smoking guns, then the stylometric scores, then the per-line lexical/structural findings:

```
AI-writing check  (intro.tex, methods.tex, related.tex)

SMOKING GUNS (near-certain chatbot provenance)
  related.tex:120  "utm_source=chatgpt.com" in a cited URL          (G2)
  methods.tex:88   "as of my last update"                           (G3)

Stylometric AI-signal (scripts/ai-metrics.py)
  related.tex   72 / 100  HIGH    burstiness 0.22, punct-entropy 0.81, "The" opens 55%
  intro.tex     34 / 100  MEDIUM  connective density 1.8 / 100w
  methods.tex   18 / 100  LOW
  → related.tex is the outlier vs. this paper's own ~25 baseline.

HIGH (likely robotic)
  intro.tex:14    "Delve into the world of"               → consider: "We study"
  intro.tex:14    sentence ends with vague -ing phrase    (H5)
  related.tex:88  "It is worth noting that"               → drop entirely, or "Note that" or "Notably,"
  related.tex:92  "not only [X] but [Y]"                  → rewrite as one clause (H4)
  related.tex:95  "It's not just faster, it's smarter"    → one clause (H11)

MEDIUM
  methods.tex:201 "Furthermore" 3rd time in 12 lines      → vary connectors
  methods.tex:240 "navigate the diverse"                  → "across the set of" or just describe what is varied
  methods.tex:267 hedge density 6.2 / 100 words           → assert what you can prove (H2)

LOW (cliché / stylistic)
  intro.tex:7     "cutting-edge"                          → "recent" or specific (e.g. "state-of-the-art on benchmark X")
  conclusion.tex:34 "in conclusion"                       → drop; the heading already says it

Density: 2 smoking guns, 11 high, 18 medium, 24 low across 3 files (≈ 4 500 words).

The sections with the highest AI signal: related.tex §2.1 (smoking gun + 72/100 + 4 high).
```

Always finish with one parseable summary line: `ai-writing: <G> guns, <H> high, <M> medium, <L> low; max-stylo <score>`.

## Step 4 — Propose rewrites

Ask the user which findings to fix. Do **not** auto-apply rewrites — academic voice is the author's. Suggested workflow:

> Want me to draft rewrites for the HIGH items? I'll show each as a diff. Reply with `all`, `none`, or a list of line numbers.

For each accepted finding, propose an `Edit`. The rewrite should:

1. **Preserve the technical claim.** Don't drop facts. If you'd have to omit information to remove the AI-ism, surface that to the user and let them rewrite.
2. **Match the surrounding voice.** Read 5 lines before and after to gauge register. Don't make one paragraph terse-Hemingway when the rest is formally academic.
3. **Be shorter, on average.** Most AI-isms inflate length. Compress.
4. **Stay neutral.** Strip editorialising ("clearly", "remarkably", "interestingly") unless the author would actually say that in this paragraph.
5. **Keep the LaTeX intact.** Don't touch `\cite{}`, `\ref{}`, math, or environment names. If the phrase is inside a `\section{}` or `\caption{}`, edit only the inner text.

### Example rewrites (use as a guide for register)

| AI-ish | Researcher-voice |
| --- | --- |
| "Delve into the intricacies of attention mechanisms." | "We analyse the attention mechanism." |
| "It is worth noting that the model converges faster with X." | "The model converges faster with X." |
| "This approach plays a pivotal role in modern NLP." | "This approach is now standard in NLP." |
| "Our method not only improves accuracy but also reduces latency." | "Our method improves accuracy and reduces latency." |
| "Furthermore, in addition, our results demonstrate that..." | "Our results show that..." |
| "Embark on a comprehensive exploration of..." | "We study ..." |
| "Cutting-edge transformer architectures" | "Recent transformer architectures" — or, better, cite the specific ones |
| "In conclusion, our work paves the way for..." | (delete; conclusion section heading already signals this) |

## Step 5 — Audit re-scan and final pass

After the user accepts a batch of rewrites, **re-run detection on the changed files** — rewriting AI-isms often introduces *new* ones (a fresh "Furthermore", a fresh triad), and a paraphrase can lower a phrase count while leaving the stylometric signal untouched. This audit-pass idea is borrowed from `blader/humanizer`; the point is that one detect→rewrite pass is rarely enough.

1. Re-run `scripts/ai-metrics.py` on the edited files. If a file's stylometric score did **not** drop after rewriting, the edits were cosmetic — say so plainly; don't claim a win the metric doesn't support.
2. Re-grep the G-group and the HIGH phrases on the edited region only.
3. Suggest a re-run of `instant-verify` (rewrites can introduce double spaces or stray punctuation).

Then commit:

```bash
git add -A && git commit -m "latex-sentinel: human-voice rewrites (<N> edits)" --allow-empty
```

## Honest limitations

Tell the user up front:
- A phrase appearing in the catalog does **not** mean it was written by an AI; humans use these phrases too. The check is a *style smell*, not a verdict. **Exception:** the Group-G smoking guns (chatbot markup, `utm_source=chatgpt.com`, cutoff disclaimers) are near-certain — those genuinely indicate paste-from-chatbot.
- The stylometric score is **calibrated for academic prose** but is still a smell, not proof. Formal venues run lower burstiness than blogs; a single number can't separate "careful formal author" from "AI". Use the *relative* spike within one paper, and never present the score as a detector verdict (it is not GPTZero/Turnitin and shouldn't be described as one).
- These metrics are exactly what AI *humanizer* tools optimise against — burstiness injection, punctuation variety, opener shuffling. A draft laundered through such a tool can score LOW while still being AI-written. A low score is **not** a clean bill of health.
- Domain conventions vary. Some venues (e.g. medical) genuinely use "It is worth noting" in the survey style — don't strip-mine domain conventions because the catalog flagged them.
- Hedge density depends on the field. Empirical work often hedges more than theory; that's appropriate.
- **Never accuse.** Report findings as style observations and rewrite suggestions. Do not tell the user (or let them tell a third party) that the text "is AI-generated" on the strength of these heuristics.

The goal is prose the *author* would write on a careful day, not prose stripped to a stylebook.
