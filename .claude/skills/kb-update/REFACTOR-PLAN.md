# kb-update Refactor — Comparator Architecture + Adjacent Cleanups

> **Status:** Approved 2026-05-04. Executable plan for another agent. All paths in this doc are relative to the repository root (`hxgtm-revops-pipelines/`) unless noted.

## Context

Within the `kb-update` skill, the per-group "raw Canon comparator" sub-agents (`groups/<slug>/group.md` for `competitive` and `messaging`, plus `references/comparators/default.md` for the other 9 groups) appear to share substantial structure but each lives in its own large file. The goal is to reduce drift risk while not flattening genuine domain differences. This plan also captures adjacent cleanups discovered during the audit (schema duplication across scripts, YAML parsing duplication, oversized files).

The roadmap ships incrementally — each phase leaves the skill releasable and has standalone value.

---

## 1. Cross-Comparator Diff Summary

| Aspect | [default.md](references/comparators/default.md) (402L, ~85% generic) | [competitive/group.md](groups/competitive/group.md) (792L, ~55% generic) | [messaging/group.md](groups/messaging/group.md) (626L, ~50% generic) |
|---|---|---|---|
| **Step 0 read** | 1–2 canon files | 1–N (profile + foundational paths) | exactly 1 file |
| **Step 1 extract** | none — direct compare | topic-gated 2-pass extraction | topic-gated 2-pass extraction |
| **Step 2 classify** | 4 categories | 6 categories (+ COSMETIC VARIANT trap) | 7 categories (+ STRENGTHENS as distinct action) |
| **Step 3 gates** | tier → deny → scope → cap → paraphrase | 9 gates incl. **corroboration**, **foundational routing**, snapshot-split | 9 gates incl. **entity-type filter**, **4 Essentials drop gates** |
| **Single-source behaviour** | demote to Notes | demote to Notes (subset of sections) | **drop entirely** (no Notes fallback) |
| **At-cap behaviour** | demote to Notes | demote to Notes | **drop** if no confident eviction |
| **Tier eligibility** | T3/T4 → Notes only | same | T3/T5 dropped outright |
| **Output JSON shape** | finding + stats | same shape, **5 extra stats fields** | same shape, **6 extra stats fields** |

**Genuine domain divergences (NOT accidental):**
- **Competitive's foundational-file routing** ([competitive/group.md#L47-L145](groups/competitive/group.md#L47-L145)) reflects a multi-file canon architecture that other groups don't have.
- **Messaging's 4 Essentials drop gates** ([messaging/group.md#L347-L412](groups/messaging/group.md#L347-L412)) directly encode a positioning rubric that doesn't apply to intel-style canon.
- **Messaging's "drop, don't demote"** policy reflects an intentional positioning-discipline call ("messaging is positioning canon, not field intel").
- **Competitive's snapshot-split rule** ([competitive/group.md#L389-L405](groups/competitive/group.md#L389-L405)) is specific to its multi-section canon shape.

**Accidental drift (genuine unification opportunities):**
- Topic-filter Pass 1 exists in competitive/messaging but is missing from default — default is more permissive and will pass off-topic claims into classification.
- Gate naming is misaligned: Gate D is "corroboration" in competitive, "entity-type" in messaging, absent in default. Same letter, different semantics.
- "Closes open question" is detected via prose cues in default/competitive but a `[NEEDS COMPLETION]` placeholder in messaging — both could be handled with a config-driven signal.
- Stats field set differs across groups even where the underlying gate exists; should normalise to a superset.

---

## 2. Recommendation on the Comparator: **Hybrid (option c)**

Rejected: **(b) single generic comparator with config inputs.** The competitive foundational-routing and messaging 4 Essentials gates are too semantically rich to be flattened into config flags without effectively re-creating per-group prompts under different names. Forcing all groups through one prompt would either silently degrade quality (default-style permissiveness applied to messaging) or balloon the "config" into a Turing-complete DSL.

Rejected: **(a) keep as-is.** The ~40–50% of each specialized comparator that IS generic instruction is real duplication and is actively drifting (gate naming, topic-filter presence, stats fields). Doing nothing means three files keep diverging.

