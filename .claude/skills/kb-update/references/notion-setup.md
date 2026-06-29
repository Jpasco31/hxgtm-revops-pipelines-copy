# kb-update — `--notion-setup` flow

## Contents
- When to run this flow
- Prerequisites
- Flow overview
- Step 1: Status check (informational)
- Step 2: Discover the landing page in Notion
- Step 3: Discover existing child databases
- Landing-page guardrail (halt-early banner)
- Step 4: Reconcile `config.yaml` with Notion reality
- Step 5: Re-check provisioning status
- Step 6: Generate creation plan for remaining groups
- Step 7: Create missing per-group databases
- Step 8: Write back, verify, and report

## When to run this flow

Triggered by `/kb-update --notion-setup [--group <slug>]`. This
short-circuits SKILL.md Step 1; no input file is required and no
comparison happens.

Three invocations:

- `/kb-update --notion-setup` — no slug → `AskUserQuestion` with one
  option per active group plus an "All groups" option.
- `/kb-update --notion-setup --group <slug>` — provision (or
  reconcile) only that group's DB. Normal path for adding a newly
  configured group without touching the other 10.
- `/kb-update --notion-setup --group all` — explicit bypass of the
  prompt, equivalent to bulk reconcile.

The goal is to create (or reconcile) the Notion database structure
kb-update publishes into:

```
📚 KB - Updates Review                   (landing page, workspace-level)
├── KB - <Group Label>                   (database, one per group)
├── …
```

The critical invariant: **never create a Notion object that already
exists.** Even if `config.yaml` has blank `notion_data_source_id`
values, the landing page or some databases might already exist in
Notion (user wiped config but not Notion, cloned the repo to a new
machine, etc.). Always check Notion first, recover existing IDs, and
only create what's genuinely missing.

## Per-group database schema

Every per-group database is provisioned from the single `SCHEMA_DDL`
block in [setup_notion.py](../scripts/setup_notion.py) — 21 columns
total, 12 visible + 9 hidden. One default view (`Triage`) filtered to
`Status = Pending Review OR Status = Needs Restage`, grouped by
**Review Bucket** (Needs Decision first), sorted Date Added desc.
Review Bucket is a formula that collapses `Pending Review` +
`Needs Restage` into a single `Needs Decision` bucket and passes the
other statuses through unchanged — so reviewers see one stack per
decision state instead of one stack per entity.

Visible by default (12, in display order):

| # | Column | Type | Purpose |
|---|---|---|---|
| 1 | Name | TITLE | `R<N>: <short finding title>` |
| 2 | Status | SELECT | `Pending Review` → `Approved` → `Needs Restage` → `Rejected` → `Integrated` |
| 3 | Reviewer | PEOPLE | Human tags themselves during triage. Never written by publisher |
| 4 | Current Text | RICH_TEXT | ≤400-char preview of the canon line being replaced (empty for append) |
| 5 | Proposed Updated Text | RICH_TEXT | Paraphrased replacement content kb-integrate writes to canon |
| 6 | Final Updated Text | RICH_TEXT | Reviewer's partial-approval tweak. Never written by publisher. kb-integrate prefers this over Proposed Updated Text when non-empty |
| 7 | Rationale | RICH_TEXT | 1–3 sentences; named attribution + quotes supporting the finding |
| 8 | Entity | SELECT | Competitor / persona / account the finding is about (options seeded reactively) |
| 9 | Source Tier | SELECT | Tier 1–5 source-trust marker |
| 10 | Section | RICH_TEXT | Exact canon heading the finding attaches under (e.g. `Weaknesses / watch-outs`, `Notes / open questions`). RICH_TEXT because section sets vary per group |
| 11 | Closes Open Question | RICH_TEXT | For replace actions resolving a `Notes / open questions` bullet, the exact text being closed |
| 12 | Source file | RICH_TEXT | Upload filename |

Hidden by default (9 — shown on the row detail panel):

| Column | Type | Purpose |
|---|---|---|
| Target file | RICH_TEXT | Canon path relative to `context/`. Hidden from the triage table but still used by kb-integrate when applying approved rows |
| Action | SELECT | `Append` or `Replace` — how kb-integrate applies the edit. Publisher writes it; hidden from the triage table since reviewers rarely need it during decision-making |
| Review Bucket | FORMULA | Derived from Status: `Pending Review` + `Needs Restage` → `Needs Decision`; others pass through. Drives `group_by` in the default view; Notion renders it as the group header so the column itself stays hidden to avoid duplication |
| Category | SELECT | Always `raw-canon-conflict` for kb-update today |
| Severity | SELECT | High / Medium / Low |
| Date Added | DATE | Run date |
| Source Line | NUMBER | Line in the raw source |
| Target Line Start | NUMBER | 1-indexed first line of the replace/append span |
| Target Line End | NUMBER | 1-indexed last line (inclusive) |

