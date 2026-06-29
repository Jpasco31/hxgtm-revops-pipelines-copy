---
name: create-pain-slide
description: >
  Synthesize customer challenges from Gong call data (via Glean) and external
  research (or an existing Account Dossier) into a structured challenge table
  on a single PowerPoint slide. Use when a user asks to create a pain slide,
  challenge table, why-change slide, aggregate pains, or build a structured
  challenge summary for a customer account.
---

# Create Pain Slide

## What this skill does

Given a target account, this skill:

1. **Sources data** — either from an existing Account Dossier (if one has been
   generated for this account) or from fresh external research (annual reports,
   investor presentations, earnings calls), plus internal Gong call data via Glean.
2. **Synthesizes** the findings into a structured challenge table with 3–5 rows,
   each describing a key business pain area with evidence, metrics, and executive
   attribution.
3. **Generates** a single PowerPoint slide containing the table, ready for use in
   sales conversations.

The output is grounded in real evidence — internal account intelligence is
prioritized over external research.

---

## Requirements

- **AskUserQuestion tool** — for validation checkpoints and the dossier/research
  choice at Step 0.
- **Web search and fetch access** — for external research (research path only).
- **Glean search** — for retrieving Gong call transcripts (always runs).
- **Bash tool** — for running the PowerPoint generation script.
- **`scripts/generate_table_slide.py`** and **`scripts/table_renderer.py`** —
  both co-located in `.claude/skills/create-pain-slide/scripts/`.

---

## Workflow

### Step 0 — Dossier check

Check for an existing Account Dossier in two ways, in order of priority.

---

#### Path A — Dossier generated earlier in this conversation

Check whether `/generate-dossier` was run earlier in this conversation. You can
tell because the conversation will contain the dossier content and a message
confirming it was saved to `outputs/generate-dossier/`.

If a dossier **was** generated in this conversation, use AskUserQuestion to ask:

> You generated a dossier for **[account name]** earlier in this conversation.
> Shall I use it for the pain slide?
>
> Options:
> - "Yes — use the [account name] dossier"
> - "No — I'd like to use a different dossier from the outputs folder"
> - "No — I'll provide an account name and you can do fresh research"

- **User confirms** → proceed to **Step 1b** using that dossier.
- **User wants a different dossier** → fall through to **Path B** below.
- **User wants fresh research** → ask for account name, then proceed to
  **Step 1a**.

---

#### Path B — No dossier in this conversation, check outputs folder

