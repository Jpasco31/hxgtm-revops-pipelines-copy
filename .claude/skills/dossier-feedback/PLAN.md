# Plan — `dossier-feedback` skill (phase 1)

## Context

Account dossiers are generated today by `.claude/skills/generate-dossier/`
using web search, Perplexity, Glean, and Salesforce. Account executives review
the dossiers in Notion and leave comments correcting facts, adding context, or
flagging mistakes. **None of this human knowledge is captured back into the
system today** — every regenerated dossier starts from a blank page and repeats
the same mistakes.

This skill closes the feedback loop. For each account, it reads comments off
the dossier's Notion page, interprets each comment alongside the text it was
anchored to, and emits **two per-account markdown files**: a full comment log
for human audit, and a section-grouped one-line "known truths" summary for the
future generate-dossier consumer. In a later phase, generate-dossier will load
the truths summary as an additional research input. **In phase 1 we only
build the capture & storage system — generate-dossier itself is not modified.**

Phase-1 scope is deliberately tight:
- Manual single-account on-demand AND a daily routine that sweeps all accounts.
- Always overwrite both output files (no merge logic, no date-based supersession).
- Both files are regenerated from scratch every run; history lives in git.
- Comments and the LLM synthesis are the source of truth; both files are derived.

## Phase-1.5 update — output split

After the initial implementation landed with a single combined file
(`<slug>-known-truths.md`), the output was split into two atomically-written
files (`comment-logs/<slug>.md` + `known-truths/<slug>.md`). Rationale: the
comment log is human-facing and rich with provenance; the truths summary is
the LLM-consumer-facing artifact for generate-dossier and benefits from less
noise. Both files share the same frontmatter and entry order; the
`interpreted_truth` line appears in both (intentionally redundant — the
comment log stays self-contained for human audit). The split also closed an
enum-drift gap: `section_tag` now has 8 values (added `why-anything` for
the conditional Section 7 of the dossier — enum-only, no classifier
heuristics added in this round; deferred to phase 2 calibration).

## Pre-implementation setup

Before any files are created, branch off `main`:

1. `git checkout main`
2. `git pull` (sync with remote)
3. `git checkout -b feature/dossier-feedback-skill`

Branch name: `feature/dossier-feedback-skill` — matches the skill name and
mirrors the existing `feature/kb-update-group-restructure` shape used in this
repo. All implementation work in this plan happens on that branch.

Current branch (`feature/kb-update-group-restructure`) has uncommitted work
that is unrelated to this plan; it stays as-is and is not touched by this
plan.

## Recommended approach

A new skill at `.claude/skills/dossier-feedback/` with three invocation modes:

| Invocation | Mode | Use case |
|---|---|---|
| `/dossier-feedback "Account Name"` | single | Manual ad-hoc run for one account |
| `/dossier-feedback --notion-url <url>` | single | Manual override when account isn't in `_batch-state.json` |
| `/dossier-feedback --all` | sweep | Walks every account; called by the routine |

The skill ships with **one daily Notion Routine** (06:00) that calls
`/dossier-feedback --all`. Adding/removing accounts is a data change
(`_batch-state.json`), not a routine change.

### Why one routine, not one-per-account

A Notion Routine is just a cron-scheduled prompt. You *could* provision one
per account, but it scales poorly: N routines for N accounts, manual
provisioning for every new account, scattered logs, and routine quotas
become a constraint. Single routine + data-driven fan-out inside the
skill is the durable shape.

### Why the per-account work runs in a subagent

If the main orchestrator did the per-account I/O directly, sweep mode
would leak ~750K tokens for 50 accounts × 30 comments before doing any
work — costly, slow, and prone to mid-sweep compaction. So **all
per-account work happens inside a per-account subagent (Sonnet)**:
fetch comments → recover anchors → synthesise → write file → return only
a one-line summary `{account, status, entries_count, elapsed_ms, error?}`.

The main orchestrator's per-account context cost collapses to ~80 tokens
× N. Single-account mode dispatches one subagent; sweep mode dispatches
in waves of 5. Same subagent, same code path.

## Skill name + slash command

