# kb-integrate

Apply `Status = Approved` rows from a group's Notion database back to the
canonical KB in `hxgtm-mcp-server/context/`, then flip each row from
`Approved` to `Integrated`. kb-integrate closes the loop opened by
[kb-update](../kb-update/README.md): kb-update writes rows as
`Pending Review`, humans triage them in Notion, and kb-integrate carries
the Approved edits to disk.

kb-integrate runs in three modes:

1. **Interactive (default, no flag)** — reads approved rows, computes the edit plan, prints a compact summary, and prompts once (`[a]pply / [p]review full / [c]ancel`) before writing. This is the normal path.
2. **Pure dry-run (`--plan`)** — prints the full preview and stops. No prompt, no disk writes, no Notion updates. Safe to run repeatedly; good for CI.
3. **Non-interactive apply (`--apply` / `--no-confirm`)** — recomputes the plan and executes it without prompting: writes to canon files and flips each successfully-applied row to `Integrated` in Notion. For CI / automated runs.

**kb-integrate never git-commits and never pushes.** It only edits files
under `<mcp_server_path>/context/`. The user reviews `git diff` in
`hxgtm-mcp-server` and commits manually.

> kb-integrate reuses [`.claude/skills/kb-update/config.yaml`](../kb-update/config.yaml)
> as its **single source of truth** for groups, codeowners, active flags,
> and `notion_data_source_id`. There is no separate
> `.claude/skills/kb-integrate/config.yaml` — adding a group remains a kb-update
> concern.

## When to use it

You use kb-integrate when:

- The team has triaged kb-update findings in Notion and there are rows
  sitting at `Status = Approved` that need to land in canon.
- You're ready to produce a visible change in `hxgtm-mcp-server/` — the
  resulting `git diff` is what you'll review before committing.
- You want the Notion database to reflect truth-on-disk: every Approved
  row that successfully applies gets flipped to `Integrated` in the same
  run.

You do **not** use kb-integrate to:

- Bypass Notion triage. Rows at `Pending Review` or `Rejected` are ignored.
- Run a kb-update-style diff on new raw sources — that's [kb-update](../kb-update/README.md).
- Audit canon for staleness or contradictions — that's [kb-lint](../kb-lint/README.md).
- Commit or push changes to `hxgtm-mcp-server`. Always review `git diff` yourself first.

## Requirements

| Requirement | Purpose | Required? |
|---|---|---|
| **Claude Opus** model | Orchestration + row-level reasoning when `current_text` matches are ambiguous | **Required** |
| **Notion MCP connector** | `notion-fetch` to read the database, `notion-update-page` to flip `Status` after a successful apply | **Required** |
| **Filesystem access** to `hxgtm-mcp-server/context/` | kb-integrate **writes files** — MCP-read-only mode is not sufficient | **Required** |
| **Python 3** on PATH | Runs `apply_integrations.py` (stdlib only — no `pip install` needed) | **Required** |
| **kb-update Notion database** already provisioned for the group | kb-integrate reads from the same per-group database kb-update publishes to. Provision it via `/kb-update --notion-setup` if it's missing. | **Required** |

### MCP server path resolution

kb-integrate locates `hxgtm-mcp-server/` via this resolution order:

1. `--mcp-server-path <path>` CLI arg (passed to `apply_integrations.py`)
2. `HXGTM_MCP_SERVER_PATH` env var
3. `../hxgtm-mcp-server/` relative to this repo root

If none resolve to a directory containing a `context/` subfolder, the
script halts with a clear error pointing at `HXGTM_MCP_SERVER_PATH`.

## Quick start

```
# Interactive — reads Approved rows, computes the plan, prompts once, applies if confirmed
/kb-integrate --group competitive

# Pure dry-run — full preview, no prompt, no writes
/kb-integrate --group competitive --plan

# Non-interactive apply — writes canon edits and flips Notion rows to Integrated, no prompt
/kb-integrate --group competitive --apply

# Omit --group to be prompted
/kb-integrate                                # AskUserQuestion picks a group

# List available groups
/kb-integrate --list-groups

# Force-run against an inactive group
/kb-integrate --group messaging --force
```

