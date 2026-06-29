# kb-update Findings — Notion Output Contract

kb-update publishes findings as rows in **per-group Notion databases**
nested under a "KB - Updates Review" landing page. Each group
(`competitive`, `messaging`, `audiences`, …) has its own `KB - <Label>`
database — one row per finding from the uploaded raw file.

This file is the single source of truth for:

1. The in-memory finding JSON schema the orchestrator (Step 5) builds
   from the comparator subagent's output.
2. The mapping from finding fields to Notion database columns (same
   schema for every per-group database).
3. The markdown body template rendered into each row's detail page.
4. The DDL needed to create a fresh group database if one is missing
   or a new group is added.

The publisher script
[`.claude/skills/kb-update/scripts/publish_to_notion.py`](../scripts/publish_to_notion.py)
consumes the finding JSON, resolves the correct database for the
target group (from `config.yaml`), and emits a Notion `create-pages`
payload. The comparator subagent must produce output the orchestrator
can normalize into this schema.

---

## Finding JSON schema

Every finding the orchestrator hands to the publisher has this shape:

```json
{
  "finding_id": "R1",
  "title": "R1: Akur8 UK pricing model contradicts current offering",
  "entity": "Akur8",
  "category": "raw-canon-conflict",
  "severity": "high",
  "source_tier": "tier_1",
  "claim_scope": "structural",
  "core_product": "Akur8 Pricing",
  "action": "replace",
  "evidence_basis": "structural",
  "closes_open_question": null,
  "current_text": "<≤400 char human-readable preview of canon span>",
  "proposed_text": "<paraphrased replacement — see paraphrase contract below>",
  "rationale": "<1–3 sentences; may include verbatim quotes for reviewer context>",
  "suggested_action": "<one-line remediation>",
  "source_file": "akur8-brief-2026-03-18.md",
  "source_line": 42,
  "target_file": "context/guidance/competitive/competitors/akur8.md",
  "target_line_start": 115,
  "target_line_end": 119,
  "group": "competitive",
  "codeowner": "product-marketing",
  "run_date": "2026-04-15"
}
```

**Internal-only fields (not published to Notion):** `claim_scope`,
`core_product`, and `evidence_basis` are kept on findings through
Pass A dedup and Gate H demotion logic in the orchestrator; they
drive routing decisions upstream of publish but their Notion columns
were removed in the 2026-04 schema cleanup.

**Field-level rules:**

| Field | Type | Rules |
|-------|------|-------|
| `finding_id` | string | `R1`, `R2`, … — unique within a run. |
| `title` | string | Short descriptive phrase prefixed with `R{n}:` for triage UX. Becomes the Notion row title. |
| `entity` | string | Target canon filename stem, title-cased (`akur8.md` → `Akur8`). Populates the `Entity` Notion column. Visible in the `Triage` view but no longer drives grouping — that role moved to the `Review Bucket` formula (see "Default view" below). |
| `category` | enum | Always `raw-canon-conflict` for kb-update findings. |
| `severity` | enum | `high` \| `medium` \| `low`. kb-update findings are typically `high`. |
| `source_tier` | enum | `tier_1` \| `tier_2` \| `tier_3` \| `tier_5`. See tier rubric in [raw-canon-comparator.md](raw-canon-comparator.md). Tier 4 findings are dropped before reaching this struct. |
| `claim_scope` | enum | `structural` \| `niche` \| `unscoped`. Outcome of the Core-products scope gate. `structural` = finding ties to a listed Core product (or landed in a non-gated section). `niche` = demoted to Notes because no product matched. `unscoped` = target file has no `Core products` section yet (graceful-degradation path). |
| `core_product` | string \| null | The Core product a gated finding ties to (e.g. `"Akur8 Pricing"`). Null for non-gated sections or `claim_scope: unscoped`. |
| `action` | enum | `replace` \| `append`. At `max_items`, the comparator may emit `replace` with `current_text` set to the weakest existing bullet it proposes to evict; reviewer approves or rejects. |
| `evidence_basis` | enum | `structural` \| `single-deployment` \| `corroborated-multi`. Added 2026-04 tightening pass. Single-deployment findings targeting high-authority sections (Snapshot / Strengths / Weaknesses / hx positioning) are demoted to Notes by Gate H unless the comparator can upgrade them with a second corroborating source. |
| `closes_open_question` | string \| null | When a `replace` action resolves an existing `## Notes / open questions` bullet, holds the exact canon bullet text being closed. Null for every other finding. Surfaces in Notion so reviewers know rejecting the finding leaves canon with a known-stale open question. |
| `current_text` | string | **Human-readable preview only**, ≤400 chars. NOT the authoritative needle — integrate time uses `target_line_start/end`. Empty for pure append actions. |
| `proposed_text` | string | Paraphrased replacement. **No verbatim quotes** ≥5 words from source when raw file is `confidentiality: internal-only`. **No metadata** — no dates, finding IDs, source URLs, or provenance stamps. See paraphrase contract below. |
| `rationale` | string | 1–3 sentences on why this finding is real. Verbatim quotes and named attribution are allowed here (displayed in Notion for reviewer context, never written to canon). |
| `suggested_action` | string | One-line remediation step. |
| `source_file` | string | Upload's filename. No `raw/` prefix — the file is not persisted. |
| `source_line` | int \| null | Line number in the raw file, or null. |
| `target_file` | string | Canon path (`context/...`) — the file that would be edited to resolve the finding. |
| `target_line_start` | int | 1-indexed first line of the replacement span in `target_file`. |
| `target_line_end` | int | 1-indexed last line of the replacement span (inclusive). Equal to `target_line_start` for a single-line replace. |
| `group` | enum | Group slug from `.claude/skills/kb-update/config.yaml`. |
| `codeowner` | string | Group codeowner from `.claude/skills/kb-update/config.yaml`. |
| `run_date` | date | `YYYY-MM-DD` — the date the kb-update run happened. |

