# Context Lint Report — Output Format

This document defines the canonical structure of the context-lint report. All
three subagents (Server Inspector, Plugin Inspector, Notion Comparator) must
produce findings that conform to this format so the orchestrator can merge
them cleanly.

---

## Report structure

```markdown
# Context Lint Report

**Date:** YYYY-MM-DD
**Sources:**
- MCP server: [production | local] — `[resolved path]`
- Plugins:    [production | local] — `[resolved path]`
- Notion:     [enabled | skipped: reason | failed: error]

**Skills audited:** N
**Context files audited:** N
**Plugin SKILL.md files audited:** N
**Fallback manifests audited:** N

**Findings:** N total — X errors, Y warnings, Z info
**Status:** [PASS (0 errors, 0 warnings) | NEEDS ATTENTION (warnings only) | FAIL (errors)]

---

## Summary

[2–3 sentence executive summary of context wiring health. Highlight the most
important finding and overall status. If Notion was skipped or failed, append
a sentence flagging that user-facing docs were not compared.]

---

## Per-Skill Breakdown

Resolved context weight per skill, sorted by total line count descending.
Skills exceeding the configured size threshold are flagged with ⚠.

| Skill | Files | Lines | Truth | Guidance | Persona | Chain | Issues |
|-------|-------|-------|-------|----------|---------|-------|--------|
| ads ⚠ | 18 | 2,140 | 800 | 367 | 287 | 343 | 4 |
| blog | 13 | 1,420 | 950 | 245 | 225 | 0 | 1 |
| ... | | | | | | | |

---

## Errors

Findings that block a clean run. Missing files, broken structural references,
plugin skills with no Notion entry.

### [E1] [Short title]
- **Check:** [#1 Pack integrity | #10 Notion structural]
- **Skill:** [skill name]
- **File / Reference:** `[path or notion block id]`
- **Finding:** [Description of the broken reference or missing file]
- **Suggested action:** [Concrete fix — e.g., "Update `SKILL_CONTEXTS["ads"]` in `src/context.ts:106` to point at the renamed file `truth/messaging/platform-overview.md`"]

---

## Warnings

Findings that degrade efficiency or quality but don't block the lint.

### [W1] [Short title]
- **Check:** [#2 / #3 / #4 / #5 / #6 / #8 / #9 / #10 semantic]
- **Skill:** [skill name(s)]
- **File / Reference:** `[path]`
- **Finding:** [Description]
- **Suggested action:** [Concrete fix]

---

## Info

Informational notes — parallelism opportunities, non-critical observations.

### [I1] [Short title]
- **Check:** [#7 Parallelism]
- **Skill:** [skill name]
- **File / Reference:** `[skill md path]`
- **Finding:** [Description]
- **Suggested action:** [Concrete fix]

---

## Actionable Fixes (grouped by fix type)

### Missing files (Check #1)
- [List of E-findings with file paths]

### Orphan files & packs (Checks #2, #3)
- [List of W-findings — orphan context files and orphan packs]

### Fallback drift (Check #4)
- [List of W-findings — per-skill fallback ↔ server mismatches]

### Chain duplication (Check #5)
- [List of W-findings — files duplicated across skill chains]

### Bulk loading (Check #6)
- [List of W-findings — packs loading everything when only one needed]

### Sequential loading (Check #7)
- [List of I-findings — independent calls that could be batched]

### Bloat (Check #8)
- [List of W-findings — skills exceeding the configured size threshold]

### Foundation coverage gaps (Check #9)
- [List of W-findings — orphan audiences/pillars/personas]

### Notion drift (Check #10)
- [List of E and W findings — structural and semantic doc drift]

---

## Statistics

| Metric | Value |
|--------|-------|
| Skills in `SKILL_CONTEXTS` | [N] |
| Plugin SKILL.md files found | [N] |
| Context packs defined | [N] |
| Context packs orphaned | [N] |
| Context files on disk | [N] |
| Context files referenced | [N] |
| Context files orphaned | [N] |
| Total context lines (sum across all files) | [N] |
| Skills above size threshold | [N] |
| Chains analyzed | [N] |
| Chains with duplicate loads | [N] |
| Foundation orphans (audiences / pillars / personas) | [N / N / N] |
| Server Inspector status | [N findings] |
| Plugin Inspector status | [N findings] |
| Notion Comparator status | [enabled — N findings | skipped (reason) | failed (error)] |
| Notion entries compared | [N] |
| Notion entries pre-filtered (no recent changes) | [N] |
```

---

## Severity classification rules

| Severity | Criteria |
|----------|----------|
| **Error** | Missing referenced file (Check #1). Plugin skill with no matching Notion entry (Check #10a structural). Notion entry naming a skill that doesn't exist and isn't in a known multi-repo plugin (Check #10b structural). |
| **Warning** | Orphan context file cluster (Check #2). Orphan pack (Check #3). Fallback ↔ server drift (Check #4). Chain duplication (Check #5). Unconditional bulk loading (Check #6). Skill above size threshold (Check #8). Foundation coverage gap (Check #9). Notion entry in multi-repo plugin not found in configured source (Check #10b). Notion semantic drift (Check #10c). |
| **Info** | Sequential loading that could be parallelized (Check #7 — single grouped finding). |

## Finding ID conventions

Each subagent assigns finding IDs with an origin prefix (the orchestrator
re-numbers them sequentially within the E / W / I sections during synthesis):

| Subagent prefix | Source |
|--------|--------|
| `SI-` | Server Inspector (Checks #1, #2, #3, #6, #8, #9) |
| `PI-` | Plugin Inspector (Checks #4, #5, #7) |
| `NC-` | Notion Comparator (Check #10) |

After re-numbering, findings appear as `E1`, `E2`, ..., `W1`, `W2`, ...,
`I1`, `I2`, ... in the merged report. The origin prefix is preserved in
the finding body for traceability.

## Status field

The top-level **Status** in the report header is one of:

| Status | Criteria |
|--------|----------|
| `PASS` | 0 errors, 0 warnings |
| `NEEDS ATTENTION` | 0 errors, ≥1 warning |
| `FAIL` | ≥1 error |

A clean run is `PASS`. Every newly added skill should hit `PASS` before
shipping.
