---
name: dossier-feedback
template_version: "1.0"
description: >
  Capture human comments left on Account Dossier pages in Notion, interpret
  each comment alongside the dossier text it was anchored to, and emit two
  per-account markdown files: a full audit trail at
  dossier-feedback/comment-logs/<slug>.md and a section-grouped
  one-line-truths summary at dossier-feedback/known-truths/<slug>.md. Runs
  single-account on demand or sweeps every account in _batch-state.json via
  --all (waves of 5 parallel per-account subagents). Phase 1: capture &
  storage only — generate-dossier is not modified and does not yet consume
  the truths files.
---

# Dossier Feedback — Capture Reviewer Knowledge from Notion Comments

## What this skill does

Account Executives review generated Account Dossiers in Notion and leave
comments correcting facts, adding context, or flagging mistakes. Today none
of that human knowledge is captured back — every regenerated dossier starts
from a blank page and repeats the same mistakes.

This skill closes the capture half of that loop. For each account, it reads
comments off the dossier's Notion page, interprets each comment alongside
the block of dossier text it was anchored to, and emits **two markdown
files** per account, written atomically together:

- `dossier-feedback/comment-logs/<slug>.md` — full audit trail (raw
  comments, anchors, author, date, resolved state, discussion id, plus the
  interpreted truth). Humans only.
- `dossier-feedback/known-truths/<slug>.md` — section-grouped one-line
  truths only. The LLM-consumer-facing artifact for the Phase-2
  generate-dossier wiring.

**Phase-1 scope is deliberately tight:**
- Capture & storage only — `generate-dossier-batch-parallel` is **not**
  modified in this phase and does not yet load the truths files.
- Both files are regenerated from scratch on every run. No merge logic,
  no date-based supersession, no archive. History lives in git.
- Comments and the LLM synthesis are the source of truth; the files are
  derived. Hand-edits are not preserved.

## Invocation modes

| Invocation | Mode | Use case |
|---|---|---|
| `/dossier-feedback "Account Name"` | single | Manual ad-hoc run for one account |
| `/dossier-feedback --notion-url <url>` | single | Manual override when account isn't in `_batch-state.json` |
| `/dossier-feedback --all` | sweep | Walks every account; called by the daily routine |

The skill ships with **one daily Notion Routine** (06:00) that calls
`/dossier-feedback --all`. Adding/removing accounts is a data change
(`_batch-state.json`), not a routine change.

## Why per-account work runs in a subagent

If the orchestrator did the per-account I/O directly, sweep mode would leak
~750K tokens for 50 accounts × 30 comments before doing any work. So **all
per-account work happens inside a per-account subagent (Sonnet)**: skip
check → fetch comments → recover anchors → synthesise → write file → return
only a one-line summary `{account, status, entries_count, elapsed_ms,
error?}`. The orchestrator's per-account context cost collapses to ~80
tokens × N. Single-account mode dispatches one subagent; sweep mode
dispatches in waves of 5. Same subagent, same code path.

## Requirements

- **Notion MCP** (**required**) — tools `notion-get-comments`,
  `notion-fetch`, and `notion-search`. Pre-flight hard stop if any of these
  schemas can't be resolved via `ToolSearch`.
- **`outputs/generate-dossier-batch-parallel/_batch-state.json`** — primary
  source of slug → notion_url mapping. Required for sweep mode and for the
  default account-name resolution path. Single-mode runs with
  `--notion-url <url>` bypass it.
- **Bash + Python 3** — for the helper scripts under `scripts/`.

## Configuration

| Setting | Value |
|---|---|
| Output directory | `dossier-feedback/` (top level of this repo) |
| Per-account comment log | `dossier-feedback/comment-logs/<slug>.md` |
| Per-account truths summary | `dossier-feedback/known-truths/<slug>.md` |
| Routine state file | `dossier-feedback/_routine-state.json` |
| Routine summary | `dossier-feedback/_routine-summary.md` |
| Routine errors | `dossier-feedback/_routine-errors.md` |
| Source dossier database id | `337802db20a6806f8fdbfe480adc0e4b` |
| Sweep-mode wave size | 5 parallel per-account subagents |
| Subagent model | `sonnet` (pinned on every Agent call) |
| Subagent type | `general-purpose` |

