# Transformation Rules

## Output Schema

The challenge table has six columns. Each column has a specific purpose and style:

| Column | Definition | Style guidance |
|--------|-----------|----------------|
| **Challenge** | A short descriptor labelling the pain area. | 2-4 words, noun phrase, not a sentence. Example: "Fragmented pricing tooling" |
| **Issue** | A concise summary of the core business or process problem. | Clear business prose, one to two sentences. Explain the root cause, not the symptom. |
| **Impact** | The consequences of the issue, synthesized into business outcomes. | Group related consequences into a coherent narrative. Frame in terms of revenue, risk, speed, talent, or operational efficiency. |
| **Measure** | Metrics, targets, financial values, ratios, time costs, or other quantifiable indicators. | List concrete numbers. Separate multiple metrics with line breaks. Use exact figures from sources when available. |
| **Org Context** | Named executive owner, stakeholder quote, or other organizational signal that grounds the problem in real business context. | Always attribute to a specific person by name and title. Include a direct quote when available. |
| **Objective** | An action-oriented statement describing what should be done in response. | Start with a strong verb (Consolidate, Automate, Enable, Accelerate, Increase). One sentence. Frame as a capability outcome, not a product pitch. |

## Transformation Rules

When converting raw source material (Gong call transcripts, strategy slides, research notes) into the structured challenge table, apply these rules:

1. **Condense** long headings or themes into short challenge labels (2-4 words).
2. **Rewrite** issue statements into clear business prose. Do not copy source text verbatim.
3. **Synthesize** multiple bullet points or discussion threads into grouped impact statements organized by business meaning.
4. **Extract** all numbers, goals, ratios, dollar values, time savings, and operational metrics into the Measure column. Do not mix qualitative impacts with quantitative measures.
5. **Include** named owners and direct quotes in Org Context. Every row should connect the problem to a specific executive or stakeholder.
6. **Rewrite** the implied need into an action-oriented Objective starting with a verb. Do not copy source goals verbatim.
7. **Normalize and sharpen** all content. Prefer concise, executive-ready wording throughout.
8. **Prioritize internal evidence** (Gong call transcripts, account intelligence) over external research. When internal and external sources conflict, internal wins.

## Character Limits (Single-Slide Fit)

The table must fit on a single 16:9 PowerPoint slide. Enforce these approximate limits per cell:

| Column | Max characters |
|--------|---------------|
| Challenge | 40 |
| Issue | 180 |
| Impact | 200 |
| Measure | 150 |
| Org Context | 180 |
| Objective | 150 |

If content exceeds these limits, tighten the language. Prioritize precision over completeness. It is better to have a sharp, shorter cell than a comprehensive but overflowing one.

The table should have **3-5 rows** (challenges). Default to the number that best represents the account's situation. Do not pad with weak challenges to reach 5, and do not compress genuinely distinct challenges to stay at 3.

## Good Output Characteristics

- Challenge is short and label-like (e.g., "Fragmented technology estate").
- Issue explains the root technical or process problem clearly.
- Impact groups consequences into business meaning (Revenue, Risk, Talent, Speed).
- Measure captures all available numbers, time costs, and volumes.
- Org Context always connects the problem to a specific executive or stakeholder reality.
- Objective starts with a strong verb (Consolidate, Automate, Enable, Accelerate).

## What to Avoid

- Copying raw source text verbatim.
- Mixing qualitative impacts with quantitative measures.
- Leaving the Objective as a copy of a source goal (rewrite for action).
- Using hx product names or marketing language in the table. Frame everything in the customer's business language.
- Including more than 5 challenges. If there are more than 5 candidate areas, select the top 5 by strength of evidence and business severity.
