---
name: kb-update
description: >
  Review raw source(s) — one or many — against a group's canonical KB
  slice and publish raw-vs-canon conflicts as rows in the group's
  Notion database for team triage. kb-update unions **every available
  input surface** on each run: `.md` / `.pdf` / `.docx` files attached
  to the chat, a URL argument (HTML or PDF), inline-pasted markdown,
  and unprocessed files staged in the group's raw directory
  (`raw/<slug>/` — e.g. `raw/competitive/`,
  resolved from `groups.<slug>.raw` in
  `.claude/skills/kb-update/config.yaml`). A raw-dir file counts as
  "unprocessed" when its `raw/<slug>/INDEX.md` row has `Process? =
  yes` AND a blank `Last processed` cell. If the union resolves to one
  file, single-source mode runs; two or more triggers batch mode —
  parallel waves (3 concurrent by default), each with its own
  parallel-per-file Sonnet comparators, cross-file pairing across the
  whole batch, and one publish to Notion. After a successful publish,
  kb-update stamps `Last processed = <today>` back into INDEX.md for
  every raw-dir file that contributed to the run, so the next
  invocation doesn't re-union them. Triggered by `/kb-update --group
  <slug>` (add `--batch <path>` only to override auto-detection).
  Findings flow through the Pending Review → Approved → Rejected →
  Integrated lifecycle directly in Notion. Use when the user says
  "review these sources against canon", "I uploaded raw source(s)",
  "check this upload", "stage for KB triage", or "publish raw-canon
  conflicts."
---

# Knowledge Base Update

## Usage

```
/kb-update --group <slug>                     (unions attachments + URL + inline + raw-dir)
/kb-update --group <slug> <https://url>       (URL added to the union)
/kb-update --group <slug> --batch <path>      (explicit batch path, overrides auto-detection)
/kb-update                                    (omit --group to be prompted)
/kb-update --notion-setup                     (prompt: pick one group or all)
/kb-update --notion-setup --group <slug>      (provision one group)
/kb-update --notion-setup --group all         (bulk, non-interactive)
/kb-update --list-groups                      (show available groups)
```

Arguments: $ARGUMENTS

kb-update unions **every available input surface** on each run:

- `.md` files attached to the current message (drag into the Claude
  Code desktop chat — attachments require the desktop app)
- An HTTP(S) URL passed on the command line (fetched via `WebFetch`,
  or Glean `read_document` for `teams.microsoft.com` URLs)
- Inline-pasted markdown typed after the command
- Unprocessed `.md` files in `raw/<slug>/` (rows with `Process? = yes`
  and blank `Last processed` in `INDEX.md`, plus any physically
  present `.md` file missing from INDEX.md)

If the union resolves to 1 file → single-source mode. ≥2 → batch mode
(parallel waves of 3 concurrent files, cross-file pairing, one
publish). After a successful publish kb-update stamps
`Last processed = <today>` into `raw/<slug>/INDEX.md` for every
raw-dir file that contributed. Raw file bodies are never edited;
URL / attachment / inline inputs are materialised to
`/tmp/kb-update-raw/<run-id>/` and not persisted.

Use `--force` to run against a group with `active: false`.

**First-time setup (two steps):**

1. In Notion, create a page titled exactly `KB - Updates Review`
   at the teamspace / parent page where you want kb-update's findings
   to live. The Notion MCP can't place it at a team-visible location
   for you — it only creates pages in your Private workspace — so you
   pick the spot once, manually.
2. Run `/kb-update --notion-setup` to provision the 11 per-group
   databases underneath it. Pass `--group <slug>` to provision just
   one group (useful when adding a new group to `config.yaml`), or
   `--group all` to provision every group non-interactively.

## What this skill does

Compares one or more raw source files against the in-scope canonical
KB for the target group, and publishes any raw-vs-canon conflicts as
rows in the group's Notion database for Pending Review → Approved →
Rejected → Integrated triage.

**Input union.** On every run kb-update enumerates all available
input surfaces — chat attachments (`.md`, `.pdf`, `.docx`), a URL
argument, inline-pasted markdown, and unprocessed source files
(`.md` / `.pdf` / `.docx`) in `raw/<slug>/` — and unions them into
a single input set. PDF and DOCX inputs are auto-converted to
markdown before the comparator pipeline runs (see
[references/input-routing.md](references/input-routing.md) for the
conversion contract). "Unprocessed" for raw-dir files means
`Process? = yes` AND `Last processed` is blank in
`raw/<slug>/INDEX.md`. Files missing from INDEX.md but physically
present under `raw/<slug>/` are treated as unprocessed (with a
warning) so a manual drop doesn't silently get skipped.

**Cardinality switch.** If the union has exactly 1 file →
single-source mode (parallel-per-entity comparators, one publish). If
≥2 → batch mode (waves of `global.batch_wave_size` concurrent files,
default **3**; each file fires its own parallel-per-entity subagents;
findings pair across the full batch in Step 5; one publish in Step 6).

**kb-update reads INDEX.md and stamps `Last processed` for raw-dir
files after a successful publish.** URL / attachment / inline inputs
are materialised to ephemeral tempfiles under
`/tmp/kb-update-raw/<run-id>/` so the batch pipeline can consume a
uniform set of file paths — these are NOT persisted under `raw/` and
are NOT tracked in INDEX.md. Raw file **bodies** are never edited;
only INDEX.md is written, and only the `Last processed` cell. If the
user wants an ad-hoc input (URL / attachment / inline) tracked for
future runs, they save it manually under `raw/<slug>/` and add an
INDEX.md row themselves, outside this skill.

## Requirements

- **Claude Opus (1M context)** for the orchestrator. Parallel
  comparator subagents run on Sonnet by default (via
  `config.yaml → global.comparator_model`).
- **Claude Code desktop** — file uploads. CLI cannot attach files, so
  `/kb-update` has no useful invocation outside the desktop app.
- **Canon access** — `hxgtm-context` MCP server OR direct filesystem
  access to `../hxgtm-mcp-server/context/`. Auto-detected at
  pre-flight.
- **Notion MCP connector** — for publishing findings and discovering
  the landing page.
- **Python 3** on PATH — for the helper scripts (stdlib only).
- **Glean MCP** (`read_document` + `search` tools) — optional. Required
  only when the input is a `teams.microsoft.com` URL. Without it, Teams
  URLs fall back to a prompt asking the user to paste content inline.

## Workflow at a glance

| Step | Purpose | Detail location |
|---|---|---|
| 0 | Model check | inline |
| 1 | Collect input | inline — union every surface (attachments + URL + inline + `raw/<slug>/`). Raw-dir filtering via `scripts/collect_inputs.py list-eligible`. URL/inline materialisation via `scripts/materialise_ephemeral_input.py`. Edge cases see [references/input-routing.md](references/input-routing.md) · `--notion-setup` see [references/notion-setup.md](references/notion-setup.md) |
| 2 | Pre-flight | inline (happy path: 2a / 2b / 2c only) · cache-miss auto-reconcile see [references/preflight.md](references/preflight.md) |
| 3 | Load inputs | inline (tier table) · narrowing + trimming see [references/load-inputs.md](references/load-inputs.md) · per-group knobs see [references/group-behaviors.md](references/group-behaviors.md) |
| 4 | Comparators | inline (per-entity fan-out) · subagent prompts under [references/comparators/](references/comparators/) — `<group_slug>.md` with fallback to `default.md` |
| 4.5 | Orchestrator dedup | inline — in-conversation AI dedup before synthesis |
| 5 | Synthesize | inline (invocation) · full contract see [references/synthesis.md](references/synthesis.md) and [references/output-format.md](references/output-format.md) |
| 6 | Publish | inline (happy path) · reactive repair (404 / missing SELECT / missing column) see [references/publish.md](references/publish.md) · Step 6a writes `Last processed` back to INDEX.md for raw-dir members |
| 7 | Report | inline (template) |

---

## Step 0 — Model check

Check the system context for the currently active model. The
recommended model is **Claude Opus 4.6+ with 1M context**. If the
active model is already `claude-opus-4-6` (or newer) with 1M context,
proceed to Step 1 without prompting.

Otherwise, use `AskUserQuestion`:

> "**Model recommendation:** kb-update works best on Claude Opus 4.6+
> with 1M context. You're currently on **[current model]**. Would you
> like to switch before running?"

Options: "Switch" (halt, user re-runs) or "Proceed" (continue). This
is advisory only; never block the workflow.

## Step 1 — Collect input

Parse arguments:

- **`--group <slug>`** — required or prompted. For `--notion-setup`,
  controls scope: a slug provisions only that group's DB; `all`
  explicitly requests bulk; omit to trigger an interactive prompt.
- **`--notion-setup`** — short-circuit to the Notion provisioning
  flow. See [references/notion-setup.md](references/notion-setup.md).
- **`--list-groups`** — print active groups from `config.yaml` and
  exit.
- **`--force`** — run against a group with `active: false`.
- **`--batch <path>`** — optional explicit batch path (overrides
  auto-detection).

### Step 1b — Input collection (union all surfaces)

kb-update collects **every** available input surface on each run and
unions them into one batch. Surfaces are not mutually exclusive — a URL
+ two attachments + three eligible files in `raw/<slug>/` all flow
through the same pipeline in one invocation, with one Notion publish.

**Short-circuit flags** (evaluated first):

1. **`--notion-setup` passed** → jump to
   [notion-setup.md](references/notion-setup.md). Exit after.
2. **`--batch <path>` passed** → batch mode on `<path>` (Step 1c).
   Overrides auto-collection; only `<path>` is scanned.
3. **`--list-groups`** / **`--force`** → handled inline per Step 1.

Otherwise, **collect from every surface** in order (all non-empty
surfaces contribute):

| # | Surface | How resolved | Filename convention |
|---|---------|--------------|---------------------|
| 1 | **Chat attachments** | Every `.md`, `.pdf`, or `.docx` file attached to the current message (N ≥ 0). PDF/DOCX are auto-converted to markdown via `scripts/convert_to_markdown.py` and materialised under `/tmp/kb-update-raw/<run-id>/`. Other binary types (images, zips, etc.) halt the whole run — see [input-routing.md](references/input-routing.md). | Uses the original filename (PDF/DOCX → `<stem>.md` after conversion). |
| 2 | **URL argument** | Any HTTP(S) URL on the command line. Fetch via `WebFetch` (plain URL) or Glean (`teams.microsoft.com` URLs — see [input-routing.md](references/input-routing.md)). Materialise to a tempfile via `scripts/materialise_ephemeral_input.py url`. | `<competitor>-url-<path-slug>-<YYYY-MM-DD>.md` (competitor slug derived from URL domain; compatible with `filename_prefix` scoping). |
| 3 | **Inline paste** | Markdown typed after the command. Materialise to a tempfile via `scripts/materialise_ephemeral_input.py inline`. Prompt once for optional `source_title` / `source_url` / `source_type` per [input-routing.md](references/input-routing.md). | `inline-paste-<YYYY-MM-DD>.md`. |
| 4 | **`raw/<slug>/` directory** | Run `python3 .claude/skills/kb-update/scripts/collect_inputs.py list-eligible --group <slug>`. Eligible = `Process? = yes` AND `Last processed` blank in INDEX.md, plus any physically-present `.md` / `.pdf` / `.docx` file missing from INDEX.md (logged as a warning). PDF/DOCX rows produce a sidecar `.md` next to the source (e.g. `foo.pdf` → `foo.pdf.md`); the eligible record carries `diff_path` pointing at the sidecar while `file` stays the original source name (so INDEX.md stamping is unchanged). Files with `Process? = no` or a non-blank `Last processed` are skipped silently. | Paths relative to `raw/<slug>/`. |

Log the union summary (one line, before any comparator fires):

```
[inputs] group=<slug> url=<0|1> attachments=<N> inline=<0|1> raw_eligible=<K>/<K_total> raw_missing_from_index=<M> total=<S>
```

**Empty union** (all four surfaces yielded zero) → halt:

> `/kb-update` needs something to process. Drop one or more `.md`
> files into the chat, paste markdown after the command, pass an
> HTTP(S) URL, or drop sources in `raw/<slug>/` (with `Process? = yes`
> and a blank `Last processed` in INDEX.md) and re-run.

**Cardinality switch**:

- `total == 1` → single-source mode. Skip to Step 2.
- `total ≥ 2` → batch mode. Continue at Step 1c.

> **CRITICAL — union is non-negotiable.** Once Step 1b resolves the
> union to N ≥ 2 files, the orchestrator MUST process all N. Dropping
> any surface — e.g. running single-source on a URL when an eligible
> raw-dir file exists, or skipping a raw-dir file because it "looks
> unrelated" to the URL the operator typed — is a skill violation, not
> a judgement call. The orchestrator has no discretionary narrowing
> authority. If the operator genuinely wants a URL-only run, re-invoke
> with `--batch <explicit-path>` (overrides auto-detection) or first
> mark the competing raw-dir row `Process? = no` in
> `raw/<slug>/INDEX.md`. See VERIFICATION.md invariant **U1**.

Track the subset of union members that came from `raw/<slug>/` as
`raw_dir_members` — this list drives the Step 6 INDEX.md writeback.
URL / attachment / inline members are NOT included in
`raw_dir_members` (they were never in INDEX.md).

Unsupported attachment types (images, archives, other binaries) halt
the run — see [input-routing.md](references/input-routing.md) for the
banner. PDF and DOCX are NOT in this set; they auto-convert.

**Group resolution**: if `--group` is omitted, prompt via
`AskUserQuestion` with active groups from `config.yaml`.

### Step 1c — Batch mode

See [input-routing.md](references/input-routing.md) for how each
`batch_source` resolves its file set. Parallel execution rules:

1. **Wave-level parallelism.** Process files in waves of
   `global.batch_wave_size` concurrent (default 3).
2. **Per-file parallelism.** Inside each wave, each file fires one
   Sonnet subagent per matched canon file.
3. **Single-message fan-out.** Emit ALL Agent calls for the wave in
   one orchestrator response so they execute concurrently.
4. **Wave barrier.** After every subagent in the current wave returns,
   start the next wave. Never overlap waves.

Log per wave:
`[batch_wave] wave=<N> files=<k> subagents=<M> duration_ms=<t>`

After all waves complete, Step 5 cross-file pairing runs across the
full batch, Step 6 publishes once.

**Batch mode does NOT modify `raw/<slug>/`.** The skill only reads.
After triage in Notion, the user decides whether to delete / move /
index the processed files.

---

## Step 2 — Pre-flight

Load the group record from `.claude/skills/kb-update/config.yaml`. Halt on
unknown group. Halt on `active: false` unless `--force` was passed.

Pre-flight is local-only: three small steps, no Notion calls on the
happy path, no summary table, no Proceed prompt. Any database-level
issue (stale ID, trashed DB, schema drift, missing SELECT option)
surfaces at publish time in Step 6 and is healed reactively there —
see [publish.md](references/publish.md).

1. **2a — MCP path.** Run
   `python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py mcp-path`.
   JSON to stdout with `path`, `source`, `cached`. Halt on the
   resolver's error message if the clone is missing or zip-not-git.
   Record `mcp_root`.

2. **2b — Canon access.** Always filesystem. Set
   `canon_access_mode = filesystem` and use `<mcp_root>/context/` as
   the canon root. No `ListMcpResourcesTool` probe — canon lives on
   disk where `kb-integrate` writes.

3. **2c — Notion DS resolve.** Run
   `python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py resolve-notion-id --group <slug>`.
   Exit 0 → use ID directly, **no Notion fetch**. Exit 1 → enter
   auto-reconcile (see [preflight.md](references/preflight.md)).

4. **2d — Pre-fetch deferred Notion MCP tools.** Step 6 always needs
   `notion-create-pages`; reactive repair may need
   `notion-update-data-source`, `notion-create-database`,
   `notion-update-view`, `notion-search`, and `notion-fetch`. All are
   deferred; fetch their schemas once now in a single `ToolSearch`
   call so Step 6 doesn't issue reactive discoveries mid-publish:

   ```
   ToolSearch(
     query: "select:mcp__claude_ai_Notion__notion-create-pages,mcp__claude_ai_Notion__notion-update-data-source,mcp__claude_ai_Notion__notion-create-database,mcp__claude_ai_Notion__notion-update-view,mcp__claude_ai_Notion__notion-search,mcp__claude_ai_Notion__notion-fetch",
     max_results: 6
   )
   ```

   **Connector gate (hard halt here, not later).** If the call returns
   empty — or `notion-create-pages` is missing from the response — the
   Notion MCP connector is not installed in this session. Halt at
   pre-flight with the banner in
   [publish.md §5 "Notion MCP connector missing"](references/publish.md#5-permission--connector-human-halt-cases)
   before any comparator runs. Surfacing this after 13 Sonnet
   subagents already finished would burn tokens for no reason.

Continue directly to Step 3.

## Step 3 — Load inputs

### Step 3a — Read raw file + infer source tier

Read the uploaded file's body from the conversation (or the resolved
file paths in batch mode). Extract: `filename`, YAML frontmatter (if
any), full body (truncated to first 2000 words + section headings if
>2000 words), word count.

**No-frontmatter warning.** If the uploaded file has no YAML frontmatter
block at all (first non-blank line is not `---`), emit a single-line
warning before tier inference and continue:

> ⚠️  No frontmatter detected in `<filename>`. Source tier will be
> inferred from filename / URL domain. For accurate routing, add a
> `source_type:` field to the file's top (see examples below). Run
> will proceed with a conservative default tier.

This is a soft warning — kb-update continues with inference — but it
surfaces the ambiguity to the operator in the run log so a mis-tagged
run can be caught before findings ship to Notion.

**Source-tier inference.** Use `source_type` frontmatter or the
dominant URL domain to map to one of the five tiers:

| Signal | Tier |
|---|---|
| `source_type` ∈ {gong_call, customer_interview, earnings_call, 10k, press_release, analyst_report, industry_news_attributed}; URL on gartner.com / forrester.com | tier_1 |
| `source_type` ∈ {hx_briefing, live_session_writeup} | tier_2 |
| `source_type` ∈ {internal_note, internal_note_unverified, slack_internal} | tier_3 |
| URL on teams.microsoft.com / slack.com / linkedin.com; `source_type` ∈ {slack_external, teams_chat, linkedin_post, rumour} | tier_4 |
| URL on competitor's own domain; `source_type` ∈ {vendor_blog, vendor_website, vendor_announcement} | tier_5 |
| No match | tier_5 (conservative default) |

**Tier_4 no longer halts.** Tier_4 (informal external — Teams, Slack
external, LinkedIn, rumour) flows through comparators restricted to
`Notes / open questions` only, with the `Informal (unverified):` render
prefix and the `informal-unverified` tag. A per-finding **significance
gate** runs in the comparator (see
[comparators/default.md § Tier 4 significance gate](comparators/default.md))
— low-signal candidates drop and are counted as
`dropped_tier4_low_signal: N` in the Step 7 stats. Reviewer approval in
Notion is the "explicitly approved" gate before `/kb-integrate`
promotes a tier_4 finding into canon.

**Confidentiality.** Frontmatter `confidentiality` (default
`internal-only`). Passed to comparators; drives the ≥5-word
verbatim-quote refusal in `proposed_text`.

### Step 3b — Load group-scoped canon

1. Glob `groups.<slug>.canon` under `<mcp_root>/context/` (always
   filesystem — canon lives on the local `hxgtm-mcp-server` clone).
2. Narrow per `groups.<slug>.scoping_strategy` when set. Supported:
   `filename_prefix` (preferred; competitive-group default — routes by
   the raw filename's first dash-/underscore-delimited segment),
   `filename_entity` (legacy; content-scans the body for every canon
   stem). See [load-inputs.md](references/load-inputs.md) for the
   algorithms and rename-banner behaviour when `filename_prefix`
   doesn't match.
3. Always-include files from `groups.<slug>.always_include` are added
   as per-entity sliced attachments (see
   [load-inputs.md](references/load-inputs.md) § Summary-file slice).
4. For summary files listed in `always_include`, the orchestrator
   trims the body to only the sections matching entities in the raw
   — preserving original line numbers. See
   [load-inputs.md](references/load-inputs.md) for the trimming
   logic.
5. Foundational-canon files from `groups.<slug>.foundational_canon`
   are attached WHOLE (no slicing) to every entity tuple. These carry
   group-wide canon (e.g. competitive's positioning.md, README.md,
   full competitors.md). See
   [load-inputs.md](references/load-inputs.md) § Foundational canon
   and [comparators/competitive.md](references/comparators/competitive.md)
   § Foundational-file routing policy — foundational files follow a
   DIFFERENT routing policy than per-entity profiles (prefer updates,
   drop weak additions rather than demote).
6. Read bodies for the final set; bind as `selected_canon_files` — a
   list of `{path, body}` tuples.

**Empty canon scope** (e.g. `rfp` group with `canon: []`) → skip Step
4, jump to Step 7 with "No canon in scope". Do NOT publish an empty
set.

## Step 4 — Parallel comparators (one subagent per detected entity)

The orchestrator groups `selected_canon_files` by entity (the
Title-cased stem of the per-entity canon filename; see
[load-inputs.md](references/load-inputs.md)). Each entity produces one
tuple: `{entity_name, canon_file_paths[]}` where `canon_file_paths`
contains the per-entity profile file, plus — when configured — the
entity's writable slice of a summary file (via `always_include`) and
zero or more whole-file `foundational_canon` attachments (group-wide
canon attached to every tuple). For the competitive group today, the
foundational set is `guidance/competitive/README.md`,
`guidance/competitive/positioning.md`, and `truth/market/competitors.md`.

Launch one `Agent` per entity tuple **in a single orchestrator message**
so they run concurrently. Each subagent compares the raw against all
canon files for its entity and emits deduplicated findings targeting
whichever file best fits each claim.

### Resolve the subagent template by group

1. `template_path = .claude/skills/kb-update/references/comparators/<group_slug>.md`
2. If that path exists, use it.
3. Otherwise, fall back to
   `.claude/skills/kb-update/references/comparators/default.md`.
4. Log: `[comparator_template] group=<slug> used=<path>`.

Currently specialized: `competitive.md`. All other groups use
`default.md` until specialized.

### Template variables

Pass these as substituted template variables:

- `{{today_date}}`, `{{group_slug}}`, `{{group_label}}`
- `{{entity_name}}` — Title-cased stem for this subagent
- `{{source_tier}}`, `{{confidentiality}}` — from Step 3a
- `{{raw_file_metadata}}` — filename + frontmatter only (body lives at
  the path; subagent reads it in Step 0)
- `{{raw_file_path}}` — absolute path to the raw file on disk
- `{{canon_file_paths}}` — JSON array of absolute canon file paths
  (1–N entries: profile + optional summary slice + zero or more
  foundational_canon paths; for competitive today: profile + 3
  foundational = 4 paths. Groups without summary/foundational: 1.)
- `{{section_schema}}` — readable YAML dump of
  `groups.<slug>.section_schema`, or `NOT CONFIGURED` when absent.
  See [group-behaviors.md](references/group-behaviors.md).
- `{{deny_list}}` — bullet list from `global.deny_list`.
- `{{scope_gate_context}}` — contents of the scope-gated section(s)
  resolved from `section_schema.*.scope_gated_by`. Extract matching
  `## <Heading>` sections from the per-entity canon file. If none
  configured or none present, pass `ABSENT`.