- Skill directory: `.claude/skills/dossier-feedback/`
- Slash command: `/dossier-feedback [account name]`
- Flags: `--notion-url <url>`, `--all`
- Output folder: `dossier-feedback/` at repo root, with two subfolders:
  `comment-logs/` (audit trail) and `known-truths/` (consumer summary).
- Output filenames: `<slug>.md` in each subfolder. Slug derived the same
  way `generate-dossier-batch-parallel` derives slugs — kebab-case
  account name. Both files for a given account share the same basename.

## Files to create

```
.claude/skills/dossier-feedback/
  SKILL.md                          # orchestration: pre-flight, dispatch, aggregation
  README.md                         # operator-facing setup + routine notes
  references/
    output-format.md                # exact markdown shape for known-truths file
    per-account-subagent.md         # subagent prompt — owns the per-account run
  scripts/
    resolve_account.py              # account name → Notion page_id resolver
    list_accounts.py                # _batch-state.json → ordered account list (for --all)
    fetch_comments_payload.py       # transform notion-get-comments output → JSON
    build_truths_file.py            # synthesised JSON → markdown file writer
    aggregate_routine_summary.py    # per-account summaries → _routine-summary.md
    test_build_truths_file.py       # pytest covering output shape
    test_resolve_account.py         # pytest covering resolution order
.claude/commands/
  dossier-feedback.md               # slash command wrapper
dossier-feedback/                   # NEW top-level output folder
  .gitkeep                          # commit the empty folder
  # populated at runtime:
  # comment-logs/<slug>.md          # full audit trail per account
  # known-truths/<slug>.md          # truths-summary per account
  # _routine-state.json             # per-account last_run_at + last_dossier_edited_at
  # _routine-summary.md             # latest sweep summary
  # _routine-errors.md              # latest sweep errors
```

## Workflow (SKILL.md)

### Mode resolution
- No args / `--all` → sweep mode.
- One positional arg → single mode (account name).
- `--notion-url <url>` → single mode (URL bypass).

### Step 0 — Pre-flight (both modes)
- Verify Notion MCP available (`notion-get-comments`, `notion-fetch`,
  `notion-search` tool schemas resolved via ToolSearch).
- Verify `outputs/generate-dossier-batch-parallel/_batch-state.json`
  exists OR `--notion-url` was supplied.
- Single Proceed/Cancel gate (suppressed in sweep mode when invoked from
  the routine — the routine is non-interactive).

### Step 1 — Build account list
- **Single mode**: list = `[ {name, slug, page_id_or_url} ]` for the one
  account. Resolution via `scripts/resolve_account.py`:
  1. `--notion-url` flag → strip hyphens to get page_id.
  2. `_batch-state.json` → match by slug or human-name → `notion_url` → page_id.
  3. Fallback: orchestrator calls `notion-search` against dossier database
     `337802db20a6806f8fdbfe480adc0e4b`; if exactly one hit, use it; if
     zero or many, ask the operator (or fail in routine mode).
- **Sweep mode**: list = `scripts/list_accounts.py` reads
  `_batch-state.json`, returns ordered list of all accounts with their
  `notion_url` and `page_id`.

### Step 2 — Dispatch per-account subagent(s)
- **Single mode**: dispatch one per-account subagent.
- **Sweep mode**: dispatch in **waves of 5 parallel subagents**. After
  each wave, append per-account results to in-memory list and persist
  partial state. Mirrors generate-dossier-batch-parallel.

Each subagent receives:
- `account_name`, `slug`, `page_id`
- `comment_log_out_path`: `dossier-feedback/comment-logs/<slug>.md`
- `truths_summary_out_path`: `dossier-feedback/known-truths/<slug>.md`
- `last_dossier_edited_at` from `_routine-state.json` (sweep mode only,
  empty in single mode)

Subagent prompt: `references/per-account-subagent.md`

### Step 3 — Aggregate (sweep mode only)
- Collect all subagent return summaries.
- Run `scripts/aggregate_routine_summary.py` with the collected JSON to
  write `dossier-feedback/_routine-summary.md` and update
  `dossier-feedback/_routine-state.json` (record `last_run_at` and
  `last_dossier_edited_at` per account).
