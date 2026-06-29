# Lint Remediation — Stakeholder Update (Bucket A)

**Date:** 2026-06-15
**Status:** ✅ Complete & verified — all items resolved (battlecard reference: Option A applied 2026-06-16)
**Branch (both repos):** `chore/lint-updates-implementation`

---

## TL;DR

We've completed the **"do-now" batch** of knowledge-base / context-lint fixes — five mechanical,
objectively-correct repairs. All five have been **re-linted and verified clean, with no regressions**.
One related item was originally **parked** for a content owner's call (the dead
`battlecard-format.md` link); it has since been **resolved via Option A** (2026-06-16) — see below.
**I'll raise the PRs for both repos** so the team can review and merge.

---

## What we set out to do

The 2026-06-10 lint pass flagged five **Bucket A** issues — mechanical fixes with no
positioning/messaging judgment required. Fixing them buys us:

- **Fewer dead links** in canon (broken cross-references that don't resolve).
- **A single canonical Hartford dossier** (we had a duplicate stub full of placeholders).
- **Lower per-run context cost** (skill chains were redundantly reloading shared content).
- **16 latent content types made reachable** (they shipped in canon but weren't wired up).

Notion-documentation fixes were intentionally **out of scope** for this batch.

---

## What we did — the 5 fixes

| # | Fix | Repo | Scope |
|---|-----|------|-------|
| 1 | Repaired broken path-prefix references so every link resolves to a real file | `hxgtm-mcp-server` (canon) | 18 files |
| 2 | Corrected the `positioning_source` frontmatter path in messaging docs | `hxgtm-mcp-server` (canon) | 7 files |
| 3 | Deleted the duplicate Hartford stub dossier (kept the complete one) | `hxgtm-mcp-server` (canon) | 1 file |
| 4 | Guarded the `polish` skill-chains against redundant context reloads | `hx-plugins` (skills) | 7 SKILL.md |
| 5 | Wired 16 content types (blog/email/social) into the guidance map | `hxgtm-mcp-server` (`src/context.ts`) | 1 file |

Phases 1–4 are committed on the branch; the Phase 5 `context.ts` change is staged in the working tree
and will go in with the PR.

---

## Verification (Phase 6)

We re-ran the linters **scoped to only the changed files** (so we'd confirm the fixes without
re-surfacing unrelated issues) and diffed against the original baseline reports.

**Result: all five findings PASS — cleared, with no regressions introduced.**

Full evidence: `outputs/lint-phase6-verification-2026-06-15.md`.

**Reproducible test plan:** any engineer can independently re-verify the branch by following
`docs/proposals/lint-test-plan/TEST_PLAN.md` — a step-by-step runbook (check out the branch, run
`/kb-lint` + `/context-lint`, confirm the five findings are gone), with a paste-ready "fast path"
prompt that checks all five fixes in ~1 minute.

> Deliberately **not** touched in this batch: the larger "Bucket B" items that need owner sign-off —
> e.g. the deprecated "hx Renew" naming, internal numeric contradictions in account dossiers, and the
> Notion documentation drift. These are real but separate, and remain queued for a future pass. Their
> continued presence is expected, not a regression.

---

## ✅ Resolved — the `battlecard-format.md` reference

This was the **one item we couldn't fix mechanically**; it was parked for a content owner's call and
has now been resolved.

**The situation:** `competitors.md` had a "Related Resources" bullet linking to a *Battlecard
generation workflow* at `…/battlecard-format.md`. That file **never existed** in canon. The
battlecard-generation capability it describes now lives in the **`battle` skill** in the `hx-sales`
plugin — a different repo, with no equivalent canon file to point at. So there was no clean 1:1 fix, and
our "verify before replace" rule meant we wouldn't point a link at a dead path. It was the single
intentional exception in the otherwise-clean link check.

**Decision: Option A, applied 2026-06-16.** The dead bullet was reworded to a by-name reference to the
competitive-intelligence (`battle`) skill in `hx-sales`, pointing at `guidance/competitive/README.md`
(both of which exist). No new canon file was created (Option C would have duplicated what the `battle`
skill already owns). The link check is now **fully clean** — the Phase 1 acceptance grep returns 0 hits.

The options considered (for the record):

| Option | What it means | Trade-off |
|--------|---------------|-----------|
| **A — Reword to name the `battle` skill** *(applied)* | Replace the dead link with a by-name reference to the competitive-intelligence (`battle`) skill in `hx-sales`. | Accurate; points readers at the actual owner of battlecard generation. |
| **B — Remove the bullet** | Delete the dead bullet entirely. | Cleanest; the competitive README already documents where battlecard generation lives, so the pointer is arguably redundant. |
| **C — Author a new canon doc** | Write a new `battlecard-format.md` in canon. | Largest effort; duplicates what the `battle` skill already owns. Not advised. |

Tracked in `docs/proposals/lint-execution-parked-tasks.md`.

---

## Next steps

1. **Done:** the `battlecard-format.md` reference resolved via Option A (2026-06-16) — bullet
   reworded in `competitors.md`, link check now fully clean.
2. **Me:** raise the PRs for **`hxgtm-mcp-server`** and **`hx-plugins`** off
   `chore/lint-updates-implementation` for team review (the battlecard edit is included).
3. **Later (separate effort):** the Bucket-B / owner-gated items remain queued for a future remediation
   batch.