Recommend: **(c) Shared base + per-group overlays + config-driven knobs.**
- Extract the common skeleton (read → topic-gate → extract claims → classify → gate → emit JSON) into a single `references/comparators/_base.md`.
- Externalize the knobs that vary purely by configuration into `config.yaml` per group: classification taxonomy enabled, single-source behaviour (`drop` / `demote`), at-cap behaviour, tier eligibility map, tier-prefix render rules, stats field set.
- Each group keeps a small overlay file (`groups/<slug>/group.md`) that supplies only the genuinely group-specific prompt content: foundational-routing policy (competitive), 4 Essentials rubric (messaging). Default groups use the base directly (no overlay).
- Expected size after refactor: base ~350L, competitive overlay ~250L, messaging overlay ~200L. Net reduction ~700L while reducing drift risk.

---

## 3. Generic-Comparator Interface Sketch

**Inputs (passed by orchestrator at subagent invocation, via [SKILL.md Step 4 L354-L420](SKILL.md#L354-L420)):**
- Already substituted today (L387-L404): `{{today_date}}`, `{{group_slug}}`, `{{group_label}}`, `{{entity_name}}`, `{{source_tier}}`, `{{confidentiality}}`, `{{raw_file_metadata}}`, `{{raw_file_path}}`, `{{canon_file_paths}}`, `{{section_schema}}`, `{{deny_list}}`, `{{scope_gate_context}}`
- Add in Phase 2: `{{source_tier_definitions}}`, `{{tier_eligibility_rules}}`, `{{classification_taxonomy}}`, `{{single_source_action}}`, `{{at_cap_action}}`, `{{topic_filter_enabled}}`, `{{closes_open_question_signal}}`, `{{stats_fields}}`, `{{foundational_routing_enabled}}`
- Template resolution at [SKILL.md L372-L381](SKILL.md#L372-L381) currently picks `groups/<slug>/group.md` if it exists, else `references/comparators/default.md`. Phase 3 changes this to: load `_base.md` always, then optionally append the overlay at `groups/<slug>/group.md` if it exists.

**Externalized knobs (move into `config.yaml#groups.<slug>`):**
| Knob | Today | After |
|---|---|---|
| `classification_taxonomy` | hardcoded in each prompt | enum list per group: `[contradicts, supersedes, strengthens, adds, already_present, cosmetic, out_of_scope]` |
| `single_source_action` | inline rule | `demote` / `drop` |
| `at_cap_action` | inline rule | `demote` / `drop` |
| `tier_eligibility` | inline tables | per-tier `{action: demote_to_section\|drop, render_prefix?, blocked_sections?}` map (see §3a) |
| `topic_filter_enabled` | implicit (present in 2/3) | bool |
| `closes_open_question_signal` | inline | `prose_cue` / `placeholder:<token>` |
| `stats_fields` | hardcoded | superset by default; group can opt-out of fields it never emits |
| `foundational_routing_enabled` | only in competitive prompt | bool; if true, requires overlay |

### 3a. Tier Handling — Exhaustive Map of What Moves Where

Tier handling is the single most-duplicated piece of comparator logic and warrants a dedicated map so implementation can't drift. Tiers split into **three layers** and each layer has one correct destination.

**Layer 1 — Tier *definitions*** (what T1–T5 mean: label, examples, default `can_update`, default `caveat`, default `render_prefix`).
- **Today:** Already centralized at [config.yaml#L71-L145](config.yaml#L71-L145). Includes `tier_4.render_prefix: "Informal (unverified):"` and `tier_5.render_prefix: "Vendor claim (unverified):"` and `tier_4.significance_gate{}`.
- **Inlined re-statements drift today** at [default.md#L128-L140](references/comparators/default.md#L128-L140) (tier rubric table) and [default.md#L131](references/comparators/default.md#L131) ("Treat existing canon as tier_2 weight").
- **After Phase 2:** Inline rubric in `default.md` is replaced by a single `{{source_tier_definitions}}` template variable rendered from `config.yaml`. The orchestrator at SKILL.md Step 4 reads `config.yaml#source_tiers`, formats it as a markdown table, and substitutes it. **No tier definition prose remains in any comparator file.**

**Layer 2 — Per-group *eligibility / behaviour***:
- **Today:** Lives as inline tables and prose:
  - default: [default.md#L136-L140](references/comparators/default.md#L136-L140) (tier table with eligible sections + prefixes), [default.md#L178-L188](references/comparators/default.md#L178-L188) (replace-at-cap rules)
  - competitive: [competitive/group.md#L27-L31](groups/competitive/group.md#L27-L31) (per-class routing)
  - messaging: T3/T5 dropped outright via [messaging/group.md#L26-L28](groups/messaging/group.md#L26-L28) (4 Essentials drop gates) — there is **no explicit per-tier table** in messaging today; the drops happen as a side-effect of the rubric.
- **After Phase 2:** Each group declares its tier behaviour in `config.yaml#groups.<slug>.tier_eligibility`. Concrete shapes:
  ```yaml
  groups:
    audiences: # default-fallback shape
      tier_eligibility:
        tier_3: { action: demote_to_section, target: Notes, render_prefix: "single-source: " }
        tier_4: { action: demote_to_section, target: Notes, render_prefix: "Informal (unverified): " }
        tier_5: { action: demote_to_section, target: Notes, render_prefix: "Vendor claim (unverified): " }
      single_source_action: demote_to_section: Notes
      at_cap_action: demote_to_section: Notes
    competitive:
      tier_eligibility:
        tier_3: { action: demote_to_section, target: Notes, render_prefix: "single-source: " }
        tier_4: { action: demote_to_section, target: Notes, render_prefix: "Informal (unverified): " }
        tier_5: { action: demote_to_section, target: Notes, render_prefix: "Vendor claim (unverified): " }
      single_source_action: demote_to_section: Notes  # only for {Snapshot, Strengths, Weaknesses, hx positioning}
      single_source_demote_scope: [Snapshot, Strengths, Weaknesses, "hx positioning"]
      at_cap_action: demote_to_section: Notes
    messaging:
      tier_eligibility:
        tier_3: { action: drop }
        tier_5: { action: drop }
      single_source_action: drop  # no Notes section to demote into
      at_cap_action: drop  # if no confident eviction
  ```
- The base prompt then has one generic block: "Apply your `{{tier_eligibility_rules}}`. For each finding's tier, perform the configured action."

**Layer 3 — Tier-related *validation logic that is genuinely prompt-resident*** (intentionally stays):
- [default.md#L348-L381](references/comparators/default.md#L348-L381) — Tier 4 significance gate. This is judgement criteria the LLM applies, not taxonomy. Stays in `_base.md` after Phase 3.
- Messaging's 4 Essentials drop gates ([messaging/group.md#L347-L412](groups/messaging/group.md#L347-L412)) — judgement criteria, stays in messaging overlay after Phase 3.
- Competitive's corroboration gate ([competitive/group.md#L488-L496](groups/competitive/group.md#L488-L496)) — judgement criteria, stays in competitive overlay after Phase 3.

**End-state guarantee:** After Phase 2, **zero tier-definition prose** remains in any comparator file. After Phase 3, the only tier mentions in prompts are layer-3 validation criteria. A grep for `tier_1|tier_2|tier_3|tier_4|tier_5` across `references/comparators/` and `groups/*/` should return only the layer-3 sites listed above and template variable placeholders.

**Outputs (unchanged contract):**
- `<FINDINGS_JSON>` block — same shape across all groups today; stays unified.
- `<STATS_JSON>` block — superset of fields; groups emit zeros for fields they don't track.

**Risks specifically to call out:**
- Messaging's "drop don't demote" is reachable via config, BUT the *reasoning* the prompt gives the subagent for that drop matters for output quality. Need to verify that swapping the rule via config doesn't change the rationale text the subagent generates.
- Stats-field superset means downstream consumers (Notion publish, synthesis) must tolerate zero-valued fields they didn't see before — verify [scripts/publish_to_notion.py](scripts/publish_to_notion.py) and [scripts/synthesize_findings.py](scripts/synthesize_findings.py) don't reject unknown fields.
- The competitive `snapshot_split` rule is currently embedded in classification logic, not a discrete gate — extracting it cleanly into the overlay needs care.

---

## 4. Prioritized Adjacent Refactor List

Only items genuinely worth doing.

| # | Finding | Where | Size | Value |
|---|---|---|---|---|
| F1 | **Notion schema defined in 3 places.** `SCHEMA_DDL` (21 cols) at [setup_notion.py#L124-L160](scripts/setup_notion.py#L124-L160) AND `EXPECTED_COLUMNS` at [publish_to_notion.py#L57-L82](scripts/publish_to_notion.py#L57-L82) AND `COLUMN_DDL` at [publish_to_notion.py#L92-L121](scripts/publish_to_notion.py#L92-L121). Assertion at [publish_to_notion.py#L123-L125](scripts/publish_to_notion.py#L123-L125) only catches *key-name* drift, not value drift. Extract to shared `lib_schema.py`. | M | **H** |
| F2 | **Custom YAML scalar parser duplicated 2×** (not 4 — `synthesize_findings.py` and `resolve_mcp_path.py` don't read config at runtime). `_read_yaml_scalar(path, key_path)` at [collect_inputs.py#L51-L72](scripts/collect_inputs.py#L51-L72) and [publish_to_notion.py#L272-L301](scripts/publish_to_notion.py#L272-L301), plus helper `_read_yaml_scalar_from_group()` at [publish_to_notion.py#L304-L306](scripts/publish_to_notion.py#L304-L306). Extract to shared `lib_yaml.py`. | S | **H** |
| F4 | **Tier definitions and `deny_list` inlined into prompts** rather than substituted as template variables. Causes silent drift from `config.yaml`. Tier rubric table at [default.md#L128-L140](references/comparators/default.md#L128-L140); `deny_list` is already a template variable per [SKILL.md#L400](SKILL.md#L400) BUT the rendered text duplicates examples from `config.yaml`. Replace with `{{source_tier_definitions}}` substitution from config (per §3a Layer 1). | S | M |
| F5 | **publish_to_notion.py at 991 lines** mixes JSON read, schema validation, Entity option inference, batch construction, and reactive repair. Split into `lib_notion_schema.py` + slimmer publisher. | L | M |
| F6 | **Unclear group.md vs references/ boundary** — competitive's `group.md` includes a "Foundational-file routing policy" block ([competitive/group.md#L47-L100](groups/competitive/group.md#L47-L100)) that is reference doc, not prompt content. Move policy reference to `groups/competitive/references/foundational-routing.md` (which already exists with 114 lines — consolidate). Document the contract: `group.md` is the subagent overlay prompt; `references/` is human-facing. | S | M |

**Explicitly rejected (looked like smells, aren't):**
- **Section schema duplication** — the audit initially flagged this as F3, but verification shows neither `groups/competitive/group.md` nor `groups/messaging/group.md` restates the section list inline. Both rely on the existing `{{section_schema}}` substitution at [SKILL.md#L397-L399](SKILL.md#L397-L399). Already de-duplicated. No action.
- Splitting `references/*.md` by step — already correctly modularized one-per-step.
- Cross-skill config library shared with `kb-lint` — too speculative, defer.
- Merging default.md into competitive/group.md — would lose default-fallback for the 9 unspecialized groups.
- Notion data-source ID resolution chain cleanup — works today; mostly a doc tidy.
- Moving `BATCH_SIZE` (50) and `MAX_RICH_TEXT_LEN` (2000) from [publish_to_notion.py#L42-L48](scripts/publish_to_notion.py#L42-L48) into `config.yaml` — these almost never change.

---

## 5. `.md` Files Over 500 Lines

| File | Lines | Verdict |
|---|---|---|
| [groups/competitive/group.md](groups/competitive/group.md) | 792 | **Split** — naturally addressed by the comparator hybrid refactor (overlay shrinks to ~250L). |
| [groups/messaging/group.md](groups/messaging/group.md) | 626 | **Split** — same; overlay shrinks to ~200L. |
| [SKILL.md](SKILL.md) | 717 | **Keep** — orchestration spine; splitting would fragment the one canonical step-by-step. Borderline; revisit only if it grows past ~900. |
| [VERIFICATION.md](VERIFICATION.md) | 636 | **Keep** — single coherent verification checklist. |
| Scripts >500L (publish_to_notion 991, setup_notion 770, synthesize_findings 650, resolve_mcp_path 502, run_checks 964) | — | **Only `publish_to_notion.py` warrants splitting** (F5); the others are coherent single-purpose modules whose length reflects necessary surface area. |

---

## 6. Phased Roadmap

Ordered for **low risk first, then high value**, with explicit dependencies. Each phase ends in a releasable state.

### Phase 1 — Shared script libraries (safe foundation)
**In scope (concrete file changes):**
- *Create* `.claude/skills/kb-update/scripts/lib_schema.py` containing one canonical schema definition (column name → `{notion_type, options?, formula?, ddl_fragment, in_default_view}`). Generate `SCHEMA_DDL`, `EXPECTED_COLUMNS`, and `COLUMN_DDL` programmatically from this single source.
- *Create* `.claude/skills/kb-update/scripts/lib_yaml.py` containing `read_yaml_scalar(path, key_path) -> str | None` and `read_yaml_scalar_from_group(path, group, field) -> str | None`. Logic copied verbatim from current implementations (they're identical), no behaviour change.
- *Modify* [setup_notion.py#L124-L160](scripts/setup_notion.py#L124-L160) — replace `SCHEMA_DDL` block with `from lib_schema import SCHEMA_DDL`.
- *Modify* [publish_to_notion.py#L57-L121](scripts/publish_to_notion.py#L57-L121) — replace `EXPECTED_COLUMNS` and `COLUMN_DDL` with imports from `lib_schema`. Keep the L123-L125 cross-check assertion (becomes a sanity tautology but cheap to keep).
- *Modify* [collect_inputs.py#L51-L72](scripts/collect_inputs.py#L51-L72) — replace `_read_yaml_scalar` with `from lib_yaml import read_yaml_scalar`.
- *Modify* [publish_to_notion.py#L272-L306](scripts/publish_to_notion.py#L272-L306) — replace `_read_yaml_scalar` and `_read_yaml_scalar_from_group` with imports.
- *Modify* `.claude/skills/kb-update/tests/run_checks.py` — `check_D1` (L116-L160) and `check_D9` (L395-L474) currently inspect schema constants; update them to inspect the lib_schema canonical dict instead.

**Out of scope:** Comparator changes; publish_to_notion split (Phase 5); any behaviour change.

**Dependencies:** none.

**Size:** S.

**Verify:**
1. `python3 .claude/skills/kb-update/tests/run_checks.py` — all 9 checks pass (D1, D2, D3, D4, D5, D6, D7, D8, D9).
2. `diff <(python3 setup_notion.py --plan)` against a pre-refactor capture — byte-identical.
3. `python3 publish_to_notion.py --dry-run --findings <fixture>` — byte-identical batch output.

**Exit criterion:** `grep -rn 'SCHEMA_DDL\|EXPECTED_COLUMNS\|COLUMN_DDL\|_read_yaml_scalar' .claude/skills/kb-update/scripts/` returns hits only inside `lib_schema.py` and `lib_yaml.py` (definitions) and import statements elsewhere.

---

### Phase 2 — Externalize comparator knobs into `config.yaml` (no prompt rewrite yet)
**In scope (concrete file changes):**
- *Modify* `.claude/skills/kb-update/config.yaml` — under each of the 11 group blocks (lines L146-L448), add the knob keys per §3a:
  - `tier_eligibility:` (per §3a; default-shape for 9 groups + competitive's variant + messaging's drop-shape)
  - `single_source_action:`, `single_source_demote_scope:` (competitive only)
  - `at_cap_action:`
  - `classification_taxonomy:` (list of allowed enum values)
  - `topic_filter_enabled:` (true for competitive/messaging; false for the 9 default-fallback groups in this phase, so behaviour is unchanged)
  - `closes_open_question_signal:` (`prose_cue` for default/competitive; `placeholder:[NEEDS COMPLETION]` for messaging)
  - `stats_fields:` (superset list; per-group opt-out lists)
  - `foundational_routing_enabled:` (true for competitive only)
- *Modify* [SKILL.md#L387-L404](SKILL.md#L387-L404) — extend the substitution block to render `{{source_tier_definitions}}`, `{{tier_eligibility_rules}}`, `{{classification_taxonomy}}`, `{{single_source_action}}`, `{{at_cap_action}}`, `{{topic_filter_enabled}}`, `{{closes_open_question_signal}}`, `{{stats_fields}}`, `{{foundational_routing_enabled}}` from the new config keys. Use `lib_yaml` to read.
- *Modify* [default.md#L128-L140](references/comparators/default.md#L128-L140) — replace the inline tier rubric table with `{{source_tier_definitions}}` + `{{tier_eligibility_rules}}`. Tier-4 significance gate at L348-L381 stays unchanged (Layer 3 per §3a).
- *Modify* [competitive/group.md#L27-L31](groups/competitive/group.md#L27-L31) — same substitution.
- *Modify* `messaging/group.md` — no inline tier table to replace, but ensure the rubric drops the assumption that T3/T5 are dropped via 4 Essentials only; the new `{{tier_eligibility_rules}}` block becomes the explicit drop authority.
- *Modify* `tests/run_checks.py` — extend `check_D8` (L477-L502) to assert every new config key exists for every active group.

**Out of scope:** Creating `_base.md`; removing per-group prompt scaffolding. The substituted values must reproduce existing behaviour.

**Dependencies:** Phase 1 (uses `lib_yaml`).

**Size:** M.

**Verify:** The right test for Phase 2 is *prompt-rendering equivalence*, not LLM-output byte-identity. The comparator is an LLM subagent — same prompt in does not yield byte-identical text out, so diffing two runs would fail even with zero behaviour change. Instead:
1. `check_D8` extended pass — every new config knob asserted present for every active group.
2. **Prompt-rendering review.** For each of competitive, messaging, and one default-fallback group (e.g. audiences), manually render the substituted comparator prompt (read SKILL.md Step 4 + the new config.yaml knobs + the comparator file together) and confirm the rendered `{{source_tier_definitions}}` / `{{tier_eligibility_rules}}` / etc. text reproduces the prior inline tier rubric and per-group eligibility prose. The point is: the *prompt* shown to the subagent in Phase 2 should be substantively the same as the prompt shown today. Capture the rendered prompt for each group as a one-off artifact; spot-check against the pre-Phase-2 inline content.
3. Optional sanity: run `/kb-update --group competitive` against a small raw fixture, eyeball `<FINDINGS_JSON>` for shape sanity (correct keys, plausible counts). Do NOT diff against a single-run baseline — LLM nondeterminism makes that test meaningless.

**Exit criterion:** `grep -rn 'tier_1\|tier_2\|tier_3\|tier_4\|tier_5' .claude/skills/kb-update/references/comparators/ .claude/skills/kb-update/groups/` returns only Layer-3 sites listed in §3a + template variable placeholders. Rendered prompts reproduce the prior inline tier prose.

---

### Phase 3 — Extract comparator base + overlays
**In scope (concrete file changes):**
- *Create* `.claude/skills/kb-update/references/comparators/_base.md` (~350L target) containing the common skeleton (Step 0 read → Step 1 topic-gate → Step 2 extract → Step 3 classify → Step 4 gate → Step 5 emit JSON). Source content from current default.md, competitive/group.md, messaging/group.md generic sections. Use the §3a Layer-3 tier-4 significance gate from default.md L348-L381 inside `_base.md`. Topic-filter (currently absent from default.md) gated by `{{topic_filter_enabled}}`.
- *Modify or delete* [default.md](references/comparators/default.md) — recommend **delete** and update SKILL.md L372-L381 to make `_base.md` the unconditional load; overlay loaded only if `groups/<slug>/group.md` exists.
- *Modify* [competitive/group.md](groups/competitive/group.md) (792 → ~250L target) — strip everything that's now in `_base.md`. Keep only: foundational-file routing, snapshot-split, corroboration gate (Layer 3 from §3a). Move foundational-file routing prose to [groups/competitive/references/foundational-routing.md](groups/competitive/references/foundational-routing.md) per F6 if not already there.
- *Modify* [messaging/group.md](groups/messaging/group.md) (626 → ~200L target) — strip everything that's now in `_base.md`. Keep only: 4 Essentials drop gates ([messaging/group.md#L347-L412](groups/messaging/group.md#L347-L412)), entity-type filter, NEEDS COMPLETION placeholder semantics, "drop don't demote" rationale text.
- *Modify* [SKILL.md#L372-L381](SKILL.md#L372-L381) — change template resolution to: load `_base.md` always, then concatenate `groups/<slug>/group.md` if present.
- *Create* `.claude/skills/kb-update/tests/fixtures/comparator-e2e/<slug>/` per group (3 dirs minimum: competitive, messaging, audiences-as-default-rep). Each fixture: 1 raw input + 1 canon snapshot + 1 expected `<FINDINGS_JSON>` + `<STATS_JSON>` baseline. **Must be created BEFORE Phase 3 starts** so Phase 2's "byte-identical" check has a stable baseline.
- *Create* `tests/run_checks.py` `check_E1` — invoke comparator subagent against each fixture, assert findings JSON matches baseline (allow tolerance for the `audiences` default-fallback case where topic-filter intentionally changes output; capture the new baseline as part of this phase).

**Out of scope:** Adjacent script refactors (F5/F6 except the foundational-routing move noted above); behaviour change in competitive/messaging.

**Dependencies:** Phase 2 (knobs must exist before `_base.md` can rely on them).

**Size:** L.

**Verify:**
1. `wc -l .claude/skills/kb-update/references/comparators/_base.md .claude/skills/kb-update/groups/*/group.md` — total under 800 lines (down from ~1820).
2. `check_E1` — comparator subagent runs against each fixture; output is checked for **structural / semantic equivalence** to baseline, not byte-identity (LLM nondeterminism rules out byte-identity even on a no-op run). Concretely: same set of `target_file` × `section` × classification across runs; same stats counters within a small tolerance; finding count stable. Default-group fixture diffed deliberately and re-baselined as an intentional improvement once topic-filter activates.
3. `grep -rn '## Step [0-5]' .claude/skills/kb-update/references/comparators/_base.md .claude/skills/kb-update/groups/*/group.md` — overlay files contain *no* duplicate Step headings; only `_base.md` has the canonical step structure.

**Exit criterion:** Comparator files total ~800L (from ~1820L); fixture-based regression tests pass; specialized-group output stable; default-group output diffed and accepted.

---

### Phase 4 — Adjacent cleanups (parallelizable after Phase 1)
**In scope (concrete file changes):**
- F6: *Move* the "Foundational-file routing policy" block from [competitive/group.md#L47-L100](groups/competitive/group.md#L47-L100) into [groups/competitive/references/foundational-routing.md](groups/competitive/references/foundational-routing.md) (which already exists, 114 lines). Keep only a short pointer in `group.md`. (May overlap with Phase 3 — coordinate so the move happens once.)
- F6: *Add* a `groups/README.md` documenting the contract: "`group.md` is the comparator overlay prompt loaded by `SKILL.md` Step 4. `references/` files are human-facing reference docs not loaded into any prompt."

**Out of scope:** publish_to_notion split (Phase 5); any comparator behaviour change.

**Dependencies:** Phase 1; cleaner if run after Phase 3 to avoid double-touching `competitive/group.md`.

**Size:** S.

**Verify:** `grep -rn 'Foundational-file routing' .claude/skills/kb-update/groups/competitive/group.md` returns at most one short pointer line, not the full policy.

**Exit criterion:** `competitive/group.md` contains zero non-prompt reference prose; `groups/README.md` exists.

---

### Phase 5 — `publish_to_notion.py` split (independent)
**In scope (concrete file changes):**
- *Create* `.claude/skills/kb-update/scripts/lib_notion_schema.py` — extract from [publish_to_notion.py](scripts/publish_to_notion.py): live-schema validation against a Notion data source, repair-DDL generation, schema cache. Imports from `lib_schema` (Phase 1).
- *Modify* [publish_to_notion.py](scripts/publish_to_notion.py) — drop to <600L by delegating schema/repair logic to the new lib. Keep: JSON ingest, Entity SELECT option inference, batch construction (`BATCH_SIZE=50`), `notion-create-pages` invocation.
- *Add* unit tests for `lib_notion_schema.py` repair-DDL paths (currently untestable because they only run mid-publish).

**Out of scope:** Behaviour change; comparator changes.

**Dependencies:** Phase 1 (uses `lib_schema.py`); independent of Phases 2–4 — runnable any time after Phase 1.

**Size:** L.

**Verify:**
1. `wc -l .claude/skills/kb-update/scripts/publish_to_notion.py` < 600.
2. `python3 .claude/skills/kb-update/tests/run_checks.py` — all checks pass, especially D1, D7, D9 (schema-validation-shaped).
3. Manual spot-publish against a scratch Notion landing page: identical pages produced before vs after.

**Exit criterion:** `publish_to_notion.py` under 600 lines; `lib_notion_schema.py` importable and unit-tested; reactive repair path covered by new tests.

---

**Stop-anywhere milestones:** After Phase 1 the skill has stronger foundations and is releasable. After Phase 2 the comparators are config-driven without prompt rewrite — stoppable here if Phase 3 feels risky. After Phase 3 the comparator goal is met. Phases 4–5 are pure adjacent wins that can be skipped or deferred.

---

## 7. Comparator Refactor — Scope and Risks

**Files touched (Phases 2–3):**
- *New:* `.claude/skills/kb-update/references/comparators/_base.md` (~350L), `.claude/skills/kb-update/scripts/lib_yaml.py`, `.claude/skills/kb-update/scripts/lib_schema.py`, `.claude/skills/kb-update/tests/fixtures/comparator-e2e/{competitive,messaging,audiences}/{raw,canon,baseline-findings.json,baseline-stats.json}`.
- *Modified:* [config.yaml](config.yaml) (+~80L of per-group knob config across the 11 group blocks at L146-L448), [groups/competitive/group.md](groups/competitive/group.md) (792 → ~250L), [groups/messaging/group.md](groups/messaging/group.md) (626 → ~200L), [SKILL.md](SKILL.md) (Step 4 invocation logic at L354-L420).
- *Deleted (recommended):* [references/comparators/default.md](references/comparators/default.md) — superseded by `_base.md`.
- *Tests:* extend `check_D8` ([tests/run_checks.py#L477-L502](tests/run_checks.py#L477-L502)) to assert every new config knob exists for every active group; add `check_E1` to invoke the comparator subagent against fixtures and diff against baseline JSON.

**Test coverage gap (CRITICAL — must fill before Phase 3 starts):** `tests/run_checks.py` today is structural — `check_D1` through `check_D9` validate schema/config/build-page logic but **NONE invoke a comparator subagent against a raw+canon fixture and assert on output JSON** (verified via the anchor scan). Before Phase 3:
1. Create `tests/fixtures/comparator-e2e/<slug>/` for at least 3 groups (competitive, messaging, one default-fallback like `audiences`).
2. Each fixture: 1 raw input file, 1 canon snapshot, plus a *representative* output capture (not a single-run baseline). Run the current pre-refactor comparator N≥3 times against each fixture and capture the stable structural fields — the set of `target_file × section × classification` tuples, finding count range, and stats-counter ranges. These are the regression baseline.
3. Phase 2 does NOT use these for byte-identity (LLM nondeterminism makes byte-identity a meaningless test). Phase 2 verifies via prompt-rendering review only.
4. Phase 3's `check_E1` asserts new runs fall inside the captured tuple set / count ranges — semantic-equivalence regression, not byte-equivalence.

**Top risks:**
1. **Subtle quality regression in default groups** when topic-filter is added in Phase 3 (it stays disabled in Phase 2 to preserve current behaviour). Mitigate per Phase 3 verify step: diff the default-group fixture output deliberately, re-baseline as semantic-equivalence ranges (not byte-baselines), document the improvement.
2. **Stats-field superset** breaks downstream consumers. Audit [synthesize_findings.py](scripts/synthesize_findings.py) (650 lines, JSON parsing + cross-file pairing + validation) and [publish_to_notion.py](scripts/publish_to_notion.py) for strict-mode JSON validation before Phase 3. If present, switch to lenient mode for unknown fields.
3. **Snapshot-split rule** in competitive ([competitive/group.md#L389-L405](groups/competitive/group.md#L389-L405)) is entangled with classification rather than living as a discrete gate. Mitigate by keeping it in the competitive overlay (Layer 3) rather than promoting it to `_base.md`.
4. **Messaging "drop don't demote" rationale text** quality may shift if rule moves from prompt prose to config flag. Mitigate by keeping the *rationale text* in the messaging overlay; only the `tier_eligibility.tier_3.action: drop` boolean moves to config.
5. **Tier-4 in default.md tier table missing from comment** ([SKILL.md L61](SKILL.md#L61) anchor scan finding) — the existing `{{source_tier}}` template-variable comment lists "tier_1 | tier_2 | tier_3 | tier_5" omitting tier_4. Tier_4 *is* a real tier (per [config.yaml#L109-L134](config.yaml#L109-L134)) and flows through. Fix the comment in Phase 2 while editing SKILL.md.
6. **Asymmetry between competitive and messaging** in tier-handling style: competitive has explicit per-tier eligibility tables; messaging encodes T3/T5 drops indirectly via 4 Essentials. The new `tier_eligibility` config makes both explicit, which is correct, but the messaging overlay's prose should be reviewed in Phase 3 to remove now-redundant 4-Essentials language about tier filtering (the rubric is only about positioning quality, not tier-source filtering).

---

## Verification (end-to-end)

After each phase:
1. `python3 .claude/skills/kb-update/tests/run_checks.py` — structural checks pass.
2. **Phase 1:** `python3 .claude/skills/kb-update/scripts/setup_notion.py --plan` — output byte-identical to a pre-refactor capture. (Pure-Python plan generator → byte-identity is a valid test here.)
3. **Phase 2:** prompt-rendering review. For competitive, messaging, and one default-fallback group, manually render the substituted comparator prompt (SKILL.md Step 4 + new config.yaml knobs + comparator file) and confirm the rendered text reproduces the prior inline tier rubric and per-group eligibility prose. Do **not** diff comparator subagent JSON against a single-run baseline — LLM output is non-deterministic and that test is meaningless.
4. **Phase 3:** `check_E1` runs the comparator subagent against each fixture and asserts semantic-equivalence (same `target_file × section × classification` tuple set, finding count + stats counters within range), not byte-equivalence. Default-fallback fixture re-baselined as the topic-filter activation lands.
5. **Phase 5:** manual spot-publish against a scratch Notion landing page to confirm publisher split is behaviour-preserving.
