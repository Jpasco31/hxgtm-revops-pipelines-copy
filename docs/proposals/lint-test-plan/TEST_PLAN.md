# Test Plan — Lint Remediation (Bucket A) — Step-by-Step Runbook

- **Target:** the `chore/lint-updates-implementation` branch changes in `hxgtm-mcp-server`
  (canon + `src/context.ts`) and `hx-plugins` (hx-marketing skills)
- **Plan version:** 2 (manual slash-command runbook; supersedes the v1 script suite)
- **Generated:** 2026-06-15 by `create-test-plan`
- **Target commits:** `hxgtm-mcp-server` `94d2cb0` · `hx-plugins` `2658557`
- **Reference "what good looks like":** `outputs/lint-phase6-verification-2026-06-15.md`

> **How this works.** You re-run the two linters that originally caught these issues — `/kb-lint`
> and `/context-lint` — against the branch, then open the reports they generate and confirm the five
> findings are **gone**. ~15 min of mostly waiting on the linters. No scripts to install.

---

## What you're verifying (the 5 fixes)

| # | Fix | Caught by | Original finding |
|---|-----|-----------|------------------|
| 1 | Broken canon path prefixes repaired (18 files) | kb-lint | `kb-lint-all-2026-06-10.md` → **M1, M2, M3** |
| 2 | `positioning_source` frontmatter repointed (7 files) | kb-lint (messaging) | `kb-lint-messaging-2026-06-09.md` → positioning_source missing-file |
| 3 | Duplicate Hartford stub dossier deleted | kb-lint | `kb-lint-all-2026-06-10.md` → **M10, L5/L4, H9** |
| 4 | `polish` skill-chains guarded against reload (7 SKILL.md) | context-lint | `context-lint-2026-06-12.md` → **W17–W22, I3** (checks #5/#6) |
| 5 | 16 content types wired into `GUIDANCE_MAP` | context-lint | `context-lint-2026-06-12.md` → **W1/W2/W3 + W4/W5/W6** (check #9) |

---

## Part 0 — Setup (~5 min, one time)

**0.1 — Get all three repos side-by-side.** They must be siblings under the same parent
(default `~/Developer/Huw/hx_projects/`):

```
hx_projects/
├── hxgtm-revops-pipelines/   ← the skills live here; you run the commands FROM here
├── hxgtm-mcp-server/         ← canon + context.ts under test
└── hx-plugins/               ← hx-marketing SKILL.md files under test
```

The linters auto-find canon at `../hxgtm-mcp-server/context/` and plugins at `../hx-plugins/plugins/`
relative to the pipelines repo — so the sibling layout is what makes setup zero-config.

**0.2 — Check out the branch in BOTH code repos and pull latest** (run from `hxgtm-revops-pipelines/`):

```bash
git -C ../hxgtm-mcp-server checkout chore/lint-updates-implementation && git -C ../hxgtm-mcp-server pull
git -C ../hx-plugins       checkout chore/lint-updates-implementation && git -C ../hx-plugins       pull
# confirm:
git -C ../hxgtm-mcp-server branch --show-current   # → chore/lint-updates-implementation
git -C ../hx-plugins       branch --show-current   # → chore/lint-updates-implementation
```

**0.3 — Open Claude Code in the `hxgtm-revops-pipelines` repo.** That's where `/kb-lint` and
`/context-lint` are registered.

**0.4 — ⚠️ Make sure the linters read your LOCAL branch, not a remote canon.** `/kb-lint` can read
canon either from a `hxgtm-context` MCP server or from the local filesystem. You want the **local
filesystem** copy (the branch you just checked out) — a remote/staging canon server would serve the
*old* content and falsely "find" the issues again. Each report states its canon source in the run
header / stats. **Confirm it reads `../hxgtm-mcp-server/context/` (filesystem mode).** If it shows an
MCP canon source that isn't your local branch, stop — the result isn't valid. (Today the only canon
MCP connected is the *staging* one, which `/kb-lint` ignores, so it falls back to filesystem
automatically — but always check the header.)

---

## ⚡ Fast path — paste this prompt (recommended quick check)

If you just need a fast, accurate confirmation that the branch is correct, **paste the prompt below
into the Claude Code session** (after Part 0). It reads `lint-execution-plan.md` as the spec and checks
exactly the five fixes — scoped to the changed files, against your local branch — in ~1 minute, with no
whole-canon noise. It is read-only. (Parts 1–2 below — running the real `/kb-lint` + `/context-lint` —
remain the thorough, independent verification; use them if the fast path flags anything or you want a
full report.)

```text
You are verifying the five Bucket-A lint fixes on the `chore/lint-updates-implementation` branch.
READ-ONLY — do not edit, move, or delete anything; only run read-only Bash (grep/test/wc/git grep/node) and Read.

Sources (use the LOCAL filesystem — do NOT use any canon MCP server; it may serve stale content):
- This repo is hxgtm-revops-pipelines. Canon = ../hxgtm-mcp-server (branch chore/lint-updates-implementation).
  Plugins = ../hx-plugins (same branch). Confirm both branches first with `git -C <repo> branch --show-current`.

Step 1 — Read these two files; they are the SPEC for what changed and each phase's acceptance criteria:
  docs/proposals/lint-execution-plan.md  (Phases 1–5)
  docs/proposals/lint-execution-parked-tasks.md  (the originally-parked battlecard item — now RESOLVED via Option A, 2026-06-16)

Step 2 — Verify each phase against the local branch, scoped ONLY to the changed files (do not report
unrelated Bucket-B findings). Run each phase's acceptance check and capture the evidence:
  • Phase 1 (broken paths): grep -rn 'platform/context/\|agents/marketing/context/\|sdr-personal-emails' ../hxgtm-mcp-server/context/
      → expect 0 hits. (The formerly-parked battlecard-format.md line in truth/market/competitors.md was reworded via Option A on 2026-06-16, so there is no longer an allowed residual. Any hit = FAIL.)
      Also confirm audience-calibration.md uses marketing/truth/brand/voice.md (no bare truth/brand/voice.md), and spot-check that rewritten targets resolve with test -f.
  • Phase 2 (positioning_source): grep -rn 'positioning_source: messaging/narratives.md' ../hxgtm-mcp-server/context/ → 0 hits;
      ../hxgtm-mcp-server/context/marketing/truth/messaging/narratives.md exists; the new value appears in 7 files.
  • Phase 3 (Hartford stub): ../hxgtm-mcp-server/context/accounts/the-hartford-dossier.md is ABSENT;
      the canonical ...-financial-services-group-inc-dossier.md exists (~362 lines, 0 'Requires Salesforce access via Glean MCP' placeholders);
      git -C ../hxgtm-mcp-server grep -l 'the-hartford-dossier' → 0 (tracked content only).
  • Phase 4 (polish guards): each of blog, email, web-copy, press-release, linkedin, create-faq under
      ../hx-plugins/plugins/hx-marketing/skills/<name>/SKILL.md contains `Do NOT call load_skill_context("polish")` exactly once (grep -c → 1);
      ads/SKILL.md still has it (reference); webinar-campaign/SKILL.md mentions the 'guarded delta-load'.
  • Phase 5 (GUIDANCE_MAP): in ../hxgtm-mcp-server/src/context.ts, GUIDANCE_MAP has a `blog` category with 8 entries,
      email includes flagship-announcement + product-announcement, linkedin includes event-live-company / event-recap-daily /
      policy-safety / recognition; all 16 target paths resolve on disk; no duplicate keys (parse with node to be sure).

Step 3 — Output one PASS/FAIL line per phase (1–5) with the exact command + result as evidence.
The Phase 1 grep should now be fully clean (0 hits) — the formerly-parked battlecard line was reworded via Option A (2026-06-16).
Flag any genuine regression (a rewritten path resolving to the wrong file, a duplicate GUIDANCE_MAP key,
a mangled guard). End with an overall verdict: PASS only if all five fixes are cleared.
```

> Why this is more accurate than reading the linter reports by eye: it is driven by the execution
> plan's own acceptance criteria, it ignores out-of-scope Bucket-B findings entirely, and it asserts
> the **exact** expected state of the link check (now 0 broken-path hits — the formerly-parked
> battlecard line was reworded via Option A) instead of leaving you to spot it.

---

## Part 1 — Run the linters (3 runs)

Run these in the Claude Code session, one at a time. Each writes a dated report into `outputs/`.

| Run | Command | Covers | New report it writes |
|-----|---------|--------|----------------------|
| A | `/kb-lint --group messaging` | Fix 2 | `outputs/kb-lint-messaging-<today>.md` |
| B | `/kb-lint` (whole canon) | Fixes 1 & 3 | `outputs/kb-lint-all-<today>.md` |
| C | `/context-lint` | Fixes 4 & 5 | `outputs/context-lint-<today>.md` |

> Run A is quick (one group). Run B scans the whole canon in parallel waves — give it a few minutes.
> Run C audits skill wiring. Do them in any order.

---

## Part 2 — Read the reports & confirm each fix is cleared

Open each new report and check the corresponding rows. "Cleared" = the finding is **absent** from the
new report. Where useful, diff against the baseline to see it dropped.

### Fix 2 — `positioning_source` (Run A → `kb-lint-messaging-<today>.md`)
- [ ] Search the report for `positioning_source`. **Expected: no finding** that the value points at a
  missing file. (Baseline `kb-lint-messaging-2026-06-09.md` flagged it; the new report should not.)

### Fixes 1 & 3 — broken paths + Hartford (Run B → `kb-lint-all-<today>.md`)
- [ ] **Fix 1 — broken paths:** search for `platform/context/`, `agents/marketing/context/`, and
  `sdr-personal-emails`. **Expected: no broken-path / stale-prefix finding** (baseline had **M1, M2,
  M3**). The formerly-parked `battlecard-format.md` reference was reworded via Option A (2026-06-16),
  so the link check is now fully clean — see `docs/proposals/lint-execution-parked-tasks.md`.
- [ ] **Fix 3 — Hartford:** search for `the-hartford-dossier` and `Hartford`. **Expected: no
  "placeholder dossier" (M10) and no "near-duplicate dossier" (L5/L4) finding.** Only the complete
  `the-hartford-financial-services-group-inc-dossier.md` should remain.

### Fixes 4 & 5 — polish guards + content types (Run C → `context-lint-<today>.md`)
- [ ] **Fix 4 — polish chains (Check #5/#6):** find the chain-duplication / `polish` section.
  **Expected: 0 unguarded polish double-loads** (baseline flagged **W17–W22**) and no
  webinar-campaign multi-reload warning (baseline **I3**). All six chains (blog, email, web-copy,
  press-release, linkedin, create-faq) should now read as guarded, like `ads`.
- [ ] **Fix 5 — content types (Check #9):** find the orphan / unreachable-content-type section.
  **Expected: 0 unreachable content types for blog/email/social** (baseline flagged the whole unwired
  `blog` set **W1**, plus **W2/W3** and orphans **W4/W5/W6**). `GUIDANCE_MAP` now has a `blog`
  category and the email/social entries.

### Expected to STILL appear — not a failure
A whole-canon `/kb-lint` (Run B) and `/context-lint` (Run C) will still report **Bucket-B** items that
were deliberately left for a later batch. Their presence is **expected** and is NOT a regression:
- kb-lint: "hx Renew" deprecated name; account-dossier numeric contradictions (incl. the *canonical*
  Hartford file's own figures); `narratives.md` == `marketing-strategy.md` duplicate; stale review
  dates; uppercase "HX".
- context-lint: Notion documentation drift (undocumented skills / stale descriptions); orphan packs;
  missing `coo` persona; "no fallback manifests".

You are only confirming the **five fixes above** dropped — ignore the rest.

---

## Part 3 — Optional 2-minute eyeball (only if a report looks off)

If any check above is ambiguous, confirm directly against the branch from `hxgtm-revops-pipelines/`:

```bash
# Fix 1 — link check now fully clean (battlecard line reworded via Option A); expect 0 hits:
grep -rn 'platform/context/\|agents/marketing/context/\|sdr-personal-emails' ../hxgtm-mcp-server/context/
# Fix 2 — old value gone:
grep -rn 'positioning_source: messaging/narratives.md' ../hxgtm-mcp-server/context/      # expect nothing
# Fix 3 — stub gone, complete one stays:
ls ../hxgtm-mcp-server/context/accounts/ | grep -i hartford
# Fix 4 — guard present in all six chains (expect 1 each):
for s in blog email web-copy press-release linkedin create-faq; do printf '%s: ' "$s"; \
  grep -c 'Do NOT call .*load_skill_context("polish")' ../hx-plugins/plugins/hx-marketing/skills/$s/SKILL.md; done
# Fix 5 — blog category now exists in the guidance map:
grep -n 'blog: {' ../hxgtm-mcp-server/src/context.ts
```

---

## Part 4 — Sign-off

The branch **passes** when all five checkboxes in Part 2 are cleared and the broken-path grep returns
0 hits (the formerly-parked battlecard line was reworded via Option A, 2026-06-16). Record the run in
§6 and you're done — the changes are ready for the PRs (raised separately).

If something is NOT cleared, see §5.

## 5. If a fix is NOT cleared

1. Re-confirm Part 0.4 — the linter must have read your **local branch** canon, not a remote one.
   (Re-check the report's canon-source header.) A stale canon source is the #1 cause of a false fail.
2. Re-confirm Part 0.2 — both repos actually on `chore/lint-updates-implementation` and pulled.
3. If still flagged, the fix genuinely regressed — record it in §6 with the report name + the finding
   text, and re-open the relevant phase in `docs/proposals/lint-execution-plan.md`.

## 6. Sign-off log
<!-- BEGIN SIGN-OFF LOG (append-only — preserved verbatim on regeneration) -->
| Date | Tester | Reports read | Fixes cleared (n/5) | Notes |
|---|---|---|---|---|
<!-- END SIGN-OFF LOG -->