## Prerequisites

- Notion MCP connector enabled in the current Claude environment.
- `python3` on PATH (stdlib only; no `pip install` needed).
- `.claude/skills/kb-update/config.yaml` readable at the repo root.

## Flow overview

1. Read `config.yaml` to know which groups exist.
2. Search Notion for the `KB - Updates Review` landing page.
3. If landing page missing → halt with manual-step banner.
4. For every expected child database, check Notion reality.
5. Reconcile `config.yaml` with what actually exists in Notion (recover
   stale IDs; blank missing ones).
6. Create only the databases that are genuinely missing.
7. Write back resolved UUIDs to `config.yaml` and cache them in
   `.kb-local.json`.

## Step 1 — Resolve scope

If `--group all` → bulk mode, proceed to Step 2.

If `--group <slug>` → single-group mode. Validate the slug against
`.claude/skills/kb-update/config.yaml`; halt on unknown slug with the active
groups list. Proceed to Step 2.

If no `--group` → `AskUserQuestion` with one option per active group
(label `KB - <Group Label>`) plus a final **"All groups"** option.
Map the selection to single-group or bulk mode.

## Step 2 — Discover the landing page in Notion

Call:

```
mcp__claude_ai_Notion__notion-search
  query: "KB - Updates Review"
  query_type: "internal"
  filters: {}
  page_size: 5
```

Filter results to `type: "page"` with the exact title
`KB - Updates Review`.

For each match, call `mcp__claude_ai_Notion__notion-fetch` with the
page `id` to load the actual state. The fetched `<page>` tag carries a
`deleted` attribute (e.g. `<page url="..." icon="📚" deleted>`) when
the page is in Notion trash.

Pick the first match whose `<page>` tag has **no** `deleted`
attribute. Record its `id` as `landing_page_id`. If the only matches
are trashed — or there are no matches at all —
`landing_page_id = null`. Trashed pages are treated as missing for
provisioning purposes.

**Cache the result** via:

```
python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py \
    landing-page-id-set --id <landing_page_id>
```

## Step 3 — Discover existing child databases

If `landing_page_id` is non-null, the fetch response from Step 2
already contains `<database url="..." data-source-url="collection://UUID">...</database>`
tags for every child database. For each such tag:

- Skip it if it has the `deleted` attribute (e.g.
  `<database url="..." inline="false" deleted data-source-url="...">`)
  — a trashed child database is treated as missing.
- Otherwise record `existing_dbs[<title>] = <UUID>` where `<title>` is
  the database title (inner text of the tag) and `<UUID>` comes from
  the `data-source-url="collection://UUID"` attribute.

If `landing_page_id` is null, `existing_dbs = {}`.

## Landing-page guardrail (halt-early banner)

If `landing_page_id` is null after Steps 2–3, halt with the banner
below **before** touching `config.yaml`. Never auto-create the landing
page: `notion-create-pages` with no parent lands in the caller's
Private workspace, which is almost never the right location for a
team-visible triage index. The user must pick the location once via
the Notion UI; every subsequent `/kb-update --notion-setup` re-discovers
it via `notion-search` no matter where they moved it.

```
⚠️  KB - Updates Review landing page not found in Notion.

First-time setup requires you to create the landing page yourself
so you control where it lives (which teamspace, visible to your
team, etc.). The Notion MCP cannot place a page at a team-visible
location automatically — it can only create pages in your private
workspace, which is almost never where you want it.

Steps:
  1. In Notion, create a new page titled exactly:

         KB - Updates Review

     Place it under the teamspace / parent page where you want
     kb-update's databases to live.
  2. Re-run /kb-update --notion-setup.

     It will discover the page via notion-search, create the 11
     per-group databases as children, and write the new data
     source IDs into .claude/skills/kb-update/config.yaml. The landing
     page itself is never touched by setup — only you place it.
```

Exit the skill after printing this banner. `config.yaml` is not
modified in this path — if the user re-runs after creating the landing
page, reconciliation (Step 4) runs from a clean state.

## Step 4 — Reconcile `config.yaml` with Notion reality

