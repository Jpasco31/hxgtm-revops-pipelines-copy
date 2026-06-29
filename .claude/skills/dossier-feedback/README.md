# dossier-feedback

Capture human comments left on Account Dossier pages in Notion and emit
**two** per-account markdown files: a full comment log for human audit,
plus a section-grouped one-line "known truths" summary for the future
generate-dossier consumer. Phase 1: capture & storage only —
`generate-dossier-batch-parallel` is **not** yet modified to consume
these files.

The full skill spec lives in [SKILL.md](SKILL.md). This README is the
operator-facing setup + routine notes.

## What gets written where

| File | Purpose |
|---|---|
| `dossier-feedback/comment-logs/<slug>.md` | One per account. Full audit trail: original passage, reviewer comment, interpreted truth, author/date, resolved state, discussion id. Humans only. Always overwritten. |
| `dossier-feedback/known-truths/<slug>.md` | One per account. Section-grouped one-line truths only — the LLM-consumer-facing artifact. Always overwritten. |
| `dossier-feedback/_routine-state.json` | Sweep-mode state: per-account `last_run_at`, `last_dossier_edited_at`, last error. Drives the skip optimisation. |
| `dossier-feedback/_routine-summary.md` | Sweep-mode summary table for the most recent `--all` run. Overwritten every sweep. |
| `dossier-feedback/_routine-errors.md` | Sweep-mode error table; only present if the most recent sweep had errors. |

Both per-account files share the same basename and frontmatter (account,
slug, source URL, `generated_at`, `entry_count`) and are written
atomically together. The `interpreted_truth` line appears in both files —
the comment log keeps it for human self-containment, the truths summary
uses it as the bullet body. See [references/output-format.md](references/output-format.md)
for the full schema.

## Invocation

```bash
# Single account, looked up in _batch-state.json
/dossier-feedback "Zurich North America"

# Single account, URL bypass (account not in _batch-state.json)
/dossier-feedback --notion-url https://www.notion.so/hyperexponential/Zurich-North-America-abc12345...

# Sweep every account in _batch-state.json (waves of 5 parallel subagents)
/dossier-feedback --all
```

## Routine setup

Provision **one** daily Notion Routine (06:00 server time) that runs
`/dossier-feedback --all`. We use a single sweep routine — not one per
account — so adding/removing accounts is a data change
(`_batch-state.json`) rather than a routine change.

**To activate the routine, use the `/schedule` skill** — it's the
recommended path because it keeps the routine definition reproducible
and discoverable. Run:

```
/schedule create --prompt "/dossier-feedback --all" --cron "0 6 * * *"
```

(Adjust the cron to your server timezone if needed.) Alternatively the
routine can be created directly in the Notion Routines UI. Recommended
cadence:

- **Cadence:** daily at 06:00.
- **Prompt:** `/dossier-feedback --all`
- **Cost behavior:** most days are no-ops thanks to the
  `last_edited_time` skip — only accounts whose dossier was edited in
  Notion since the previous run get reprocessed.

## Pre-flight requirements

- **Notion MCP** with the tools `notion-get-comments`, `notion-fetch`,
  and `notion-search`. Hard stop at pre-flight if any of these can't be
  resolved.
- **`outputs/generate-dossier-batch-parallel/_batch-state.json`** — must
  exist for sweep mode and for the default name-based single-mode
  resolution path. Single-mode runs with `--notion-url` bypass it.
- **Python 3** + `pytest` (only for the unit tests under `scripts/`).

## Folder structure

```
.claude/skills/dossier-feedback/
  SKILL.md
  README.md                            # this file
  PLAN.md                              # phase-1 implementation plan
  references/
    output-format.md                   # comment-log + truths-summary schemas
    per-account-subagent.md            # subagent prompt template
  scripts/
    resolve_account.py                 # account name / URL → page_id resolver
    list_accounts.py                   # _batch-state.json → ordered account list
    fetch_comments_payload.py          # raw notion-get-comments output → JSON
    build_truths_file.py               # synthesised JSON → both markdown files
    aggregate_routine_summary.py       # sweep summaries → state + summary + errors
    test_build_truths_file.py
    test_resolve_account.py
dossier-feedback/                      # output folder; contents written at runtime
  comment-logs/                          # one <slug>.md per account (audit trail)
  known-truths/                          # one <slug>.md per account (truths summary)
.claude/commands/
  dossier-feedback.md                  # slash command wrapper
```

## Running the unit tests

```bash
pytest .claude/skills/dossier-feedback/scripts/ -q
```

## Phase-1 boundaries (intentional)

- The skill writes both files; **nothing reads them yet**. The
  generate-dossier consumer side is a deliberate phase-2 follow-up that
  will read the truths summary, not the comment log.
- Both files are regenerated from scratch on every run. No merge logic,
  no archive, no preservation of hand edits. Hand-edits will be
  overwritten on the next run — treat both files as derived state.
  History lives in git.
- All comments (resolved and unresolved) are captured. Each entry tags
  `Resolved: true|false` so reviewers can see thread state, but
  resolution does not gate inclusion.

## Known limitations

- **Tool argument names**: `notion-get-comments` argument names vary
  slightly between Notion MCP shipments. The subagent prompt instructs
  the LLM to use whatever the canonical names are in its own
  `ToolSearch` schema; the prompt documents the *intent* rather than
  the exact arg names.
- **URL-bypass slug derivation**: when invoked with `--notion-url` and
  the page isn't in `_batch-state.json`, the slug is derived from the
  Notion page title at first fetch. If the page title is empty or
  unparseable, both files land under
  `dossier-feedback/{comment-logs,known-truths}/dossier-<8-char-id>.md`.
- **Comment author identification**: Notion comments expose the user's
  display name but not always their email. Authorship in the comment
  log uses the display name verbatim.
