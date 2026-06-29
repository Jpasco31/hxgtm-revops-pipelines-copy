# Lint Remediation — Bucket A Execution Plan

> Each phase below is a self-contained brief — paste one into a fresh chat to execute it.
> Source: `outputs/lint-report-2026-06-10.md` + `outputs/lint-next-steps-2026-06-12.md`.

## Context

The 2026-06-10 lint report and 2026-06-12 triage identified five **Bucket A ("Do Now")**
fixes — mechanical, objectively-correct repairs with no positioning/messaging/content-owner
judgment required. The value: fewer dead links, a single canonical Hartford dossier, lower
per-run context cost, and 16 latent content types becoming reachable. Notion-doc fixes
(#10, #15) are deliberately **out of scope**.

Each item is independent. We execute them as **5 separate phases, each in a fresh chat**, make
**unstaged edits only** (no commits, no PRs — leave the diff for human review), and close with a
**single final lint pass** (Phase 6) as batch verification.

### Two corrections discovered during verification (vs. the original task card)

1. **Item 4 does NOT live in `context.ts`.** The `polish` skill-chain guards are prose in the
   **SKILL.md files of the `hx-plugins` repo**, not `hxgtm-mcp-server/src/context.ts`. The
   reference `ads → polish` guard is at `hx-plugins/plugins/hx-marketing/skills/ads/SKILL.md`
   (its `## Skill Chaining` section). So items 4 and 5 are in **different repos** — they are NOT
   batched together.
2. **Live counts differ from the card.** `positioning_source` appears in **7 files (5 consumers +
   2 templates), not 9**. Broken-path references span **15 distinct files** (one file —
   `google-ads-rsa.md` — carries both prefix families). And the two prefix families do **not**
   strip uniformly: brand-file targets resolve under `marketing/truth/brand/…`, persona targets
   under `truth/audiences/…`. Each reference must be resolved to its real file individually — do
   not blanket-replace.

### Repos & roots

| Repo | Root | Used by |
|------|------|---------|
| Canon | `/Users/jericho/Developer/Huw/hx_projects/hxgtm-mcp-server/context/` | Phases 1, 2, 3 |
| MCP server code | `/Users/jericho/Developer/Huw/hx_projects/hxgtm-mcp-server/src/context.ts` | Phase 5 |
| Plugins | `/Users/jericho/Developer/Huw/hx_projects/hx-plugins/plugins/hx-marketing/skills/` | Phase 4 |
| Pipelines (this repo) | `/Users/jericho/Developer/Huw/hx_projects/hxgtm-revops-pipelines/` | Phase 6 lint |

> **Canon path convention:** references inside canon `.md` files are relative to the `context/`
> root. To check "does `X` resolve?", test `context/X`.

### Shared conventions (apply to every phase)

- **Unstaged edits only.** Do not `git add`, commit, branch, or push. Finish with `git -C <repo>
  status` + `git -C <repo> diff --stat` so the human can review.
- **Verify before replace.** For every rewritten path, confirm the target file exists on disk
  before saving the edit. Never blind-replace.
- **Scope discipline.** Touch only what the phase names. Do not "fix" adjacent findings from
  Bucket B (positioning category descriptor, narratives de-dup, hx Renew purge, dossier figures,
  etc.) — those need owner sign-off and are explicitly out of this batch.
- **Record the true count** of files/edits touched in your phase summary (counts were estimates).

---

## Phase 1 — Fix broken path prefixes (Item 1)

**Repo:** `hxgtm-mcp-server/context/` · **Edits:** ~15 files · **Risk:** low (structural only)

> ### ✅ DONE — implemented 2026-06-15 (unstaged in `hxgtm-mcp-server`)
> **18 canon files edited** (true count; estimate was ~15), all rewrites verified to
> resolve on disk. `git diff --stat`: 32 insertions / 32 deletions, nothing staged.
>
> **Corrections to this brief, discovered during execution:**
> - **Class A is a plain `platform/context/` prefix strip, not the persona/brand/competitive
>   split below.** The brief's "brand targets → `marketing/truth/brand/<file>.md`" rule was
>   **wrong**: `terms.md`, `positioning.md`, `platform-scope.md` actually live at
>   `truth/brand/`. Only `voice.md` / `voice_social.md` live at `marketing/truth/brand/`.
> - **Two competitive exceptions** in `competitors.md`: L272 dropped the nonexistent
>   `shared/` segment → `guidance/competitive/positioning.md`; L273 → `guidance/competitive/competitors/`.
> - `google-ads-rsa.md` L27 carried **both** families on one line (Class A
>   `truth/brand/terms.md` + Class B `marketing/truth/brand/voice.md`) — both fixed.
>
> **⏸ One item PARKED (not edited):** `competitors.md` **L276** (`…/battlecard-format.md`).
> The target never existed and its true successor is the out-of-repo `battle` skill, so this
> is a content/ownership call requiring PM sign-off — see
> `docs/proposals/lint-execution-parked-tasks.md` (item 1). As a result the acceptance grep
> returns **exactly 1 intentional hit** (the parked line) rather than 0.

### Goal
Rewrite every stale path reference so it resolves to a real file. Three reference classes:

**Class A — `platform/context/…` prefix (11 files).** Resolution is NOT a uniform strip:
- persona targets → `truth/audiences/<persona>.md`
  (confirmed real: `truth/audiences/{actuary,underwriter,it,cuo}-persona.md`)
- brand targets → `marketing/truth/brand/<file>.md`
  (e.g. `platform/context/truth/brand/terms.md` → `marketing/truth/brand/terms.md`;
  same for `positioning.md`, `platform-scope.md`)
- competitive targets → `guidance/competitive/…` (verify under `context/guidance/competitive/`)

Files (with line refs from verification):
- `truth/audiences/actuary-job-profile.md` (L7, L13)
- `truth/audiences/actuary-job-profile-uk.md` (L7, L13)
- `truth/market/competitors.md` (L272, L273, L276 → competitive guidance)
- `marketing/guidance/ads/content-types/google-ads-rsa.md` (L27 — also Class B, see below)
- `marketing/guidance/workflows/booth-copy.md` (L58, L60 → brand)
- `marketing/guidance/blog/shared/guardrails.md` (L21 → brand/terms.md)
- `marketing/guidance/social/shared/guardrails.md` (L55 → brand/terms.md)
- `marketing/persona-guides/underwriter-writing-guide.md` (L5, L11)
- `marketing/persona-guides/actuary-persona-guide.md` (L5, L11)
- `marketing/persona-guides/it-writing-guide.md` (L5, L11)
- `marketing/persona-guides/cuo-writing-guide.md` (L5, L11)

**Class B — `agents/marketing/context/…` prefix (5 files).** Uniform rule: `agents/marketing/context/` → `marketing/`.
- `marketing/guidance/ads/examples/labeled/google-ads-rsa-good-vs-weak.md` (L231)
- `marketing/guidance/web/shared/output_protocol.md` (L14)
- `marketing/guidance/ads/content-types/google-ads-rsa.md` (L27 — both classes)
- `marketing/guidance/workflows/README.md` (L31–L34)
- `marketing/guidance/social/content-types/product-use-case.md` (L32, L74)

**Class C — three named references:**
- `sdr-personal-emails.md` (×3, in `marketing/guidance/email/content-types/executive-roundtable.md` L148
  and `event-marketing.md` L11, L485) → `platform/guidance/email/personal-emails.md` ✅ exists
- `audience-calibration.md`'s `truth/brand/voice.md` (×2, in
  `marketing/guidance/email/shared/audience-calibration.md` L9, L165) → `marketing/truth/brand/voice.md` ✅ exists

