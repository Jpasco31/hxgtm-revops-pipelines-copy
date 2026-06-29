# kb-lint Findings — Markdown Report Contract

kb-lint produces a severity-ranked markdown report at
`outputs/kb-lint-<group>-YYYY-MM-DD.md`. This file is the single source
of truth for:

1. The in-memory finding JSON schema the orchestrator (Step 5d) builds
   from subagent output.
2. The structure of the markdown report the orchestrator renders in
   Step 5f and writes to disk in Step 6.

kb-lint does NOT publish to Notion and does NOT process raw sources. If
you want raw sources diffed against canon and staged in a Notion
database for async team triage, use the sibling skill `/kb-update`, which
unions raw inputs and owns the write path to Notion.

---

## Finding JSON schema

Every finding the orchestrator renders into the markdown report has
this shape:

```json
{
  "finding_id": "H1",
  "title": "Akur8 described differently in positioning.md and competitors.md",
  "category": "consistency",
  "severity": "high",
  "confidence": "high",
  "current_text": "<verbatim quote from target_file>",
  "proposed_text": "<verbatim replacement, or empty string>",
  "rationale": "<1–3 sentences>",
  "suggested_action": "<one-line remediation>",
  "source_file": "context/guidance/competitive/positioning.md",
  "source_line": 42,
  "target_file": "context/guidance/competitive/competitors/akur8.md",
  "target_line": 117,
  "group": "competitive",
  "codeowner": "competitive-intelligence",
  "run_date": "2026-04-15"
}
```

**Field-level rules:**

| Field | Type | Rules |
|-------|------|-------|
| `finding_id` | string | Prefix + number (`H1`, `M3`, `L2`, `E1`). Unique within a run. |
| `title` | string | Short descriptive phrase. Rendered as the finding heading in the report. |
| `category` | enum | One of: `freshness`, `cross-reference`, `consistency`, `template`, `coverage-gap`, `external`, `cross-group`. `cross-group` is emitted only in all-mode by the Cross-Group Consistency pass. |
| `severity` | enum | `high` \| `medium` \| `low`. |
| `confidence` | enum | `high` \| `medium` \| `low`. |
| `current_text` | string | Verbatim quote. Empty only for structural findings with no quotable source text. |
| `proposed_text` | string | Verbatim replacement, OR empty string for freshness / orphan / coverage-gap / broken-link / template findings (structural issues with no textual rewrite). |
| `rationale` | string | 1–3 sentences on why this finding is real. |
| `suggested_action` | string | One-line remediation step. |
| `source_file` | string | Evidence path (`context/...`) — the canon file the finding was observed in. |
| `source_line` | int \| null | Line number in source_file, or null. |
| `target_file` | string | Canon path (`context/...`) — the file that would be edited to resolve the finding. |
| `target_line` | int \| null | Line number in target_file, or null. |
| `group` | enum | Group slug from `.claude/skills/kb-lint/config.yaml`, or the literal `all` in all-mode. |
| `codeowner` | string | Group codeowner from `.claude/skills/kb-lint/config.yaml`, or `all-codeowners` in all-mode. |
| `run_date` | date | `YYYY-MM-DD` — the date the lint ran. |

Malformed findings (missing required fields) are still included in the
report with `[MALFORMED]` prefixed to the title.

---

## Markdown report template

The orchestrator renders the findings list into this structure in
Step 5f, then writes the result to
`outputs/kb-lint-<group>-YYYY-MM-DD.md` in Step 6.

