# kb-update

Review raw source(s) — one or many — against a group's canonical KB
slice, and stage any raw-vs-canon conflicts as rows in the group's
Notion database for team triage. kb-update unions every available input
surface on each run: chat attachments, an HTTP(S) URL argument,
inline-pasted markdown, and unprocessed `.md` files in `raw/<slug>/`.
With ≥2 inputs it auto-switches to batch mode (parallel waves of 3
concurrent files, cross-file pairing, one publish). kb-update is the
write-path-to-Notion counterpart to [kb-lint](../kb-lint/README.md) —
kb-lint does read-only audits with markdown output, kb-update publishes
triage rows when you have specific new sources to feed into canon.

## When to use it

You use kb-update when:

- You just received a new raw source (press release, article, analyst
  brief, meeting notes, Notion clipping) and want a structured diff
  against canon.
- You want the findings staged in a Notion database so the team can
  triage them asynchronously, instead of sitting in a local markdown
  report.
- You've dropped one or more files into `raw/<slug>/` and want them
  checked against canon + published to Notion in one go (kb-update
  picks up everything with `Process? = yes` and blank `Last processed`
  in `INDEX.md`).

You use kb-lint (not kb-update) when:

- You want a periodic health snapshot of a group (freshness,
  contradictions, cross-refs, templates, coverage gaps).
- You want the report as a markdown file in `outputs/`, not as Notion
  rows.

## Requirements

| Requirement | Purpose | Required? |
|---|---|---|
| **Claude Code desktop** | Drives kb-update via file-attachment in the chat. The CLI can't attach files. | **Required** |
| **Claude Opus (1M context)** model for the orchestrator | Holds the group's canon fan-out + merged findings without mid-run context pressure | **Required** for orchestrator; parallel comparator subagents run on Sonnet by default (see `global.comparator_model` in [config.yaml](config.yaml)) |
| **Notion MCP connector** enabled in Claude | Discovering the landing page + publishing findings | **Required** |
| **Canon access**: either the `hxgtm-context` MCP server configured OR the `hxgtm-mcp-server` repo cloned at `../hxgtm-mcp-server/` | Reading the canonical GTM KB | **Required** — auto-detected at pre-flight |
| **Python 3** on PATH | Runs `setup_notion.py` and `publish_to_notion.py` (stdlib only — no `pip install` needed) | **Required** |

