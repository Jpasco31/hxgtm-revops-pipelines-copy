---
name: create-initiative-slides
description: >
  Generate a 2-slide PPTX from an existing Account Dossier. Slide 1 shows the
  Vision/Mission and a numbered Sales Plays table (Priority, Measures of Success,
  hx Solution). Slide 2 shows the numbered Evidence table. Uses the hx PowerPoint
  template.
---

## Context Loading

Call `list_account_dossiers` (no parameters) to discover which Account Dossiers are
available on the MCP server. This returns a list of dossier filenames from the
server's `context/accounts/` directory.

If no dossiers are returned: STOP. Do not generate any output. Do not offer to create
one. An Account Dossier must exist before this skill can run -- it is the primary
data input, not optional enrichment.

Present the available dossiers to the user and let them select one. Then call
`load_account_dossier` with the account name (e.g. `"MetLife North America"`) to load
the selected dossier.

If either MCP tool is unavailable: STOP. Do not generate any output. Do not attempt
to work without the dossier. Follow the fallback procedure in
`${CLAUDE_PLUGIN_ROOT}/context/mcp-fallback.md` and do not proceed until the dossier
is loaded.

# Create Initiative Slides

## What this skill does

Given an Account Dossier, this skill extracts Section 2 -- Vision/Mission &
Potential Sales Plays -- and generates a 2-slide PPTX using the hx template:

- **Slide 1** -- Vision/Mission as the headline, Sales Plays table (numbered rows): Priority | Measures of Success | hx Solution
- **Slide 2** -- Evidence table (numbered rows matching Slide 1 priorities)

The numbering on both slides lets the AE quickly link each priority to its evidence
source during a conversation.

## Requirements

This skill requires:

- **Python + python-pptx** -- `pip install python-pptx lxml`
- **AskUserQuestion tool** for validation checkpoints.
- **Bash tool** for running the PowerPoint generation script.
- **hx-pptx skill** (sibling plugin, hx-core) for the shared template,
  `generate.py`, `validate.py`, and layout references.

## References

The hx-pptx skill in the sibling `hx` (hx-core) plugin provides the layout guide
and outline format reference. After resolving `HX_PPTX_DIR` in Step 5 below, read:

- `${HX_PPTX_DIR}/references/layout-guide.md` -- placeholder indices and character
  limits for every hx template layout. **Read this before writing the outline.**
- `${HX_PPTX_DIR}/references/outline-format.md` -- full outline syntax reference
  including table format and multi-line cell rules.

---

## Workflow

### Step 1 -- Discover and select the dossier

1. **MCP tool** -- call `list_account_dossiers`. This returns a list of available
   dossier files in `context/accounts/`.

2. **MCP fallback** -- if `list_account_dossiers` is unavailable, follow the fallback
   in `${CLAUDE_PLUGIN_ROOT}/context/mcp-fallback.md` to mount the local MCP repo,
   then list `.md` files in `context/accounts/` (excluding `.gitkeep`).

3. **No dossiers found** -- if the list is empty, hard stop. Do not offer to create
   one. Report to the user and do not proceed:

```
No account dossiers were found on the MCP server. To generate initiative slides,
an Account Dossier must first be added to the server's context/accounts/ directory.
Please contact your team to get one set up.
```

4. **Present the list using `AskUserQuestion`** -- use the `AskUserQuestion` tool
   to confirm or select the dossier. Do not proceed until the user responds:
   - If only one dossier exists, present it as a single option and ask "Which account
     dossier should I use?" with the one dossier as a choice.
   - If multiple dossiers exist, list each as an option in `AskUserQuestion` and ask
     the user to pick one.

5. **Load the dossier** -- once the user has selected, load the dossier content via
   `load_account_dossier` with the account name. If using the fallback, read the file
   directly from `context/accounts/[slug]-dossier.md` in the mounted repo.

### Step 2 -- Ask preferences

Once the dossier is loaded, ask the user:
1. Colour preference: Blue (default), Orange, or Green.
2. Output path: "Where should I save the PowerPoint file?
   (e.g. `~/Desktop/the-hartford-initiative-slides.pptx`)"

### Step 3 -- Parse Section 2

Section 2 of the dossier uses bullet-block "Potential Sales Plays" (one block per
priority), not markdown tables. Extract the following from that section:

1. **Locate Section 2.** Find the `## 2.` heading (the title may read
   `Vision, Mission & Potential Sales Plays` or similar -- match on the literal
   `## 2.` prefix). Everything from that heading up to the next `## ` heading is
   the Section 2 body.

2. **Extract Vision/Mission.**
   - Inside the Section 2 body, find the FIRST blockquote (a contiguous run of
     lines beginning with `> `) that appears before any `### ` sub-heading.
   - Line 1 of the blockquote holds the quote text wrapped in double quotes
     (after the leading `> `). A following italic line `> *Source: ...*` provides
     the attribution and may include a date or note.
   - **Quote text:** strip the leading `> `, then unwrap the surrounding double
     quotes, then trim whitespace.
   - **Label selection:**
     - If both `vision` and `mission` appear (case-insensitive) in the quote text
       OR the source line, use `Vision / Mission`.
     - Else if `mission` appears (case-insensitive), use `Mission`.
     - Else default to `Vision`.
   - **Fallback handling:** if the blockquote contains the line
     `> *Vision/Mission not confidently identifiable from primary sources.*`,
     set the label to `Vision / Mission` and the quote text to
     `Not confidently identifiable from primary sources`. The slide template
     will render the placeholder gracefully.
   - **Render** in the outline as `<!-- quote: [Label] | [Quote text] -->`.
     No character limit applies to this directive.

