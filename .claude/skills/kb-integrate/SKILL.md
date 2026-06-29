---
name: kb-integrate
description: >
  Apply Approved rows from a group's "KB - <Label>" Notion database back
  to the canonical KB in hxgtm-mcp-server/context/, then flip each row
  from Approved to Integrated (or Needs Restage if canon has drifted
  since publish). Closes the kb-update loop: kb-update writes rows as
  Pending Review, humans triage them in Notion, and kb-integrate
  applies the Approved edits to disk at the recorded line range.
  Triggered by
  `/kb-integrate --group <slug>` (interactive: plan → confirm → apply),
  `/kb-integrate --group <slug> --plan` (CI dry-run), or
  `/kb-integrate --group <slug> --apply` (CI apply, no prompt). Use
  when the user says "integrate the approved rows", "apply approved
  kb-updates", "sync Notion approvals to canon", or "finish the
  kb-update loop".
---

# Knowledge Base Integrate

## Usage

```
/kb-integrate --group <slug>             (interactive: prompt, then apply if confirmed)
/kb-integrate --group <slug> --plan      (dry-run preview only, no prompt, no writes)
/kb-integrate --group <slug> --apply     (non-interactive write, no prompt)
/kb-integrate                            (omit --group to be prompted)
/kb-integrate --list-groups              (show available groups)
```

Arguments: $ARGUMENTS

**Three modes.** `/kb-integrate --group <slug>` (no flag) computes the
plan, prints a compact summary, and prompts once
(`[a]pply / [p]review full / [c]ancel`) before any write — this is the
normal interactive path. `--plan` is a pure dry-run (CI use): prints the
full preview and stops, no prompt, no writes. `--apply` /
`--no-confirm` skips the prompt and writes immediately (CI use).

Use `--force` to run against a group with `active: false` in
`.claude/skills/kb-update/config.yaml` (kb-integrate reuses kb-update's
group config — there is no separate kb-integrate config).

**Pre-conditions:**
- `hxgtm-mcp-server` checked out next to this repo (or
  `HXGTM_MCP_SERVER_PATH` pointing at it) — kb-integrate requires
  filesystem write access to `context/`.
- Notion MCP connector enabled (for `notion-fetch` and
  `notion-update-page`).

## What this skill does

Reads every row with `Status = Approved` from a group's Notion database
and applies each row's `Proposed Updated Text` to the referenced canon
file in `hxgtm-mcp-server/context/`. After a successful write, it flips
the Notion row from `Approved` to `Integrated`.

kb-integrate is the **write-path-to-disk** companion to kb-update:

- **kb-update** (Pending Review): uploads → Notion database
- **human triage** (Approved / Rejected): Notion UI
- **kb-integrate** (Integrated): Notion database → canon files on disk

The skill runs in three modes, chosen by CLI flags:

1. **Interactive (default, no flag)** — reads approved rows, computes
   the edit plan, prints a compact summary, and prompts once:
   `apply / preview full / cancel`. The apply path then writes to
   canon files and updates Notion statuses.
2. **`--plan`** — CI dry-run. Computes and prints the full plan
   preview, then stops. No disk writes, no Notion updates.
3. **`--apply`** (or `--no-confirm`) — CI apply. Computes the plan,
   writes to canon files, and flips Notion statuses without the
   interactive prompt.

kb-integrate reuses `.claude/skills/kb-update/config.yaml` as its single source
of truth for groups and data source IDs — there is no separate
`.claude/skills/kb-integrate/config.yaml`. Adding a group is still a one-time
kb-update concern.

**kb-integrate does NOT git-commit, git-push, or otherwise touch the
MCP server repo beyond editing files inside `context/`.** The user
reviews `git diff` and commits themselves.

## Requirements

- **Claude Opus** — the orchestration itself is simple; Opus is chosen
  for parity with the other kb-* skills and for the row-level reasoning
  when a current_text match is ambiguous.
- **Notion MCP connector** — `notion-fetch` to read the database,
  `notion-update-page` to flip Status after a successful apply.