If no dossier was generated in this conversation (or the user chose "use a
different dossier" in Path A), scan `outputs/generate-dossier/` for any `.md`
files using the Glob tool with pattern `outputs/generate-dossier/*-dossier.md`.

**If one or more dossier files are found**, use AskUserQuestion to ask:

> I found the following Account Dossiers in this project:
>
> [list each filename, formatted as the account name derived from the kebab-case
> filename — e.g. `zurich-north-america-dossier.md` → "Zurich North America"]
>
> Would you like to use one of these for the pain slide? Using a dossier skips
> external web research and uses the strategic intelligence already gathered.
>
> Options:
> - Pick a dossier by name
> - "No — I'll provide an account name and you can do fresh research"

- **User picks a dossier** → proceed to **Step 1b** (skip Step 1a).
- **User declines** → ask for the account name, then proceed to **Step 1a**.

**If no dossier files are found**, use AskUserQuestion to ask:

> What account should I build the pain slide for?

Wait for the reply, then proceed to **Step 1a**.

---

After resolving Step 0, if the account name is ambiguous (e.g. a parent group vs
regional subsidiary), ask one follow-up question to clarify before proceeding.

---

### Step 1a — Research: external data (research path only)

**Only run this step if no dossier was selected in Step 0.**

**ALWAYS run this step fully.** Do not skip or abbreviate external research
because internal data will be provided later. Run Steps 1a and 2 fully before
synthesizing.

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

---

### Step 1b — Extract from Account Dossier (dossier path only)

**Only run this step if a dossier was selected in Step 0.**

Read the chosen dossier file from `outputs/generate-dossier/`. Extract the
following from it:

- **Section 2 (Vision, Mission & Strategic Priorities)** — strategic priorities,
  measures of success, required capabilities, and the evidence table
- **Section 3 (Who's Who)** — executive names, titles, and types to populate
  Org Context
- **Section 5 (What People Are Saying)** — key findings across the 10 themes
  (especially: AI, workflow modernization, operational efficiency, data & analytics,
  growth, loss ratio, GWP, executive statements)

Treat this extracted content as the external data layer for synthesis. Do not
do any web searching on this path.

---

### Step 2 — Research: internal data (Glean)

**Always run this step, on both paths.**

If Glean is available, search it for recent Gong call transcripts related to the
account. Use queries like the account name combined with "challenges", "pain
points", "pricing", "strategy", "roadmap". Extract pain points, metrics,
executive quotes, and named stakeholders from the results.

If Glean is not available, post this message to the user and then **stop
completely**:

> Do you have any internal Gong call notes, call summaries, or account
> intelligence for **[account name]**? If yes, paste them below. If not,
> reply "none" and I'll work from the dossier / external research only.

Do not call any tools, do not read any files, do not begin synthesis. Just post
the message above and end your turn. The user's next message is the internal
data — use it to proceed to Step 3.

**Source priority**: Internal evidence (Gong calls, account intelligence from
Glean or the user's reply above) always takes precedence over external research
or dossier content when sources conflict. All available sources are used in
synthesis regardless.

---

### Step 3 — Synthesize into challenge table

**MANDATORY**: Read `.claude/skills/create-pain-slide/references/transformation-rules.md`
for the transformation rules and output schema before synthesizing.

**MANDATORY**: Read `.claude/skills/create-pain-slide/references/training-examples.md`
for three worked examples showing how raw input maps to structured output.

Combine the external/dossier data and internal Gong evidence into 3–5 structured
rows. Each row has six columns:

| Column | Content |
|--------|---------|
| **Challenge** | Short label (2–4 words) |
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

---

### Step 4 — Generate PowerPoint slide

Once the user approves the table, save the PowerPoint file to:

```
outputs/create-pain-slide/[account-name-kebab-case]-pain-slide.pptx
```

For example: `outputs/create-pain-slide/zurich-north-america-pain-slide.pptx`.

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

2. Locate the skill's scripts directory. It is at
   `.claude/skills/create-pain-slide/scripts/` relative to the repo root.
   Store this as `SKILL_SCRIPTS_DIR`.

3. Run the generation script. Both `generate_table_slide.py` and
   `table_renderer.py` are co-located in `SKILL_SCRIPTS_DIR`, so no PYTHONPATH
   manipulation is needed:

```bash
python .claude/skills/create-pain-slide/scripts/generate_table_slide.py \
  data.json \
  -o outputs/create-pain-slide/[account-name]-pain-slide.pptx \
  -t .claude/skills/create-pain-slide/assets/hx-ppt-template.pptx
```

If the template is not found at the above path, try without the `-t` flag to
generate a standalone branded slide.

**If the script fails** (Python not available, missing dependency, or any other
error), do not stop. Tell the user:

> "The PowerPoint generation script couldn't run in this environment.
> Here's what you can do instead:
> - The table data is saved as `data.json` — you can use it to generate the
>   slide manually by running the script locally once python-pptx is installed
>   (`pip install python-pptx`).
> - The markdown table above is ready to copy into a slide manually."

Then deliver the markdown table (from the Step 3 checkpoint) as the fallback
output.

4. Deliver the file path to the user.

---

### Step 5 — Sources summary

After delivering the slide, post a **Sources** section in the conversation.
This does NOT go inside the PowerPoint — it sits in the conversation after the
deliverable.

Format:

**Sources**
- [Short document title](https://example.com) — date
- Dossier: `outputs/generate-dossier/[filename]` — date generated (if dossier path)
- Internal: Gong call with [person/topic] — date (if available)

---

## Quality bar

The final output should:
- Reflect the account's real challenges, not a generic insurance industry template
- Contain 3–5 rows (never more than 5)
- Use the customer's business language, not hx product names or marketing speak
- Have short, label-like Challenge names (2–4 words)
- Include real metrics in Measure (no fabricated numbers)
- Attribute Org Context to named executives where possible
- Start every Objective with a strong verb
- Fit on a single PowerPoint slide at readable font sizes

---

## Formatting rules

- Generate the draft table in raw markdown for the user review checkpoint.
- Use `<br>` tags to separate multiple items within a single table cell.
- Bold challenge names in the markdown preview.
- Format all links as markdown hyperlinks — never print a bare URL.
- Keep all cell content concise. Refer to the character limits in
  `.claude/skills/create-pain-slide/references/transformation-rules.md` to ensure
  single-slide fit.

---

## Completion Checklist

Run this self-check at the end of Step 3, before generating the PowerPoint slide.
Tick off each item. If any item fails, fix the table before proceeding.

- [ ] `references/transformation-rules.md` was read before synthesizing
- [ ] `references/training-examples.md` was consulted to calibrate output quality
- [ ] Internal sources (Gong/Glean) were prioritized over external/dossier sources where both exist
- [ ] Every Challenge label is 2–4 words (noun phrase, not a sentence)
- [ ] Every Measure cell contains only quantitative data — numbers, ratios, targets, time costs (no qualitative statements)
- [ ] Every Objective starts with a strong verb (Consolidate, Automate, Enable, Accelerate, Increase, etc.)
- [ ] Every Org Context row names a specific executive with their title
- [ ] Row count is between 3 and 5 (never more than 5)
- [ ] No cell content was copied verbatim from source material — all content was rewritten and sharpened
- [ ] The user reviewed the draft table and approved it before this step
