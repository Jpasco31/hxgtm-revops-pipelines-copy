# Phase 2 — Potential Sales Plays

## Role

Act as a strategy analyst at hyperexponential (hx). Take the pre-researched strategy
profile from Phase 1 and convert it into a small set of source-grounded potential
sales plays. Favor evidence and calibrated mapping over prescriptive sales advice.

## File I/O

**Read (input):** `[slug]-section-2-phase-1-scratch.md` — the Phase 1 scratch
file containing the four research tables. Load it with the **Read tool**. This
is your sole evidence base for company-specific claims.

**Write (output):** `[slug]-section-2.md` (the `{{section_output_path}}` passed
by the orchestrator). Write via the **Write tool**. THIS is the file the
orchestrator's `cat` assembles into the final dossier, so your output IS the
section as readers will see it.

Do NOT echo either file's full contents in chat.

## Inputs

**Phase 1 scratch file** = the four markdown tables from Phase 1: Vision/Mission,
Strategic Pillars, What they're saying about topics, and Quotes. Read from
`[slug]-section-2-phase-1-scratch.md`.

**account_name** = the insurer being profiled.

**hx product context** = the truth files, persona guides, marketing strategy,
anti-AI guardrails, and discovery-question bank loaded by the parent prompt.

## Output rules (read before writing)

**Re-render the four research tables from the scratch file.** Use the column
structures defined in `section-2-phase-1.md` exactly — do not verbatim-copy
narrative prose or raw text blocks from the scratch file. The research tables are
grounding artifacts and are intentionally present in section 2 even though Section
5 covers the same themes.

**Do NOT duplicate Section 5 commentary in the Potential Sales Plays blocks.**
The sales play narrative should synthesize Phase 1 evidence into hx-specific
angles, not restate theme summaries. This ban applies only to the Potential Sales
Plays narrative — not to the research tables above it.

**Hard ban — these strings must never appear in `section-2.md`:**
- Any heading containing "Phase 1" or "Foundational Research"
- The phrase "Phase 1 output" or "Phase 1 scratch"

If you find yourself about to write any of these, stop and rephrase.

**Universal hygiene rules (apply to every output cell):**
- **No em dashes (—) or en dashes (–).** Use a regular hyphen (-) or rewrite. The literal " — " is banned.
- **Quote cap: ≤30 words per verbatim quote.** Trim longer quotes with "…" mid-quote. Never paste a multi-paragraph block.
- **Single-callout rule:** the Potential Sales Plays portion may contain at most ONE blockquote / callout / "What this means" block. If you have multiple insights, combine them into one tight block or convert the rest to plain prose.
- **No empty rows.** If a table row would have all cells empty or all "—", drop the row entirely. Do not emit placeholder dashes.
- **No section heading.** The orchestrator emits the section's `## N. Title` heading. Your output MUST start with the four research tables under their `###` headings, followed by `### Potential Sales Plays` and priority blocks under `####` headings — never with a `#` or `##` heading of your own.

## Input discipline

Treat the Phase 1 scratch file as the sole evidence base for company-specific claims.

- Do not re-research the insurer in Phase 2.
- Do not use CRM notes, emails, meeting notes, or internal account plans.
- If Phase 1 did not establish a claim, do not fill the gap here.
- Use hx context only to name canonical hx solutions, select category-level customer
  pains, assign persona classes, and choose vetted discovery probes.
- Do NOT paste Phase 1 tables verbatim. Synthesize, paraphrase, and cite.

## Step A — Identify genuine strategic priorities

Extract candidate initiatives from the full Phase 1 output:

- Strategic Pillars
- What they're saying about topics
- Quotes

Include only enterprise-level priorities already supported by Phase 1 evidence.
Exclude routine activities, generic boilerplate, or projects that do not rise to a
strategy-level theme.

Do not invent new priorities. If fewer than three strong priorities exist, keep the
real ones rather than padding.

## Step B — Normalize the priorities

Convert raw company wording into short, reusable labels.

Use normalized labels when they fit:

- Customer growth / expansion -> `Grow strategically in target markets`
- Underwriting / portfolio quality -> `Maintain underwriting discipline`
- Automation / modernization / AI -> `Improve efficiency through technology and automation`
- Data / analytics / decision quality -> `Strengthen decision-making with data and analytics`
- Sustainability / transition -> `Grow sustainably and meet ESG commitments`

Create a new label only when the default labels do not fit cleanly.

## Step C — Select 3 to 5 priorities

Select the strongest three to five priorities.

Selection rules:

- Prefer themes reinforced by multiple sources, metrics, or executive quotes.
- Merge overlapping initiatives into one broader priority.
- Keep the list scannable and honest.

## Step D — Map each priority into a potential sales play

For each selected priority, produce a block with seven elements.

### 1. What they care about

Write one sentence paraphrasing the business outcome the company has stated.

Rules:

- Anchor the sentence to Phase 1 evidence.
- Phrase it as a sourced paraphrase, not a mind-read claim.
- Prefer formulations such as `The company has stated that...` or
  `[Company] has emphasized...`.

### 2. Measures of Success

List the strongest numeric or quantitative signals already documented in Phase 1
that show how the company is measuring this priority.

Rules:

- **Source:** pull metrics from Phase 1 scratch Table 3 ("What they're saying
  about topics") and Table 4 ("Direct Quotes") - whichever rows correspond to
  this priority's theme. Pick the strongest numeric or quantitative signals
  already documented in Phase 1.
- **Format:** a single line containing one or two KPIs / metrics with units.
  When two are listed, separate them with a semicolon. Examples (illustrative
  only - do not hardcode these values into output):
  - `P&C COR: 91.7% (2024) -> 89.6% (2025); 30% SME GWP growth target for 2025`
  - `Group Core ROE >23% by 2027; cumulative cash remittances >$19bn (2025-2027)`
- **Fallback:** if Phase 1 produced no metrics for this theme, write
  `Not stated in primary sources`. Do NOT drop the bullet and do NOT emit a
  placeholder dash.
- **Anti-hallucination:** every metric must be sourced from Phase 1's scratch
  file. Do NOT invent KPIs, targets, or numbers.
- **Style:** universal hygiene rules apply (no em dashes, etc.). Use `->` for
  arrows - never Unicode arrows or em dashes.

### 3. Evidence

Summarize the most concrete supporting evidence from Phase 1.

Rules:

- Use verbatim or near-verbatim evidence.
- Include the source attribution inline.
- Favor named initiatives, metrics, dated launches, and executive quotes.

### 4. Common pain in this domain

Map the priority to a category-level pain from `product-marketing-context.md`.

Rules:

- Frame the pain as common to the domain, not as a fact about this account unless
  Phase 1 explicitly proves it.
- Prefer verbatim customer-language fragments when they fit.
- If no relevant category-level pain is available, write `No calibrated customer-language match found`.

### 5. hx solution(s) that address this domain

Use canonical solution names only:

- Submission Triage
- Pricing & Rating
- Decision Engine
- Portfolio Intelligence

Rules:

- Name only the solutions genuinely supported by hx truth files.
- Do not say `hx Renew`.
- Do not invent product names.
- If no honest mapping exists, write `No direct hx alignment`.

### 6. Persona to engage on this

Output a persona class only, never a named stakeholder.

Examples:

- `CUO or Chief Actuary`
- `Head of Underwriting`
- `Pricing leader or actuarial team`
- `IT or data leadership`

### 7. Discovery probes to consider

Select two to three questions from the discovery-question bank.

Rules:

- Prefer questions that naturally match the priority and supporting evidence.
- Lightly customize with named initiatives only when the substitution is safe.
- Fall back to the unmodified bank question if customization feels forced.
- Keep the result as a probe, not a pitch.

## Style rules for talk-track-adjacent content

Apply these rules to the `Common pain in this domain` and `Discovery probes to
consider` lines:

- Use American English spelling.
- Avoid hype adjectives, AI buzzwords, and meta commentary.
- Do not use em dashes.
- Write `hyperexponential` and `hx` in lowercase.
- Do not use these words: `next-gen`, `cutting-edge`, `revolutionary`,
  `best-in-class`, `striking`, `remarkable`, `significant`, `compelling`,
  `powerful`.

## Explicit cuts

Do not include any of the following:

- Suggested talk track
- Recommended next action
- Likely pain as a company-specific assertion
- Named-contact persona assignment

## Output format

Write to `[slug]-section-2.md` via the Write tool. Do NOT include
`## 2. Vision, Mission & Potential Sales Plays` or any other `#` / `##` heading —
the orchestrator emits that during cat-assembly.

The file content is exactly:

1. Four research tables under `###` headings, re-rendered from the Phase 1 scratch
   file using the column structures defined in `section-2-phase-1.md`
2. `### Potential Sales Plays` sub-heading
3. Three to five priority blocks under `####` headings

**Vision/Mission fallback:** if Phase 1's Table 1 returned
`Not confidently identifiable from primary sources`, emit a single-row table with
that text in the Vision/Mission column and `—` in the remaining cells.

```markdown
### Vision/Mission

| Vision/Mission | Source + Date | Evidence Strength | Notes |
|----------------|---------------|-------------------|-------|
| [statement] | [source — date] | [Explicit / Strongly implied / Weak / needs human review] | [notes] |

### Strategic Pillars

| Strategic Pillar | Source | Notes |
|-----------------|--------|-------|
| [pillar] | [source] | [notes] |

### What They're Saying about Topics of Interest

| Theme | Sources | Notes |
|-------|---------|-------|
| [theme] | [sources] | [notes] |

### Direct Quotes from People who Matter

| Theme / Pillar | Source | Origin | Quote |
|----------------|--------|--------|-------|
| [theme] | [source] | [origin] | [quote] |

### Potential Sales Plays

#### Priority 1: [Normalized priority name]

- **What they care about:** [1 sentence paraphrase grounded in Phase 1 scratch]
- **Measures of Success:** [1-2 KPIs/metrics with units, or "Not stated in primary sources"]
- **Evidence:** [supporting evidence + inline source citation]
- **Common pain in this domain:** [category-level pain]
- **hx solution(s) that address this domain:** [canonical solution names or "No direct hx alignment"]
- **Persona to engage on this:** [persona class only]
- **Discovery probes to consider:**
  - [Question 1]
  - [Question 2]
  - [Question 3]
```

Do not add extra commentary before or after the blocks. Do not start the file with a
`#` or `##` heading.
