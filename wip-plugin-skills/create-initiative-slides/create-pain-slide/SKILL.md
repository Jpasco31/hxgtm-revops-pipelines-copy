---
name: create-pain-slide
description: >
  Synthesize customer challenges from Gong call data (via Glean) and external
  research into a structured challenge table on a single PowerPoint slide. Use
  when a user asks to create a pain slide, challenge table, why-change slide,
  aggregate pains, or build a structured challenge summary for a customer account.
---

# Create Pain Slide

## What this skill does

Given a target account name, this skill:

1. **Researches** the account using external public sources (annual reports, investor
   presentations, earnings calls) and internal sources (Gong call transcripts
   retrieved via Glean).
2. **Synthesizes** the findings into a structured challenge table with 3-5 rows,
   each describing a key business pain area with evidence, metrics, and executive
   attribution.
3. **Generates** a single PowerPoint slide containing the table, ready for use in
   sales conversations.

The output is grounded in real evidence -- internal account intelligence is
prioritized over external research.

---

## Requirements

This skill requires:

- **Web search and fetch access** for researching public company materials.
- **Glean search** for retrieving Gong call transcripts (if available).
- **AskUserQuestion tool** for validation checkpoints.
- **Bash tool** for running the PowerPoint generation script.
- **hx-pptx skill** (sibling plugin, hx-core) for the shared template and
  `table_renderer` module.

---

## Workflow

### Step 0 -- Input collection

Use AskUserQuestion to ask:

> What account should I build the pain slide for?

Wait for the user's reply before taking any further action.

After receiving the Step 0 reply, assess whether the account name is ambiguous
(e.g., a parent group vs regional subsidiaries). If ambiguous, ask one follow-up
question to clarify before starting research. If the name clearly maps to a single
entity, proceed immediately.

### Step 1 -- Research: external data

**ALWAYS run this step.** Do not skip or abbreviate external research because
internal data will be provided later. Run Steps 1 and 2 fully before synthesizing.

Search for public information about the account's business challenges, strategic
priorities, and pain points. Look for:

- Annual reports and investor presentations
- Earnings calls and CEO letters
- Press releases about strategic initiatives
- Industry analysis mentioning the company

Focus on extracting:
- Strategic challenges and pain points discussed publicly
- Metrics, targets, and financial indicators
- Executive commentary and quotes
- Organizational context (who owns what)

### Step 2 -- Research: internal data (Glean)

If Glean is available, search it for recent Gong call transcripts related to the
account. Use queries like the account name combined with "challenges", "pain points",
"pricing", "strategy", "roadmap". Extract pain points, metrics, executive quotes,
and named stakeholders from the results.

If Glean is not available, post this message to the user and then **stop
completely**:

> Do you have any internal Gong call notes, call summaries, or account intelligence
> for **[account name]**? If yes, paste them below. If not, reply "none" and I'll
> work from external research only.

Do not call any tools, do not read any files, do not begin synthesis. Just post the
message above and end your turn. The user's next message is the internal data --
use it to proceed to Step 3.

