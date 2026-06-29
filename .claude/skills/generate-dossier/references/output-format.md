# Account Dossier — Canonical Output Format

This document defines the exact structure of an Account Dossier. Every dossier must
follow this format so reps see a consistent layout as they flip between accounts.

---

## Document Header

```markdown
# [Account Name]

**Generated:** [YYYY-MM-DD]
**Quarter:** Q[X] [YYYY]
```

---

## Section 1: Account Overview

```markdown
## 1. Account Overview

**Account Overview**

| Field | Value |
| --- | --- |
| **Entity Type** | [Operating Company / Holding / MGA / etc.] |
| **Parent Brand** | [Parent group name] |
| **Account Tier** | [Tier 1 / Tier 2 / Tier 3] |
| **Account Type** | [Customer / Prospect / Other] |
| **Account Status** | [Active / Inactive] |
| **Account Maturity** | [New / Stabilising / Mature] |
| **Engagement Status** | [High / Medium / Low] |
| **hx Executive Alignment** | [Yes / No] |
| **Insurance Global Ranking** | [#N] |
| **Global Parent Size** | [XL / L / M / S] |
| **Employees** | [N] |
| **HQ** | [City, Country] |
| **Website** | [URL] |
| **AE / Owner** | [Name] |
| **SDR** | [Name] |
| **Pod** | [Pod name] |
| **Territory** | [Territory code] |

**GWP**

| Field | Value |
| --- | --- |
| **GWP (USD Billions)** | [N] |
| **Total LOB GWP $M** | [N] |
| **Account GWP $M** | [N] |
| **GWP in Pipeline** | [N] |
| **GWP Whitespace** | [N] |
| **Global Parent GWP (USD Millions)** | [N] |

**Key Child Entities**

| Entity | LOB GWP $M |
| --- | --- |
| [Entity name] | [N] |

**Business Description**

> [1-2 sentence description of the company]
```

---

## Section 2: Vision, Mission & Potential Sales Plays

```markdown
## 2. Vision, Mission & Potential Sales Plays

### Vision/Mission

| Vision/Mission | Source + Date | Evidence Strength | Notes |
| --- | --- | --- | --- |
| [statement] | [source — date] | [Explicit / Strongly implied / Weak / needs human review] | [notes] |

### Strategic Pillars

| Strategic Pillar | Source | Notes |
| --- | --- | --- |
| [pillar] | [source] | [notes] |

### What They're Saying about Topics of Interest

| Theme | Sources | Notes |
| --- | --- | --- |
| [theme] | [sources] | [notes] |

### Direct Quotes from People who Matter

| Theme / Pillar | Source | Origin | Quote |
| --- | --- | --- | --- |
| [theme] | [source] | [origin] | [quote] |

### Potential Sales Plays

#### Priority 1: [Normalized priority name]

- **What they care about:** [1 sentence paraphrase anchored to Phase 1 evidence]
- **Measures of Success:** [1-2 KPIs/metrics with units, or "Not stated in primary sources"]
- **Evidence:** [verbatim or near-verbatim evidence + source]
- **Common pain in this domain:** [category-level pain grounded in hx context]
- **hx solution(s) that address this domain:** [canonical solution names or "No direct hx alignment"]
- **Persona to engage on this:** [persona class only, never a named contact]
- **Discovery probes to consider:**
  - [Question 1]
  - [Question 2]
  - [Question 3]
```

