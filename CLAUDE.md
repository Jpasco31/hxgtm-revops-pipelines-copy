# hx GTM OS — Account Research Pipelines

This repo contains account research workflows for the hyperexponential (hx) GTM team.
Each workflow is defined as a markdown SKILL.md file inside the `.claude/skills/` directory,
which Claude Code auto-discovers as both a registered skill (matched on `description`) and a
`/<skill-name>` slash command.

## Slash Commands

| Command | Description |
|---------|-------------|
| `/generate-dossier [account1] [account2] ...` | Generate one or more Account Dossiers for target insurance companies. Handles 1-account or N-account runs identically (single-account = 1-account batch wave). Parallel waves of 3, auto-publishes each to Notion + `hxgtm-mcp-server/context/accounts/`. Resumable via `_batch-state.json`. Pass `--file <path>` for a newline-separated list. |
| `/kb-lint [dimensions]` | Whole-canon health audit (no `--group`). Scans **every** file under `context/` (by file walk, so canon files no group claims are covered too) plus the project meta docs (`README.md`, `AGENTS.md`, `docs/`), sharded across parallel subagents in waves, with a cross-group consistency pass. Produces one merged report at `outputs/kb-lint-all-YYYY-MM-DD.md`. |
| `/kb-lint --group <slug> [dimensions]` | Group-scoped canon health audit (staleness, contradictions, drift, structural integrity, template compliance, coverage gaps, optional external verification). Canon-only — does not touch `raw/`. Produces a markdown report at `outputs/kb-lint-<group>-YYYY-MM-DD.md`. Run `/kb-lint --list-groups` to see groups. |
| `/kb-update --group <slug>` | Diff raw source(s) — chat attachments (`.md` / `.pdf` / `.docx`), URL, inline-pasted markdown, or unprocessed files in `raw/<slug>/` — against a group's canonical KB and publish findings to the "KB - Updates Review" Notion database for team triage. PDF/DOCX are auto-converted to markdown. Auto-batches with ≥2 inputs (parallel waves of 3). |
| `/kb-update --notion-setup [--group <slug>\|all]` | One-off provisioner for kb-update's Notion database structure (landing page + 11 per-group databases). No `--group` → interactive prompt (pick one group or "All groups"); `--group <slug>` → provision just that group; `--group all` → bulk, non-interactive. Safe to re-run — only creates what's missing. |
| `/kb-integrate --group <slug>` | Read every `Status = Approved` row from a group's Notion database and apply the edit to canon in `hxgtm-mcp-server/context/`. Interactive by default (computes plan, prompts once, then applies if confirmed). Pass `--plan` for a pure dry-run (no prompt, no writes) or `--apply` / `--no-confirm` for non-interactive write. |
| `/create-pain-slide [account name]` | Create a structured challenge table slide — uses an existing dossier if available, otherwise does fresh external research |
| `/context-lint [args]` | Audit context wiring across MCP server, plugin SKILL.md files, fallback manifests, and the Notion "Agents & Skills" page |
| `/scaffold-skill [brief]` | Create a new GTM OS skill or content type across hx-plugins and hxgtm-mcp-server |
| `/framer-template-sync [--apply]` | Audit all format-for-framer CMS reference files against the live Framer schema in one pass. Optionally rewrite cached IDs and enum case names when drift is unambiguous. |

## Available Workflows

### Account Dossier (Batch / Parallel) — Generate One or More Account Dossiers

When the user asks to generate an account dossier, batch-generate dossiers in
parallel, or asks for the resumable parallel-wave dossier runner, read and
follow `.claude/skills/generate-dossier/SKILL.md`.

A single-account invocation is treated as a 1-account batch wave — the same
pre-flight, assembly, save, and publish steps apply.

It generates a comprehensive 6-section research document per account and
writes each to three destinations: `outputs/generate-dossier/`,
`hxgtm-mcp-server/context/accounts/`, and Notion. Accounts run in parallel
waves of 5 (25 concurrent section subagents pinned to Sonnet), with
per-account checkpointing, atomic writes, partial-dossier acceptance, a
per-dossier self-check, an error log, and an end-of-batch summary.
Auto-resumes on rerun by skipping accounts already marked `done` in
`_batch-state.json`.

**Sections:**
1. Account Overview (company profile from Salesforce)
2. Vision, Mission & Strategic Priorities (web research, hx alignment)
3. Who's Who — Top 20 Power Players (key executives)
4. Past Opportunities & Interactions (commercial history from Salesforce + Gong)
5. What People Are Saying (public commentary across 10 strategic themes)
6. Discovery Questions (3–5 research-informed questions, generated inline from Sections 2 and 5)

