# Framer Template Sync — Output Format

This file defines the structure of the daily drift report emitted by `/framer-template-sync` (audit mode) and `/framer-template-sync --apply` (apply mode).

## File Location

`outputs/framer-template-sync-YYYY-MM-DD.md`

Example: `outputs/framer-template-sync-2026-06-28.md`

## Header

```
# Framer Template Sync Report

**Date:** 2026-06-28
**Session ID:** <framer-agent-session-id>
**Mode:** audit | apply
**References scanned:** 10
**Live collections found:** 12

## Summary

| Reference | OK | Unambiguous | TBD | Ambiguous | Orphan Ref | Total Findings |
|-----------|----|-------------|-----|-----------|------------|----------------|
| newsroom.md | 8 | 0 | 0 | 0 | 0 | 0 |
| faqs.md | 5 | 2 | 3 | 0 | 0 | 5 |
| customer-story.md | 12 | 1 | 0 | 0 | 0 | 1 |
| ... | ... | ... | ... | ... | ... | ... |

**Overall:** 3 Unambiguous, 3 TBD, 0 Ambiguous, 0 Orphan Ref
```

## Per-Reference Section

One section per reference file, in the same order as the glob (alphabetical by filename). Each section:

```
## newsroom.md

**Status:** OK (no drift)

> **✅ IDs confirmed 2026-06-24.** Preflight run against session 2 (branch: glassy-flare). Two collections, 14 fields, 4 enum cases verified.

Findings: none
```

```
## faqs.md

**Status:** DRIFT DETECTED (3 TBD, 2 Unambiguous)

### Findings

| Severity | Kind | Location | Reference Value | Live Value | Action |
|----------|------|----------|-----------------|------------|--------|
| TBD | Field ID | lines 36-38 | `TBD` (Slug) | `kCI7wbxLr__slug` | Backfill |
| TBD | Field ID | lines 36-38 | `TBD` (Page Title) | `kCI7wbxLr__pageTitle` | Backfill |
| TBD | Field ID | lines 36-38 | `TBD` (Meta Description) | `kCI7wbxLr__metaDescription` | Backfill |
| Unambiguous | Enum case | line 52 | `Virtual Event` | `irtual Event` | Rewrite |
| Unambiguous | Field ID | line 67 | `qVU37w2bj` (old) | `qVU37w2bj_new` | Rewrite |

### Apply Actions (if --apply)

- [x] Backfilled 3 TBD field IDs (Slug, Page Title, Meta Description) on lines 36-38.
- [x] Rewrote 2 Unambiguous enum / field values.
- [ ] Skipped 0 Ambiguous findings (requires human review).

**Stamp added:** `> **✅ IDs confirmed 2026-06-28.** Preflight run against session <id>. Backfilled 3 TBD, rewrote 2 Unambiguous.`
```

## Severity Ranking

Findings are listed in this order within each reference section:

1. **Ambiguous** — vanished field/case with no clear live equivalent. Requires human decision. Apply mode stops for this reference.
2. **Orphan Ref** — collection ID in reference no longer exists live. Requires human decision (delete reference? archive?).
3. **TBD** — literal `TBD` placeholder. Auto-fixable via backfill.
4. **Unambiguous** — same role/name, new ID or case name. Auto-fixable via rewrite.
5. **OK** — no findings for this reference.

## Footer

```
---

## Next Steps

- Run `/framer-template-sync --apply` to auto-fix Unambiguous + TBD drift.
- For Ambiguous or Orphan Ref findings, open the reference file and reconcile manually against the live schema.
- After any manual edits, re-run this skill to confirm `OK` status.
- `format-for-framer` continues to handle per-publish drift for the single page type being published right now — this report is the outer-loop cache maintenance pass.
```

## Apply Summary Block (only present in --apply mode)

```
## Apply Summary

**Files rewritten:** 2 (faqs.md, customer-story.md)
**Fields backfilled:** 3
**Enum cases corrected:** 1
**Lines changed:** 12

**Deferred to human:**
- 0 Ambiguous findings (none encountered)
- 0 Orphan Ref findings (none encountered)

**Unstaged changes:** Run `git status` and `git diff` to review before committing.
```