```markdown
# kb-lint — <Group Label>          # all-mode: "# kb-lint — Whole Canon"

# --- Group-mode header ---
**Scan mode:** group
**Group:** <slug> (<label>)
**Codeowner:** <codeowner>
**Active:** <yes | no>
**Run date:** <YYYY-MM-DD>
**Canon access:** <mcp | filesystem>
**Canon scope:** <K> in-scope files (of <N> total)
**Dimensions:** <list of active dimensions>
**Subtree focus:** <full | <path>>
**Phase 3 status:** <enabled — N claims verified, X contradicted, Y outdated | skipped (reason) | failed mid-run — <error>>

# --- All-mode header (replaces Group/Active/Subtree with whole-canon lines) ---
**Scan mode:** all
**Run date:** <YYYY-MM-DD>
**Canon access:** <mcp | filesystem>
**Canon scope:** <K> files (context/ <C> + project meta docs <M>)
**Shards:** <shard_count> (wave size <W>) — <all returned | K incomplete>
**Dimensions:** <list of active dimensions>
**Cross-group pass:** <N findings | skipped | failed>
**Project meta docs:** <scanned (M files) | skipped (reason)>
**Phase 3 status:** <enabled — N claims verified, X contradicted, Y outdated | skipped (reason) | failed mid-run — <error>>

---

## Summary

<2–3 sentence executive summary: overall health, most important
finding. If Phase 3 was skipped/failed, append the skip disclaimer.>

---

## High Severity

> Internal contradictions within canon + cross-group contradictions
> (all-mode `cross-group`) + externally-disproven claims (Phase 3
> `contradicted`).

### [H1] <title>

- **Category:** <consistency | external | ...>
- **Severity:** high
- **Confidence:** <high | medium | low>
- **Source:** `context/<path>` (line <N>)
- **Target:** `context/<path>` (line <N>)

**Current text:**

> <verbatim quote>

**Proposed text:**

> <verbatim replacement, or "_No textual replacement proposed._">

**Rationale:** <1–3 sentences>

**Suggested action:** <one-line remediation>

---

## Medium Severity

> Staleness, broken references, template compliance issues,
> superseding data (Phase 3 `outdated`).

### [M1] <title>

- **Category:** <freshness | cross-reference | template | external | ...>
- **Severity:** medium
- **Target:** `context/<path>` (line <N>)

**Rationale:** <1–3 sentences>

**Suggested action:** <one-line remediation>

---

## Low Severity

> Orphans, missing metadata, coverage gaps, informational notes.

### [L1] <title>

- **Category:** <coverage-gap | ...>
- **Severity:** low
- **Target:** `context/<path>`

**Rationale:** <1–3 sentences>

---

## Coverage Gaps

| Topic | Referenced in | Canonical location missing? |
|-------|---------------|-----------------------------|
| ... | ... | ... |

---

## Statistics

| Metric | Value |
|--------|-------|
| Scan mode | <group / all> |
| Group | <slug> (<label>)  — `all (Whole Canon)` in all-mode |
| Codeowner | <codeowner> |
| Run date | <YYYY-MM-DD> |
| Canon access | <mcp / filesystem> |
| Canon files in scope | <K> / <N> |
| Shards (all-mode) | <shard_count> — <all returned / K incomplete> |
| Cross-group findings (all-mode) | <C> |
| Project meta docs (all-mode) | <scanned (M) / skipped (reason)> |
| Findings: high / medium / low | <X> / <Y> / <Z> |
| Malformed findings | <N> |
| Phase 3 status | <enabled / skipped (reason) / failed> |
```

Omit the all-mode-only rows (`Shards`, `Cross-group findings`, `Project meta
docs`) in a group-mode report.

### Rendering rules

- **Omit empty sections.** If there are no L findings, drop the "Low
  Severity" heading entirely — do not print an empty section with a
  "No findings" placeholder.
- **Zero findings overall** → still write the report, but the only
  body sections are the Summary ("Group is healthy — no findings this
  run") and Statistics.
- **Finding ordering inside each severity section:** by category first,
  then by `source_file` / `target_file` alphabetical. Use the
  `finding_id` order as the tiebreaker.
- **Prefix `[MALFORMED]` in the `###` heading** for any finding that
  failed the required-fields check in Step 5d.

---

## Severity classification rules

| Severity | Criteria |
|----------|----------|
| **High** | Internal contradiction within canon (same entity described differently in 2+ files). Cross-group contradiction (all-mode, two shards disagree on one entity). Externally disproven claim (Phase 3). |
| **Medium** | Stale content (last_reviewed past review cadence). Broken cross-reference. Template compliance violation. Cross-group divergence (all-mode, softer drift). Externally outdated claim (Phase 3). |
| **Low** | Orphaned file. Missing date metadata. Coverage gap. Informational notes. |

## Finding ID conventions

Each subagent assigns finding IDs with a prefix:

| Prefix | Source |
|--------|--------|
| `H` | High severity (canon internal) |
| `M` | Medium severity |
| `L` | Low severity |
| `E` | External verification findings (Phase 3, when enabled) |
| `X` | Cross-group consistency findings (all-mode, when enabled) |

The orchestrator renumbers findings sequentially within each severity
section during synthesis (Step 5) to avoid ID collisions between subagents.
`X` findings are routed into the High / Medium sections by their own
severity (like `E` findings), with `category: cross-group` preserved.