- Failed accounts: append entries to `dossier-feedback/_routine-errors.md`.

### Step 4 — Report (both modes)
- Single mode: print output path, entry count, counts by section_tag and
  resolved/unresolved, source page URL.
- Sweep mode: print sweep totals (accounts processed, skipped,
  succeeded, failed) and the summary file path.

## Per-account subagent (references/per-account-subagent.md)

Owns the per-account run end-to-end. Returns only a small summary.

1. **Skip check** (sweep mode only): call `notion-fetch` on `page_id`,
   read `last_edited_time`. If `last_edited_time <= last_dossier_edited_at`
   AND a truths file already exists at the target path, return immediately
   with `status: "skipped-unchanged"`. This is the optimisation that keeps
   daily runs cheap.
2. Call `notion-get-comments` with
   `page_id=<resolved>, include_all_blocks=true, include_resolved=true`.
3. Pipe output through `scripts/fetch_comments_payload.py` to normalise
   to JSON: `[{discussion_id, parent_block_id?, author, created_time,
   resolved, comment_text}]`. If list is empty, return
   `status: "no-comments"`, no file written.
4. **Anchor recovery**: for each entry with `parent_block_id`, call
   `notion-fetch` on that block id and extract rendered text as
   `anchor_text`. Page-level comments (no parent_block_id) and
   recovery failures get `anchor_text: null`.
5. **Synthesise interpreted truths**: subagent reasons over each
   `(comment + anchor)` pair and emits per-entry: `{title, anchor_text,
   comment_text, interpreted_truth, section_tag, author, created_time,
   resolved, discussion_id}`. `section_tag` ∈ `{overview, vision-mission,
   power-players, past-opps, sentiment, discovery, why-anything, untagged}`
   (8 values; `why-anything` is enum-only — no deterministic classifier
   rules in phase 1; LLM judgment plus `untagged` fallback handles
   detection until phase 2 calibration).
6. **Write files**: pipe synthesised JSON to
   `scripts/build_truths_file.py --account "<name>" --slug <slug>
   --source-url <url>
   --comment-log-out dossier-feedback/comment-logs/<slug>.md
   --truths-summary-out dossier-feedback/known-truths/<slug>.md`. Both
   files written atomically; always overwrites.
7. **Return** to orchestrator:
   ```json
   {"account": "...", "slug": "...", "status": "ok|skipped-unchanged|no-comments|error",
    "entries_count": 0, "anchor_failures": 0, "elapsed_ms": 0,
    "last_dossier_edited_at": "...", "error": null}
   ```

## Output file shapes (references/output-format.md)

Two files per account, written atomically together. The comment log
preserves the original 7-field entry shape (now 8-value `Section` enum);
the truths summary is a section-grouped flat-bullet digest. See
`references/output-format.md` for the canonical schemas.

```markdown
# comment-logs/<slug>.md (entry block)
### <short title>
- **Section:** <section_tag>
- **Original passage:** <anchor_text or "(page-level comment, no anchor)">
- **Reviewer comment:** <comment_text verbatim>
- **Interpreted truth:** <one-line synthesis>
- **Author / date:** <author> · <ISO date>
- **Resolved:** <true|false>
- **Discussion ID:** <discussion_id>
```

```markdown
# known-truths/<slug>.md (section-grouped bullets)
## <section_tag>
- <interpreted-truth one-liner> _(see: <entry-title>)_
```

## Routine

- **Cadence**: Daily, 06:00 (server timezone).
- **Prompt**: `/dossier-feedback --all`
- **Provisioning**: documented in `.claude/skills/dossier-feedback/README.md`;
  use the `schedule` skill to create the routine, or set up via Notion
  Routines UI directly.
- **Cost behavior**: most days are no-ops thanks to the `last_edited_time`
  skip — only accounts whose dossier was edited (i.e. someone left a
  comment) since the previous run get reprocessed.

## Critical existing files referenced

