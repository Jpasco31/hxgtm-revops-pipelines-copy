# KB-Lint + Context-Lint: Manual Test & Analysis Runbook

## Context

We need to produce a "current state" read on knowledge-base and skill-wiring health so Huw can brief David. The plan is **run → analyse → highlight** only — no remediation. Two linters feed it:

- **`kb-lint`** — group-scoped content-quality audit (contradictions, stale claims, data gaps, broken refs, template compliance, optional external fact-check). One report per group.
- **`context-lint`** — global structural-wiring audit (skills ↔ context files ↔ plugin SKILL.md ↔ MCP fallbacks ↔ Notion docs). One report total.

This run also feeds an upcoming product launch (~4–5 weeks out) needing a clean website-messaging sweep, so **messaging-related findings get called out prominently** in the final analysis.

Both linters are runnable now: canon resolves via `../hxgtm-mcp-server/context/` ✓, plugins via `../hx-plugins/plugins/` ✓. Optional phases (kb-lint Phase 3 / Perplexity, context-lint Check #10 / Notion) are non-blocking and skip silently if unavailable.

**Decisions locked for this run:**
- Cover **all 11 active groups** including `rfp` (empty canon → near-empty report is expected, not a failure).
- Leave kb-lint **Phase 3 on auto** (no `--no-external`); it self-skips if Perplexity isn't wired.
- `competitive` already has a report dated today (`outputs/kb-lint-competitive-2026-06-09.md`) — re-run it so all 11 are produced under one consistent pass.

This document is the manual runbook: **run each command one at a time, eyeball the output, tick the box, then move to the next.** Stage 3 (analysis) only starts once all 12 reports exist.

---

## Stage 1 — kb-lint, one group per run (11 runs)

Run these **one at a time** in the project root. After each, confirm the report file was written under `outputs/` and skim it before moving on. Expected output path: `outputs/kb-lint-<group>-2026-06-09.md` (a same-day re-run appends `-2`, `-3`, … — note the actual filename in the check column).

| # | Command | Output file | Done? | Notes (findings count / anomalies) |
|---|---------|-------------|-------|------------------------------------|
| 1 | `/kb-lint --group competitive` | `outputs/kb-lint-competitive-2026-06-09*.md` | ☐ | (re-run; prior report exists) |
| 2 | `/kb-lint --group messaging` | `outputs/kb-lint-messaging-2026-06-09.md` | ☐ | **launch-critical** |
| 3 | `/kb-lint --group audiences` | `outputs/kb-lint-audiences-2026-06-09.md` | ☐ | |
| 4 | `/kb-lint --group company-policies` | `outputs/kb-lint-company-policies-2026-06-09.md` | ☐ | |
| 5 | `/kb-lint --group company-overview` | `outputs/kb-lint-company-overview-2026-06-09.md` | ☐ | |
| 6 | `/kb-lint --group marketing-strategy` | `outputs/kb-lint-marketing-strategy-2026-06-09.md` | ☐ | |
| 7 | `/kb-lint --group brand-voice` | `outputs/kb-lint-brand-voice-2026-06-09.md` | ☐ | **launch-relevant** (positioning) |
| 8 | `/kb-lint --group channel-playbooks` | `outputs/kb-lint-channel-playbooks-2026-06-09.md` | ☐ | |
| 9 | `/kb-lint --group sales-methodology` | `outputs/kb-lint-sales-methodology-2026-06-09.md` | ☐ | |
| 10 | `/kb-lint --group accounts` | `outputs/kb-lint-accounts-2026-06-09.md` | ☐ | |
| 11 | `/kb-lint --group rfp` | `outputs/kb-lint-rfp-2026-06-09.md` | ☐ | empty canon → expect near-empty report |

**Per-run check (do this for each before ticking the box):**
1. Report file exists at the expected path (or a `-N` variant if re-run same day).
2. It has the standard sections: a header/run-stats block, and severity-grouped findings (**Requires Human Review / High / Medium / Low**).
3. Run stats name the group and a non-zero file count (except `rfp`, which is expected to be ~0).
4. No hard error in the transcript about canon being unreachable (would mean MCP + filesystem both failed — stop and fix before continuing).

> Optional speed-up: if running all 11 by hand is tedious, they can be launched in parallel waves later — but for this **manual one-by-one test pass**, run sequentially so each report can be eyeballed in isolation.

---

## Stage 2 — context-lint, single global run (1 run)

| # | Command | Output file | Done? | Notes |
|---|---------|-------------|-------|-------|
| 12 | `/context-lint` | `outputs/context-lint-2026-06-09.md` | ☐ | global; not group-scoped |

**Per-run check:**
1. Report exists at `outputs/context-lint-2026-06-09.md` (or `-N` variant).
2. Pre-flight resolved both sources via local fallback (MCP `../hxgtm-mcp-server/`, plugins `../hx-plugins/plugins/`) — no hard failure.
3. Findings are grouped by tier: **Errors / Warnings / Info**, covering the 10 checks (pack integrity, orphan files, orphan packs, fallback sync, chain dup, bulk loading, parallelism, size profiling, foundation coverage, Notion drift).
4. Check #10 (Notion) either ran or skipped silently — both are acceptable.

---

## Stage 3 — Cross-report analysis (after all 12 reports exist)

Goal: one analysis doc that **surfaces and ranks the biggest opportunities** across all reports. It does **not** fix anything — it tells the team what to tackle and why. Save to `outputs/lint-analysis-2026-06-09.md`.

**Inputs:** all 11 `outputs/kb-lint-*-2026-06-09.md` + `outputs/context-lint-2026-06-09.md`.

**Method:**
1. **Collect** — read every report; pull each finding with its source report, group, severity tier, and a one-line description.
2. **Normalise severity** — map both scales onto one impact ranking. Starting point:
   - kb-lint: Requires Human Review ≈ highest → High → Medium → Low.
   - context-lint: Errors → Warnings → Info.
   - The analyst makes the final ranking call; tiers are the seed, not the verdict.
3. **Rank "biggest opportunities"** — top KB content issues (from kb-lint) and top structural-wiring issues (from context-lint), highest-impact first.
4. **Flag launch-relevant items** — tag every messaging/positioning/website-copy finding (esp. from `messaging` and `brand-voice`) as **🚀 launch-relevant** and give them a dedicated callout — they feed the website-messaging sweep even though that sweep is separate work.
5. **Stay at the "what & why" altitude** — no remediation steps, no edits to canon or skills.

**Analysis doc structure:**
- **Executive summary** — 3–5 bullets: overall KB health, overall wiring health, the single biggest opportunity in each.
- **Top KB opportunities (ranked)** — table: rank · group · finding · severity · why it matters.
- **Top structural-wiring opportunities (ranked)** — table: rank · check · finding · severity · why it matters.
- **🚀 Launch-messaging callout** — messaging/positioning findings most relevant to the upcoming launch sweep.
- **Coverage notes** — which groups had nothing notable; any report that errored or ran degraded (e.g. Phase 3 skipped, `rfp` empty); run statistics.

**This also seeds Huw's update to David**, which should contain:
- Summary of kb-lint + context-lint output.
- Suggested HXGTM MCP knowledge-base changes implied by the findings (named as opportunities, not applied).
- Improvements to the kb-lint / context-lint skills themselves, based on observations from this run (e.g. noise, false positives, missing dimensions, ergonomics of one-by-one running).

---

## Verification / definition of done

- [ ] 11 kb-lint reports exist under `outputs/` (one per group, dated 2026-06-09), each with the standard section structure.
- [ ] 1 context-lint report exists under `outputs/`, dated 2026-06-09.
- [ ] No run aborted on a canon-unreachable or source-missing hard error (rfp's empty report is expected, not an error).
- [ ] `outputs/lint-analysis-2026-06-09.md` exists, ranks the biggest KB + wiring opportunities, and has a dedicated 🚀 launch-messaging callout.
- [ ] The analysis stays at "what to tackle & why" — no canon or skill edits were made.

## Notes / scope guardrails

- **Run, analyse, highlight only.** Whether/how to fix individual findings — and whether to invest further in the lint tooling — is decided *after* the team sees the analysis.
- Both optional phases are non-blocking; a skipped Perplexity (Phase 3) or Notion (Check #10) is fine and just gets noted in coverage.
- Re-running on the same day appends `-N` to filenames — record the actual filename in the runbook table if that happens, so Stage 3 reads the right files.
