# AI-writing phrase catalog

Compiled from:
- **ETBI Library — Signs of AI Writing** (library.etbi.ie/sources2/aisigns)
- **ChatGPT Overused Words and Phrases** (community-sourced list, see attached PDF reference)

Severity is the strength of the AI signal:
- **SMOKING GUN** — near-certain chatbot provenance; near-zero false positives. Handled as Group G in SKILL.md and reported above HIGH.
- **HIGH** — strong indicator on its own, almost always worth rewriting in academic prose.
- **MEDIUM** — common in AI output but also in human writing; flag if dense or contextually weak.
- **LOW** — cliché / stylistic; many fine human writers use these. Suggest only.

The "Suggested rewrite direction" is a *direction*, not a substitution. The skill should adapt to context.

---

## Category: Provenance smoking guns (Group G)

These are not style smells — they are artifacts that survive copy-paste from a chatbot and essentially never occur in hand-written LaTeX. One hit outweighs any number of style findings. Matched as regex in SKILL.md Step 1, Group G.

| Tell | Severity | Action |
| --- | --- | --- |
| `citeturn0search0` / `turn0news1` reference markup | SMOKING GUN | delete; the citation never resolved — this is leaked ChatGPT UI markup |
| `utm_source=chatgpt.com` in a URL | SMOKING GUN | the link was copied from a ChatGPT answer; verify the source independently |
| "as of my last update", "knowledge cutoff", "as an AI language model" | SMOKING GUN | delete; assistant disclaimer leaked into prose |
| unfilled placeholder brackets `[Your Name]`, `[insert citation]` | SMOKING GUN | fill or remove; a template was never completed |
| "I hope this helps", "Great question!", "Certainly! Here's…" | SMOKING GUN | delete; chatbot conversational turn leaked in |

## Category: Clichés and overused expressions

| Phrase | Severity | Suggested rewrite direction |
| --- | --- | --- |
| beacon of hope | HIGH | be specific about what it does |
| cutting-edge | MEDIUM | "recent", or name the specific work |
| dive into / dive into the world of | HIGH | "we study", "we examine" |
| game changer | HIGH | quantify the change |
| hustle and bustle | HIGH | drop or describe concretely |
| navigate the uncharted waters | HIGH | "explore" + the actual unknown |
| out of the box | MEDIUM | "novel" + what is novel |
| sights unseen / sounds unheard | HIGH | drop |

## Category: Complex and convoluted phrases

| Phrase | Severity | Suggested rewrite direction |
| --- | --- | --- |
| a comprehensive overview | MEDIUM | "an overview" |
| a dynamic interplay | HIGH | "interaction" — and say what interacts |
| a myriad of | MEDIUM | "many" or a count |
| a pivotal role | HIGH | say what role |
| at the core of | MEDIUM | "central to", "key to" |
| bridging the gap between | MEDIUM | "connects" or "links" |
| converge to forge a path | HIGH | drop; say the result |
| delve into | HIGH | "examine", "study", "look at" |
| delve into the world of | HIGH | "we study X" |
| evolving over time | MEDIUM | "changes" + how |
| from a holistic perspective | MEDIUM | drop, or "overall" |
| in the context of | LOW | "in", "for" |
| in-depth | LOW | "detailed" or drop |
| intricacies involved | MEDIUM | "details of" |
| navigate a complex maze | HIGH | drop the metaphor |
| on a broader scale | MEDIUM | "more generally", "at scale" |
| peel back the layers of this | HIGH | drop; "examine" |
| taking into account | LOW | "given", "considering" |
| the spectrum of | MEDIUM | "the range of" or be specific |
| transformative impact | HIGH | quantify the impact |
| uncover the layers of this | HIGH | drop |
| underpinning principles | MEDIUM | "the principles behind" |
| unraveling the mysteries of | HIGH | "explaining" |

## Category: Emphasising importance