**Key behaviors:**
- Parallel waves of 5 accounts; each account's 5 section subagents launch in parallel
- Section subagents pinned to Sonnet
- Single Proceed/Cancel gate after pre-flight; per-account loop is non-interactive
- Per-account publish/save failures are logged and marked `partial` — the batch never stops mid-wave
- Web research tries Perplexity Sonar API → Perplexity MCP → built-in `WebSearch` + `WebFetch`
- Clones `hxgtm-mcp-server` at `/tmp/hxgtm-mcp-server-clone/` for read-side context (Section 2 + discovery-question bank + product-marketing files)

**Requirements:**
- Perplexity Sonar API (optional, preferred) — `PERPLEXITY_API_KEY` env var + `requests` Python package
- Perplexity MCP (optional fallback)
- Built-in `WebSearch` + `WebFetch` (Anthropic-native; always available as final fallback)
- Glean MCP (optional; placeholders if missing — affects Sections 1, 3, 4)
- **Notion publishing (required)** — pre-flight hard stop if missing. Either direct REST via `NOTION_API_KEY` / `NOTION_TOKEN` (preferred) OR the Notion MCP connector
- **Local `hxgtm-mcp-server` clone with write access (required)** — via `HXGTM_MCP_SERVER_PATH` or `../hxgtm-mcp-server`; pre-flight hard stop if missing
- Git + `hxgtm-mcp-server` repo URL (optional; env `HXGTM_MCP_SERVER_REPO_URL`, default `git@github.com:hx-gtm/hxgtm-mcp-server.git`) — for the read-side clone

**Output:** `outputs/generate-dossier/[slug]-dossier.md` per account, plus a copy at `$HXGTM_MCP_SERVER_PATH/context/accounts/[slug]-dossier.md` and a Notion page per account, and batch files `_batch-state.json`, `_batch-errors.md`, `_batch-summary.md`.

### Create Pain Slide — Build a Structured Challenge Table Slide

When the user asks to create a pain slide, challenge table, why-change slide,
or structured challenge summary for an account, read and follow
`.claude/skills/create-pain-slide/SKILL.md`.

This synthesizes customer challenges from Gong call data and either an existing
Account Dossier or fresh external research into a structured 6-column table on
a single PowerPoint slide.

**Workflow:**
1. Checks `outputs/generate-dossier/` for existing dossiers and asks the user
   whether to use one (skips external web research if yes)
2. If no dossier selected, does fresh external research (annual reports,
   investor presentations, earnings calls)
3. Always searches Glean for internal Gong call data
4. Synthesizes into a 3–5 row challenge table (Challenge, Issue, Impact, Measure,
   Org Context, Objective)
5. Generates a single PowerPoint slide using the hx template

**Requirements:**
- Glean MCP (for internal Gong data — always runs)
- Web search and fetch access (for external research path only)

**Output:** `outputs/create-pain-slide/[account-name]-pain-slide.pptx`

---

### KB Lint — Audit Knowledge Base Health

When the user asks to lint the KB, check for inconsistencies, find stale content,
or audit the knowledge base, read and follow `.claude/skills/kb-lint/SKILL.md`.

kb-lint has two scan modes:

- **Whole-canon (all) mode** — a no-argument `/kb-lint` audits the **entire
  canon** in one run: every `.md` under `../hxgtm-mcp-server/context/`
  (enumerated by file walk, so files no group claims are still covered) plus
  the project meta docs (`README.md`, `AGENTS.md`, `docs/`). The content is
  size-sharded across parallel Canon Analyzer subagents (waves of 5 by
  default), with an added cross-group consistency pass that catches
  contradictions spanning shards. Writes one merged report at
  `outputs/kb-lint-all-YYYY-MM-DD.md`.
- **Group mode** — `/kb-lint --group <slug>` targets one group from
  `.claude/skills/kb-lint/config.yaml` (e.g. `competitive`, `messaging`) and
  writes `outputs/kb-lint-<group>-YYYY-MM-DD.md`. All 11 groups are active.

Both modes cross-reference documents and produce a severity-ranked markdown
report. kb-lint audits canon only — it does NOT read the raw staging folder
(`raw/<group>/`) or touch `INDEX.md`.

**Dimensions checked:**
- Freshness (stale review dates, outdated claims)
- Internal consistency (cross-document contradictions within group scope)
- Structural integrity (broken references, orphaned files)
- Template compliance (persona, product, segment templates)
- Coverage gaps (topics referenced but never defined)
- External verification (optional, Phase 3 — high-churn claims vs live web)