### Paraphrase contract (for `proposed_text`)

`proposed_text` is the only field the integrator writes into canon, so
its content rules are stricter than the other fields:

- **No metadata.** No dates, finding IDs, source URLs, provenance
  stamps, or `R{n}:` prefixes. Content only.
- **No verbatim customer quotes when `confidentiality: internal-only`.**
  The comparator refuses to emit any finding whose `proposed_text`
  contains ≥5 consecutive words copied verbatim from the source; such
  findings are dropped as `dropped_quote_verbatim: N` in stats.
  Named carrier references are replaced with tier descriptors
  (`"a named tier_1 carrier"`).
- **Full attribution belongs in `rationale`.** Raw quotes and named
  sources stay there — displayed in Notion for reviewer context,
  never applied to canon.
- **Style match.** Matches the surrounding canon's sentence length,
  register, and format (bullet vs. prose; bolded-lead rule for
  Strengths / Weaknesses). If the comparator cannot match the style,
  it leaves `proposed_text` empty and sets
  `suggested_action: "Human author needed — style match not possible"`.

### Action field — `replace` vs. `append`

- `append` (default) — add as a new bullet / line at the end of the
  target section. `current_text` empty.
- `replace` at cap — when a section is at `max_items` and a new
  finding passes all other gates, the comparator emits
  `action: replace` with `current_text` set to the weakest existing
  bullet it can identify (lowest-tier citation if present, else most
  niche). Reviewer approves or rejects the eviction in Notion. If the
  comparator cannot pick a confident eviction candidate, it demotes
  the new finding to Notes instead.
- `replace` for direct canon corrections (contradictions /
  supersessions) — `current_text` is the existing canon span being
  corrected.

---

## Finding → Notion column mapping

The publisher maps each finding field to the corresponding Notion column
on the target group's database. All 11 per-group databases share the
same schema. Look up the database ID for a group from
`groups.<slug>.notion_data_source_id` in
[../config.yaml](../config.yaml).

