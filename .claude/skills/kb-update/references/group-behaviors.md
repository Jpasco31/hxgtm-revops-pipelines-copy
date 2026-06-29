# kb-update — Per-group extended behaviours

## Contents
- When this reference is loaded
- How group extensions plug into the generic flow
- competitive
  - Scope-gate section heading
  - Summary file (`always_include`) — attached per-entity, not fanned out
  - Foundational canon (`foundational_canon`) — whole-file, every tuple
  - Section schema (8 sections with caps)
  - `canon_aliases` (currently empty)
  - `max_new_sections_per_run`
- Other groups (placeholder)
- Adding extensions for a new group

## When this reference is loaded

SKILL.md Steps 3b, 4, and 5 keep the generic flow inline and use
template variables that resolve dynamically from `config.yaml`. Read
this reference when you need the worked example for a specific group
— today only `competitive` has extended config.

## How group extensions plug into the generic flow

The generic steps in SKILL.md consume per-group extensions via these
data-driven hooks (all resolved from `config.yaml` at run time):

| Generic step | Config key consulted | Effect on the run |
|---|---|---|
| Step 3b narrowing | `groups.<slug>.scoping_strategy` | Enables filename-entity matching when set to `filename_entity`. Otherwise all canon files load unnarrowed. |
| Step 3b aliases | `groups.<slug>.canon_aliases` | Extra regex alternates for the same filename stem. |
| Step 3b summary slice | `groups.<slug>.always_include` | Per-entity section of the summary file is attached to the entity's tuple as a second writable canon path. Subagent picks per-finding which path to target. |
| Step 3b foundational canon | `groups.<slug>.foundational_canon` | Files attached WHOLE (no slicing) to every entity tuple. Carry group-wide canon (e.g. competitive's positioning.md). Subagent applies a different routing policy: prefer updates, drop weak additions (not demote). See [comparators/competitive.md](comparators/competitive.md) § Foundational-file routing policy. |
| Step 4 template | `references/comparators/<slug>.md` (fallback `default.md`) | Group-specific subagent prompt if present; generic fallback otherwise. |
| Step 4 subagent prompt | `groups.<slug>.section_schema` | Serialized as YAML and passed to each comparator subagent. Missing → subagent sees `NOT CONFIGURED` and falls back to tier-only gating. |
| Step 4 scope gate | `section_schema.*.scope_gated_by` | Orchestrator computes the scope-gated section heading(s) from the schema; extracts matching section(s) from canon as `{{scope_gate_context}}`; `ABSENT` when the schema has none. |
| Step 4 section cap | `groups.<slug>.max_new_sections_per_run` | When `0`, unmapped findings demote to `Notes / open questions` instead of creating new sections. |
| Step 4.5 dedup | (orchestrator AI) | In-conversation dedup across subagent outputs. No config — model judgement. |

No hardcoded group values in SKILL.md — everything flows through this
data contract.

## `competitive`

Codeowner: `product-marketing`. Canon: `guidance/competitive/**` and
`truth/market/competitors.md`.

### Scope-gate section heading

The `section_schema` marks `Strengths`, `Weaknesses / watch-outs`,
`hx positioning`, and `Talk track` with `scope_gated_by: "Core products"`.

The orchestrator (Step 4) resolves these at run time:

```python
scope_gate_headings = {
    s["scope_gated_by"] for s in section_schema
    if s.get("scope_gated_by")
}
# {"Core products"}
```

For each canon file, extract the `## Core products` section body and
pass it as `{{scope_gate_context}}`. If the file has no such section,
pass `ABSENT` — subagents then set `claim_scope: unscoped` on every
finding (graceful-degradation path counted as `scope_gate_skipped`).

### Summary file (`always_include`) — attached per-entity

`always_include: []` as of 2026-04 — intentionally empty.
`truth/market/competitors.md` was previously attached here as a
per-entity slice; it moved to `foundational_canon` (see below) so the
full catalog is a writable target, not just the entity's slice. The
key stays in config for future catalog-style summary files that
genuinely benefit from slicing; no group uses it today.

When populated, each matched entity gets a writable slice of the
summary file attached as an additional canon path. Trimming preserves
original line numbers so `target_line_start` / `target_line_end`
anchor against the real on-disk file (see
[load-inputs.md](load-inputs.md) § Summary-file slice and § Trimmed
summary-file input).

### Foundational canon (`foundational_canon`) — whole-file, every tuple

```yaml
foundational_canon:
  - guidance/competitive/README.md
  - guidance/competitive/positioning.md
  - truth/market/competitors.md
```

Files listed here are attached **whole** (no slicing) to every entity
tuple produced by narrowing. They carry group-wide canon that every
competitor-level subagent may need to compare against: category
positioning, top-level guidance, the full competitor catalog.

Each comparator subagent for the competitive group therefore receives
**4 writable canon paths** by default:

- The per-entity profile (e.g. `guidance/competitive/competitors/federato.md`)
- `guidance/competitive/README.md`
- `guidance/competitive/positioning.md`
- `truth/market/competitors.md`

**Routing policy differs for foundational files.** The classification
framework is unchanged — every finding is still labelled through the
eight canonical section lenses (Snapshot, Strengths, etc.). What
changes is where a foundational-labelled finding writes to:

- **Prefer updates.** Foundational files are attached so we catch
  contradictions and drift, not so we grow them. Findings that
  replace existing foundational text are the high-value case.
- **Additions are the exception.** A net-new bullet to a foundational
  file is only allowed when it's group-wide, critical, and has no
  profile home. Per-competitor tactical colour belongs in the
  profile, not here.
- **Drop, don't demote.** If a finding's natural home is a
  foundational file but it's neither an update nor a critical
  addition, the subagent drops it (stats counter
  `dropped_foundational_low_value`). Group-wide content is NOT
  redirected into the per-entity profile — that would bloat the
  profile with off-scope content.

The subagent reads each foundational file at its own Step 0 and
enumerates the file's existing `##` headings — those become the
valid section set for findings targeting that file. `section_schema`
heading names (Snapshot / Strengths / etc.) do NOT apply to
foundational files — the subagent matches by meaning, writing the
exact existing heading from the file into the finding's `section`
field.

For the full ruleset see
[comparators/competitive.md](comparators/competitive.md) §
Foundational-file routing policy and
[load-inputs.md](load-inputs.md) § Foundational canon.

### Section schema

Eight sections, with tier-eligibility and caps enforced by the
comparator:

| Section | max | Eligible tiers | Scope-gated? |
|---|---|---|---|
| Snapshot | 50 words | tier_1 | No |
| Where they show up | 6 | tier_1, tier_2 | No |
| Core products | 5 | tier_1 | No |
| Strengths | 6 | tier_1, tier_2 | Yes |
| Weaknesses / watch-outs | 6 | tier_1, tier_2 | Yes |
| hx positioning | 3 | tier_1 | Yes |
| Talk track | 3 | tier_1 | Yes |
| Notes / open questions | 5 | all tiers | No |

Tier_2 findings are blocked from Snapshot / Core products / hx
positioning / Talk track (per the tier rubric in
[comparators/competitive.md](comparators/competitive.md)) and must
carry an italic caveat when landing in Strengths / Weaknesses.

### `canon_aliases`

Empty by default. Populate only when the scope-narrowing log shows a
real miss. Format:

```yaml
canon_aliases:
  federato.md: ["federato.ai"]
  akur8.md: ["Akur8 Pricing"]
```

Empty map means "filename stem is the only match key".

### `max_new_sections_per_run`

Set to `0`. Findings that don't map to any existing section demote to
`Notes / open questions` — the comparator never invents new canon
headings autonomously.

## Other groups (placeholder)

| Group | Extended config |
|---|---|
| messaging | None — uses tier-only gating, all canon loaded unnarrowed |
| audiences | None |
| company-policies | None |
| company-overview | None |
| marketing-strategy | None |
| brand-voice | None |
| channel-playbooks | None |
| sales-methodology | None |
| accounts | None |
| rfp | None (canon: [] — skill short-circuits to Step 7 with "No canon in scope") |

When these groups activate extended behaviours (e.g. audiences
eventually adopting a `section_schema` for persona template
enforcement), append a new section here documenting the knobs.

## Adding extensions for a new group

1. Decide which knobs the group needs:
   - `scoping_strategy` — only if the raw file is typically
     entity-specific and canon has one-file-per-entity.
   - `canon_aliases` — only when entity names in the raw body differ
     from canon filenames.
   - `always_include` — only when a catalog / summary file has
     per-entity sections that benefit from sliced attachment (each
     entity sees only its own slice).
   - `foundational_canon` — only for group-wide canon files that
     every subagent should compare against as whole files (e.g.
     positioning guides, category READMEs). Remember the stricter
     routing policy: updates preferred, weak additions dropped. Do
     not use this for per-entity files — that's what narrowing is
     for.
   - `section_schema` — only if you want tier-aware routing,
     per-section caps, and scope-gating.
   - `max_new_sections_per_run` — only when `section_schema` is set.

2. Add the keys to `config.yaml` under `groups.<slug>`.

3. If `section_schema` is set, decide the scope-gate section name
   (used as `scope_gated_by`). There is no SKILL.md change — the
   generic `scope_gate_context` resolution picks it up dynamically.

4. If `always_include` is set with a summary/catalog file, consider
   whether `load-inputs.md`'s trimmed-input heuristic applies. Today
   the heuristic looks for `**<Entity>** ` bolded headings; adapt the
   regex in the orchestrator's trimming step if your summary file
   uses a different convention.

   If `foundational_canon` is set, no trimming applies — each file
   attaches whole to every entity tuple. Ensure the group's
   comparator prompt encodes the foundational-file routing policy
   (prefer updates, drop weak additions). The default `default.md`
   comparator does not yet handle foundational canon; until it does,
   foundational_canon should only be used by groups with a
   specialized `comparators/<slug>.md` that encodes the policy
   (today: competitive).

5. If the group needs a specialized comparator prompt (beyond the
   generic `references/comparators/default.md`), author
   `references/comparators/<slug>.md`. The orchestrator auto-resolves
   it in Step 4 and falls back to `default.md` when the group-specific
   file doesn't exist.

6. Append a new section to this reference file documenting the
   group's knobs and any non-obvious choices.

7. Run `/kb-update --group <slug>` once to verify the pre-flight
   summary, narrowing log, and comparator routing all behave as
   intended.