| Phrase | Severity | Suggested rewrite direction |
| --- | --- | --- |
| a testament to | HIGH | "shows" or drop |
| continues to captivate | HIGH | drop |
| deeply rooted | MEDIUM | "long-established" or "long-standing" |
| highlights its significance | HIGH | say what is significant |
| is a testament | HIGH | "shows that" |
| key turning point | MEDIUM | "shift" + what shifted |
| leaves a lasting impact | HIGH | quantify or drop |
| plays a vital/significant/crucial role | HIGH | say the role |
| profound heritage | HIGH | drop or be specific |
| serves as | MEDIUM | "is" |
| solidifies | MEDIUM | "confirms" or "establishes" |
| stands as | MEDIUM | "is" |
| steadfast dedication | HIGH | drop |
| underscores its importance | HIGH | say *why* it matters |
| watershed moment | HIGH | drop unless precisely defended |

## Category: Engagement, introduction, and invitation phrases

These are almost never appropriate in academic prose.

| Phrase | Severity | Suggested rewrite direction |
| --- | --- | --- |
| delve into / delve into the world of | HIGH | "we study" |
| embark | HIGH | drop |
| here are several | MEDIUM | enumerate directly |
| in this article | LOW | usually fine, but sometimes redundant in a paper |
| in this blog post | HIGH | not academic |
| in this comprehensive guide | HIGH | "we describe" |
| in this guide | MEDIUM | "we describe" |
| in this travel guide | HIGH | not academic |
| join us | HIGH | drop |
| this article acts | HIGH | "this paper" + verb |
| this article aims | MEDIUM | "we aim", "we show" |
| this article embarks | HIGH | "this paper presents" |
| this article endeavors | HIGH | "we attempt", "we present" |
| this article invites | HIGH | drop |
| this article is your ticket | HIGH | drop |
| this article serves | MEDIUM | "this paper provides" |
| this article takes / takes you on a journey through | HIGH | "this paper covers" |
| this article will provide you with | MEDIUM | "this paper provides" |
| this guide is your companion | HIGH | not academic |
| we invite you to explore | HIGH | drop |
| your passport to unlocking | HIGH | drop |
| your ticket to unlocking | HIGH | drop |

## Category: Hedge words and qualifiers

Hedges are sometimes necessary in research writing — track *density* rather than presence. Heuristic H2 in the skill flags clusters.

| Phrase | Severity | Suggested rewrite direction |
| --- | --- | --- |
| apparently | LOW | "appears to", or assert / cite |
| arguably | MEDIUM | drop or attribute the argument |
| basically | MEDIUM | drop |
| by and large | MEDIUM | "in most cases" |
| essentially | MEDIUM | drop |
| fairly | LOW | quantify |
| for the most part | MEDIUM | "mostly" or quantify |
| frequently | LOW | quantify ("in N of M runs") |
| generally | LOW | "usually" or quantify |
| important to consider | MEDIUM | drop; lead with the consideration |
| important to remember | MEDIUM | drop |
| it could be argued | HIGH | attribute or assert |
| it depends on | LOW | say what it depends on |
| it is worth mentioning that | HIGH | drop the preamble |
| it should be noted that | HIGH | drop the preamble |
| occasionally | LOW | quantify |
| often | LOW | quantify |
| possibly | LOW | "may" or assert with citation |
| potentially | LOW | "may" + condition |
| presumably | MEDIUM | attribute or assert |
| quite | LOW | quantify |
| rather | LOW | quantify |
| relatively | LOW | quantify ("vs. baseline X") |
| seemingly | MEDIUM | "appears to" + cite, or drop |
| sometimes | LOW | quantify |
| somewhat | LOW | drop |
| to a certain degree | MEDIUM | quantify |
| to a certain extent | MEDIUM | quantify |
| to some extent | MEDIUM | quantify |
| typically | LOW | "usually" + condition |
| usually | LOW | quantify |

## Category: Problem-solution language

| Phrase | Severity | Suggested rewrite direction |
| --- | --- | --- |
| a solution for every | HIGH | drop the universal claim |
| designed to enhance | MEDIUM | "improves" + metric |
| enable | LOW | "lets" or specific verb |
| ensure | LOW | "make sure" or guarantee + condition |
| foster | MEDIUM | "support", "encourage" |
| revolutionize | HIGH | quantify the change |
| unlock the | HIGH | drop |
| harness the power of | HIGH | "use" |
| pave the way for | HIGH | "enables" or be specific |
| the challenge is | LOW | "the challenge:" or restate |
| the key issue is | LOW | "the issue:" |
| the question remains | LOW | state the question |