| Finding field | Notion column | Notion type | Notes |
|---------------|---------------|-------------|-------|
| `title` | `Name` | title | Row title — keeps the `R{n}:` prefix for triage UX. |
| — | `Status` | select | Publisher always sets `Pending Review` on new rows. Options (`Pending Review`, `Approved`, `Needs Restage`, `Rejected`, `Integrated`) are seeded via DDL at database creation time. |
| — | `Reviewer` | people | **Never set by publisher.** Left empty for a human to fill in via the Notion UI during triage. |
| `current_text` | `Current Text` | rich_text | Human-readable preview only (≤400 chars). Not used as the integrate-time needle. |
| `proposed_text` | `Proposed Updated Text` | rich_text | Empty rich_text array for pure append actions with no textual replacement. Uses the existing `_split_text` helper for values >2000 chars. |
| — | `Final Updated Text` | rich_text | **Never set by publisher.** Reviewers type partial-approval tweaks here in Notion; integrate time reads `effective_text = Final Updated Text or Proposed Updated Text`. |
| `rationale` | `Rationale` | rich_text | Split with `_split_text` if >2000 chars. |
| `entity` | `Entity` | select | Auto-populated from target canon filename stem. Visible in the triage view; no longer the grouping column. |
| `source_tier` | `Source Tier` | select | `Tier 1` \| `Tier 2` \| `Tier 3` \| `Tier 5` (title-cased). Tier 4 findings are dropped before publish. |
| `action` | `Action` | select | `Append` or `Replace` — how kb-integrate applies the edit. |
| `section` | `Section` | rich_text | Exact canon heading the finding will attach under (`Weaknesses / watch-outs`, `Where they show up`, `Notes / open questions`, etc.). RICH_TEXT because valid section set varies per group's canon template. |
| `closes_open_question` | `Closes Open Question` | rich_text | Populated only on `replace` findings that resolve an existing Notes bullet. Blank otherwise. |
| `source_file` | `Source file` | rich_text | Upload filename only — no `raw/` path prefix. |
| `target_file` | `Target file` | rich_text | Canon path only. Hidden from the triage table but still consumed by kb-integrate when applying approved rows. |
| — | `Review Bucket` | formula | **Never set by publisher.** Formula derived from Status: `Pending Review` + `Needs Restage` → `Needs Decision`; others pass through. Drives `group_by` in the default view; hidden from the row table because Notion renders it as the group header. |
| `category` | `Category` | select | Always `raw-canon-conflict` in kb-update. Hidden. |
| `severity` | `Severity` | select | `High` \| `Medium` \| `Low` (title-cased). Hidden. |
| `run_date` | `Date Added` | date | `YYYY-MM-DD`. Hidden. |
| `source_line` | `Source Line` | number | Integer or unset. Hidden. |
| `target_line_start` | `Target Line Start` | number | 1-indexed first line of the replacement span. Authoritative needle for integrate-time replace. Hidden. |
| `target_line_end` | `Target Line End` | number | 1-indexed last line (inclusive). Equals `Target Line Start` for a single-line replace. Hidden. |

**Dropped columns (2026-04 cleanup):**

- **Group / Codeowner** — each database represents one group; both
  values are constant per DB. Kept on the in-memory finding and
  rendered in the detail-page body.
- **Canon Heading** — redundant with `Section`; findings must slot
  into existing `section_schema` headings rather than spawning new
  sections.
- **Evidence Basis** — comparator still computes `evidence_basis`
  for Gate H demotion and Pass A dedup, but the column was dropped
  from Notion because reviewers didn't use it.
- **Core Product** — comparator still runs the scope gate
  (`claim_scope: structural / niche / unscoped`) and demotes
  niche findings to Notes, but the column was dropped from Notion
  because `Section` already signals product relevance.
- **Target Content Hash** — drift guard was removed alongside the
  column; kb-integrate now writes unguarded at the recorded line
  range. Assumes canon isn't edited concurrently during triage.

**Default view** (the database's built-in default view — no separate
view is created; `setup_notion.py` emits `default_view_config` and the
pipeline applies it via one `notion-update-view` call):

- filter `Status IN (Pending Review, Needs Restage)`, grouped by
  `Review Bucket` (Needs Decision first), sorted `Date Added` desc.
  Visible columns (12, in display order): Name, Status, Reviewer,
  Current Text, Proposed Updated Text, Final Updated Text, Rationale,
  Entity, Source Tier, Section, Closes Open Question, Source
  file. Target file, Action, and Review Bucket are hidden.

## Fresh-database DDL (for adding a new group or repairing)

When onboarding a new group, create a new Notion database under the
"KB - Updates Review" landing page with this schema, then copy
the new data source ID into `groups.<slug>.notion_data_source_id` in
`config.yaml`:

```sql
CREATE TABLE (
  -- Visible by default (12, in display order)
  "Name" TITLE,
  "Status" SELECT('Pending Review':gray, 'Approved':blue, 'Needs Restage':orange, 'Rejected':red, 'Integrated':green),
  "Reviewer" PEOPLE,
  "Current Text" RICH_TEXT,
  "Proposed Updated Text" RICH_TEXT,
  "Final Updated Text" RICH_TEXT,
  "Rationale" RICH_TEXT,
  "Entity" SELECT(),
  "Source Tier" SELECT('Tier 1':blue, 'Tier 2':purple, 'Tier 3':yellow, 'Tier 4':gray, 'Tier 5':red),
  "Section" RICH_TEXT,
  "Closes Open Question" RICH_TEXT,
  "Source file" RICH_TEXT,
  -- Hidden by default (9)
  "Target file" RICH_TEXT,
  "Action" SELECT('Append':green, 'Replace':orange),
  "Review Bucket" FORMULA(if(prop("Status") == "Pending Review" or prop("Status") == "Needs Restage", "Needs Decision", prop("Status"))),
  "Category" SELECT('raw-canon-conflict':red, 'freshness':yellow, 'cross-reference':blue, 'consistency':orange, 'template':purple, 'coverage-gap':gray),
  "Severity" SELECT('High':red, 'Medium':yellow, 'Low':gray),
  "Date Added" DATE,
  "Source Line" NUMBER,
  "Target Line Start" NUMBER,
  "Target Line End" NUMBER
)
```