- `outputs/generate-dossier-batch-parallel/_batch-state.json` — primary
  source of slug → notion_url mapping. Schema documented at
  `.claude/skills/generate-dossier/SKILL.md:310`.
- `.claude/skills/generate-dossier/scripts/save-dossier-to-notion.py:740`
  — confirms the `{notion_url, page_id}` shape we read.
- Dossier database id `337802db20a6806f8fdbfe480adc0e4b` (used as the
  search scope in the Step 1 fallback).
- `.claude/skills/generate-dossier/SKILL.md` — wave-of-N + per-item
  subagent + per-item state pattern we mirror.
- `.claude/skills/kb-update/scripts/resolve_mcp_path.py` — pattern reference for
  multi-source ID resolution; we reuse the env → cache → search idea but
  do NOT share code (skills are self-contained per kb-update / kb-integrate
  precedent).

## Out of scope (deferred to phase 2+)

- Modifying `generate-dossier-batch-parallel` to load the truths file as
  a research input. **This must happen as a separate task to make the
  loop useful**, but is explicitly deferred per the phase-1 brief.
- Merge / supersession logic (date-based or otherwise).
- Date-aware "Perplexity is fresher than truths file" arbitration.
- Regenerating dossiers from comments alone, skipping research.
- Resolving the comment in Notion after capture (acknowledgment loop).
- Multi-routine fan-out (one routine per account) — rejected as
  operationally heavy. Revisit only if the single sweep routine becomes
  a bottleneck.

## Deferred alternative — file location

We chose to land both files in **this** repo at
`dossier-feedback/{comment-logs,known-truths}/<slug>.md`.

The alternative — landing the truths summary as a sibling to the dossier
at `hxgtm-mcp-server/context/accounts/<slug>-known-truths.md` — was
rejected for phase 1 because it co-mingles derived state with canon.
Worth revisiting in phase 2 when the consumer side of generate-dossier
needs to load it: putting it on the canon path means the consumer just
reads a sibling file and we avoid teaching generate-dossier about a
second repo.

## Verification

### Single-account path
1. Pick one published dossier whose Notion page has at least 2 comments
   (one block-anchored, one page-level if possible).
2. Run `/dossier-feedback "<account name>"` from the repo root.
3. Confirm pre-flight passes and prints the resolved page URL.
4. Confirm both files exist:
   - `dossier-feedback/comment-logs/<slug>.md`
   - `dossier-feedback/known-truths/<slug>.md`
5. Open both files and verify:
   - Frontmatter matches between them (account, slug, source URL,
     `entry_count`).
   - Comment log: each entry has all 7 fields including `Interpreted truth`.
   - Truths summary: bullets grouped under `## <section_tag>` headers in
     the canonical order; empty groups omitted.
   - At least one comment-log entry has a non-null `Original passage`.
   - `section_tag` values are from the 8-value allowed set.
6. Re-run the same command — confirm both files are overwritten (mtimes
   updated) and counts match (no duplicate entries).
7. Edge cases:
   - Account with zero comments → "no comments found", no file written.
   - Account not in `_batch-state.json` → search fallback finds it OR
     clear error.
   - `--notion-url <bad url>` → useful error.

### Sweep path
8. Run `/dossier-feedback --all`.
9. Confirm waves of 5 dispatch in parallel; orchestrator console shows
   only one-line per-account summaries (no comment XML, no anchor text).
10. Verify `dossier-feedback/_routine-summary.md` lists every account
    with status (`ok` / `skipped-unchanged` / `no-comments` / `error`).
11. Verify `dossier-feedback/_routine-state.json` has `last_run_at` and
    `last_dossier_edited_at` per account.
12. Re-run immediately. Expect every account `status: skipped-unchanged`
    (the skip optimisation working).
13. Edit one dossier in Notion (or simulate by mutating the state
    file's `last_dossier_edited_at`). Re-run. Expect only that one
    account reprocessed.

### Unit tests
- `test_build_truths_file.py` — JSON-in → both markdown files; comment
  log shape, truths-summary section grouping, why-anything tag rendering,
  empty-section omission, atomic dual-write.
- `test_resolve_account.py` — resolution order + edge cases.