**Minimal Notion setup.** You create **one** landing page manually in
Notion (at your chosen teamspace / parent — kb-update can't pick that
for you), then kb-update provisions all 11 per-group databases
underneath it on first `--notion-setup` run. See
[Notion database setup](#notion-database-setup).

## Quick start

```
# One-time manual step — create a page in Notion titled exactly:
#     KB - Updates Review
# at the teamspace / parent of your choice (where your team can see it).
# The MCP cannot do this for you; see Notion database setup below.

# One-time — provision the 11 per-group databases under that landing page
/kb-update --notion-setup

# Run kb-update — any combination of inputs is unioned into one run:
/kb-update --group competitive                             # Uses chat attachments + raw/competitive/ eligible files
/kb-update --group competitive https://example.com/post    # URL + whatever else is present
/kb-update --group competitive --batch path/to/batch-dir   # Explicit batch path (overrides auto-detection)

# Inline paste: put markdown on the line(s) after the command in the same message

# Omit --group to be prompted for a group
/kb-update                                  # AskUserQuestion picks a group

# List available groups
/kb-update --list-groups

# Force-run against an inactive group
/kb-update --group messaging --force

# Provision just one group (skip the other 10)
/kb-update --notion-setup --group competitive

# Provision all groups (non-interactive, bulk mode)
/kb-update --notion-setup --group all
```

`--notion-setup` is scoped — it only creates databases that don't
already exist within the scope you pass:

- `--notion-setup` (no slug) — prompts you to pick a group or `All
  groups`.
- `--notion-setup --group <slug>` — provisions only that group's DB,
  leaves the other 10 alone. Use this when adding a newly-configured
  group.
- `--notion-setup --group all` — bulk reconcile, equivalent to the
  "all" prompt option.

Running it a second time after everything is provisioned is a
no-op.

### Upgrading to the cleaned schema (2026-04)

The 2026-04 cleanup removed 4 columns (`Canon Heading`, `Core
Product`, `Evidence Basis`, `Target Content Hash`) and renamed
`Edited Text` → `Final Updated Text`. Notion doesn't support column
rename or drop via DDL, so existing DBs can't be migrated in place
— you must recreate them.

1. In Notion, trash all 11 `KB - <Group>` databases under the
   `KB - Updates Review` landing page. (Any `Pending Review` rows
   not yet triaged are lost — finish triage on the old DBs first if
   needed.) Keep the landing page.
2. Blank every `notion_data_source_id` in
   [config.yaml](config.yaml) (or delete `.kb-local.json`).
3. Run `/kb-update --notion-setup`. It rediscovers the landing
   page, creates fresh DBs with the new 21-column schema, and
   writes the new UUIDs back to config.

### Retro-fit existing DBs to the new triage view (2026-04 follow-up)

A later pass added a `Review Bucket` formula column, reordered the
visible columns, hid `Target file`, and flipped `group_by` from
`Entity` → `Review Bucket`. Existing DBs can be migrated in place
(no row loss) via:

```bash
python3 .claude/skills/kb-update/scripts/setup_notion.py --migrate-views
```

Claude reads the emitted plan and calls `notion-update-data-source`
(`ALTER TABLE ADD COLUMN "Review Bucket"`) then `notion-update-view`
on each DB. The ALTER is guarded by a live-schema fetch so re-runs
are safe.

## Input surfaces

On every run kb-update enumerates **all four input surfaces** and
unions them into one batch. Surfaces are not mutually exclusive — a
URL + two attachments + three eligible files in `raw/<slug>/` all
flow through the same pipeline in one invocation, with one Notion
publish.

| # | Surface | How to use | Persisted? |
|---|---------|------------|------------|
| 1 | **Chat attachments** | Drag `.md`, `.pdf`, or `.docx` files into the Claude Code desktop chat before running the command (N ≥ 0). PDF/DOCX are auto-converted to markdown via `scripts/convert_to_markdown.py`. Other binary types (images, archives) halt the run. | No — ephemeral |
| 2 | **URL argument** | Pass an HTTP(S) URL on the command line. Fetched via `WebFetch` (plain URLs) or Glean `read_document` (`teams.microsoft.com` URLs). | No — materialised to `/tmp/kb-update-raw/<run-id>/` |
| 3 | **Inline paste** | Paste markdown on the line(s) after the command in the same message. kb-update prompts once for optional `source_title` / `source_url` / `source_type`. | No — materialised to tempfile |
| 4 | **Raw directory** | Drop `.md` / `.pdf` / `.docx` files under `raw/<slug>/` and add a row to `raw/<slug>/INDEX.md` with `Process? = yes` and blank `Last processed`. kb-update also picks up files physically present under `raw/<slug>/` that are missing from INDEX.md (with a warning). PDF/DOCX rows produce a sidecar `.md` next to the source on first run (e.g. `foo.pdf` → `foo.pdf.md`). | Yes — lives on disk; kb-update mutates only the INDEX.md `Last processed` cell after a successful publish |

**How PDF / DOCX conversion works.** `scripts/convert_to_markdown.py`
runs before the union is finalised. PDFs go through `pymupdf`; DOCX
goes through Pandoc (preferred, if on `PATH`) or `mammoth`. Install
the Python fallbacks with `pip install pymupdf mammoth` if you don't
have Pandoc. Conversion failures (oversize >25 MB, scanned/image PDFs
without an OCR layer, or missing libs) halt the run with the
converter's stderr surfaced — there is no silent skip.

For raw-dir sources, the sidecar `.md` is committed to git so
reviewers can read what kb-update actually compared against.
**Don't hand-edit the sidecar — it's regenerated on every run.**
INDEX.md stamping always targets the original source filename
(`foo.pdf`), not the sidecar.

**Cardinality switch.** If the union resolves to exactly 1 file →
single-source mode. If ≥2 → batch mode with parallel waves of 3
concurrent files (`global.batch_wave_size` in `config.yaml`),
cross-file pairing at synthesis, and one publish at the end.

**INDEX.md writeback.** After a successful publish, kb-update stamps
`Last processed = <today>` into `raw/<slug>/INDEX.md` for every
raw-dir file that contributed. Raw file **bodies** are never edited.
URL / attachment / inline inputs are not tracked in INDEX.md — if you
want one of those tracked, save it to `raw/<slug>/` and add an
INDEX.md row yourself, outside this skill.

### Workflow

1. **Provide input.** Any combination of the four surfaces above.
2. **Run `/kb-update --group <slug>`.** The skill logs the union
   summary (`[inputs] group=<slug> url=<n> attachments=<N>
   inline=<n> raw_eligible=<K>/<K_total> ...`), diffs each input
   against the group's in-scope canon, and publishes findings.
3. **Triage in Notion.** Filter the group's database by
   `Date Added = today` to see the new findings, and walk the
   Pending Review → Approved → Rejected → Integrated lifecycle.

Use `--batch <path>` to override auto-detection and run batch mode
against an explicit directory only.

## Group scoping

kb-update requires an explicit `--group <slug>` (or asks for one if
omitted). Each group maps to a slice of the canonical KB, defined in
[config.yaml](config.yaml) (whose `canon` globs must stay in sync with
[.claude/skills/kb-lint/config.yaml](../kb-lint/config.yaml)). The `raw:`
staging paths are owned by kb-update alone — kb-lint no longer scans
`raw/`, so they live only in this skill's config.

| Slug | Label | Codeowner | Active |
|---|---|---|---|
| `competitive` | Competitive Intelligence | competitive-intelligence | yes |
| `messaging` | Product & Segment Messaging | product-segment-messaging | yes |
| `audiences` | Audiences & Personas | audiences-personas | yes |
| `company-policies` | Company Policies & Platform Commitments | company-policies-platform-commitments | yes |
| `company-overview` | Company Overview & Narrative | company-overview-narrative | yes |
| `marketing-strategy` | Marketing Strategy | marketing-strategy | yes |
| `brand-voice` | Brand, Voice & Positioning | brand-voice-positioning | yes |
| `channel-playbooks` | Channel Playbooks | channel-playbooks | yes |
| `sales-methodology` | Sales Methodology | sales-methodology | yes |
| `accounts` | Account & Opp-level Context | account-opp-context | yes |
| `rfp` | RFP Responses | rfp-responses | yes |

All 11 groups are active — kb-update runs directly against any of them
via `/kb-update --group <slug>`.

### Competitive group — canon fan-out

For a single competitor raw (e.g. `federato-research.md`) the
competitive group compares against **four canon files**, not just the
per-competitor profile:

1. `guidance/competitive/competitors/federato.md` — the per-competitor
   profile (narrowed from the raw filename stem).
2. `guidance/competitive/README.md` — top-level competitive guidance.
3. `guidance/competitive/positioning.md` — hx positioning vs the
   competitive set.
4. `truth/market/competitors.md` — the full competitor catalog.

Files 2–4 are the group's **foundational canon**
(`foundational_canon` in [config.yaml](config.yaml)) — attached to
every run so raw sources can surface drift at the group-wide level,
not just on the individual competitor profile.

Foundational files follow a stricter routing policy than per-competitor
profiles:

- **Updates preferred.** Findings that contradict, refine, or correct
  existing foundational text are the high-value case.
- **Additions are the exception.** A net-new bullet to a foundational
  file only passes when the claim is genuinely group-wide and
  critical (category-shifting, Tier 1 disclosure, changes hx's stance
  across multiple competitors). Per-competitor tactical detail goes
  to the profile, not here.
- **Drop, don't demote.** A finding whose natural home is a
  foundational file but that fails both bars above is dropped — not
  redirected into the per-entity profile — to keep the profile lean.

See [references/comparators/competitive.md](references/comparators/competitive.md)
§ Foundational-file routing policy for the full ruleset and
[references/group-behaviors.md](references/group-behaviors.md) for
the worked example.

---

## Notion database setup

kb-update publishes each finding as a row in a Notion database. There is
**one database per group** (11 total) nested under a single landing page
called **"KB - Updates Review"**. Each group's database is
independent — you can customize views, filters, and assignee rotations
per group without affecting the others.

**Zero manual setup after the landing page.** kb-update provisions the
full Notion structure on first run via
[scripts/setup_notion.py](scripts/setup_notion.py). All column options
(including the Status lifecycle) are seeded by DDL at database creation
time — there is nothing to configure in the Notion UI after the
landing page exists.

### Architecture

```
📚 KB - Updates Review                  (landing page — users' entry point)
├── KB - Competitive Intelligence                     (competitive-intelligence)
├── KB - Product & Segment Messaging                  (product-segment-messaging)
├── KB - Audiences & Personas                         (audiences-personas)
├── KB - Company Policies & Platform Commitments      (company-policies-platform-commitments)
├── KB - Company Overview & Narrative                 (company-overview-narrative)
├── KB - Marketing Strategy                           (marketing-strategy)
├── KB - Brand, Voice & Positioning                   (brand-voice-positioning)
├── KB - Channel Playbooks                            (channel-playbooks)
├── KB - Sales Methodology                            (sales-methodology)
├── KB - Account & Opp-level Context                  (account-opp-context)
└── KB - RFP Responses                                (rfp-responses)
```

Each database shares the same schema. The column list is the single
source of truth in
[references/output-format.md](references/output-format.md) (see
"Finding → Notion column mapping" and "Fresh-database DDL"); the same
DDL is emitted at provisioning time by
[scripts/setup_notion.py](scripts/setup_notion.py).

High-level groupings reviewers see in the single default `Triage`
view (21 columns total — 12 visible, 9 hidden). The view is grouped
by `Review Bucket` (a formula derived from `Status`) so `Pending
Review` + `Needs Restage` stack under a single **Needs Decision**
header, with `Approved` / `Rejected` / `Integrated` visible when the
filter is widened:

- **Visible by default** (in display order): `Name`, `Status`,
  `Reviewer`, `Current Text`, `Proposed Updated Text`,
  `Final Updated Text`, `Rationale`, `Entity`, `Source Tier`,
  `Section`, `Closes Open Question`, `Source file`.
- **Hidden by default** (one click on the row opens the detail
  panel): `Target file`, `Action`, `Review Bucket`, `Category`,
  `Severity`, `Date Added`, `Source Line`, `Target Line Start`,
  `Target Line End`. `Target file` is still consumed by
  kb-integrate when applying approved rows; `Action` is machine-
  written by the publisher and consumed by kb-integrate at apply
  time — reviewers rarely need it during triage, so it's off the
  table; `Review Bucket` is the group_by column, so Notion renders
  it as the group header and the column stays hidden from the
  table to avoid duplication.
- **Never written by publisher:** `Reviewer` (humans tag themselves
  during triage), `Final Updated Text` (reviewers type
  partial-approval tweaks in Notion — integrate time reads
  `effective_text = Final Updated Text or Proposed Updated Text`),
  and `Review Bucket` (formula derived from Status at read time).

`Status` is written once at row creation (`Pending Review`) and then
owned by humans for the rest of its lifecycle
(`Approved` → `Needs Restage` → `Rejected` → `Integrated`).

### First-time setup

First-time setup is a **two-step** process:

1. **You create the landing page in Notion manually.** kb-update will
   not do this for you — see "Why the landing page is manual" below.
2. **Run `/kb-update --notion-setup`.** It discovers your landing page
   and provisions the 11 per-group databases underneath it.

#### Step 1 — Create the landing page manually

In Notion, create a new page titled exactly:

```
KB - Updates Review
```

Place it at the location you want kb-update's findings to live — a
teamspace visible to your team, a department root page, or wherever
fits your workspace's layout. The page body can be empty or you can
paste in the template copy shown by
`python3 .claude/skills/kb-update/scripts/setup_notion.py --plan`
(field: `landing_page_template.body_markdown`).

**Why the landing page is manual.** The Notion MCP can only create
pages in the caller's **Private** workspace section (a quirk of the
API — there's no "create in teamspace X" option). If kb-update
auto-created the landing page, it would always land in your private
pages, and you'd have to move 12 objects (landing page + 11 child
databases) out of Private on every first-run setup. By making you
place the page once, in the right spot, you pick the location and
every subsequent `/kb-update --notion-setup` run rediscovers it via
`notion-search` regardless of where it lives.