**Model pin.** Pass `model: "sonnet"` on each `Agent` call (or the
value of `config.yaml → global.comparator_model`).

**Subagent type.** Always pass `subagent_type = "general-purpose"`
(Claude Code is the only supported host).

**Single-message fan-out.** Emit ALL `Agent` tool calls in the same
response. Do NOT serialize across multiple responses — wall time
scales with the slowest subagent only when calls are truly concurrent.

Time the fan-out; log
`[parallel_comparators] entities=<N> duration_ms=<ms>`.

**Zero canon case.** If no entities were detected or `selected_canon_files`
is empty, Step 3b short-circuited to Step 7 — you won't reach this step.

## Step 4.5 — Orchestrator dedup pass

Before invoking the synthesis script, the orchestrator (the model,
in-conversation) performs a dedup pass over the union of findings
returned by all subagents. **Two sub-passes:**

### Pass A — Same-section dedup (cross-subagent / intra-subagent)

1. Collect every subagent's `<FINDINGS_JSON>` array into one pool.
2. For each finding, inspect: `entity`, `target_file`, `section`,
   `proposed_text`, `rationale`.
3. Identify duplicates across subagents — same claim surfacing twice
   (rare; typically a multi-entity raw with overlap) or the same
   subagent emitting near-duplicates. Reason about the claim, not
   tokens.