- **Filesystem access** to `hxgtm-mcp-server/context/`. Unlike kb-update,
  the MCP-only read path is NOT sufficient — kb-integrate writes files,
  so filesystem access is required. Resolution (shared with kb-update
  via `.claude/skills/kb-update/scripts/resolve_mcp_path.py`):
    1. `--mcp-server-path` CLI arg (via `apply_integrations.py`)
    2. `.kb-local.json` cache at the repo root (gitignored)
    3. `HXGTM_MCP_SERVER_PATH` env var
    4. `../hxgtm-mcp-server/` adjacent-repo convention
    5. Scan of common dev roots (`~/Desktop`, `~/dev`, `~/code`,
       `~/Projects` + immediate children) — first hit with
       `context/` + `.git/` wins
  Successful resolutions cache the absolute path to `.kb-local.json`
  so future runs skip the scan.
- **Python 3** on PATH — `apply_integrations.py` is stdlib-only.

## Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Group config | `.claude/skills/kb-update/config.yaml` | Reused. Same group → `notion_data_source_id` map as kb-update. |
| MCP server path | `HXGTM_MCP_SERVER_PATH` or `../hxgtm-mcp-server/` | Must contain a `context/` subfolder. Filesystem-required. |
| Apply mode | off by default | `--apply` must be explicit; dry-run prints the plan and stops. |
| Notion target | Per-group `KB - <Label>` database | Resolved from the group's `notion_data_source_id` in kb-update's config. |
| Worker script | `.claude/skills/kb-integrate/scripts/apply_integrations.py` | `--plan` returns a preview; `--apply` writes and returns results. |

---

## Workflow

### Step 1 — Parse args

- **`--group <slug>`** — identifies the Notion database to read from.
  If omitted, use AskUserQuestion to present the active groups from
  `.claude/skills/kb-update/config.yaml` and record the user's pick.
- **No flags (default)** — one-flow mode. Computes the plan, prints a
  compact summary, and prompts once: `[a]pply / [p]review full / [c]ancel`.
- **`--plan`** — CI dry-run. Computes the plan, prints the full
  preview (no prompt), stops. Never writes to disk or Notion.
- **`--apply`** — CI apply. Computes the plan, executes the writes,
  and flips Notion statuses (no prompt). Equivalent to answering `a`
  at the default-mode prompt.
- **`--no-confirm`** — alias for `--apply`, kept for scripted runs
  that read more naturally as "skip confirmation."
- **`--force`** — allows running against a group with `active: false`.
- **`--list-groups`** — print available groups and exit. Delegates to
  `apply_integrations.py --list-groups`.

`--plan` and `--apply` are mutually exclusive; if both are passed,
halt with "Pass only one of --plan / --apply / --no-confirm."

### Step 2 — Pre-flight (lean, zero-prompt)

Mirror kb-update's pattern: resolve the three inputs we actually need
and proceed. **No schema verification, no git-status check, no Proceed
prompt** — the dry-run plan (Steps 4–5) is itself the preview, and the
apply prompt (Step 6) is the real gate. Schema drift and dirty-git
states surface reactively at Step 7 or in the Step 8 diff summary.

Run these three subprocesses **in parallel** (single message, three
Bash calls — they have no dependencies on each other):

```
python3 .claude/skills/kb-integrate/scripts/apply_integrations.py \
    --group <slug> --emit-group-record

python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py \
    resolve-notion-id --group <slug>

python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py mcp-path
```

**Group record (call 1).** Loads `.claude/skills/kb-update/config.yaml` and
emits `{slug, label, codeowner, active, notion_data_source_id}`. If the
group is unknown, the script exits non-zero and tells the user to run
`--list-groups`. If `active: false` and `--force` was not passed, halt:

> Group `<slug>` is inactive in kb-update's config (`active: false` in
> `.claude/skills/kb-update/config.yaml`). Re-run with `--force` to integrate
> against it anyway, or flip the `active` flag when the group is ready.

**Notion ID (call 2).** Walks env → `.kb-local.json` cache →
`config.yaml`. Exit 0 with an ID → use it. Exit 1 (`source: "missing"`)
OR a later Step 3 `notion-fetch` 404s → auto-reconcile the same way
kb-update does:

1. `notion-search` for `"KB - Updates Review"`.
2. If the landing page doesn't exist, halt with the landing-page
   banner (user must create the page once in the right teamspace —
   the MCP can't pick the location).
3. Landing page present + child database titled `KB - <Group Label>`
   exists → `resolve_mcp_path.py write-notion-id --group <slug> --id
   <uuid>` and proceed.
4. Landing page present but the specific database is missing → invoke
   `/kb-update --notion-setup` inline; it handles Case D (create
   missing databases) non-interactively and writes IDs back to cache
   + config. Re-resolve and proceed.

Never halt on "ID missing in config.yaml" alone — the reconcile flow
is fast and removes the old manual interruption.

**MCP server path (call 3).** Walks `.kb-local.json` cache →
`HXGTM_MCP_SERVER_PATH` env → `../hxgtm-mcp-server/` adjacent →
dev-root scan. First run logs
`[resolve_mcp_path] scan: walking dev roots…` and writes the hit back
to `.kb-local.json`. If the resolver halts (zip-not-git / nothing
found), surface its stderr verbatim and stop before Step 3 — the
`.git/` precondition matters because kb-integrate leaves the user
running `git diff` afterward.

Once all three calls return, print a one-line summary so the user can
see the resolved context, then proceed directly to Step 3:

```
kb-integrate · group `<slug>` (<label>, <codeowner>) · <mcp_path> · DB <data_source_id[:8]>…
```

No AskUserQuestion here — if any of the three resolvers halted, the
workflow already stopped. If they all succeeded, the dry-run plan is
the next thing the user sees.

### Step 3 — Fetch approved rows from Notion

The Anthropic Notion MCP does NOT enumerate rows via `notion-fetch` on
a data source ID — that call returns schema only. Row discovery is a
two-step `notion-search` + per-page `notion-fetch` flow:

1. **Discover page IDs.** Call `notion-search` with:
   - `data_source_url: "collection://<notion_data_source_id>"`
   - `query_type: "internal"`
   - `query: "<group label>"` or any broad term — search is semantic,
     so use a term that scopes to the group (e.g. `"competitive"`,
     `"messaging"`) to maximize recall.
   - `page_size: 25` (the MCP cap), `max_highlight_length: 0`.
   The result is a list of `{id, title, url, …}` entries — one per row.
   If the result count equals 25, re-run with a different query term
   (e.g. a list of expected `R{n}` prefixes or entity names) and union
   the IDs. Note this as a soft caveat for groups that may exceed 25
   Approved rows at once (rare today).

2. **Read full properties.** For each discovered page ID, call
   `notion-fetch` — up to **10 concurrent calls per message** so the
   harness can fan them out in parallel. Each response carries the
   `properties` block with every column the row uses.

3. **Client-side filter** to rows where `Status` equals `Approved`
   exactly (not `Integrated`, not `Pending Review`, not `Needs Restage`,
   not `Rejected`). Status is not queryable via `notion-search`, so
   this filter must happen after the fetch.

4. If zero approved rows were found after filtering, short-circuit to
   Step 8 with "Nothing to integrate — no rows with `Status = Approved`
   in `KB - <label>`."

For each approved row, extract and normalize:

```json
{
  "page_id": "<notion page id — needed for notion-update-page in Step 7>",
  "finding_id": "R1",
  "title": "R1: Akur8 agentic roadmap",
  "section": "Weaknesses / watch-outs",
  "action": "replace",
  "target_file": "context/guidance/competitive/akur8.md",
  "target_line_start": 117,
  "target_line_end": 121,
  "current_text": "<≤400 char preview — not used for matching>",
  "proposed_text": "<paraphrased replacement>",
  "final_updated_text": "<reviewer-typed tweak, may be empty>",
  "category": "raw-canon-conflict",
  "source_file": "akur8-q1-2026.md",
  "source_line": 12
}
```

Field-by-field extraction rules:

- **`finding_id`** — the `Name` property now carries the `R{n}:` prefix
  directly (Phase 2 dropped the `[R{n}]` wrapper). Match
  `^(R\d+):\s*(.*)$` against the first rich_text chunk of `Name`.
  Legacy rows with the old `[R{n}] <title>` format fall through to
  `^\[([^\]]+)\]\s*(.*)$`.
- **`action`** — read the `Action` SELECT column directly: `"Append"` →
  `"append"`, `"Replace"` → `"replace"` (lowercase the value before
  passing to `apply_integrations.py`). If `Action` is empty (legacy
  rows from before the column existed), fall back to the old heuristic:
  `current_text` empty → `"append"`, otherwise `"replace"`. Note the
  publisher now writes a sentinel `"(addition to canon — no existing
  text replaced)"` into `Current Text` on append rows, so the explicit
  `Action` column is authoritative — do NOT rely on current_text
  emptiness when `Action` is populated.
- **`target_line_start` / `target_line_end`** — read from their
  respective Notion columns. Missing values cause
  `apply_integrations.py` to flip the row to `Needs Restage` in
  Step 4 — no action required here.
- **`section`** — read from the `Section` column. This is the
  existing canon h2 heading the finding was tagged with at publish
  time (e.g. `"Notes / open questions"`, `"Weaknesses / watch-outs"`).
  The comparator guardrail restricts findings to existing
  `section_schema` headings, so this should always match a real
  section in the target file. Appends merge INTO this section.
- **`final_updated_text`** — read from the `Final Updated Text`
  column. Empty on rows the reviewer didn't tweak; the script's
  `effective_text()` helper falls back to `proposed_text`
  automatically.
- **Prose fields** — `current_text`, `proposed_text`,
  `final_updated_text`, `rationale`, `section` may contain
  `⟪ast⟫ / ⟪us⟫ / ⟪hash⟫ / ⟪bt⟫ / ⟪tld⟫` placeholders from
  `publish_to_notion.py`'s markdown escape. Hand them through as-is —
  `apply_integrations.py` runs `unescape_markdown_from_notion_property`
  on ingest.

Other rules:

- If the Notion row has no `Target file`, skip it in this step and log
  the skip for Step 8's summary — it was malformed at publish time.
- Record the page URL for each row — it goes into the Step 8 report so
  the user can click straight to any skipped / needs-restage row.

**What you DON'T need to normalize in this step.** `apply_integrations.py`
absorbs several drift patterns between kb-update's emission contract
and what's actually in Notion today — hand rows through as-is and
let the script clean them up:

- `section` arriving with a `## ` prefix (the comparator copies
  canon section headings verbatim) — the script strips leading `#`
  markers before rendering.
- `target_file` stored as `guidance/...` without the `context/` prefix
  vs. `context/guidance/...` — the script accepts both shapes.
- `target_file` / `source_file` returned as `[name.md](http://name.md)`
  because Notion's rich_text reader auto-links filename-shaped strings
  — the script peels `[X](Y)` back to `X` on ingest.

### Step 4 — Build the edit plan

Pipe the normalized row list as JSON into:

```
echo '<rows_json>' | python3 .claude/skills/kb-integrate/scripts/apply_integrations.py \
    --group <slug> --plan --run-date <YYYY-MM-DD>
```

The script returns a JSON payload with `group`, `mcp_server_path`,
`plan`, and `stats`. Each plan entry has:

```json
{
  "page_id": "...",
  "finding_id": "R1",
  "title": "...",
  "target_file": "context/guidance/competitive/akur8.md",
  "target_path": "/abs/path/to/akur8.md",
  "target_rel": "context/guidance/competitive/akur8.md",
  "action": "replace" | "append" | "skip",
  "will_succeed": true | false,
  "needs_restage": true | false,
  "reason": "line match at lines 117-121"
          | "target file does not exist: …"
          | "target_line_end <tle> beyond file length (<n> lines)",
  "preview_before": "...",
  "preview_after": "..."
}
```

The script handles:
- **Target-path confinement** — must resolve under `<mcp_root>/context/`.
- **Replace** — `target_line_start / end` locate the span; the
  script writes `effective_text` at that range unconditionally.
  **No drift check** — we assume canon isn't edited concurrently
  during the triage window. If the recorded line range is beyond the
  current file length, the row flips to `Needs Restage` instead of
  corrupting the file.
- **Append** — heading-aware. The script looks for an existing `##
  <section>` (h2) section in the target file (whitespace-trimmed,
  marker-insensitive match):
    - **If found**, splice the provenance HTML comment + effective
      text at the end of that section, trimming trailing blank lines
      before the next heading so the insertion lands against real
      content. The reason is `merge into existing '## <heading>'
      section`.
    - **If not found**, append a new `## <section>` block at EOF
      with a blank-line separator, the provenance comment, and the
      effective text. Creates the file if missing. The reason is
      `append new '## <heading>' section at EOF` (or `create new file
      with '## <heading>' section`).
  Provenance is toggleable via `global.include_provenance_comment` in
  `config.yaml` (default on). Multiple approved rows sharing a heading
  collapse under a single section — either the existing one, or a
  single new one created by the first row, with the rest merging into
  it. Apply order within a file: replaces bottom-up first, then
  appends in row order so each append sees the post-replace state.
- **`effective_text` resolution** — `Final Updated Text` wins over
  `Proposed Updated Text` wherever either is referenced (replace
  payload, append body, Landing preview).
- **Markdown unescape** — `⟪ast⟫ / ⟪us⟫ / ⟪hash⟫ / ⟪bt⟫ / ⟪tld⟫`
  placeholders are reversed on ingest so canon gets `*`, `_`, `#`,
  `` ` ``, `~` back.
- **Git precondition** — the resolved MCP server path must contain a
  `.git/` directory. Zip-downloads halt with
  `"hxgtm-mcp-server at <path> is not a git clone — kb-integrate
  needs git diff/commit to work."`

`--plan` never writes to disk. Safe to run repeatedly.

### Step 5 — Render the plan preview

Render the plan to stdout as:

```
kb-integrate plan — group `<slug>` (<N> approved rows)

| R#  | Action  | Target                                            | Status         | Notes                                          |
|-----|---------|---------------------------------------------------|----------------|------------------------------------------------|
| R1  | append  | context/guidance/competitive/akur8.md             | will do        | create new file                                |
| R6  | replace | context/guidance/competitive/earnix.md            | will do        | line match at lines 112-115                    |
| R13 | replace | context/guidance/competitive/artificial.md        | NEEDS RESTAGE  | target_line_end 45 beyond file length (40 lines) |
| R17 | replace | context/guidance/competitive/missing.md           | SKIP           | target file does not exist                     |
```

Below the table, for each `will do` row, print a compact before/after
block using `preview_before` / `preview_after` from the plan. Clip
each side to at most 10 lines.

```
--- R6 · context/guidance/competitive/earnix.md ---
BEFORE:
  > <preview_before>

AFTER:
  > <preview_after>
```

At the bottom, print the stats block from `stats`: rows, will_replace,
will_append, needs_restage, skipped.

**Mode-specific printing.** In `--plan` mode, print the full
preview (every row). In the default interactive mode, print a
compact one-line-per-row summary plus stats — the full preview is
gated behind the `[p]review full` prompt option. `--apply` skips the
preview entirely and jumps to Step 7.

### Step 6 — Confirm (default mode) / Gate (CI mode)

- **`--plan`** — stop after Step 5 with:
  > Plan-only run complete. Re-run `/kb-integrate --group <slug>
  > --apply` (or without any flag for interactive mode) to execute.
- **`--apply`** or **`--no-confirm`** — skip the prompt and continue
  to Step 7.
- **Default (no flag)** — use AskUserQuestion:

  ```
  Apply <N_will_succeed> edits to canon?
  (<will_replace> replace / <will_append> append ·
   <needs_restage> needs restage · <skipped> skipped)
  ```

  Options:
  - **"[a]pply"** — continue to Step 7.
  - **"[p]review full"** — print the full Step 5 preview (every
    row's before/after snippet), then re-prompt with the same
    three options. Loops until the user picks apply or cancel.
  - **"[c]ancel"** — halt cleanly without Step 7; no disk or Notion
    writes.

### Step 7 — Execute the apply

Pipe the same row list (NOT the plan — the script recomputes the plan
from scratch) into:

```
echo '<rows_json>' | python3 .claude/skills/kb-integrate/scripts/apply_integrations.py \
    --group <slug> --apply --run-date <YYYY-MM-DD>
```

The script writes to each target file where `will_succeed` is true,
then emits a `results` array with one entry per row:

```json
{
  "page_id": "...",
  "finding_id": "R1",
  "action": "append" | "replace",
  "target_rel": "context/guidance/competitive/akur8.md",
  "status": "success" | "skipped" | "needs_restage" | "failure",
  "reason": "..."
}
```

**Apply-time matching.** The script groups rows by `target_file`.
Within each file, replaces run **bottom-up** (`target_line_start`
descending) so earlier edits don't shift later anchors. Replaces
write unconditionally at the recorded range — no drift check. If
canon was edited concurrently between publish and apply, the
concurrent edit is silently overwritten; this is the documented
trade-off of the cleaned 2026-04 schema.

**Post-apply readback.** After each file is written, the script
re-reads it and asserts each success-marked row's `effective_text`
is present. Any entry that fails the readback is downgraded from
`success` to `failure` — kb-integrate leaves its Notion Status as
`Approved` so the next run can retry.

**Notion Status update — concurrent batches with spot-check readback.**

For each result where `status == "success"`, call `notion-update-page`
to flip Status to `Integrated`. For each result where
`status == "needs_restage"`, flip Status to `Needs Restage`. Skipped
and failed rows are left at `Approved` for retry.

```json
{
  "page_id": "<result.page_id>",
  "properties": {
    "Status": "Integrated"   // or "Needs Restage" for out-of-range rows
  }
}
```

Issue updates in batches of up to **10 concurrent calls per message**
so the harness fans them out in parallel.

**Readback is a spot-check, not a per-row audit.** Notion's update API
is strongly consistent — per-row readback rarely fires the retry path
but burns one fetch per row. After all update batches return, issue
**one `notion-fetch` sample per batch** (the first page_id in the
batch) and confirm its Status holds the expected value. If the
sample disagrees, retry that page's update once and log any remaining
mismatch as `<page_id> · <finding_id> · status not persisted after
retry` in the Step 8 error list. On a 5-row run that's 1 readback
instead of 5; on a 30-row run with 3 batches, 3 readbacks instead of
30.

Do not rollback the disk edit on a Status-flip failure — the canon
change is already written and the user can flip the Status manually.

Do NOT touch the `Reviewer` column — the human tagged themselves
when they approved the row; kb-integrate preserves that attribution.
Do NOT touch `Final Updated Text` — it's the reviewer's workspace
and the integrator reads from it, never writes to it.

### Step 8 — Report to user

Output a summary:

```
kb-integrate run complete.

Group:  <slug> (<label>) — owner: <codeowner> — mode: plan-only | apply | cancelled

Approved rows found: <N>
  Replaces: <X_total> (<X_applied> applied, <X_skipped> skipped, <X_restage> needs restage)
  Appends:  <Y_total> (<Y_applied> applied, <Y_skipped> skipped)

MCP server repo: <path> (git: clean | dirty, <K> files)
Notion updates: <M_integrated> rows flipped to Integrated,
               <M_restage> flipped to Needs Restage,
               <F> update / readback failures
                 - <page_id> · <finding_id> · status not persisted after retry
                 - ...

Skipped / needs-restage rows:
  - [R13 · NEEDS RESTAGE] replace context/guidance/competitive/artificial.md
          target_line_end 45 beyond file length (40 lines)
          <notion row url>
  - [R17 · SKIP] replace context/guidance/competitive/missing.md
          target file does not exist
          <notion row url>
  - ...

Next steps:
  1. cd <mcp_server_path>
  2. git diff context/            # review the edits
  3. git add context/ && git commit -m "kb-integrate: <group> <date>"
  4. Push when ready.
  <extra line if any needs_restage rows exist:>
  5. Re-run /kb-update on the affected sources — the Needs Restage
     rows will get republished with fresh line anchors against the
     current canon.
```

On plan-only runs, replace the "Notion updates" line with
`(plan-only — no disk or Notion writes)` and drop the
"git add / git commit" steps.

On cancelled runs, the summary shows only the stats block and
"Cancelled at prompt; no disk or Notion writes."

---

## Error handling

- If `notion-fetch` fails or returns zero approved rows, halt cleanly
  with the zero-approved message (Step 3).
- If `apply_integrations.py --plan` exits non-zero, print the stderr
  output and stop. Do not proceed to Step 7.
- If `--apply` was passed but the plan has zero `will_succeed` entries
  (everything needs_restage / skipped), still call the apply script
  once to flip Notion statuses for the `needs_restage` rows, then
  jump to Step 8 with "No disk edits — every approved row was
  flagged needs_restage or skipped during planning."
- If a `notion-update-page` call fails or the readback disagrees
  after one retry, record the row in Step 8's failure list but do
  not roll back the disk edit. The user can flip the row manually
  or re-run kb-integrate after the upstream issue clears.
- If the MCP server repo cannot be located at pre-flight, halt with
  the script's "could not locate hxgtm-mcp-server" error and tell
  the user to set `HXGTM_MCP_SERVER_PATH`.
- If the resolved MCP server path has no `.git/` directory, halt
  with the script's "not a git clone" error and the `git clone`
  instruction. kb-integrate needs git to be meaningful for the
  human follow-up.

---

## Relationship to kb-update and kb-lint

- **kb-update** writes the inbound side (raw → Notion rows as
  `Pending Review`).
- **kb-integrate** writes the outbound side (approved Notion rows →
  canon files on disk → `Integrated`).
- **kb-lint** is orthogonal — a read-only audit that scans `raw/` and
  canon and writes a markdown report.

The three share exactly one config file (`.claude/skills/kb-update/config.yaml`)
so groups + Notion IDs + codeowners + active flags stay in one place.
