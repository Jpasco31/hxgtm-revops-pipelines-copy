# Output format — dossier-feedback per-account files

dossier-feedback writes **two files per account** on every run, atomically
together. Both are **always regenerated from scratch** — phase 1 has no
merge logic, no archive, and no preservation of hand edits. History lives
in git.

## Paths

```
dossier-feedback/
  comment-logs/
    <slug>.md          # full audit trail; humans only
  known-truths/
    <slug>.md          # section-grouped one-line truths; LLM consumer
  _routine-state.json
  _routine-summary.md
  _routine-errors.md
```

`<slug>` is the same kebab-case slug `generate-dossier-batch-parallel`
emits (e.g. `Zurich North America` → `zurich-north-america`). The two
files for a given account share the same basename, so cross-referencing
between them is trivial.

## Why two files

| File | Purpose | Audience |
|---|---|---|
| `comment-logs/<slug>.md` | Full audit trail: original passage, reviewer comment, interpreted truth, author, date, resolved state, discussion id. | Humans reviewing what the team has said. |
| `known-truths/<slug>.md` | Tight digest of synthesised one-line truths, grouped by dossier section. | The Phase-2 generate-dossier consumer (and humans who want the punch line without the comment context). |

The synthesised `interpreted_truth` line appears in **both** files. The
redundancy is intentional: the comment log stays self-contained for human
audit, while the truths summary stays signal-dense for the LLM consumer.
Both files are written from the same in-memory entry list in the same run,
so they cannot drift.

## Comment-log shape — `comment-logs/<slug>.md`

```markdown
---
account: "<Account Name>"
slug: <slug>
source_dossier_url: <notion url>
generated_at: <ISO timestamp, UTC, "Z" suffix>
entry_count: <int>
---

# Known Truths — <Account Name>

> Full reviewer-comment log derived from human comments on the latest Account Dossier in Notion.
> Companion to `../known-truths/<slug>.md` (consumer summary). Phase 1: regenerated from scratch on every run; do not hand-edit.

## Entries

### <short title>
- **Section:** <section_tag>
- **Original passage:** <anchor_text or "(page-level comment, no anchor)">
- **Reviewer comment:** <comment_text verbatim>
- **Interpreted truth:** <one-line synthesis>
- **Author / date:** <author> · <ISO date>
- **Resolved:** <true|false>
- **Discussion ID:** <discussion_id>

### <next title>
- **Section:** ...
...
```

## Truths-summary shape — `known-truths/<slug>.md`

Section-grouped flat bullets. Empty sections (no entries with that tag)
are omitted.

```markdown
---
account: "<Account Name>"
slug: <slug>
source_dossier_url: <notion url>
generated_at: <ISO timestamp, UTC, "Z" suffix>
entry_count: <int>
---

# Known Truths — <Account Name>

> Synthesised one-line truths from human comments on the latest Account Dossier in Notion.
> See `../comment-logs/<slug>.md` for the source comments and full provenance.
> Phase 1: regenerated from scratch on every run; do not hand-edit.

## overview
- <interpreted-truth one-liner> _(see: <entry-title>)_

## power-players
- <interpreted-truth one-liner> _(see: <entry-title>)_
- <interpreted-truth one-liner> _(see: <entry-title>)_

## past-opps
- <interpreted-truth one-liner> _(see: <entry-title>)_

## why-anything
- <interpreted-truth one-liner> _(see: <entry-title>)_
```

Section emit order matches the dossier's section IDs:
`overview` → `vision-mission` → `power-players` → `past-opps` →
`sentiment` → `discovery` → `why-anything` → `untagged`. The
`_(see: <entry-title>)_` suffix is the back-reference into
`comment-logs/<slug>.md` (entry titles match between the two files).

## Field definitions (comment log)

| Field | Source | Notes |
|---|---|---|
| `account` (frontmatter) | display name | Quoted; preserves spaces and punctuation. |
| `slug` (frontmatter) | derived | Bare token, no quotes. |
| `source_dossier_url` (frontmatter) | Notion page URL | Bare URL, no quotes. |
| `generated_at` (frontmatter) | UTC now | ISO 8601 with `Z` suffix, e.g. `2026-04-29T06:00:00Z`. |
| `entry_count` (frontmatter) | derived | Integer; equals the number of `### <title>` headings. Drives the "Entries: N" line in the orchestrator's report. The truths-summary file shares the same value. |
| short title | LLM synthesis | 4–8 words, no markdown, no quotes. Should describe the correction or addition, not paraphrase the comment. Used as the back-reference in the truths summary, so titles must be unique-enough within an account run. |
| `Section` | section_tag enum | One of `overview`, `vision-mission`, `power-players`, `past-opps`, `sentiment`, `discovery`, `why-anything`, `untagged` (8 values). |
| `Original passage` | `anchor_text` | Verbatim rendered text of the dossier block the comment was anchored to. If the comment is page-level OR anchor recovery failed, write the literal `(page-level comment, no anchor)`. |
| `Reviewer comment` | `comment_text` | Verbatim. Newlines collapsed to spaces. No reinterpretation. |
| `Interpreted truth` | LLM synthesis | One line. The neutral, declarative claim a future dossier run should treat as ground truth. Must NOT be a question, a meta-comment, or a quote of the reviewer. The same string is used (verbatim) as the bullet in the truths-summary file. |
| `Author / date` | comment author + `created_time` | `<author> · <YYYY-MM-DD>`. Time component dropped in the rendered file. |
| `Resolved` | comment thread state | Literal `true` or `false`. |
| `Discussion ID` | Notion `discussion_id` | Bare token. Lets a phase-2 consumer dedupe across runs. |