You can also invoke the worker script directly for CI-style dry-runs
without Claude / the Notion MCP:

```bash
# List groups (reads kb-update's config)
python3 .claude/skills/kb-integrate/scripts/apply_integrations.py --list-groups

# Emit a group's config record as JSON
python3 .claude/skills/kb-integrate/scripts/apply_integrations.py \
    --group competitive --emit-group-record

# Plan from a JSON row list piped in on stdin (no Notion calls)
echo '<rows_json>' | python3 .claude/skills/kb-integrate/scripts/apply_integrations.py \
    --group competitive --plan --run-date 2026-04-16
```

`--plan` is pure read — it never writes to disk. `--apply` writes to
canon files but still requires the Notion MCP (invoked by Claude) to
flip row Status.

## Group scoping

kb-integrate requires an explicit `--group <slug>` (or asks for one if
omitted). The group map is the same as kb-update and kb-lint:

| Slug | Label | Codeowner | Active |
|---|---|---|---|
| `competitive` | Competitive Intelligence | product-marketing | yes |
| `messaging` | Product & Segment Messaging | product-marketing | yes |
| `audiences` | Audiences & Personas | product-marketing | yes |
| `company-policies` | Company Policies & Platform Commitments | product-marketing | yes |
| `company-overview` | Company Overview & Narrative | cmo | yes |
| `marketing-strategy` | Marketing Strategy | cmo | yes |
| `brand-voice` | Brand, Voice & Positioning | cmo | yes |
| `channel-playbooks` | Channel Playbooks | cmo | yes |
| `sales-methodology` | Sales Methodology | sales-enablement | yes |
| `accounts` | Account & Opp-level Context | revops | yes |
| `rfp` | RFP Responses | solutions-engineering | yes |

All 11 groups are active. The source of truth is
[`.claude/skills/kb-update/config.yaml`](../kb-update/config.yaml) — kb-integrate
reuses that file directly and does not maintain its own copy.

---

## Workflow

### 1. Plan the group (interactive by default)

```
/kb-integrate --group competitive
```

- Reads every `Status = Approved` row in `KB - Competitive Intelligence`
- Computes the edit plan: which canon file each row targets, whether the
  `Current Text` match succeeds, and what the before/after looks like
- Prints a compact summary table (`will do` / `SKIP` + reason)
- Prompts once: `[a]pply / [p]review full / [c]ancel`
  - `p` prints full before/after snippets, then re-prompts
  - `a` applies the plan (writes canon files + flips Notion rows to Integrated)
  - `c` exits without writing

For a pure dry-run with no prompt and no writes, pass `--plan` instead:

```
/kb-integrate --group competitive --plan
```

### 2. Review the plan

For each row marked `will do`, confirm:

- **Target file** — is the path what you expected? (Row authors are free
  to redirect a finding from one file to another during Notion triage.)