Read `.claude/skills/kb-update/config.yaml`. In **single-group mode**,
iterate only over that one group; in **bulk mode**, iterate over
every group in the file. For each group in scope, compute the
expected database title: `KB - <label>` (from the group's `label`
field).

- **Case A — live Notion database exists, config has matching UUID**:
  no-op.

- **Case B — live Notion database exists, config is blank or has a
  different UUID**: use the Edit tool to write the Notion UUID into
  the group's `notion_data_source_id` field. Also cache it via:

  ```
  python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py \
      write-notion-id --group <slug> --id <uuid>
  ```

  Add the group to a `recovered` list. This also correctly handles the
  "config has a stale UUID because the old Notion object was trashed
  and a new one was created" case — Notion reality wins.

- **Case C — no live Notion database, config has a UUID**: the config
  value points at a deleted or missing Notion object. Use the Edit
  tool to blank it (`notion_data_source_id: ""`) so the next step
  treats this group as missing and recreates it. Add the group to a
  `stale` list.

- **Case D — no live Notion database, config is blank**: no-op (the
  group will be created in Step 7).

## Step 5 — Check what's still missing

Run:

```
python3 .claude/skills/kb-update/scripts/setup_notion.py --status
```

After Step 4's reconciliation, `missing_groups` reflects what
actually needs to be created in-scope.

- In **single-group mode**: if the target group is already in
  `provisioned_groups` AND was not in the `recovered` / `stale`
  lists, print "Group `<slug>` already provisioned and verified
  against Notion." and exit. Otherwise continue to Step 6.
- In **bulk mode**: if `all_provisioned: true` AND `recovered` /
  `stale` are empty, print "All groups already provisioned and
  verified against Notion." and exit. If `all_provisioned: true`
  with recovered entries, print the recovered list and exit. If
  still missing groups, continue to Step 6.

## Step 6 — Generate creation plan

**Single-group mode:**

```
python3 .claude/skills/kb-update/scripts/setup_notion.py --plan \
    --group <slug> --landing-page-id <landing_page_id>
```

**Bulk mode:**

```
python3 .claude/skills/kb-update/scripts/setup_notion.py --plan \
    --landing-page-id <landing_page_id>
```

Either call returns `databases[]` — one entry per group to create.
Single-group mode forces exactly one entry regardless of
`config.yaml` state (used by reactive repair too — see
[publish.md §3b](publish.md)).

## Step 7 — Create missing per-group databases

By this point `landing_page_id` is guaranteed non-null (the guardrail
after Step 3 would have halted otherwise), so we only create child
databases — never the landing page itself.

For each entry in `plan.databases`, call `notion-create-database`
with:

```json
{
  "parent": {"type": "page_id", "page_id": "<landing_page_id>"},
  "title": "<entry.title>",
  "description": "<entry.description>",
  "schema": "<entry.schema verbatim>"
}
```

Capture the returned data source ID — it's the UUID inside
`<data-source url="collection://UUID">` in the tool's response. Record
a mapping `{<group_slug>: <uuid>}` as you go.

Configure each new database's built-in default view (auto-created by
`notion-create-database` — do NOT create a second view) by calling
`notion-update-view` on it with `plan.databases[i].default_view_config`.
Pass `filter`, `group_by`, `sort`, `visible_columns`, and
`hidden_columns` verbatim.

## Step 8 — Write back, verify, and report

For each `(group_slug, uuid)` pair from Step 7:

1. Use the Edit tool to update `.claude/skills/kb-update/config.yaml`. Change
   the group's line to `notion_data_source_id: "<uuid>"`. Preserve
   existing indentation and quoting.
2. Cache the same UUID in `.kb-local.json`:

   ```
   python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py \
       write-notion-id --group <slug> --id <uuid>
   ```

Re-run `setup_notion.py --status` as a post-condition. Confirm
every group in scope is now provisioned — if not, report which are
still missing and stop.

Print the final summary:

```
Notion structure provisioned.

Landing page: <notion URL>
Databases recovered from Notion: <N_recovered>
  - <list — from Step 4 Case B>
Stale config entries cleared: <N_stale>
  - <list — from Step 4 Case C, now recreated below>
Databases created: <N_created>
  - <list — from Step 7>

Status options are already seeded (Pending Review default →
Approved → Rejected → Integrated). No manual Notion UI setup
required.

You can now upload a file and run /kb-update --group <slug>.
```

**Exit after this flow completes.** Do not proceed to SKILL.md Step 2
— the skill has finished its job for this invocation.