**Requirements:**
- `--group <slug>` (optional) — omit it for a whole-canon (all) run; pass it
  to scope to one group. See `.claude/skills/kb-lint/config.yaml` for
  available groups, or run `/kb-lint --list-groups`
- Canon access via hxgtm-context MCP server OR direct filesystem access to
  `../hxgtm-mcp-server/context/` (auto-detected). All-mode's project meta
  docs are filesystem-only — skipped with a note if the repo isn't on disk
- Perplexity MCP (optional, Phase 3)

**Output:** `outputs/kb-lint-<group>-YYYY-MM-DD.md` (group mode) or
`outputs/kb-lint-all-YYYY-MM-DD.md` (all mode) — a markdown report with
high/medium/low severity findings, coverage gaps, and run statistics.
kb-lint does NOT publish to Notion and does NOT process raw sources — to
diff raw sources against canon and triage them in Notion, use `/kb-update`
instead.

### KB Update — Post Raw-vs-Canon Findings to Notion

When the user provides raw source(s) — attachments, URL, inline-pasted
markdown, or files staged in `raw/<slug>/` — and asks to review them
against canon, check them against canon, stage them for KB triage, or
publish raw-canon conflicts, read and follow `.claude/skills/kb-update/SKILL.md`.

kb-update is the **write-path-to-Notion companion to kb-lint**. On
every run it unions **every available input surface** — chat
attachments (`.md`, `.pdf`, `.docx`), an HTTP(S) URL argument,
inline-pasted markdown, and unprocessed `.md` / `.pdf` / `.docx`
files in `raw/<slug>/` (rows with `Process? = yes` and blank
`Last processed` in `INDEX.md`) — into a single input set. PDF and
DOCX inputs are auto-converted to markdown via
`scripts/convert_to_markdown.py` before the comparator runs (sidecar
`.md` next to raw-dir sources; ephemeral tempfile for chat/URL).
If the union has 1 file → single-source mode; ≥2 → batch mode with
parallel waves of 3 concurrent files, cross-file pairing at synthesis,
and one publish. After a successful publish kb-update stamps
`Last processed = <today>` into `raw/<slug>/INDEX.md` for every
raw-dir file that contributed. Raw file bodies are never edited;
URL / attachment / inline inputs are materialised to
`/tmp/kb-update-raw/<run-id>/` and not persisted.

**Workflow:**
1. User provides input (any combination of the four surfaces above)
2. User runs `/kb-update --group <slug>` (or omits `--group` to be prompted)
3. kb-update logs the union summary, diffs each input against the
   group's in-scope canon, and publishes findings as rows in the
   `KB - <Group Label>` database with `Status = Pending Review`
4. On success, INDEX.md gets `Last processed` stamped for raw-dir members
5. The team triages each row through Pending Review → Approved →
   Rejected → Integrated in Notion

**Requirements:**
- Claude Code desktop — required only for the attachment input surface. URL / inline / raw-dir paths work in the CLI too.
- `--group <slug>` (required or prompted) — see `.claude/skills/kb-update/config.yaml`
- Canon access via hxgtm-context MCP server OR direct filesystem access to
  `../hxgtm-mcp-server/context/` (auto-detected)
- Notion MCP connector for publishing findings and discovering the landing page
- Glean MCP (optional) — required only when the input is a `teams.microsoft.com` URL
- One-time manual step: create a Notion page titled exactly
  `KB - Updates Review` at the teamspace of your choice, then run
  `/kb-update --notion-setup` to provision the 11 per-group databases

**Output:** Per-finding rows in the group's Notion database, all nested
under the `KB - Updates Review` landing page. Each database's default
view is grouped by `Review Bucket` (`Pending Review` + `Needs Restage`
→ `Needs Decision`; `Approved` / `Rejected` / `Integrated` each in
their own bucket) so reviewers see one stack per decision state. Data
source IDs are configured per group in `.claude/skills/kb-update/config.yaml`
(`groups.<slug>.notion_data_source_id`). To retro-fit already-provisioned
DBs to the current schema and view shape, run
`python3 .claude/skills/kb-update/scripts/setup_notion.py --migrate-views`.
See `.claude/skills/kb-update/README.md` for the full setup and triage workflow.

### KB Integrate — Apply Approved Notion Rows Back to Canon

When the user asks to integrate approved kb-update rows, apply
approved rows to canon, sync Notion approvals to disk, or finish the
kb-update loop, read and follow `.claude/skills/kb-integrate/SKILL.md`.

kb-integrate is the **write-path-to-disk** companion to kb-update. It
closes the triage loop: kb-update writes rows as `Pending Review`,
humans triage in Notion (`Approved` / `Rejected`), and kb-integrate
applies every `Approved` row's `Proposed Updated Text` to the
referenced canon file in `hxgtm-mcp-server/context/`, then flips the
row to `Integrated`.