#### Step 2 — `/kb-update --notion-setup`

```
/kb-update --notion-setup
```

**The setup is safe to run against any workspace state** — it always
checks Notion reality before creating anything, so it will never
produce duplicates. The flow:

1. Runs [scripts/setup_notion.py --status](scripts/setup_notion.py) to
   see which groups have a `notion_data_source_id` in
   [config.yaml](config.yaml) and which don't.
2. **Discovers the landing page.** Searches Notion for a page titled
   `KB - Updates Review`. If no live (non-trashed) match exists,
   **halts with a banner telling you to do Step 1 above**. The setup
   never creates the landing page itself.
3. **Discovers existing child databases.** Parses the landing page's
   fetched content for every child database (title + data source ID).
4. **Reconciles config.yaml with Notion reality.** Recovers UUIDs
   into config for databases that already exist (Case B), and blanks
   stale UUIDs in config that point at deleted Notion objects
   (Case C). The idempotency guarantee: wiping config never
   duplicates Notion state.
5. **Creates only what's genuinely missing.** Calls
   `notion-create-database` for each group whose database isn't
   already under the landing page, passing the 21-column schema DDL
   (12 visible + 9 hidden; Status SELECT pre-seeded with its five
   options).
6. **Writes back and verifies.** Every newly-created UUID goes into
   config.yaml, then `--status` is re-run as a post-condition check.
