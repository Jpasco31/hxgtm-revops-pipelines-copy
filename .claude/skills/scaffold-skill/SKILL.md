---
name: scaffold-skill
description: >
  Use this skill when the user asks to create a new skill, scaffold a skill,
  add a content type to an existing skill, wire a new skill across repos, or
  set up a new slash command for the GTM OS. This skill generates everything
  needed for a new skill or content type to work correctly across both repos
  (hx-plugins and hxgtm-mcp-server) — SKILL.md, content-type playbooks,
  context.ts wiring, command wrappers, mcp-fallback manifest, and Notion
  documentation. It handles the six wiring points so the author can focus on
  the skill's logic rather than remembering which files to touch. NOT for
  editing or refactoring existing skills — this skill creates new ones.
  NOT for auditing wiring — use context-lint instead. NOT for optimizing
  trigger descriptions — use skill-creator instead. Trigger phrases:
  'create a new skill', 'scaffold a skill', 'add a content type',
  'wire a new skill', 'set up a new command'.
---

# Scaffold Skill

## What This Skill Does

Creates new skills and content types across the two interlocking GTM OS repos:

- **Plugins** (`hx-plugins/plugins/<plugin-name>/`) — SKILL.md files, command wrappers, and plugin manifests
- **MCP** (`hxgtm-mcp-server/`) — Brand truth, shared guidance, and content-type playbooks served at runtime via `load_skill_context` and `load_guidance`

Adding a new skill or content type requires touching **both repos** in a specific order. There are six wiring points — missing any one breaks the skill in production:

| # | Wiring Point | Repo |
|---|---|---|
| 1 | SKILL.md (skill definition + context loading block) | Plugins |
| 2 | Content-type playbook (editorial or lint-based guidance) | MCP |
| 3 | `context.ts` `SKILL_CONTEXTS` entry | MCP |
| 4 | `GUIDANCE_MAP` entry per content type | MCP |
| 5 | Command wrapper(s) | Plugins |
| 6 | `mcp-fallback.md` section with accurate file counts | Plugins |

Plus three supporting updates: README index, save-to-Notion routing (if content-producing), and Notion "Agents & Skills" documentation.

This skill handles all of them.

## Requirements

All three are **hard-stop conditions** — if any fails, no files are generated:

1. **Both repos accessible** — hx-plugins and hxgtm-mcp-server must be reachable via production or local fallback paths
2. **Both repos in clean git state** — no uncommitted changes (ensures scaffold output is isolated and revertible)
3. **Notion MCP connected** — every scaffolded skill must ship with Notion documentation

## Deciding What to Build

Answer three questions before writing any files:

**1. Full skill or new content-type only?**
- Full skill: new AI capability that doesn't exist yet → Steps 0–10 below
- New content-type within an existing skill (e.g., a new LinkedIn format for the `linkedin` skill) → abbreviated workflow at the bottom

**2. Which plugin?**
- `hx-marketing` — marketing content (copy, campaigns, web, social, email, ads)
- `hx-sales` — sales intelligence (competitive, research, account strategy)
- `hx-sdr` — personal outreach (cold email, follow-ups, sequences)
- `hx-core` — cross-role (presentations, utilities)

**3. Does it chain to `polish`?**
- Yes for any skill that produces copy-ready marketing content
- No for research, data, save/utility, and non-marketing skills

---

## Workflow — New Skill

### Step 0 — Plan mode check + conversational planning

#### Phase A: Plan mode gate

Plan mode is the right place to run Batches 1–3 (identity, behavior, wiring
details) and the Step 2 wiring plan review: it lets the user see everything
that will be created before any files are touched. Once the wiring plan is
approved, plan mode **must be exited** — the actual scaffold execution
(Steps 3–9) writes files across both repos and cannot run under plan mode's
read-only constraint.