`Entity` is a SELECT whose options are created on demand at write
time — one per distinct canon filename stem. It seeds with no
options; reactive repair at publish time unions run values with live
options (see [publish.md §1](publish.md)).

No manual Notion UI setup is required — Status is a SELECT with
DDL-seeded options, and the publisher always writes `Pending Review` on
new rows. `scripts/setup_notion.py` emits this DDL for every missing
group and Claude executes it via the `notion-create-database` MCP tool.

**Reviewer invariant:** `publish_to_notion.py` MUST NEVER emit a value for
the `Reviewer` column. The column exists so a human reviewer can tag
themselves in the Notion UI when they accept/reject the row. If the
publisher writes to it, it defeats the point of the column.

**Final Updated Text invariant:** `publish_to_notion.py` MUST NEVER
emit a value for the `Final Updated Text` column. The column is for
reviewers to type partial-approval tweaks in the Notion UI;
integrate time reads
`effective_text = Final Updated Text or Proposed Updated Text`. If
the publisher writes to it, reviewer edits will be silently
overwritten on a republish.

**Status invariant:** `publish_to_notion.py` always writes
`Status = Pending Review` on newly-created rows and never updates the
column on existing rows. `publish_to_notion.py` only creates rows; it
has no update path, so this invariant is structurally enforced. Humans
transition the row through Approved / Rejected / Integrated during
triage in the Notion UI; `Needs Restage` is set by `kb-integrate` when
canon has drifted since publish and the line+hash check fails.

Status is a SELECT column (not Notion's built-in STATUS type). SELECT
options are configurable via DDL, so `setup_notion.py` seeds the four
options at database creation time — no manual Notion UI setup is needed
for a fresh provision.

---

## Detail-page body template

Every published row has a markdown body rendered to Notion blocks. The
body is richer than the flat column values — reviewers read it when
triaging. Template:

```markdown
**Finding ID:** <finding_id> · **Severity:** <severity> · **Source Tier:** <source_tier>
**Entity:** <entity> · **Section:** <section> · **Action:** <action>
**Group:** <group> · **Codeowner:** <codeowner> · **Run date:** <run_date>

---

## Landing preview

_<target_file> lines <target_line_start>–<target_line_end>_

```
<±5 lines of canon around the replacement span, replacement span bolded>
```

**Proposed replacement:**

```
<proposed_text>
```

_Edit the `Final Updated Text` column above to tweak before approval._

---

## Current text (preview)

> <current_text verbatim as blockquote, or "_(no current text — append action)_">

_Source: `<source_file>` line <source_line>_

## Rationale

<rationale prose — may include verbatim quotes and named attribution>

## Suggested action

<suggested_action text>

---

## Triage checklist

- [ ] Verify current_text matches source at cited line
- [ ] Review proposed_text for accuracy and style fit
- [ ] Tweak via the `Final Updated Text` column if partial approval
- [ ] Apply change to target_file or reject
- [ ] Update Status column when done

## Provenance

- **Source file:** `<source_file>`<optional line suffix>
- **Target file:** `<target_file>` lines <target_line_start>–<target_line_end>
- **Category:** <category>
- **Generated by:** kb-update
```

The Landing preview section turns the Notion row into the reviewer's
default surface — no canon round-trip needed during triage. See
IMPROVEMENTS.md RC 8b.

---

## Severity classification rules

kb-update only produces `raw-canon-conflict` findings, all with severity
`high` by default. The comparator may downgrade to `medium` or `low` for
weak-evidence cases, but structural findings (freshness, cross-ref,
template) do not apply here — those are kb-lint's domain.

Severity is **orthogonal** to `source_tier`: severity answers "how
load-bearing is this claim in canon?", tier answers "how trustworthy
is the evidence behind it?". The tier rubric (see
[raw-canon-comparator.md](raw-canon-comparator.md)) gates section
eligibility; severity only colors the Notion row.

| Severity | Criteria |
|----------|----------|
| **High** | Raw source directly contradicts canonical content, OR supersedes it with newer primary-source data. Default for kb-update findings. |
| **Medium** | Weaker evidence (secondhand source, partial overlap, minor correction). |
| **Low** | Net-new information from an informal source, or a comparison the reviewer should confirm against a more authoritative reference first. |

## Finding ID conventions

Each finding is assigned an ID with the `R` prefix (raw-canon-conflict),
numbered sequentially from `R1` within a single run.

The `R{n}:` prefix appears in `title` (for Notion row scanability)
but never in `proposed_text` — it is prohibited as metadata.

After cross-file dedup (Step 5d), finding IDs are renumbered
sequentially so gaps from merged/dropped findings don't surface to the
reviewer.