### Steps
1. `grep -rn "platform/context/\|agents/marketing/context/" context/` to refresh the live inventory
   (reconcile against the list above; record the true file count).
2. For Class A, resolve each reference's basename to its real path under `context/` (persona →
   `truth/audiences/`, brand → `marketing/truth/brand/`, competitive → `guidance/competitive/`).
   Edit each occurrence.
3. For Class B, apply the uniform `agents/marketing/context/` → `marketing/` rewrite; confirm each
   resulting path exists.
4. For Class C, replace the three named references with their confirmed targets.

### Acceptance / verification
- `grep -rn "platform/context/\|agents/marketing/context/\|sdr-personal-emails" context/` → **0 hits**.
- `grep -n "truth/brand/voice.md" context/marketing/guidance/email/shared/audience-calibration.md` →
  only the corrected `marketing/truth/brand/voice.md` form remains.
- Resolver spot-check: for each rewritten path, `test -f context/<path>` passes.
- `git -C hxgtm-mcp-server status` shows ~15 modified canon files, nothing staged.

---

## Phase 2 — Repair `positioning_source` frontmatter (Item 2)

**Repo:** `hxgtm-mcp-server/context/` · **Edits:** 7 files · **Risk:** low (frontmatter only)

> ### ✅ DONE — implemented 2026-06-15 (unstaged in `hxgtm-mcp-server`)
> **7 canon files edited** (true count; card said 9), uniform value replacement
> `positioning_source: messaging/narratives.md` → `positioning_source: marketing/truth/messaging/narratives.md`.
> Verification passed: old value → 0 hits, new value → 7 hits, target file resolves on disk,
> nothing staged. `narratives.md` content untouched (Bucket B).
>
> **"9 vs 7" reconciled:** the 8th `positioning_source` grep hit
> (`truth/messaging/_template-platform.md`) is explanatory prose, not a value — platform
> messaging intentionally has no `positioning_source` (it *is* the source). So 7 is correct.
>
> Files: `_template-segment.md`, `_template-product.md`, `products/portfolio-intelligence.md`,
> `products/pricing-rating.md`, `products/submission-triage.md`, `products/decision-engine.md`,
> `segments/admitted.md` (all under `truth/messaging/`).