Check whether plan mode is currently active (indicated by "Plan mode is
active" in the system context).

**If plan mode is NOT active**, use AskUserQuestion to prompt the user:

> "Scaffold-skill creates files across two repos and edits context.ts. The
> planning phases (identity, behavior, wiring plan) are safer in plan mode
> so you can review everything before execution. Switch to plan mode now?
> You'll be prompted to exit plan mode after the wiring plan is approved."

Options:
- "I'll switch to plan mode" — stop; resume from Phase B on re-invocation
- "Proceed without plan mode" — continue to Phase B

**If plan mode IS active**, proceed directly to Phase B. After Step 2 (wiring
plan approval), call `ExitPlanMode` to leave plan mode before Step 3 writes
files. If the user rejects `ExitPlanMode`, treat that as "cancel scaffold"
and stop cleanly — do not attempt to write files under plan mode.

#### Phase B: Conversational planning

From the user's brief, determine what's known and what's missing. Ask targeted
questions in batches to fill gaps. Pre-populate answers inferred from the brief
and ask the user to confirm or correct.

**Batch 1 — Identity** (required before anything else):

Use AskUserQuestion to present inferred values for confirmation:

1. **Mode**: Full skill or content-type-only? If the brief mentions an existing
   skill by name + a new format, auto-detect content-type-only. Otherwise
   default full-skill.
2. **Skill name**: Suggest a kebab-case name derived from the brief
   (e.g., "case study skill" → `draft-case-study`).
3. **Target plugin**: Infer from domain keywords. If ambiguous, ask.
4. **One-line purpose**: Draft from the brief.

**Batch 2 — Behavior** (depends on Batch 1 answers):

5. **Content types**: What content-type variants does this skill support? Each
   becomes a playbook file + `GUIDANCE_MAP` entry.
6. **Chains to polish?**: Infer from skill type. Yes for copy-producing, no for
   research/utility. Confirm if ambiguous.
7. **Input types**: What does the skill accept? List required vs optional.
8. **Output format sections**: Suggest the section list from the closest existing
   pattern (editorial, review/lint, or research).

**Batch 3 — Wiring details** (depends on Batch 2):

9. **Command wrappers**: How many, and what `Content-type:` headers? Default: one
   per content type.
10. **Saves to Notion?**: If content-producing, ask for Working + Reference DB IDs.
11. **MCP base context files**: Which truth/guidance files should the loader
    include? Suggest by examining the closest existing skill's loader in
    `context.ts`.

**Convention-driven defaults:** For anything the user doesn't specify, derive from
the closest existing skill and state what is being defaulted and why.

**If the brief is detailed enough** to cover most parameters, collapse to a single
confirmation: present all inferred values in a summary table and ask the user to
confirm or correct.

### Step 1 — Pre-flight checks

Three hard-stop checks. If any fails, print a clear message and refuse to
proceed — no files are generated.

**1a. Repo access (two-tier detection):**

Resolve paths for both repos independently:

1. Check if `Projects/Plugins/plugins/` exists (production path). If yes, set
   `plugins_source_root = Projects/Plugins/`, `plugins_source_mode = production`.
2. If not, check if `../hx-plugins/plugins/` exists (local fallback). If yes, set
   `plugins_source_root = ../hx-plugins/`, `plugins_source_mode = local`.
3. If neither exists, **hard-stop**: "Cannot find the Plugins repo. Expected at
   `Projects/Plugins/plugins/` or `../hx-plugins/plugins/`. Clone hx-plugins as a
   sibling directory and re-run."

Same pattern for MCP:

1. Check if `Projects/MCP/src/context.ts` exists. If yes, set
   `mcp_source_root = Projects/MCP/`, `mcp_source_mode = production`.
2. If not, check if `../hxgtm-mcp-server/src/context.ts` exists. If yes, set
   `mcp_source_root = ../hxgtm-mcp-server/`, `mcp_source_mode = local`.
3. If neither exists, **hard-stop**.

The two sources resolve independently — production Plugins + local MCP is valid.

**1b. Clean git state:**

Run `git status --porcelain` in both repos. If either returns non-empty output,
**hard-stop**: "The [Plugins/MCP] repo has uncommitted changes. Please commit or
stash your work before scaffolding. This ensures all scaffold-generated changes
are isolated and you can revert cleanly with `git checkout .` if needed."

**1c. Notion MCP availability:**

Check available tools for any tool name containing `notion`. If no Notion tools
are found, **hard-stop**: "Notion MCP is not connected. Every scaffolded skill
must ship with Notion documentation. Please configure the Notion MCP connector
and re-run."

**1d. Baseline the context validator:**

Run:

```bash
cd ${mcp_source_root} && bash scripts/validate-context.sh > /tmp/scaffold-validate-baseline.txt 2>&1 || true
```

Capture the output *before* any scaffold changes are made. Pre-existing
failures are NOT a hard-stop — they become the baseline to compare against
in Steps 7d and 9. Main branches often carry pre-existing missing-file
errors that are unrelated to the scaffold; capturing them here prevents the
scaffold from getting stuck in a fix loop trying to correct files it did
not create.

**Present pre-flight summary via AskUserQuestion:**

```
Pre-flight check:

| Check | Status | Details |
|-------|--------|---------|
| Plugins repo | [production / local / FAIL] | [resolved path] |
| MCP repo | [production / local / FAIL] | [resolved path] |
| Plugins git state | [clean / DIRTY] | [file count if dirty] |
| MCP git state | [clean / DIRTY] | [file count if dirty] |
| Notion MCP | [available / UNAVAILABLE] | [tool detected / not configured] |
| Validator baseline | [N pre-existing failures captured] | `/tmp/scaffold-validate-baseline.txt` |

All pre-flight checks passed. Proceed with scaffolding?
```

If any check fails, do NOT offer "Proceed" — present only the error messages
and stop.

Options (only when all pass):
- "Proceed" — continue to Step 2
- "I'll fix my setup first" — stop and let the user resolve issues

### Step 2 — Present wiring plan

Before creating any files, present a complete list of everything that will be
created or modified:

```
Wiring plan for <skill-name>:

Sources:
- Plugins: [production/local] — [resolved path]
- MCP:     [production/local] — [resolved path]

Files to CREATE:
- [path to SKILL.md]
- [path to playbook 1]
- [path to playbook 2 (if applicable)]
- [path to command wrapper 1]
- [path to command wrapper 2 (if applicable)]

Files to MODIFY:
- [path to context.ts] — add SKILL_CONTEXTS entry + GUIDANCE_MAP entries
- [path to mcp-fallback.md] — add skill section with file counts
- [path to README.md] — add to Skills + Commands tables
- [path to save-to-notion/SKILL.md] — add routing row (if content-producing)

Notion:
- Create sub-page under "Agents & Skills" with skill documentation

Validation:
- Run validate-context.sh
- Walk wiring checklist (references/wiring-checklist.md)
- Generate 3 test prompts

Proceed?
```

Wait for user approval before proceeding.

**Plan mode exit gate:** If plan mode is still active at this point, call
`ExitPlanMode` now — Steps 3–9 write files and cannot run under plan mode.
If the user rejects the exit, stop cleanly.

### Step 3 — Create the SKILL.md

Plan mode must be exited before this step runs. Use the annotated template
in `references/skill-template.md`. Apply the description quality rules from
that file's "Description Quality Rules" section:

- **Imperative form**: "Use this skill when..." not "This skill is for..."
- **100-200 words**: long enough for concrete trigger phrases, short enough for
  always-in-context
- **3-5 trigger phrases**: realistic things a user would say
- **Should-not-trigger redirects**: explicitly name adjacent skills
- **Progressive disclosure**: SKILL.md body under ~500 lines; move detail to
  `references/`

The section order is mandatory — all existing skills follow it exactly:

1. YAML frontmatter (`name`, `description`)
2. `## Context Loading` block
3. `## Mandatory Workflow` block (only if skill chains to polish)
4. `# [Skill Title]` heading
5. `## Purpose`
6. `## When to Use`
7. `## Inputs`
8. `## [Detection / Mode sections]` (if applicable)
9. `## Output Format` — numbered sections in exact order
10. `## Examples` — 2–4 concrete examples (user intent → assistant behavior)
11. `## Guidelines`
12. `## Quality Gate` (only if writing skill)
13. `## Skill Chaining — Required Final Step` (only if chains to polish)

Save to: `${plugins_source_root}plugins/<plugin>/skills/<skill-name>/SKILL.md`

### Step 4 — Create Content-Type Playbooks in MCP

For each content type the skill supports, create one playbook file. Choose the
right template from `references/content-type-templates.md`:

- **Editorial playbook** — social, web, ads. Covers: definition, core principle,
  required structure, do's/don'ts, tone checklist, success signals.
- **Lint-based playbook** — email. Covers: definition, numbered lint rules
  (severity/detection/rationale/fix), rewrite macros, sequence logic, tone/voice,
  inline examples.

Place files in the correct MCP channel directory:

| Channel | Directory |
|---------|-----------|
| Social (LinkedIn/X) | `${mcp_source_root}context/marketing/guidance/social/content-types/` |
| Email | `${mcp_source_root}context/marketing/guidance/email/content-types/` |
| Web | `${mcp_source_root}context/marketing/guidance/web/content-types/` |
| Ads | `${mcp_source_root}context/marketing/guidance/ads/content-types/` |
| Workflow (task-level) | `${mcp_source_root}context/marketing/guidance/workflows/` |
| Sales | `${mcp_source_root}context/sales/guidance/content-types/` |

Sales skills use their own top-level `sales` `GUIDANCE_MAP` key (not
`marketing`). When scaffolding the first content type under a new channel
(e.g., sales), create a new top-level key in `GUIDANCE_MAP` rather than
adding to an existing channel.

All content-type files use this frontmatter:

```yaml
---
type: guidance
scope: [<content-type-slug>]
last_reviewed: <YYYY-MM-DD>
---
```

If a content type has account/voice sub-variants (e.g., company vs exec), create
a subdirectory: `content-types/<type-name>/company.md` and
`content-types/<type-name>/exec.md`.

### Step 5 — Wire context.ts (direct edit)

Edit `${mcp_source_root}src/context.ts` directly with two changes. Because the
pre-flight check ensures a clean git working tree, the author can review all
changes via `git diff` and revert with `git checkout` if anything looks wrong.

**5a. Add a new entry to `SKILL_CONTEXTS`** (the existing object at ~line 81).
`SKILL_CONTEXT_MAP` is auto-generated from the keys of `SKILL_CONTEXTS` via
`Object.fromEntries(...)` at the bottom of the file — there is no separate
registration step and no `load<SkillName>Context()` function to write.

```typescript
const SKILL_CONTEXTS: Record<string, ContextEntry[]> = {
  // ... existing entries ...
  "<skill-name>": [
    "pack:marketing-content-base",            // reusable bundle
    "marketing/marketing-strategy.md",
    // ... add other truth/guidance files this skill needs
  ],
};
```

Use `pack:<name>` to include a reusable bundle from `CONTEXT_PACKS` (e.g.,
`marketing-content-base` = product-marketing-context + policies +
anti-ai-guardrails). Pull the right combination from existing entries as a
starting point. The `linkedin` skill uses 5 files; `email` uses 13; match the
scope to the task. Paths are relative to `context/` (no leading slash, no
`context/` prefix).

**5b. Add guidance entries to GUIDANCE_MAP** (one entry per content type):

```typescript
const GUIDANCE_MAP: Record<string, Record<string, string>> = {
  // If the channel key already exists, add to the existing object.
  // If new, add a new top-level key.
  "<channel-or-category>": {
    "<content-type-slug>": "marketing/guidance/<channel>/content-types/<name>.md",
  },
};
```

Never create a duplicate top-level key — add to the existing channel object if
it already exists.

### Step 6 — Create Command Wrappers

Each command is a thin 3-part file. Commands set a `Content-type:` header and
shell out to the skill:

```markdown
---
description: <One sentence — what this command does>
---

Content-type: <content-type-slug>

!`cat ${CLAUDE_PLUGIN_ROOT}/skills/<skill-name>/SKILL.md`
```

For commands with no specific content-type (e.g., `save-to-notion`,
`webinar-campaign-kit`), omit the `Content-type:` line:

```markdown
---
description: <One sentence>
---

!`cat ${CLAUDE_PLUGIN_ROOT}/skills/<skill-name>/SKILL.md`
```

Save to: `${plugins_source_root}plugins/<plugin>/commands/<command-name>.md`

Naming convention: action-object in kebab-case matching the content type.
Examples: `li-promote-blog.md`, `email-action-follow-up.md`,
`edit-webinar-lp.md`.

### Step 7 — Update Support Files

Four files to update; all four are required:

**7a. `mcp-fallback.md`**

Path: `${plugins_source_root}plugins/<plugin>/context/mcp-fallback.md`

Add a section following the exact format of existing entries. Count files
precisely — the expected total is validated at runtime:

```markdown
### <skill-name>

**Expected: N base context files + M guidance files = N+M total reads before drafting.**

**Base context (`load_skill_context`):**
- `<path/to/file-1.md>`
- `<path/to/file-2.md>`

**Guidance (`load_guidance`):**
- `<content-type-slug>` - `<path/to/content-type.md>`
```

**7b. `save-to-notion` routing** (only if skill produces copy-ready content
users will want to save to Notion)

Add one row to the Database Routing table in
`${plugins_source_root}plugins/hx-marketing/skills/save-to-notion/SKILL.md`:

```markdown
| `<skill-name>` | <Display type label> | `<Working DB ID>` | `<Reference DB ID>` |
```

Also add a `Type` → `Sub Type` detection entry in the Content Type Detection
section.

**7c. README index**

Path: `${plugins_source_root}README.md`

Add the skill to the appropriate plugin's Skills table. Add any new commands to
the Commands table in the same plugin section.

**7d. Run the context validator (delta check):**

```bash
cd ${mcp_source_root} && bash scripts/validate-context.sh > /tmp/scaffold-validate-after.txt 2>&1 || true
diff /tmp/scaffold-validate-baseline.txt /tmp/scaffold-validate-after.txt
```

The script greps `context.ts` for all file paths and verifies each exists on
disk. Only NEW `MISSING:` lines (present in `after` but not in the baseline
captured in Step 1d) belong to this scaffold and must be fixed. Pre-existing
failures are reported to the user as "pre-existing — not caused by this
scaffold" and left alone. Fix only the delta before proceeding to Step 8.

### Step 8 — Publish to Notion

Create a new sub-page under the "Agents & Skills" parent page.

**8a. Find the parent page:**

Use `notion-search` to find a page titled "Agents & Skills". If multiple results,
select the one that is a parent page (not a database or sub-page).

**8b. Inspect existing sub-pages:**

Before creating, fetch the parent page to see how existing skill sub-pages are
structured. Match the convention for headings, sections, and formatting.

**8c. Create the sub-page:**

Use `notion-create-pages` to create a sub-page containing:

- **Skill name** and **plugin** (e.g., `draft-case-study` in `hx-marketing`)
- **Purpose**: one-line description from SKILL.md
- **When to use**: trigger phrases and use cases
- **Inputs**: required and optional, with descriptions
- **Output**: what the skill produces
- **Commands**: list of slash commands that invoke this skill
- **Chains to polish**: yes/no
- **Content types supported**: list with descriptions

### Step 9 — Validate (auto-fix and report)

1. Re-run the delta check from Step 7d. Only NEW `MISSING:` lines (absent from
   `/tmp/scaffold-validate-baseline.txt`) count as failures caused by this
   scaffold.
2. If new failures exist, attempt to auto-fix:
   - Mistyped file path in the `SKILL_CONTEXTS` entry → correct the path
   - Missing file that should have been created in Step 4 → create it from
     template
   - Re-run delta check after each fix attempt.
3. Walk the wiring checklist (`references/wiring-checklist.md`) — all items
   must pass.
4. Report results to the user, grouped:
   - **Passed**: items that validated successfully
   - **Auto-fixed**: items that failed but were corrected automatically
   - **Pre-existing (ignored)**: missing-file errors already in the baseline —
     unrelated to this scaffold; flag them to the user as separate work
   - **Remaining failures**: items the author must address manually

### Step 10 — Generate test prompts

Generate 3 realistic test prompts that a user would say to invoke this skill:

1. **Straightforward invocation** — a clear, direct request
   (e.g., "draft a case study for Zurich based on the recent win")
2. **Edge case / ambiguous phrasing** — something a user might say that should
   still trigger this skill
   (e.g., "can you write up the Zurich deal?")
3. **Should-not-trigger** — a prompt that sounds similar but should redirect to
   a different skill, with the expected redirect noted
   (e.g., "send a cold email to Zurich" → should trigger `draft-outreach` instead)

Save to: `${plugins_source_root}plugins/<plugin>/skills/<skill-name>/test-prompts.md`

For deeper trigger optimization, use `/skill-creator` with these test prompts as
a starting eval set.

---

## Workflow — Content-Type Only

When adding a content type to an existing skill (e.g., a new LinkedIn format,
a new email variant):

### Step 0 — Planning

Same conversational planning as the full workflow, but scoped:

1. Identify the **existing skill** this content type belongs to
2. Identify the **content type name** (kebab-case slug for `GUIDANCE_MAP`)
3. Identify the **channel** (social, email, web, ads, workflow)
4. Select the **playbook template** (editorial or lint-based)

Present a scoped wiring plan showing only the files that will be created/modified.

### Step 1 — Pre-flight

Same three hard-stop checks as the full workflow (repo access, clean git state,
Notion MCP).

### Step 2 — Create playbook

Select the correct template from `references/content-type-templates.md`
(editorial for social/web/ads, lint-based for email). Place in the correct MCP
directory under `${mcp_source_root}context/`. Ensure YAML frontmatter `scope`
slug exactly matches the planned `GUIDANCE_MAP` key.

### Step 3 — Wire GUIDANCE_MAP

Add one entry to the existing channel object in
`${mcp_source_root}src/context.ts`. Do NOT touch `SKILL_CONTEXTS` — the
existing skill's entry already handles base context; new content-types load
on-demand via `GUIDANCE_MAP`.

### Step 4 — Create command wrapper (if applicable)

Optional but recommended for specific-format content types. The `Content-type:`
header must match the new `GUIDANCE_MAP` key. Save to
`${plugins_source_root}plugins/<plugin>/commands/<command-name>.md`.

### Step 5 — Update mcp-fallback.md

Add the new guidance key to the existing skill's section in
`${plugins_source_root}plugins/<plugin>/context/mcp-fallback.md`. Increment the
expected file count (base stays the same, guidance count increases by 1).

### Step 6 — Update Notion sub-page

Find the existing skill's sub-page under "Agents & Skills" using `notion-search`.
Update it to include the new content type in its supported formats list using
`notion-update-page`.

### Step 7 — Validate

Run `validate-context.sh`. Confirm the new content type loads correctly via the
existing skill's `load_guidance` call. Walk the content-type-only section of the
wiring checklist.

---

## Paths at a Glance

After path resolution in Step 1, all paths use `${plugins_source_root}` and
`${mcp_source_root}`. The table below shows the logical component mapping:

| Component | Path |
|-----------|------|
| Plugin skill | `${plugins_source_root}plugins/<plugin>/skills/<skill-name>/SKILL.md` |
| Content-type playbook | `${mcp_source_root}context/<channel>/guidance/content-types/<name>.md` |
| Shared channel guidance | `${mcp_source_root}context/<channel>/guidance/shared/` |
| Base context entry | `${mcp_source_root}src/context.ts` → new `SKILL_CONTEXTS` key (auto-exposed via `SKILL_CONTEXT_MAP`) |
| Guidance mapping | `${mcp_source_root}src/context.ts` → `GUIDANCE_MAP` |
| Command wrapper | `${plugins_source_root}plugins/<plugin>/commands/<command-name>.md` |
| MCP fallback | `${plugins_source_root}plugins/<plugin>/context/mcp-fallback.md` |
| Notion routing | `${plugins_source_root}plugins/hx-marketing/skills/save-to-notion/SKILL.md` |
| README index | `${plugins_source_root}README.md` |

---

## Additional Resources

- **`references/skill-template.md`** — Annotated, copy-ready SKILL.md template with every mandatory section and description quality rules
- **`references/content-type-templates.md`** — Editorial playbook template and lint-based playbook template with inline guidance
- **`references/wiring-checklist.md`** — Validation checklist covering all wiring points across both repos, including Notion documentation