7. **Prints a summary** listing recovered vs created databases and
   which IDs landed in config.yaml.

After this runs once, **normal kb-update runs don't touch the Notion
structure at all** — they just read `notion_data_source_id` from
config and publish. No auto-detection, no provisioning checks, no
per-run overhead.

You can also invoke the underlying script directly for dry-runs
(without Claude / MCP):

```bash
# Check what's missing
python3 .claude/skills/kb-update/scripts/setup_notion.py --status

# Dry-run the provisioning plan (JSON, no Notion API calls)
python3 .claude/skills/kb-update/scripts/setup_notion.py --plan

# Dry-run when a landing page already exists
python3 .claude/skills/kb-update/scripts/setup_notion.py --plan --landing-page-id <uuid>
```

The Python script is pure plan-generation — it never calls Notion
directly. Actual Notion writes only happen when you run `/kb-update
--notion-setup` and Claude executes the plan via the Notion MCP.

### Data source resolution for `publish_to_notion.py`

1. `--parent-data-source <uuid>` CLI override (explicit one-off)
2. `KB_UPDATE_NOTION_DS_<GROUP_UPPER>` env var (e.g.
   `KB_UPDATE_NOTION_DS_COMPETITIVE`) — useful for pointing a local run
   at a different workspace (e.g. prod vs test)
3. `groups.<group>.notion_data_source_id` in `config.yaml` (default,
   populated by auto-setup)

### Triage workflow

1. Open the `KB - Updates Review` landing page, click your group's database
2. Filter by `Date Added = today` to see the latest upload's findings
3. For each row, decide:
   - **Approved** — apply the Proposed Updated Text to the Target file
     in canon, set Status to `Integrated`, tag yourself in Reviewer
   - **Rejected** — set Status to `Rejected`, comment with the reason
   - **Defer** — leave Status as `Pending Review` until you're ready
     to revisit

---

## File structure

```
.claude/skills/kb-update/
├── SKILL.md                    ← Main orchestrator
├── README.md                   ← This file
├── config.yaml                 ← Group definitions + notion_data_source_id
├── references/
│   ├── raw-canon-comparator.md ← Subagent spec (single-file variant)
│   └── output-format.md        ← Finding JSON schema + Notion column mapping + DDL
└── scripts/
    ├── setup_notion.py         ← Provisioner (plan generator, no auth)
    └── publish_to_notion.py    ← Finding → notion-create-pages transformer
```