The dossier-feedback database id is the same Notion database that
`generate-dossier-batch-parallel` publishes into — we treat it as the only
valid scope when falling back to `notion-search` in single-mode account
resolution.

---

## Workflow

### Step 0 — Mode resolution

Parse the slash command arguments:

- No args **or** the literal flag `--all` → **sweep mode**.
- `--notion-url <url>` → **single mode** (URL bypass; no name needed).
- One positional arg (the account name) → **single mode**.

Reject any other shape with a one-line error.

### Step 1 — Pre-flight

This skill is **non-interactive in sweep mode** (the routine is
non-interactive) and uses a single Proceed/Cancel gate **only** in
manually-invoked single mode. There is no `AskUserQuestion` call in sweep
mode, ever.

Detection:
- **Notion MCP**: resolve the schemas for `notion-get-comments`,
  `notion-fetch`, and `notion-search` via `ToolSearch`. If any one fails to
  resolve, **hard stop** with an actionable error: "Notion MCP connector
  required. Connect the Notion MCP server and rerun."
- **`_batch-state.json`**: check
  `outputs/generate-dossier-batch-parallel/_batch-state.json`. Required for
  sweep mode and for the default single-mode resolution path. **Hard stop
  in sweep mode if missing.** In single mode, missing is acceptable only
  when `--notion-url` was supplied.

Print a short status block:

```
Pre-flight status:

| Connector / input               | Status | Note                                                  |
|---------------------------------|--------|-------------------------------------------------------|
| Notion MCP (get-comments, fetch, search) | ✓/✗ | ⛔ REQUIRED — pre-flight hard stop if ✗               |
| _batch-state.json               | ✓/✗    | Required for --all and for name-based resolution      |

Mode: single | sweep
```

In **single mode**, after printing the table, gate once with a single
Proceed/Cancel question naming the resolved account and the page URL. In
**sweep mode**, skip the gate entirely and continue.

### Step 2 — Build the account list

#### Single mode

Resolve the one account via `scripts/resolve_account.py` in this order:

1. `--notion-url` → strip hyphens to get the page id; record as
   `{name: <user-supplied or "(URL bypass)">, slug: null, page_id: <id>,
   notion_url: <url>}`. Slug derivation is deferred to step 3 once the
   subagent has the actual title (or fall back to a slug derived from the
   user-supplied name).
2. Look up by name in `_batch-state.json`:
   - exact slug match, then exact human-name match, then case-insensitive
     name match.
   - Record `{name, slug, page_id, notion_url}` from the matched account.
3. Fallback: orchestrator calls `notion-search` against the dossier
   database `337802db20a6806f8fdbfe480adc0e4b` with the account name as
   the query.
   - Exactly one hit → use it.
   - Zero hits → fail with "Account not found in `_batch-state.json` or
     Notion database. Pass `--notion-url <url>` to override."
   - Multiple hits → fail with "Ambiguous match. Pass `--notion-url <url>`
     to override."

Output of step 2 in single mode is a **list of one** account record.

#### Sweep mode

Run `python3 .claude/skills/dossier-feedback/scripts/list_accounts.py
outputs/generate-dossier-batch-parallel/_batch-state.json`.

It prints a JSON list:

```json
[
  {"name": "Zurich North America", "slug": "zurich-north-america",
   "page_id": "abc...", "notion_url": "https://www.notion.so/..."},
  ...
]
```

The script includes only accounts whose `notion_url` is non-null. Accounts
without a Notion URL (publish previously failed and was never retried)
are skipped silently in sweep mode and not even dispatched.

### Step 3 — Dispatch per-account subagent(s)

For every account in the list, dispatch a per-account subagent. The prompt
template lives at `references/per-account-subagent.md`. The orchestrator
substitutes:

- `{{account_name}}` — display name
- `{{slug}}` — kebab-case slug; in URL-bypass mode, derive from the page
  title returned by the subagent's first `notion-fetch`, or fall back to a
  hash of the page id if title extraction fails (the subagent owns this)
- `{{page_id}}` — Notion page id
- `{{notion_url}}` — Notion page URL
- `{{comment_log_out_path}}` — absolute path to
  `dossier-feedback/comment-logs/<slug>.md` (the orchestrator computes the
  absolute path; in URL-bypass mode where the slug is unknown, pass the
  literal token `__derive_from_subagent__` and let the subagent build the
  path after extracting the slug)