## Category: Promotional language

Almost always inappropriate in academic prose.

| Phrase | Severity | Suggested rewrite direction |
| --- | --- | --- |
| a gateway to | HIGH | "leads to" + specifics |
| a testament to | HIGH | "shows" |
| alluring individuals with | HIGH | drop |
| beacon of hope | HIGH | drop |
| beyond the surface allure | HIGH | drop |
| captivating exploration | HIGH | "study of" |
| captivating universe of | HIGH | drop |
| compelling journey | HIGH | drop |
| cutting-edge | MEDIUM | "recent" or be specific |
| designed to enhance | MEDIUM | "improves" |
| elevate | HIGH | "raises" + metric |
| embark on a journey of discovery | HIGH | drop |
| emerged as a popular | MEDIUM | "is widely used" + cite |
| game changer | HIGH | quantify |
| harness the power of | HIGH | "use" |
| holds a treasure trove | HIGH | drop |
| imagine | MEDIUM | drop (in academic prose) |
| join us | HIGH | drop |
| master the art of | HIGH | drop |
| navigate the uncharted waters | HIGH | drop |
| pave the way for | HIGH | "enables" + specifics |
| revolutionize | HIGH | quantify |
| rich tapestry | HIGH | drop |
| seamlessly marries the | HIGH | "combines" + how |
| this article is your ticket | HIGH | drop |
| unlock the | HIGH | drop |
| unveil the secrets | HIGH | "explain", "show" |
| your passport to unlocking | HIGH | drop |
| your ticket to unlocking | HIGH | drop |

## Category: Summary and conclusion

| Phrase | Severity | Suggested rewrite direction |
| --- | --- | --- |
| all in all | MEDIUM | drop |
| at the end of the day | HIGH | drop |
| in conclusion | LOW | drop if section heading is already "Conclusion" |
| in a nutshell | HIGH | drop |
| in summary | MEDIUM | drop in research papers |
| to conclude | MEDIUM | drop if heading already says so |
| to summarise | MEDIUM | drop in research papers |
| ultimately | LOW | drop or "finally" |

## Category: Transition words and phrases

Some are common in academic prose; flag *overuse* and *clustering*, not single occurrences.

| Phrase | Severity | Suggested rewrite direction |
| --- | --- | --- |
| absolutely | MEDIUM | drop |
| additionally | LOW | "also" or restructure |
| all things considered | MEDIUM | drop |
| although | LOW | fine in moderation |
| as a consequence | LOW | "so" |
| as a corollary | LOW | usually fine in proofs |
| as a general rule | MEDIUM | "usually" |
| as a matter of fact | HIGH | drop |
| as a result | LOW | "so" |
| as a rule | MEDIUM | "usually" |
| as an illustration | LOW | "for example" |
| because of this | LOW | "so" or "thus" |
| by comparison | LOW | fine; vary |
| by contrast | LOW | fine; vary |
| by extension | LOW | rephrase |
| by the same token | MEDIUM | drop |
| clearly | MEDIUM | drop; if it were clear you wouldn't need to say so |
| consequently | LOW | "so" or "thus" |
| despite | LOW | fine |
| even though | LOW | fine |
| for example | LOW | fine; vary with "e.g." or named example |
| for instance | LOW | fine |
| in fact | MEDIUM | drop or assert |
| in other words | MEDIUM | restructure so the second statement isn't needed |
| indeed | MEDIUM | drop |
| nevertheless | LOW | "still" |
| next | LOW | fine; vary |
| such as | LOW | fine; vary with "e.g." |
| that is to say | MEDIUM | restructure |
| therefore | LOW | "so" or "thus" |
| to elaborate | LOW | fine; vary |
| to illustrate | LOW | "for example" |
| to put it simply | MEDIUM | drop |
| while it may seem | MEDIUM | restructure |

## Category: Other words and phrases