Notes:
- The four research tables (Vision/Mission, Strategic Pillars, What They're Saying, Direct Quotes) come first — grounding artifacts from Phase 1.
- The Potential Sales Plays section follows with 3–5 priority blocks.
- Priority blocks use `####` headings to maintain hierarchy under `### Potential Sales Plays`.
- Use `<br>` between bullet points in table cells.

---

## Section 3: Who's Who — Top 10 Power Players

```markdown
## 3. Who's Who — Top 10 Power Players

> **Warning: this is a draft only created by AI. AEs should vet this carefully
> and update. Some fields left intentionally blank.**

| Contact Name | Title | Type | Champion Stage | hx Relationship(s) |
| --- | --- | --- | --- | --- |
| [Name] | [Title] | [Actuarial / Underwriting / Technology / Finance / Executive] | | |
```

Notes:
- Top 10 contacts maximum.
- Type categories: Actuarial, Underwriting, Technology, Finance, Executive.
- Champion Stage and hx Relationship(s) columns are intentionally blank — placeholders for AE input.
- Sort by relevance to hx (Chief Actuary / CUO first, then CIO/CTO, then CFO/COO/CEO).

---

## Section 4: Past Opportunities & Interactions

```markdown
## 4. Past Opportunities & Interactions

**Opportunities in Salesforce ([N] total)**

| Opportunity | Stage | ARR (Amount) | Owner | Notes |
| --- | --- | --- | --- | --- |
| [Opportunity name] | [Stage] | [Amount] | [Owner] | [Brief notes] |

---

**Notable Past Deal — [Deal Name]**

[Narrative paragraph describing the primary deal, its journey, key milestones,
and key contacts involved. Include timeline.]

---

**Notable Meetings (from Gong)**

**[Phase name] ([Date range])**

- [YYYY-MM-DD] **[Meeting title]** — [One-line summary]

---

**Key Themes**

- [Theme 1: brief description]
- [Theme 2: brief description]
- [Theme 3: brief description]
```

---

## Section 5: What People Are Saying

```markdown
## 5. What People Are Saying

| Theme | Sources | Notes |
| --- | --- | --- |
| 1. AI | [Source(s)] | [Key finding — 1 bullet point] |
| 2. Workflow modernization | [Source(s)] | [Key finding] |
| 3. Operational efficiency improvements | [Source(s)] | [Key finding] |
| 4. Data & analytics | [Source(s)] | [Key finding] |
| 5. Top-line growth ambitions | [Source(s)] | [Key finding] |
| 6. Loss ratio targets or performance | [Source(s)] | [Key finding] |
| 7. Expense ratio targets or performance | [Source(s)] | [Key finding] |
| 8. GWP scale, growth, or mix | [Source(s)] | [Key finding] |
| 9. Business expansion (geographic, product, distribution) | [Source(s)] | [Key finding] |
| 10. Recent CEO/executive statements and priorities | [Source(s)] | [Key finding] |
```

Notes:
- Exactly 10 rows, one per theme.
- If no evidence exists for a theme: Sources = "—", Notes = "Not found in reviewed primary sources."
- Sources should be 1–2 per row, preferring primary sources (annual reports, investor presentations).

---

## Section 6: Discovery Questions You Might Consider Asking

```markdown
## 6. Discovery Questions You Might Consider Asking

| # | Question | Persona | Strategic Theme | What It Surfaces |
| --- | --- | --- | --- | --- |
| 1 | [Question text — open-ended, references a specific finding from Section 2 or 5] | [Target persona, e.g. "Chief Underwriting Officer"] | [Linked strategic priority or theme from Section 2/5] | [What signal/pain this probes for] |
| 2 | ... | ... | ... | ... |
| 3 | ... | ... | ... | ... |
```

Notes:
- 3–5 questions. Aim for 3 by default; go to 4 or 5 only when distinct strategic initiatives or persona dynamics warrant it.
- Each question must reference a specific finding from Section 2 (Strategic Priorities) or Section 5 (What People Are Saying) — not generic discovery questions.
- Each question must map to a known hx pain point and be open-ended (not yes/no).
- Spread across at least two different personas across the full set.
- "What It Surfaces" should describe the qualifying signal the question probes for, in one short phrase.

---

## Document Footer

```markdown
---

*Generated by hx GTM OS — Account Dossier v1*
```

---

## Formatting Rules (apply across all sections)

- Generate output in raw markdown.
- Bold table headers and section names.
- Format all links as Markdown hyperlinks — never print bare URLs.
- Use bullet points (not dashes) inside table cells.
- Use `<br>` tags between bullet points in table cells for line breaks.
- Keep all content concise and business-like.
- Use the account's own language from their public materials where possible.
- Horizontal rules (`---`) separate major sections.