- `{{truths_summary_out_path}}` — absolute path to
  `dossier-feedback/known-truths/<slug>.md` (same `__derive_from_subagent__`
  rule applies in URL-bypass mode)
- `{{last_dossier_edited_at}}` — sweep-mode skip-check anchor read from
  `dossier-feedback/_routine-state.json`. Empty string in single mode and
  for accounts with no prior routine state.

**Single mode**: dispatch one subagent.

**Sweep mode**: dispatch in **waves of 5 parallel subagents**. Within one
wave, fire all five Agent calls in a single message so they run
concurrently. After each wave returns, append the per-account summaries to
the running results list and continue to the next wave. Mirrors
`generate-dossier-batch-parallel`'s wave-of-N pattern.

Subagent type: `general-purpose`. Model: `sonnet` on every Agent call.

Each subagent returns ONLY a small JSON status object (≤300 chars):

```json
{"account": "Zurich North America", "slug": "zurich-north-america",
 "status": "ok", "entries_count": 12, "anchor_failures": 1,
 "elapsed_ms": 4321,
 "last_dossier_edited_at": "2026-04-28T22:11:00Z",
 "error": null}
```

`status` is one of `ok`, `skipped-unchanged`, `no-comments`, `error`.

### Step 4 — Aggregate (sweep mode only)

After every wave has returned, run
`python3 .claude/skills/dossier-feedback/scripts/aggregate_routine_summary.py` and
pipe the array of subagent summaries on stdin. The script:

- Writes `dossier-feedback/_routine-summary.md` (full table of every
  account with status, entry count, elapsed time).
- Atomically merges per-account `last_dossier_edited_at` and
  `last_run_at` into `dossier-feedback/_routine-state.json`. Accounts that
  returned `error` are NOT advanced — their previous `last_dossier_edited_at`
  is preserved so the next run will retry.
- Writes `dossier-feedback/_routine-errors.md` with the failure rows from
  the current sweep (one row per `error` status). The file is overwritten
  every sweep — this matches the phase-1 "regenerate from scratch" stance.

Single mode skips this step entirely. The routine state and summary files
are only meaningful in sweep mode.

### Step 5 — Report to operator

#### Single mode

```
Dossier feedback captured.

Account:    <Account Name>
Source:     <Notion page URL>
Comment log: dossier-feedback/comment-logs/<slug>.md
Truths:      dossier-feedback/known-truths/<slug>.md
Entries:    <count>  (resolved: <r>, unresolved: <u>)
By section:
  overview:        <n>
  vision-mission:  <n>
  power-players:   <n>
  past-opps:       <n>
  sentiment:       <n>
  discovery:       <n>
  why-anything:    <n>
  untagged:        <n>
```

If the subagent returned `no-comments`, print "No comments on this dossier
page. No file written." and exit 0.

#### Sweep mode

```
Sweep complete.

Accounts processed: <total>
  ok:                 <n>
  skipped-unchanged:  <n>
  no-comments:        <n>
  error:              <n>

Outputs: dossier-feedback/
Summary: dossier-feedback/_routine-summary.md
State:   dossier-feedback/_routine-state.json
Errors:  dossier-feedback/_routine-errors.md   (only present if any errors)
```

---

## Per-account subagent

The subagent owns the per-account run end-to-end. Its full prompt template
lives at `references/per-account-subagent.md`. Summary of what it does:

1. **Skip check** (sweep mode only): call `notion-fetch` on `page_id`, read
   `last_edited_time`. If `last_edited_time <= last_dossier_edited_at` AND
   the truths file already exists, return immediately with
   `status: "skipped-unchanged"`.
2. Call `notion-get-comments` with `include_all_blocks=true,
   include_resolved=true`.
3. Pipe through `scripts/fetch_comments_payload.py` to normalise to JSON.
   Empty list → return `status: "no-comments"`.
4. **Anchor recovery**: for each entry with `parent_block_id`, call
   `notion-fetch` on that block id and extract rendered text as
   `anchor_text`. Page-level comments and recovery failures get
   `anchor_text: null`.