**Workflow:**
1. User runs `/kb-integrate --group <slug>` for a dry-run preview
   (every approved row, planned action, before/after snippets)
2. kb-integrate calls `notion-fetch` on the group's database, filters
   to `Status = Approved`, and pipes the rows through
   `.claude/skills/kb-integrate/scripts/apply_integrations.py --plan`
3. User reviews the preview, then re-runs with `--apply` to commit
4. On `--apply`, canon files are edited in place and each
   successfully-applied row is updated to `Status = Integrated` via
   `notion-update-page`
5. The user reviews `git diff` in `hxgtm-mcp-server` and commits
   themselves — kb-integrate never auto-commits or pushes

**Requirements:**
- `--group <slug>` (required or prompted) — kb-integrate reuses
  `.claude/skills/kb-update/config.yaml` as the single source of truth for
  groups and `notion_data_source_id`
- Filesystem access to `hxgtm-mcp-server/context/` (set
  `HXGTM_MCP_SERVER_PATH` or place the repo at `../hxgtm-mcp-server/`).
  MCP-read-only mode is NOT sufficient — kb-integrate writes files.
- Notion MCP connector for `notion-fetch` and `notion-update-page`

**Output:** Edits to files under `hxgtm-mcp-server/context/` (left as
unstaged changes for the user to review and commit) and `Status`
updates in the group's Notion database (`Approved → Integrated`).
Failed and skipped rows stay `Approved` for retry.

### Context Lint — Audit Skill / Context / Docs Wiring

When the user asks to lint context, audit skill wiring, check for orphan
context files, check fallback drift, audit context packs, or check
documentation drift, read and follow `.claude/skills/context-lint/SKILL.md`.

This audits the structural wiring between three sources of truth: the MCP
server's `src/context.ts` (skill definitions, packs, guidance map), the
plugin SKILL.md files and their fallback manifests, and the user-facing
Notion "Agents & Skills" page. Produces a severity-ranked report.

**Checks:**
- Pack integrity (referenced files exist)
- Orphan files (every context file is referenced somewhere)
- Orphan packs (every CONTEXT_PACK is used by ≥1 skill)
- Fallback-to-server sync (manifests match SKILL_CONTEXTS)
- Cross-skill chain duplication (e.g. ads → polish double-loads)
- Unconditional bulk loading (loading all personas when only one is used)
- Parallelism opportunities (sequential MCP calls that could be batched)
- Context size profiling (skills exceeding line-count threshold)
- Foundation coverage (audience ↔ messaging ↔ persona wiring)
- Notion documentation drift (semantic comparison, gated by temporal pre-filter)

**Requirements:**
- MCP server source: `Projects/MCP/` (production) OR `../hxgtm-mcp-server/`
  (local fallback) — auto-detected
- Plugins source: `Projects/Plugins/plugins/` (production) OR
  `../hx-plugins/plugins/` (local fallback) — auto-detected
- Notion MCP (optional — enables Check #10; non-blocking, skips silently
  if unavailable)

**Output:** `outputs/context-lint-YYYY-MM-DD.md`

### Scaffold Skill — Create New Skills or Content Types

When the user asks to create a new skill, scaffold a skill, add a content type,
or wire a new skill, read and follow `.claude/skills/scaffold-skill/SKILL.md`.

This creates all files needed for a new skill or content type to work across
both repos (hx-plugins and hxgtm-mcp-server), including Notion documentation.
Uses a conversational planning flow to gather requirements from a brief.

**What it creates:**
- SKILL.md, content-type playbooks, context.ts wiring, command wrappers
- mcp-fallback.md section, README index, save-to-Notion routing
- Notion sub-page under "Agents & Skills"
- Test prompts for trigger verification

**Requirements:**
- Both repos accessible: `Projects/Plugins/` or `../hx-plugins/` AND
  `Projects/MCP/` or `../hxgtm-mcp-server/` — auto-detected
- Both repos in clean git state (no uncommitted changes)
- Notion MCP connected (hard requirement)

**Output:** Files across both repos + Notion sub-page

---

## Batch Mode

To generate dossiers for multiple accounts at once, run `/generate-dossier`
with a space-separated list of quoted account names, or with
`--file inputs/batch-accounts.txt` pointing at a newline-separated list. The
skill processes accounts in parallel waves of 3, writes outputs under
`outputs/generate-dossier/`, copies each dossier to
`hxgtm-mcp-server/context/accounts/`, and auto-publishes each to Notion. The
batch is resumable via `_batch-state.json`.