## Section-tag heuristics

The subagent maps each comment to a section tag using the following rules,
applied in order. First match wins:

1. The comment's `parent_block_id` resolves to a block whose nearest
   preceding `heading_2` matches one of the dossier's section names →
   tag from that mapping:
   - `Account Overview` → `overview`
   - `Vision, Mission & Potential Sales Plays` (or any `Vision, Mission &
     Strategic Priorities` legacy variant) → `vision-mission`
   - `Potential Champions and Influencers` (or `Who's Who — Top 20 Power
     Players` legacy variant) → `power-players`
   - `Past Opportunities & Interactions` → `past-opps`
   - `What People Are Saying on Topics We Care About` (or `What People
     Are Saying`) → `sentiment`
   - `Discovery Questions You Might Consider Asking` (or `Discovery
     Questions`) → `discovery`
2. If the heading lookup fails OR the comment is page-level, infer from
   the synthesised `interpreted_truth` content:
   - mentions an executive name, title, or org chart → `power-players`
   - mentions a Salesforce stage, Gong call, or opportunity history →
     `past-opps`
   - mentions strategic pillars, M&A, transformation, vision, mission →
     `vision-mission`
   - mentions sentiment, public commentary, press, analyst takes →
     `sentiment`
   - mentions a discovery question or recommends one → `discovery`
   - is a metadata correction (HQ, employee count, ticker) → `overview`
3. Otherwise → `untagged`.

**`why-anything` is in the enum but has no deterministic classifier rule
in phase 1.** It maps to the dossier's conditional Section 7 (a
cost-of-inaction table; only generated when the highest open opportunity
is at Stage 3 or later). Use it when the comment clearly relates to
Section 7 or to a "why now / why change / cost of inaction" framing. When
in doubt, prefer `untagged` over `why-anything`. Phase 2 (generate-dossier
consumer wiring) will revisit and add deterministic anchor-text /
keyword rules calibrated against real reviewer comments.

The orchestrator does NOT validate the tag distribution. The eight-tag
enum is fixed; future tags require a phase-2 schema bump.

## Edge cases

- **No anchor block (page-level comment)** — `Original passage:
  (page-level comment, no anchor)`. The subagent still produces a title
  and an interpreted truth from the comment alone.
- **Anchor recovery failed** (block deleted, fetch errored, etc.) —
  same literal: `(page-level comment, no anchor)`. Increment
  `anchor_failures` in the subagent's return summary so the orchestrator
  can surface the count.
- **Comment is just a reaction or "+1"** — still emit an entry, but the
  interpreted truth should reflect that the reviewer agreed with the
  passage; tag it `untagged` if no clearer category applies.
- **Multi-author thread on the same block** — emit one entry **per
  comment** (each `discussion_id` + author + `created_time` triple is
  unique). Threads disagreeing with each other are preserved verbatim;
  reconciliation is a phase-2 concern.
- **Empty comments / drafts** — skip. They have no `comment_text`.
- **Empty sections in the truths summary** — sections with zero entries
  are omitted entirely (no `## <tag>` heading, no placeholder line).
  Dossiers without a Section 7 simply produce no `## why-anything` group.
- **Zero entries overall** — both files are still written, with a
  `_No entries — this file is a placeholder._` body and `entry_count: 0`
  in the frontmatter.

## Examples

### Block-anchored, fact correction (comment log entry)

```markdown
### HQ moved to Schaumburg in 2023
- **Section:** overview
- **Original passage:** Headquartered in Zurich, Switzerland with US operations based in New York.
- **Reviewer comment:** Wrong — US HQ moved to Schaumburg IL in 2023, NY is sales only now.
- **Interpreted truth:** Zurich North America's US headquarters relocated to Schaumburg, IL in 2023; the New York office is now sales-only.
- **Author / date:** Sarah Chen · 2026-04-22
- **Resolved:** false
- **Discussion ID:** abc123-def456
```

The same entry in the truths summary (under the `## overview` group):

```markdown
- Zurich North America's US headquarters relocated to Schaumburg, IL in 2023; the New York office is now sales-only. _(see: HQ moved to Schaumburg in 2023)_
```

### Page-level, executive context (comment log entry)

```markdown
### Joanne Wong is the real economic buyer
- **Section:** power-players
- **Original passage:** (page-level comment, no anchor)
- **Reviewer comment:** This dossier missed Joanne Wong (Chief Underwriting Officer). She owns the platform spend, not the CIO.
- **Interpreted truth:** Joanne Wong (CUO) is the economic buyer for platform spend at this account, not the CIO listed in Section 3.
- **Author / date:** Marco Russo · 2026-04-23
- **Resolved:** false
- **Discussion ID:** xyz789-uvw012
```

The same entry in the truths summary (under the `## power-players` group):

```markdown
- Joanne Wong (CUO) is the economic buyer for platform spend at this account, not the CIO listed in Section 3. _(see: Joanne Wong is the real economic buyer)_
```