**Source priority**: Internal evidence (Gong calls, account intelligence from Glean
or the user's reply above) always takes precedence over external research when
sources conflict. Both sources are used in synthesis regardless.

### Step 3 -- Synthesize into challenge table

**MANDATORY**: Read `references/transformation-rules.md` for the transformation
rules and output schema before synthesizing.

**MANDATORY**: Read `references/training-examples.md` for three worked examples
showing how raw input maps to structured output.

Combine external and internal evidence into 3-5 structured rows. Each row has
six columns:

| Column | Content |
|--------|---------|
| **Challenge** | Short label (2-4 words) |
| **Issue** | Root business/process problem |
| **Impact** | Consequences grouped by business meaning |
| **Measure** | Metrics, targets, financial values |
| **Org Context** | Named executive + quote |
| **Objective** | Action-oriented statement starting with a verb |

Apply the transformation rules from the reference doc. Key rules:
- Condense themes into short challenge labels
- Rewrite issues into clear business prose (never copy verbatim)
- Synthesize impacts into grouped business outcomes
- Extract all quantifiable indicators into Measure
- Always attribute Org Context to a named person
- Start Objectives with a strong verb (Consolidate, Automate, Enable)

**Checkpoint**: Present the draft table to the user in markdown format via
AskUserQuestion. Ask them to review and confirm before generating the slide.
Frame it as: "Here's the challenge table I've synthesized for [account]. Does
this look right before I generate the PowerPoint slide?"

Before proceeding to Step 4, run the **Completion Checklist** at the bottom of
this skill. Fix any failing items before generating the slide.

### Step 4 -- Generate PowerPoint slide

Once the user approves the table, ask where to save the file:

> "Where should I save the PowerPoint file? (e.g. `~/Desktop/zurich-pain-slide.pptx`)"

Then:

1. Write the table data as a JSON file. The JSON format is:

```json
{
  "account_name": "Company Name",
  "rows": [
    {
      "challenge": "Short label",
      "issue": "Root problem description",
      "impact": "Business consequences",
      "measure": "Metric 1<br>Metric 2<br>Metric 3",
      "org_context": "Name, Title. Quote: ...",
      "objective": "Action-oriented statement"
    }
  ]
}
```

Use `<br>` tags to separate multiple metrics in the Measure column.

2. Locate the **hx-pptx** skill directory. It lives in the `hx` (hx-core) sibling
   plugin. Find the path to its `skills/hx-pptx/` folder — you can derive it from
   the hx-pptx skill's own SKILL.md path (available in your loaded skills). Store
   that path as `HX_PPTX_DIR`.

3. Run the generation script with `PYTHONPATH` set so it can import `table_renderer`
   from hx-pptx:

```bash
PYTHONPATH="${HX_PPTX_DIR}/scripts:$PYTHONPATH" \
python ${SKILL_DIR}/scripts/generate_table_slide.py \
  data.json \
  -o <output-path-from-above>.pptx \
  -t "${HX_PPTX_DIR}/assets/hx-ppt-template.pptx"
```

Where `SKILL_DIR` is the directory containing this SKILL.md, and `HX_PPTX_DIR` is
the hx-pptx skill directory resolved in step 2.

If the hx template is not found at the resolved path, try without the `-t` flag
to generate a standalone branded slide.

**If the script fails** (Python not available, missing dependency, or any other
error), do not stop. Tell the user:

> "The PowerPoint generation script couldn't run in this environment.
> Here's what you can do instead:
> - The table data is saved as `data.json` — you can use it to generate the slide
>   manually by running the script locally once python-pptx is installed
>   (`pip install python-pptx`).
> - The markdown table above is ready to copy into a slide manually."

Then deliver the markdown table (from the Step 3 checkpoint) as the fallback output.

3. Deliver the file path to the user.

### Step 5 -- Sources summary

After delivering the slide, post a **Sources** section in the conversation.
This does NOT go inside the PowerPoint -- it sits in the conversation after the
deliverable.

Format:

**Sources**
- [Short document title](https://example.com) -- date
- Internal: Gong call with [person/topic] -- date (if available)
- ...

---

## Quality bar

The final output should:
- Reflect the account's real challenges, not a generic insurance industry template
- Contain 3-5 rows (never more than 5)
- Use the customer's business language, not hx product names or marketing speak
- Have short, label-like Challenge names (2-4 words)
- Include real metrics in Measure (no fabricated numbers)
- Attribute Org Context to named executives where possible
- Start every Objective with a strong verb
- Fit on a single PowerPoint slide at readable font sizes

---

## Formatting rules

- Generate the draft table in raw markdown for the user review checkpoint.
- Use `<br>` tags to separate multiple items within a single table cell.
- Bold challenge names in the markdown preview.
- Format all links as markdown hyperlinks -- never print a bare URL.
- Keep all cell content concise. Refer to the character limits in
  `references/transformation-rules.md` to ensure single-slide fit.

---

## Completion Checklist

Run this self-check at the end of Step 3, before generating the PowerPoint slide.
Tick off each item. If any item fails, fix the table before proceeding.

- [ ] `references/transformation-rules.md` was read before synthesizing
- [ ] `references/training-examples.md` was consulted to calibrate output quality
- [ ] Internal sources (Gong/Glean) were prioritized over external research where both exist
- [ ] Every Challenge label is 2-4 words (noun phrase, not a sentence)
- [ ] Every Measure cell contains only quantitative data -- numbers, ratios, targets, time costs (no qualitative statements)
- [ ] Every Objective starts with a strong verb (Consolidate, Automate, Enable, Accelerate, Increase, etc.)
- [ ] Every Org Context row names a specific executive with their title
- [ ] Row count is between 3 and 5 (never more than 5)
- [ ] No cell content was copied verbatim from source material -- all content was rewritten and sharpened
- [ ] The user reviewed the draft table and approved it before this step