5. **Synthesise interpreted truths**: reason over each
   `(comment + anchor)` pair and emit per-entry: `{title, anchor_text,
   comment_text, interpreted_truth, section_tag, author, created_time,
   resolved, discussion_id}`. `section_tag` ∈ `{overview, vision-mission,
   power-players, past-opps, sentiment, discovery, why-anything, untagged}`
   (8 values; `why-anything` maps to the dossier's conditional Section 7).
6. **Write files**: pipe synthesised JSON to
   `scripts/build_truths_file.py --account "<name>" --slug <slug>
   --source-url <url>
   --comment-log-out dossier-feedback/comment-logs/<slug>.md
   --truths-summary-out dossier-feedback/known-truths/<slug>.md`. Both
   files are written atomically; always overwrites.
7. **Return** the small status object to the orchestrator.

The output file shape is documented at `references/output-format.md`.

---

## Critical existing files referenced

- `outputs/generate-dossier-batch-parallel/_batch-state.json` — primary
  source of slug → notion_url mapping. Schema documented at
  `.claude/skills/generate-dossier/SKILL.md:296`.
- `.claude/skills/generate-dossier/scripts/save-dossier-to-notion.py:740`
  — confirms the `{notion_url, page_id}` shape we read.
- Dossier database id `337802db20a6806f8fdbfe480adc0e4b` — used as the
  `notion-search` scope in the single-mode fallback.
- `.claude/skills/generate-dossier/SKILL.md` — wave-of-N + per-item
  subagent pattern this skill mirrors.

## Out of scope (deferred to phase 2+)

- Modifying `generate-dossier-batch-parallel` to load the truths file as a
  research input. **This must happen as a separate task to make the loop
  useful**, but is explicitly deferred per the phase-1 brief.
- Merge / supersession logic (date-based or otherwise).
- Date-aware "Perplexity is fresher than truths file" arbitration.
- Regenerating dossiers from comments alone, skipping research.
- Resolving the comment in Notion after capture (acknowledgment loop).
- Multi-routine fan-out (one routine per account) — rejected as
  operationally heavy. Revisit only if the single sweep routine becomes a
  bottleneck.
- Landing the truths file in `hxgtm-mcp-server/context/accounts/` as a
  sibling to the dossier (Q5a-A). Worth revisiting when the consumer side
  is built — co-locating with dossier means the consumer reads a sibling
  file with no second-repo plumbing.

## Atomic writes

- Per-account comment log AND truths summary → `build_truths_file.py`
  writes each to a `.tmp` sibling and `os.replace`s into final position.
  The two files are written sequentially in one process; if the first
  succeeds and the second fails, the run is recorded as `error` and the
  newly-replaced first file is left in place (git records the
  inconsistency for the next run to pick up).
- `_routine-state.json` → `aggregate_routine_summary.py` writes via the
  same `.tmp` + `os.replace` pattern.
- `_routine-summary.md` and `_routine-errors.md` → same pattern; the
  Python script writes both atomically.

## Error handling

| Failure | Behavior |
|---|---|
| Notion MCP missing at pre-flight | Hard stop. Skill never starts. |
| `_batch-state.json` missing in sweep mode | Hard stop. |
| Single-mode account name has 0 hits in fallback search | Fail with "Account not found. Pass `--notion-url <url>`." |
| Single-mode account name has >1 hits in fallback search | Fail with "Ambiguous match. Pass `--notion-url <url>`." |
| `notion-get-comments` returns empty | Subagent returns `no-comments`. No file written. |
| `notion-fetch` for an anchor block fails | Entry kept with `anchor_text: null` and `anchor_failures` incremented. Run continues. |
| `build_truths_file.py` exits non-zero | Subagent returns `status: error` with the stderr message. The previous output files (if any) are left untouched in the common failure modes (render error, first write error) because the script writes to `.tmp` siblings first. If the second `os.replace` fails after the first succeeded, the comment log will be the new run while the truths summary stays on the previous run — recorded as `error` so the next run picks it up. |
| Subagent itself errors / times out | Orchestrator records `status: error` with the Agent error message. Sweep continues; never stops the wave. |
| Routine ran during a Notion outage (every account errors) | `_routine-state.json` is not advanced for any account — next run retries the entire sweep. |
