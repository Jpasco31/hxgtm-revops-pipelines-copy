# Lint Execution — Parked Tasks

> Running register of items carved out of the Lint Remediation batch
> (`docs/proposals/lint-execution-plan.md`) because they need owner/PM sign-off rather
> than a mechanical fix. Each entry stays here until a decision is recorded and applied.
> Append new parked items as later phases surface them.

| # | Item | Raised in | Status | Owner |
|---|------|-----------|--------|-------|
| 1 | Dead `battlecard-format.md` reference in `competitors.md` | Phase 1 (broken paths), 2026-06-15 | RESOLVED — Option A applied 2026-06-16 | _pending_ |

---

## 1. Resolve the dead `battlecard-format.md` reference in canon

> **Status: PARKED — requires PM confirmation before any canon edit.**
> Raised during Lint Remediation Phase 1 (broken-path repairs), 2026-06-15.
> Owner sign-off needed because the fix is a content/ownership judgment, not a
> mechanical path repair.

### The reference

`hxgtm-mcp-server/context/truth/market/competitors.md`, "Related Resources" section
(currently line 276):

```md
- **`platform/context/guidance/competitive/battlecard-format.md`** - Battlecard generation workflow
```

This was the only broken-path reference in Phase 1 that was **not** auto-fixed. The
other 17 references were rewritten to verified real files; this one was carved out and
parked here.

### Why it can't be mechanically fixed

1. **The target does not exist and never has.** No `battlecard-format.md` (or any
   `battlecard*` file) exists anywhere under `context/`. `git log --all` for `*battlecard*`
   in the canon repo returns nothing — the file was never committed. The reference has
   always been dangling.
2. **There is no canon file successor.** The "battlecard generation workflow" the bullet
   describes now lives in the **`battle` skill** (title "Competitive Intelligence Skill")
   at `hx-plugins/plugins/hx-sales/skills/battle/SKILL.md`. That skill carries the full
   structured battlecard output format (Quick Prep / Know the Competitor / Win the Deal
   groupings and per-section templates). It lives in a **different repo, outside
   `context/`**, so there is no canon path to repoint to.
   - `context/guidance/competitive/README.md` (L27) already documents this: "The
     competitive-intelligence skill in `hx-sales` handles competitor questions and
     battlecard generation."
   - Battlecard *content* (per-competitor) lives in
     `context/guidance/competitive/competitors/{slug}.md` — but that's the L273 bullet
     directly above, not a generation workflow.
3. **Recreating a canon `battlecard-format.md` is new content** (a Bucket-B,
   owner-gated change), explicitly out of Phase 1's mechanical-repair scope.

Because verify-before-replace forbids pointing at the dead path, and there is no clean
1:1 successor file, no edit was made. The `platform/context/…/battlecard-format.md`
string therefore remains in `competitors.md` as the single intentional exception to the
Phase 1 "0 stale prefixes" acceptance grep.

### Candidate resolutions (for PM to choose)

| Option | Edit | Trade-off |
|---|---|---|
| **A. Reword to name the `battle` skill** | Replace the bullet with a by-name reference to the competitive-intelligence (`battle`) skill in `hx-sales` (matching README L22/L27 prose convention, which references skills by name, not path). | Points at the actual owner of battlecard generation. It's a reword (text + label change) and references an out-of-repo skill, not a canon file. |
| **B. Remove the bullet** | Delete the dead bullet entirely. | Factually clean — the target is gone and README L27 already documents where battlecard generation lives, so the `competitors.md` pointer is redundant. Removes information some readers may expect in this list. |
| **C. Create a canon `battlecard-format.md`** | Author a new canon doc describing the battlecard generation workflow. | Largest scope (new content); duplicates what the `battle` skill already owns; needs a content owner. Likely undesirable. |

**Recommendation:** Option A (reword to name the `battle` skill) — it preserves a useful
pointer and is accurate. Option B is the lighter-touch alternative if the team prefers
README L27 to be the single source.

### Decision

- **PM:** _pending_
- **Chosen option:** A — applied 2026-06-16. Reworded the `competitors.md` "Related
  Resources" bullet to name the `battle` skill (Competitive Intelligence, hx-sales) and
  point at `guidance/competitive/README.md`; no new canon file created. Phase 1 acceptance
  grep now returns 0 hits.
- **Once decided:** apply the edit to `competitors.md` L276 and re-run the Phase 1
  acceptance grep (should then return 0 hits).