### Goal
Change the frontmatter value `positioning_source: messaging/narratives.md` →
`positioning_source: marketing/truth/messaging/narratives.md` (the real file ✅ exists).

Files (5 consumers + 2 templates):
- `truth/messaging/_template-segment.md` (L18) — template
- `truth/messaging/_template-product.md` (L17) — template
- `truth/messaging/products/portfolio-intelligence.md` (L7)
- `truth/messaging/products/pricing-rating.md` (L7)
- `truth/messaging/products/submission-triage.md` (L7)
- `truth/messaging/products/decision-engine.md` (L7)
- `truth/messaging/segments/admitted.md` (L7)

> **Note:** the card/triage said "9 files" — live grep finds **7**. Re-grep and reconcile; if the
> live set still differs, fix every occurrence found and record the true count.
> **Coupling (do not action):** a separate Bucket-B item may later move the *content* of
> `narratives.md`. If that happens, `positioning_source` gets repointed then. This path repair is
> correct in the meantime — do not treat it as closing the narratives question.

### Steps
1. `grep -rn "positioning_source" context/` to confirm the live set.
2. In each file, edit the value to `marketing/truth/messaging/narratives.md`.

### Acceptance / verification
- `grep -rn "positioning_source: messaging/narratives.md" context/` → **0 hits**.
- `test -f context/marketing/truth/messaging/narratives.md` passes.
- `git -C hxgtm-mcp-server status` shows the modified files, nothing staged.

---

## Phase 3 — Remove the Hartford stub dossier (Item 3)

**Repo:** `hxgtm-mcp-server/context/accounts/` · **Edits:** 1 deletion · **Risk:** low