4. Keep the canonical version per duplicate cluster. Preference order:
   - per-entity profile target over summary-file target
   - higher-specificity `proposed_text`
   - higher-tier source
   - higher-corroboration `evidence_basis` (`corroborated-multi` >
     `structural` > `single-deployment`)

### Pass B — Cross-SECTION semantic dedup (new)

Catches the same underlying factual claim surfacing as two findings
in **different sections** (Pass A misses these because section differs).

1. For every pair of findings (Fa, Fb) where
   `Fa.entity == Fb.entity` AND `Fa.section != Fb.section`:
2. Inspect whether the underlying factual claim is the same — same
   subject, same predicate, same evidence. Rephrasings count as the
   same claim. Example: R6 ("No model explanation or troubleshooting
   layer") in Weaknesses vs. R9 ("hx covers the model explanation gap
   Federato cannot fill") in hx positioning — the underlying claim
   ("Federato has no model explanation capability") is identical.
3. If yes, **keep one, drop the other.** Section preference:
   - Weaknesses / watch-outs > Strengths > Notes / open questions
     > hx positioning > Snapshot
   - Rationale: hx positioning is for framing, not restating
     Weaknesses. Weaknesses is the canonical home for capability
     gaps. Snapshot never restates anything — it's top-level
     framing only.
4. Log: `[cross_section_dedup] kept=<Fa.id> in=<Fa.section>
   dropped=<Fb.id> in=<Fb.section> reason=<short claim summary>`.
5. Count as `cross_section_dedup_dropped: N` in stats.

### Produce output

Produce one deduplicated array (Pass A output → Pass B input → final)
and carry it into Step 5.

Log briefly: `[orchestrator_dedup] input=<N_in> output=<N_out>
dropped=<N_dropped> cross_section_dropped=<N>`. Include the dedup
reasoning summary in the Step 7 report so reviewers can audit it.

This step is intentionally AI-judgement-based. The synthesis script
no longer pairs or collapses findings.

## Step 5 — Synthesize findings

Collect every subagent's raw text response into a JSON array of strings
(one string per subagent) and pipe it into the synthesis script via
`--subagent-outputs-stdin`. This avoids writing 13+ temp files per run
— the subagent outputs are already in conversation context.

```bash
python3 -c 'import json, sys; json.dump([<subagent_1_text>, <subagent_2_text>, ...], sys.stdout)' \
  | python3 .claude/skills/kb-update/scripts/synthesize_findings.py \
      --group <slug> \
      --run-date <YYYY-MM-DD> \
      --mcp-root <resolved mcp_root> \
      --subagent-outputs-stdin \
    > /tmp/kb-update-findings.json
```

(The orchestrator substitutes each subagent's raw response — including
its `<FINDINGS_JSON>` and `<STATS_JSON>` fenced blocks — into the Python
list literal.)

The script parses `<FINDINGS_JSON>` / `<STATS_JSON>` fenced blocks
from each subagent, merges, pairs cross-file findings (sharing a
`dedup_pair_id`), renumbers contiguously, hashes canon spans, and
validates required fields. See [synthesis.md](references/synthesis.md)
for the full contract.

Malformed findings and malformed subagents are logged but don't
abort the run — the publish step tags rows with `[MALFORMED]` where
appropriate.

Exit 1 from the script (all subagents malformed) → skip Step 6,
report the error in Step 7.

## Step 6 — Publish to Notion

Pipe the synthesis JSON into the publisher:

```bash
cat /tmp/kb-update-findings.json \
  | python3 .claude/skills/kb-update/scripts/publish_to_notion.py \
      --group <slug> --run-date <YYYY-MM-DD> \
  > /tmp/kb-update-pages.json
```

For each batch in the emitted `batches` array, call
`mcp__claude_ai_Notion__notion-create-pages` with the batch's `parent`
and `pages` verbatim. Wait for each call to return before starting the
next.

**Reactive repair** — database-level issues are discovered and fixed
here, not pre-flight. **The orchestrator auto-heals every failure it
can via MCP; it never asks the user to run `/kb-update --notion-setup`
mid-flow.** See [publish.md](references/publish.md) for the full
reactive flow. Summary:

- **400 `Invalid select value for property "<Name>"`** (Entity or any
  SELECT with run-time values) → seed options via
  `ALTER COLUMN "<Name>" SET SELECT(...)` from the current run's
  distinct values unioned with the live column's existing options,
  retry the batch. Retry cap 3; on failure see
  [publish.md §5 "Schema repair failed 3 times"](references/publish.md#5-permission--connector-human-halt-cases).
- **400 `property does not exist` / `Unknown property` /
  `property "<X>" not found`** → schema drift. `ADD COLUMN` DDL
  from `publish_to_notion.py --check-schema --group <slug>`, call
  `notion-update-data-source`, retry. On second failure, re-fetch
  live schema via `notion-fetch collection://<ds>`, diff, and retry
  once more — do NOT halt. See
  [publish.md §2](references/publish.md#2-schema-drift-missing-column).
- **404 / object_not_found** → dispatch into the three sub-cases of
  [publish.md §3](references/publish.md#3-404--object_not_found-db-presence):
  `3a` cache-stale (rewrite cached UUID), `3b` group's DB missing
  (auto-create via `setup_notion.py --plan --group <slug>
  --landing-page-id <id>`), `3c` landing page blank (full bulk
  re-provision of all 11 groups via
  `setup_notion.py --plan --landing-page-id <id>`). Landing page
  itself missing → halt with the landing-page banner (the one
  genuine human-action case). Retry cap 3 total.
- **`unauthorized` / 403** → treated as a permission issue, not a
  presence issue. Re-discover the DS once (in case the integration
  was re-scoped); on persistent 401/403, halt with the integration
  ID from the error body — see
  [publish.md §5 "Persistent unauthorized"](references/publish.md#5-permission--connector-human-halt-cases).
- **429 `rate_limited` / 409 `conflict_error` / 5xx** → auto-retry
  the batch with 2s/4s/8s backoff (cap 3). Failed after 3 →
  record and continue to next batch. See
  [publish.md §4](references/publish.md#4-transient-failures-rate-limit-conflict-5xx).
- **Other 4xx** → record, continue remaining batches, count
  failures, report in Step 7.

**Publisher invariants** (enforced by `publish_to_notion.py`):
`Status` = `Pending Review` only; `Reviewer` and `Final Updated Text` are
never written. See [publish.md](references/publish.md) for the full
contract.

**Zero-findings case.** Skip Step 6 entirely; report "Upload matches
canon — no conflicts to publish" in Step 7.

Capture the landing-page URL and the group DB URL for Step 7.

### Step 6a — INDEX.md writeback for raw-dir members

After every `notion-create-pages` batch for this run has either
succeeded or been logged as a terminal failure, stamp
`Last processed = {{today_date}}` in `raw/<slug>/INDEX.md` for every
file in `raw_dir_members` that contributed to a successful publish.

- **Zero-findings case**: still stamp — the raw file WAS processed,
  it just produced no conflicts.
- **Publish hard-failed** (no batches succeeded at all): skip the
  stamp so the next run retries the same file set.
- **Partial publish failure** (some batches 4xx / 5xx after retry cap):
  stamp anyway — the raw files were fully compared; the gap is in
  Notion, not in INDEX.md. The failed batches already surface in the
  Step 7 `Failed batches` line.

Invocation:

```bash
python3 .claude/skills/kb-update/scripts/collect_inputs.py stamp-processed \
    --group <slug> \
    --date <YYYY-MM-DD> \
    --files "<rel_path_1>,<rel_path_2>,..."
```

`<rel_path_N>` is each raw-dir member's path relative to
`raw/<slug>/` (the exact `File` column value from INDEX.md, or the
detected disk path for missing-from-index files — `stamp-processed`
appends the latter as new INDEX.md rows).

URL / attachment / inline members are NOT stamped — they were never
in INDEX.md. If `raw_dir_members` is empty, skip this substep
silently.

Log the script's JSON summary (`updated`, `appended`,
`requested_but_missing` counts) as
`[index_writeback] updated=<U> appended=<A> missing=<M>`.

## Step 7 — Report

Output a summary:

```
kb-update run complete.

Group: [slug] ([label]) — owner: [codeowner] — active: [yes/no]
Inputs: url=[0|1] attachments=[N] inline=[0|1] raw_eligible=[K]/[K_total] raw_missing_from_index=[M] total=[S]
Input: [filename or batch-<N>-files]
Source tier: [tier_1/2/3/4/5]
Confidentiality: [internal-only | shareable]

Findings: [N] total ([X] high, [Y] medium, [Z] low)
By tier:     tier_1 [N] · tier_2 [N] · tier_3 [N] · tier_4 [N] · tier_5 [N]
By scope:    structural [N] · niche [N] · unscoped [N]
By entity:   [E1] [N] · [E2] [N] · ...

Drops:       tier4_low_signal [N] · deny_list [N] · quote_verbatim [N]
Gate:        scope_gate_miss [N] · scope_gate_skipped [N]
Caps:        replace_at_cap [N] · section_full_demoted [N]
Pairing:     dedup_pairs [N]  (cross-file pairs linking specific + summary files)
Dedup:       cross_section_dedup_dropped [N]
Splits:      snapshot_split [N] · demoted_single_deployment [N]
Drift:       style_mismatch_in_section [N] · style_mismatch_with_schema [N]
Closures:    closes_open_question [N]

Canon scope: [K_matched]/[M_total] files matched (strategy: [filename_entity/none])
Canon access: filesystem
Comparators: [N_ok] ok / [N_failed] failed

Published to Notion: [N] rows in "KB - [Group Label]"
Data source: [resolved DS ID]
View: [notion URL]
Landing page: [notion URL]
Failed batches: [N]
Malformed findings: [N] (rows prefixed [MALFORMED])

Timings (ms):
  parallel_comparators: [N]
  synthesis (parse/renumber/validate/total): [N] / [N] / [N] / [N]
  publish: [N]
  total:   [N]

INDEX.md writeback: updated=[U] appended=[A] (raw-dir members only)

Reminder: URL / attachment / inline inputs were NOT persisted to
raw/[group]/ — tempfiles live under /tmp/kb-update-raw/<run-id>/
only. To track them for future runs, save to raw/[group]/<source-type>/
and add an INDEX.md row manually.
```

---

## Error handling

- **Any comparator subagent fails or times out** → capture the error,
  keep findings from successful subagents, log failure in Step 7.
- **All comparators fail** → skip Step 6, report and stop.
- **Canon access fails entirely** (neither MCP nor filesystem) →
  report and stop.
- **`--group` missing and user cancels resolution prompt** → halt
  cleanly.
- **Inactive group without `--force`** → halt with the Step 2 banner.
- **Unsupported attachment type** (images, archives, other binaries —
  NOT PDF/DOCX, which auto-convert) → halt with the
  [input-routing.md unsupported-attachment banner](references/input-routing.md#unsupported-attachment-types-halt).
- **PDF/DOCX conversion failure** (oversize input, scanned/image-only
  PDF, missing pymupdf/mammoth lib) → halt with the converter's
  stderr message; do not fall back to silent skip. See
  `scripts/convert_to_markdown.py` exit codes 3–6.
- **Empty input union** (no attachments, no URL, no inline paste,
  zero eligible files in `raw/<slug>/`) → halt with the Step 1b
  empty-union banner.
- **Empty canon scope** (`canon: []` or all filtered out) → skip Step
  6, report "No canon in scope" in Step 7.
- **Malformed subagent JSON** → logged, that subagent's findings
  skipped, others proceed.
- **Synthesis exit 1** (all subagents malformed) → skip publish,
  report in Step 7.

---

## Relationship to kb-lint

kb-update and kb-lint are complementary, and their scopes do NOT
overlap:

- **kb-lint** is a read-only **canon health audit** skill. It scans only
  the group's slice of the canonical KB (`../hxgtm-mcp-server/context/`)
  for freshness, internal consistency, structural integrity, template
  compliance, coverage gaps, and (optionally) external verification,
  then writes a severity-ranked markdown report to
  `outputs/kb-lint-<group>-YYYY-MM-DD.md`. It does NOT read
  `raw/<group>/`, does NOT touch INDEX.md, and does NOT publish to
  Notion.
- **kb-update** is the write-path skill that owns the raw-source domain
  end to end. It unions uploaded files (chat attachments + URL + inline)
  with unprocessed files in `raw/<group>/` (filtered by INDEX.md's
  `Process?` + `Last processed` contract), runs raw-vs-canon comparison,
  and publishes findings as rows in the group's `KB - <Label>` database
  for async team triage. It reads INDEX.md and stamps `Last processed`
  for raw-dir files after publish. Never edits raw file bodies and never
  writes a markdown report.

Run kb-lint for a periodic canon health snapshot; run kb-update when you
have specific new raw sources to triage into canon (closed by
`/kb-integrate`).