3. **Extract priority blocks.** Inside the Section 2 body, after the
   `### Potential Sales Plays` sub-heading, locate every block whose heading
   matches the regex `^### Priority (\d+): (.+)$`.
   - Capture group 1 is the priority number `(N)`; capture group 2 is the
     priority `(label)`. Use `(label)` for the Priority column on both slides.
   - Prepend a numbered `#` column independently (1, 2, 3...) so numbering
     matches between Slide 1 and Slide 2 -- do not reuse `(N)` as the row number.

4. **Parse the bullets within each block.** Each block contains bullets keyed
   by a bold label:
   - `- **What they care about:** ...`
   - `- **Measures of Success:** ...`
   - `- **Evidence:** ...` (may contain `[text](url)` hyperlinks -- PRESERVE them)
   - `- **Common pain in this domain:** ...`
   - `- **hx solution(s) that address this domain:** ...`
   - `- **Persona to engage on this:** ...`
   - `- **Discovery probes to consider:** ...` (followed by sub-bullets)

   For this skill, you only need: **Priority label**, **Measures of Success**
   content, **hx solution(s)** content, and **Evidence** content. Ignore the
   other bullets.

   **Bullet content extraction:** take the text after the `**Label:**` marker on
   the same line. If the bullet content runs onto subsequent indented
   continuation lines, include the continuation text up to the next top-level
   bullet or block boundary. Strip leading and trailing whitespace.

5. **Validation / skip rule:**
   - If a priority block is missing **all three** target bullets (Measures of
     Success, hx solution, Evidence), log a warning and skip that block. Do not
     abort the whole run.
   - If a priority block is missing 1 or 2 of the three target bullets,
     populate the missing cells with empty strings -- the validation step in
     Step 5 will catch problems.
   - If fewer than 1 priority block is found, abort with the actionable error:

     ```
     Section 2 contains no `### Priority N:` blocks. The dossier may be using an
     older schema. Regenerate the dossier with the latest
     `generate-dossier` skill, or report the bug.
     ```

### Step 4 -- Write the outline

Write a temporary outline file at `./outline.md` (current working directory):

```markdown
##
<!-- layout: Title1 -->
<!-- quote: Vision | [full quote text verbatim] -->

| # | Priority | Measures of Success | hx Solution |
|---|----------|--------------------|-------------|
| 1 | ...      | ...                | ...         |
| 2 | ...      | ...                | ...         |

##
<!-- layout: Title1 -->
<!-- ph:11 Evidence -->

| # | Priority | Evidence |
|---|----------|----------|
| 1 | ...      | ...      |
| 2 | ...      | ...      |
```

Cell-to-bullet mapping (from the priority blocks parsed in Step 3):
- Slide 1, column **Priority** = the priority `(label)` captured from
  `### Priority N: (label)`.
- Slide 1, column **Measures of Success** = the `Measures of Success` bullet content.
- Slide 1, column **hx Solution** = the `hx solution(s) that address this domain`
  bullet content.
- Slide 2, column **Priority** = same `(label)` as Slide 1, in the same row order.
- Slide 2, column **Evidence** = the `Evidence` bullet content.
- The `#` column on both slides is a sequential 1, 2, 3... assigned in row order so
  that Slide 1 row N matches Slide 2 row N.

Key rules:
- Every table cell that contains bullet points from the dossier should be condensed
  to plain text, removing markdown bullet syntax (`- `, `* `), keeping content readable.
- **Preserve any markdown hyperlinks** (`[text](url)`) -- do not strip them. The
  generator will render them as clickable links in the PPTX output.
- Cell content should be concise -- aim for <=120 chars per cell (excluding URL length).
  Truncate plain text with ... if needed, but never truncate a hyperlink.
- Do NOT include a cover slide -- these are content-only insert slides.

### Step 5 -- Locate hx-pptx and generate

1. **Resolve the hx-pptx skill directory.** It lives in the `hx` (hx-core) sibling
   plugin. Find the path to its `skills/hx-pptx/` folder -- you can derive it from
   the hx-pptx skill's own SKILL.md path (available in your loaded skills). Store
   that path as `HX_PPTX_DIR`.

2. **Generate the PPTX:**

```bash
python ${HX_PPTX_DIR}/scripts/generate.py \
  ./outline.md \
  -t ${HX_PPTX_DIR}/assets/hx-ppt-template.pptx \
  -o <output-path-from-step-2> \
  --colour <Blue|Orange|Green>
```

3. **Validate:**

```bash
python ${HX_PPTX_DIR}/scripts/validate.py \
  <output-path-from-step-2>
```

If validation fails, report the error clearly and stop. Do not delete the generated file.

4. **Clean up** the temporary outline file after successful generation:

```bash
rm ./outline.md
```

### Step 6 -- Report

Tell the user:

```
Initiative slides generated: <output-path>

  Slide 1 -- [Vision/Mission label]: "[quote]" + Sales Plays ([N] rows)
  Slide 2 -- Evidence ([N] rows)
  Colour: Blue
```