> ### ✅ DONE — implemented 2026-06-15 (unstaged in `hxgtm-mcp-server`)
> **1 file deleted** (true count matches estimate): `context/accounts/the-hartford-dossier.md`.
> `git status` shows a single `deleted:` entry, nothing staged. No other repo touched.
>
> **Same-entity confirmed from content (not just the lint report):** both files describe
> **The Hartford Financial Services Group Inc (NYSE: HIG)** — matching CEO Christopher J. Swift,
> President A. Morris "Mo" Tooker, the Prevail personal-lines platform (10→~30 states by early
> 2027), and SEC source CIK 874766. Not a name collision.
>
> **Why the stub was the inferior copy:** the deleted file was generated **2026-04-21**, 5 days
> *before* the canonical **2026-04-26** dossier, on a run where Glean/Salesforce/Gong access
> failed — leaving 27 `[Requires Salesforce access via Glean MCP]` placeholder lines across
> Sections 1 & 4. The canonical run succeeded (real AE Chris Atkins, Strategic pod STRAT-04,
> 1 open opp, named champions, Gong meetings).
>
> **No salvage needed:** the stub's Glean-independent web-research sections (2/5/6) carry no
> unique content vs. the canonical file — the canonical Section 6 has 5 discovery questions vs.
> the stub's 3, and Section 3 is far richer. The only differing data points in the stub
> ("Kinova Group / 7 years", Tooker "Jan 2025") are exactly the **less accurate** variants
> kb-lint flagged (it's Keynova / 6 years), so nothing worth keeping.
>
> **Acceptance:** stub absent ✓ · full dossier intact at 362 lines ✓ ·
> `grep -rn "the-hartford-dossier" .` from repo root → 0 hits ✓.

### Goal
Delete the stub `accounts/the-hartford-dossier.md` (159 lines, placeholder rows like
`[Requires Salesforce access via Glean MCP]`), leaving
`accounts/the-hartford-financial-services-group-inc-dossier.md` (362 lines, complete) as the single
Hartford dossier. Verification confirmed **zero references** to the stub anywhere in the repo.

### Steps
1. Re-confirm the canonical file is complete (not itself a stub):
   `wc -l context/accounts/the-hartford-financial-services-group-inc-dossier.md` (~362) and skim it.
2. Re-confirm no references to the stub:
   `grep -rn "the-hartford-dossier" .` from the `hxgtm-mcp-server` repo root → expect only the file
   itself. If any other reference appears, repoint it to the full dossier first.
3. `rm context/accounts/the-hartford-dossier.md`.

### Acceptance / verification
- `the-hartford-dossier.md` no longer exists; the full dossier remains.
- `grep -rn "the-hartford-dossier\"" .` (and bare `the-hartford-dossier`) → no live references.
- `git -C hxgtm-mcp-server status` shows the deletion, nothing staged.

---

## Phase 4 — Guard the unguarded `polish` chains (Item 4) — ✅ DONE (2026-06-15)

**Repo:** `hx-plugins/plugins/hx-marketing/skills/` · **Edits:** 7 SKILL.md files · **Risk:** low (efficiency only, no output change)

> **Status (2026-06-15):** Implemented as unstaged edits in the `hx-plugins` working tree.
> All 7 files modified, nothing staged. Verified: guard string present exactly once in each of
> the six content files; `git diff` confirms the only change per content file is the exists-line
> split + added guard paragraph (warning blocks byte-for-byte untouched), and webinar-campaign's
> rule 3 amended. `punch-up` / `clip-podcast` → polish were **skipped** by design (zero file
> overlap with polish, so the guard's premise does not hold — see Optional note below).

> **Correction:** this is a **SKILL.md (markdown) edit in the plugins repo**, NOT a `context.ts`
> change. The guards are prose in each skill's `## Skill Chaining` section.

### Goal
Copy the existing guarded pattern from **`ads/SKILL.md` (`## Skill Chaining`, ~L420–432)** into the
six unguarded chains and fix webinar-campaign. The reference guard reads (paraphrased):

> **Context for chained polish:** Do NOT call `load_skill_context("polish")` — the parent context
> already includes the anti-AI guardrails and policies that polish would reload. Instead, load only
> the two net-new files in a single batch: `load_guidance("editor","qa-checklist")` and
> `load_guidance("editor","voice")`. Output only the polished result.

**Mechanism:** the parent skill already loads `pack:marketing-content-base` (guardrails + policies +
voice). Calling `load_skill_context("polish")` would reload all of it; the guard instead loads only
the delta (`editor/qa-checklist` + `editor/voice`). Saves ~281–343 lines per chain run.

Files edited (guard paragraph added into each `## Skill Chaining` section) — all ✅:
- [x] `blog/SKILL.md` — guard added (noun: the Final Post)
- [x] `email/SKILL.md` — guard added (noun: every email body that will be shipped)
- [x] `web-copy/SKILL.md` — guard added (noun: the Final Copy)
- [x] `press-release/SKILL.md` — guard added (noun: the Final Release)
- [x] `linkedin/SKILL.md` — guard added (noun: the Final Post)
- [x] `create-faq/SKILL.md` — guard added (noun: the Copy-Ready FAQ)
- [x] `webinar-campaign/SKILL.md` (`## Orchestration Rules`, rule 3) — amended so each child's
  polish step uses the guarded delta-load (do NOT re-`load_skill_context("polish")`), so the
  double-load is not tripled across its 3 children (web-copy, linkedin, email).

> **Optional (cheap, while in the repo):** the report flags `punch-up` and `clip-podcast` → polish
> as pre-emptive guard candidates. They currently overlap zero files, so this is **not required for
> "done."** Mention in the phase summary whether you added them.

### Steps
1. Read `ads/SKILL.md` `## Skill Chaining` as the exact reference wording.
2. For each of the six skills, insert the "Context for chained polish" guard paragraph, adapting the
   "apply to <X>" wording to that skill's final-output noun (Final Post / Final Copy / Final Release
   / Copy-Ready FAQ / email bodies). Keep the existing "if polish not found" warning block intact.
3. Update `webinar-campaign/SKILL.md` orchestration rules to require the guarded delta-load per child.

### Acceptance / verification — ✅ all passed (2026-06-15)
- [x] Each of the six SKILL.md files now contains the `Do NOT call load_skill_context("polish")`
  guard matching `ads/SKILL.md`'s pattern (`grep -c` → 1 hit per file, 6/6).
- [x] `webinar-campaign/SKILL.md` no longer implies a per-child full reload (rule 3 amended).
- [x] Diff review confirms the only change is the added guard text (warning blocks untouched).
- [x] `git -C hx-plugins status` shows the 7 modified files, nothing staged.

> **Not yet committed:** edits live in the `hx-plugins` working tree. Plan is to land them on a
> new branch `chore/lint-updates-implementation` (off an up-to-date `main`), committing only the
> 7 SKILL.md files — the untracked `campaigns/` and `docs/` dirs must NOT be included.

---

## Phase 5 — Wire 16 content types into `GUIDANCE_MAP` (Item 5) — ✅ DONE (2026-06-15)

**Repo:** `hxgtm-mcp-server/src/context.ts` (`GUIDANCE_MAP`, L222–294; `loadGuidance`, L296–302) · **Edits:** 1 file · **Risk:** low

> ### ✅ DONE — implemented 2026-06-15 (unstaged in `hxgtm-mcp-server`)
> **14 net-new entries added** (true count; brief said 16), `src/context.ts` only.
> `git diff --stat`: 16 insertions, nothing staged.
>
> **"16 vs 14" reconciled:** 2 of the brief's entries were **already wired to the identical
> paths** and were left untouched to avoid duplicate keys —
> `email."executive-roundtable"` (was L236) and
> `linkedin."alliance-partnership-company"` (was L253). Net result: **16/16 content types
> reachable.**
>
> **Added:**
> - **`blog` (new category, 8):** comparison-guide, how-to-framework, industry-commentary,
>   interview-qa, product-news, product-tutorial, research-data-insights, why-thought-leadership.
> - **`email` (+2):** flagship-announcement, product-announcement.
> - **`linkedin` (+4):** event-live-company, event-recap-daily, policy-safety, recognition
>   (social types are keyed under `linkedin` per the existing convention).
>
> **Verification:** all 16 target files resolve on disk (`test -f`); the edited `GUIDANCE_MAP`
> literal `eval`-parses cleanly (no syntax/duplicate-key error); category counts now blog 8 /
> email 7 / linkedin 19. Smoke-tests via `loadGuidance` trace all resolve to real files:
> `blog/why-thought-leadership`, `email/product-announcement`, `linkedin/recognition` ✓.
>
> **Typecheck note:** `node_modules` was not installed and there is no `tsc` binary, so the full
> `npm run build` could not run without a fresh `npm install`. A lightweight Node literal-syntax
> check was used instead (object literal `eval`-parses + smoke-tests) — adequate for a
> literal-only edit. `git -C hxgtm-mcp-server status` shows only `src/context.ts` modified,
> nothing staged.

### Goal
Add 16 entries so `loadGuidance(category, contentType)` can reach content types that ship in canon
but are currently unreachable. All target files verified to exist on disk.

**Blog (8) — add a new `blog` category** (none exists today):
```ts
  blog: {
    "comparison-guide": "marketing/guidance/blog/content-types/comparison-guide.md",
    "how-to-framework": "marketing/guidance/blog/content-types/how-to-framework.md",
    "industry-commentary": "marketing/guidance/blog/content-types/industry-commentary.md",
    "interview-qa": "marketing/guidance/blog/content-types/interview-qa.md",
    "product-news": "marketing/guidance/blog/content-types/product-news.md",
    "product-tutorial": "marketing/guidance/blog/content-types/product-tutorial.md",
    "research-data-insights": "marketing/guidance/blog/content-types/research-data-insights.md",
    "why-thought-leadership": "marketing/guidance/blog/content-types/why-thought-leadership.md",
  },
```

**Email (3) — add to the existing `email` category:**
```ts
    "executive-roundtable": "marketing/guidance/email/content-types/executive-roundtable.md",
    "flagship-announcement": "marketing/guidance/email/content-types/flagship-announcement.md",
    "product-announcement": "marketing/guidance/email/content-types/product-announcement.md",
```

**Social (5) — add to the existing `linkedin` category** (social content types are keyed under
`linkedin` in this map; follow that existing convention):
```ts
    "alliance-partnership-company": "marketing/guidance/social/content-types/alliance-partnership/company.md",
    "event-live-company": "marketing/guidance/social/content-types/event-live/company.md",
    "event-recap-daily": "marketing/guidance/social/content-types/event-recap/daily-roundup.md",
    "policy-safety": "marketing/guidance/social/content-types/policy-safety.md",
    "recognition": "marketing/guidance/social/content-types/recognition.md",
```

> **Reconcile during execution:** the 8 blog names are from the report; the 3 email + 5 social names
> were derived by diffing on-disk files against the current map. Re-list the on-disk content-type
> files (`ls context/marketing/guidance/{blog,email,social}/content-types/`) and confirm each path
> resolves before saving.

### Steps
1. Read `GUIDANCE_MAP` and `loadGuidance` to confirm the entry shape (`category → { type: path }`).
2. Add the `blog` category and the email/social entries above.
3. Confirm every added path resolves: `test -f context/<path>` for all 16.
4. If the repo has a TS build/typecheck (`npm run build` / `tsc --noEmit`), run it to confirm no
   syntax error introduced.

### Acceptance / verification
- All 16 paths exist on disk.
- Smoke-test one per category resolves via `loadGuidance` (e.g. `blog/why-thought-leadership`,
  `email/product-announcement`, `linkedin/recognition`) — either via a typecheck + manual trace or
  a quick node/ts harness if available.
- `git -C hxgtm-mcp-server status` shows only `src/context.ts` modified, nothing staged.

---

## Phase 6 — Final lint verification (batch close-out)

**Repo:** `hxgtm-revops-pipelines` (this repo) · run after Phases 1–5 are reviewed.

### Goal
Confirm the five findings are cleared by re-running the linters that originally flagged them.

### Steps
1. **kb-lint** over the groups touched by Phases 1–3 (messaging, competitive, audiences,
   channel-playbooks, accounts) — or a whole-canon `/kb-lint` run. Expect: 0 broken-path /
   stale-prefix findings, 0 `positioning_source` missing-file finding, no Hartford
   placeholder/duplicate finding.
2. **context-lint** (`/context-lint`) — expect: checks #5/#6 report 0 unguarded `polish` chains and
   no webinar-campaign double-load; check #9 reports 0 unreachable content types for blog/email/social.
3. Compare against `outputs/kb-lint-all-2026-06-10.md` and `outputs/context-lint-2026-06-12.md` to
   confirm only the five targeted findings dropped (no regressions introduced).

### Acceptance
- Clean re-run on all five findings; new report(s) saved under `outputs/`.

---

## Verification summary (end to end)

| Phase | Item | Repo | Status | What to prove |
|-------|------|------|--------|---------------|
| 1 | Broken paths | hxgtm-mcp-server/context | ✅ **DONE 2026-06-15** (18 files; 1 item parked) | every rewrite resolves; grep returns exactly 1 intentional hit (parked battlecard) |
| 2 | positioning_source | hxgtm-mcp-server/context | ✅ **DONE 2026-06-15** (7 files; card said 9) | 0 occurrences of old value; target exists |
| 3 | Hartford stub | hxgtm-mcp-server/context | ✅ **DONE 2026-06-15** (1 file deleted) | stub gone; full dossier intact at 362 lines; 0 refs |
| 4 | polish guards | hx-plugins | ☐ not started | 6 SKILL.md guarded like ads; webinar fixed |
| 5 | GUIDANCE_MAP | hxgtm-mcp-server/src | ✅ **DONE 2026-06-15** (14 net-new; 2 already wired) | 16/16 content types reachable; all paths resolve; literal parses clean (no tsc — deps not installed) |
| 6 | Final lint | hxgtm-revops-pipelines | ☐ not started | kb-lint + context-lint clean on all five |

## Out of scope (do not action in this batch)
- hx Renew purge, positioning category descriptor, narratives de-dup, competitor re-categorization,
  dossier figure conflicts, stale-doc refresh, em-dash rule, actuary persona, COO persona guide,
  fallback-manifest rebuild, Notion doc fixes (#10/#15), rfp config — all Bucket B / owner-gated.