- **Action** — `replace` (swap `Current Text` → `Proposed Updated Text`
  in place) or `append` (add a new block to the end of the file,
  creating the file if it doesn't exist).
- **Before/after** — the actual bytes that will change.

For rows marked `SKIP`, the most common causes are:

- `current_text not found` — canon drifted between Notion-approval time
  and now. Edit the Notion row's `Current Text` to match current canon
  and re-approve, or apply the edit manually.
- `ambiguous needle` — the `Current Text` appears more than once in the
  target file. Tighten the row's `Current Text` with more surrounding
  context (a line before/after) and re-approve.
- `target path escapes context/` — malformed `Target file` field in the
  Notion row. Fix the row's `Target file` value.

### 3. Apply

Either confirm the interactive prompt from Step 1 with `a`, or re-run
non-interactively:

```
/kb-integrate --group competitive --apply
```

Apply behaviour (same in both paths):

- Recomputes the plan from scratch (canon may have moved since plan-time)
- Writes every `will_succeed` row to disk
- Flips each successfully-applied row to `Status = Integrated` in Notion
- Leaves skipped and failed rows at `Status = Approved` for retry
- Preserves the `Reviewer` column — whoever approved the row stays
  attributed; kb-integrate never writes `Reviewer`

Apply-time matching uses an **in-memory buffer per target file**. If
multiple rows edit the same file, each row's replacement runs against
the live buffer (including every prior row's edits in the same run),
not the stale on-disk state from plan time. This is how kb-integrate
survives multi-row edits without carrying byte offsets around.

### 4. Review `git diff` and commit

```
cd <hxgtm_mcp_server_path>
git diff context/
git add context/
git commit -m "kb-integrate: <group> <date>"
```

**This step is manual.** kb-integrate never commits, never pushes, and
never touches anything outside `context/`. If you run `/kb-integrate`
again before committing, the earlier edits are still sitting on disk
as unstaged changes — kb-integrate will not discard them.

### 5. Re-triage skipped rows (if any)

Rows that were skipped or failed are still `Approved` in Notion. The
post-run summary includes a clickable Notion URL for each skipped row.
Fix the row's content (usually `Current Text`) and re-run
`/kb-integrate --group <slug> --apply` to pick them up.

---

## What the run summary looks like

After `--apply`:

```
kb-integrate run complete.

Group:  competitive (Competitive Intelligence) — owner: product-marketing — mode: apply

Approved rows found: 7
  Replaces: 5 (4 applied, 1 skipped)
  Appends:  2 (2 applied, 0 skipped)

MCP server repo: /Users/…/hxgtm-mcp-server (git: dirty, 6 files)
Notion updates: 6 rows flipped to Integrated, 0 update failures

Skipped / failed rows:
  - [R13] replace  context/guidance/competitive/artificial.md
          current_text not found in target file
          https://www.notion.so/…

Next steps:
  1. cd /Users/…/hxgtm-mcp-server
  2. git diff context/
  3. git add context/ && git commit -m "kb-integrate: competitive 2026-04-16"
  4. Push when ready.
  5. Re-triage the skipped rows in Notion (they're still Approved).
```

On a dry-run, the `Notion updates` line is replaced with `(dry-run — no
Notion writes)` and the `git add / git commit` steps are omitted.

---

## Error handling

- **Zero approved rows** — kb-integrate short-circuits with "Nothing to integrate — no rows with `Status = Approved` in `KB - <label>`."
- **Plan script exits non-zero** — stderr is printed and the run halts; no apply step runs.
- **`--apply` but plan has zero `will_succeed` entries** — apply step is skipped and the summary reports "No actionable rows — every approved row was skipped during planning."
- **`notion-update-page` fails after a successful disk write** — the failure is recorded in the summary but never retried and never rolled back. The canon edit is already on disk; flip the row manually or re-run after the retry fixes.
- **MCP server repo can't be located** — the script halts with a clear error pointing the user at `HXGTM_MCP_SERVER_PATH`.

---

## File structure

```
.claude/skills/kb-integrate/
├── SKILL.md                         ← Main orchestrator
├── README.md                        ← This file
└── scripts/
    ├── apply_integrations.py        ← Plan generator + applier (stdlib only)
    └── test_apply_integrations.py   ← Unit tests for the applier
```

There is no `config.yaml` in this directory — kb-integrate reads groups
and `notion_data_source_id`s straight from
[`.claude/skills/kb-update/config.yaml`](../kb-update/config.yaml).

See [SKILL.md](SKILL.md) for the full step-by-step orchestration, the
exact JSON payloads exchanged between the orchestrator and
`apply_integrations.py`, and the apply-time buffering semantics used
when multiple rows edit the same file.