| Phrase | Severity | Suggested rewrite direction |
| --- | --- | --- |
| alright | LOW | not academic |
| bustling | MEDIUM | be specific |
| dance (as a metaphor for interaction) | HIGH | name the actual interaction |
| diving | HIGH | "examining" |
| even if / even though | LOW | fine |
| everchanging / ever-evolving / ever-shifting | HIGH | "changes" + how |
| excels | MEDIUM | quantify ("outperforms by X%") |
| expanding | LOW | quantify |
| fancy | MEDIUM | drop |
| fast-moving / fast-paced | MEDIUM | drop |
| for the most part | MEDIUM | "mostly" or quantify |
| for this reason | LOW | "so" |
| gossamer | HIGH | drop |
| keen | MEDIUM | drop |
| leverage | MEDIUM | "use" |
| loom | MEDIUM | drop |
| metamorphosis | HIGH | "change" + how |
| needless to say | HIGH | drop |
| nestled | HIGH | drop |
| nexus | MEDIUM | "intersection of" or "point where" |
| nonetheless | LOW | "still" |
| not only [X] but [Y] | HIGH | merge into one clause (H4) |
| power (as a metaphor) | MEDIUM | name the capability |
| promptly | LOW | quantify |
| put simply | MEDIUM | restructure |
| rapidly | LOW | quantify |
| realm | MEDIUM | "field", "area" |
| remember that… | MEDIUM | drop or restructure |
| remnant | LOW | fine if literal |
| reverberate | MEDIUM | "affect", "carry over to" |
| sure | LOW | not academic in this register |
| to clarify | LOW | restructure so clarification isn't needed |
| to consider | LOW | fine; vary |
| to give an example | LOW | "for example" |
| to illustrate | LOW | "for example" |
| to make matters worse | MEDIUM | drop or "additionally" + the fact |
| to put it differently | MEDIUM | restructure |
| to put it simply | MEDIUM | restructure |
| to reiterate | MEDIUM | drop or restructure |
| to take one example | LOW | "for example" |
| to that end | LOW | "for this" or "to do this" |
| to this day | MEDIUM | "still" + cite |
| to this effect | MEDIUM | drop |
| to this end | LOW | "to do this" |
| towards | LOW | "to" or be specific |
| traverse the diverse / traverse the varied | HIGH | drop the metaphor |
| ultimately | LOW | drop or "finally" |
| uncover the layers of this | HIGH | drop |
| uncovering the science | HIGH | "studying" + topic |

---

## Formatting / structural patterns (handled in SKILL.md as heuristics H1–H15, listed here for completeness)

- **Excessive boldface** — `\textbf{}` density > ~6 per 500 words. (H8)
- **Em-dash overuse** — `—` density > 3 per 1000 words. (H1)
- **Title-case headings** — every main word capitalised in section titles.
- **Oxford-comma uniformity** — every list of ≥ 3 items has a serial comma, no exceptions.
- **American-English defaults** — `-ize` over `-ise`, `color` over `colour`, when the rest of the text uses British forms.
- **Rule of three** — three adjectives, three short phrases, three clauses, repeated. (H3)
- **Generic question opening** — "Have you ever wondered…?", "What is the significance of…?" (H7)
- **Outline-like conclusion** — "Despite ... " transitioning to a positive note at section end. (H6)
- **Vague closing -ing participle** — sentence ends with `, doing X` that adds editorial colour rather than substance. (H5)
- **Negative parallelism** — "It's not just X, it's Y". (H11)
- **Synonym cycling / elegant variation** — one entity renamed every mention ("the model" → "the architecture" → "the system") to avoid repetition; a human repeats the precise term. (H12)
- **"Whether…" closer** — "Whether you prefer X or Y…" marketing cadence. (H13)
- **Structured-list syndrome** — `\textbf{Header:}` openers repeated across consecutive paragraphs/items. (H14)
- **Symbolic gloss** — "represents", "symbolises", "serves as a testament" used to editorialise meaning. (H15)

## Stylometric metrics (computed by scripts/ai-metrics.py, layer C — see SKILL.md Step 2b)

These measure distribution, not vocabulary, so they catch AI text that uses no catalog phrase:

- **Burstiness** — coefficient of variation of sentence length; AI is uniform (low CV).
- **Punctuation entropy** — Shannon entropy of punctuation classes; AI uses only `.` and `,`.
- **Opener diversity** — repeated "The…/This…/It is…" sentence openings.
- **Connective density** — however/moreover/furthermore per 100 words.
- **Type-token ratio**, **gzip compressibility**, **bigram repetition** — secondary repetition signals (informational).