---

## Repository Structure

```
.claude/
  skills/
    generate-dossier/            # Parallel-wave batch dossier generator (publishes to Notion + MCP server, resumable). 1-account runs just use a 1-account wave.
      references/                # Section prompts + output format
      scripts/
        perplexity-sonar.py      # Perplexity Sonar API wrapper (preferred web-research path)
        save-dossier-to-notion.py # Markdown-to-Notion parser/publisher (supports --publish, --multi)
        test_save_dossier_to_notion.py
    kb-lint/                     # Canon health audit. Group mode (1–2 subagents) or whole-canon all-mode (sharded parallel waves + cross-group pass), markdown output
      references/                # Subagent prompts + output format + templates
    kb-update/                   # Single-file raw-vs-canon triage → Notion
      references/                # Comparator prompt + Notion output format
      scripts/
        setup_notion.py          # Notion provisioner (plan generator, no auth)
        publish_to_notion.py     # Finding → notion-create-pages transformer
    kb-integrate/                # Approved Notion rows → canon edits on disk
      scripts/
        apply_integrations.py    # Row-list → edit plan → (optional) apply
    create-pain-slide/           # Challenge table slide generator
      references/                # Transformation rules and training examples
      scripts/
        generate_table_slide.py  # PowerPoint generation script
        table_renderer.py        # Shared hx table rendering module
      assets/
        hx-ppt-template.pptx     # hx branded PowerPoint template
    scaffold-skill/              # Skill scaffolding from templates
      references/                # Content-type templates, wiring checklist
    context-lint/                # Structure compliance linter (spec only — PRD.md)
    design-system/               # hx brand system reference (tokens, fonts, logos) — dependency for the card skills
    framer-template-sync/        # Proactive cache sync for format-for-framer CMS references (audit + --apply)
    linkedin-partnership-card/   # LinkedIn partnership-announcement card generator
    linkedin-single-image-ad/    # LinkedIn single-image-ad generator
    webinar-promo-card/          # LinkedIn webinar-promo card generator
      references/                # Gradient asset map, headshot-cleanup prompt, grain/vignette CSS
      assets/                    # Gradient PNG backgrounds (wine / ink / forest)
      scripts/                   # export_card.js (Puppeteer PNG), cleanup_headshot.js (Gemini headshot)
      templates/                 # 1/2/3-speaker HTML scaffolds
    download-from-notion/        # Utility skill — download Notion-attached files to disk (chained by webinar-promo-card)
    upload-to-notion/            # Utility skill — upload local files/URLs to a Notion page block, row, cover, or icon
skills/
  dossier-feedback/              # Runtime feedback workflow (not yet a SKILL.md)
  staging/                       # WIP skills not yet promoted (hx-core, hx-delivery)
scratch/
  market-insights-competitor-scan/  # WIP — not yet promoted to skills/
raw/                             # Raw source staging area for kb-update (11 group folders)
scripts/
  kb-group-init.sh               # Per-codeowner sparse-checkout setup (hides other groups' raw/ from disk)
  install_card_skill_deps.sh     # Pre-installs Puppeteer for all 5 card skills (run by the SessionStart hook)
  package-skill.sh               # Packages a .claude/skills/<skill> dir into a .skill file for Claude Desktop
outputs/
  generate-dossier/              # Dossiers (single- or multi-account) + _batch-state.json / _batch-errors.md / _batch-summary.md
  create-pain-slide/             # Generated pain slide .pptx files saved here
  kb-lint-<group>-YYYY-MM-DD.md  # kb-lint markdown reports saved at repo-root outputs/
```

---

## Notes

- The dossier skill has a single Proceed/Cancel gate at the end of pre-flight
  (Step 1). That gate reports MCP availability and lets the operator confirm
  before any subagents launch. Once proceed is clicked, the per-account loop
  runs without prompts.
- Sections 1 and 4 require Salesforce and Gong access via Glean MCP. Without it,
  those sections output structured placeholder tables.
- Section 2 uses the same methodology as the find-strategic-priorities CoWork
  skill. It reads hx capability context from a `/tmp/hxgtm-mcp-server-clone/`
  checkout (cloned in Step 0.5), falling back to https://www.hyperexponential.com
  if the clone fails.
- Notion publishing uses database ID `337802db20a6806f8fdbfe480adc0e4b` and is
  required — a per-account publish failure is logged and the account is marked
  `partial`, but missing Notion transports at pre-flight is a hard stop.
- This is a Claude Code project (not a Claude Cowork plugin). It runs via the
  `claude` CLI or the Claude Code IDE extension.
