# hxgtm-revops-pipelines

Account research and KB maintenance workflows for the hyperexponential GTM team.
Each workflow is a Claude Code skill defined in [.claude/skills/](.claude/skills/).

## Skills

| Skill | Slash command | What it does | Status |
|-------|---------------|--------------|--------|
| [generate-dossier](.claude/skills/generate-dossier/) | `/generate-dossier [account1] [account2] …` | Generate 6-section account research dossiers for one or more target insurance companies. Single-account runs are 1-account batch waves. Parallel waves of 3, per-account publish to Notion + `hxgtm-mcp-server/context/accounts/`. Resumable via `_batch-state.json`. | Active |
| [kb-lint](.claude/skills/kb-lint/) | `/kb-lint --group <slug>` | Group-scoped, canon-only audit of the GTM knowledge base for staleness, contradictions, and structural drift. Writes a markdown report to `outputs/` | Active |
| [kb-update](.claude/skills/kb-update/) | `/kb-update --group <slug>` | Diff raw source(s) — attachments, URL, inline paste, or unprocessed files in `raw/<slug>/` — against a group's canonical KB slice and publish findings to Notion for team triage. Auto-batches with parallel waves when ≥2 inputs are present | Active |
| [kb-integrate](.claude/skills/kb-integrate/) | `/kb-integrate --group <slug>` | Apply `Approved` rows from a group's Notion database back to canon in `hxgtm-mcp-server/context/` | Active |
| [create-pain-slide](.claude/skills/create-pain-slide/) | `/create-pain-slide [account]` | Create a structured challenge table slide — uses an existing dossier if available, otherwise does fresh external research | Active |
| [context-lint](.claude/skills/context-lint/) | `/context-lint` | Audit context wiring across MCP server, plugin SKILL.md files, fallback manifests, and Notion docs | Active |
| [scaffold-skill](.claude/skills/scaffold-skill/) | — | Scaffold a new skill from a template | Active |
| [market-insights-competitor-scan](scratch/market-insights-competitor-scan/) | — | Glean scan of Teams Market Insights for competitor threads, full-thread reads, structured hx implications | WIP (`scratch/`) |

---

## kb-lint — Knowledge base health audit

Group-scoped, read-only audit of the **canonical KB**
(`../hxgtm-mcp-server/context/`). Cross-references documents against each
other and against current web data (Phase 3, optional), and produces a
severity-ranked markdown report. kb-lint audits canon only — it does **not**
read the raw staging area (`raw/<group>/`) or touch `INDEX.md`. Raw sources
are owned by [`/kb-update`](#kb-update--raw-vs-canon-triage-in-notion).

Every run targets **one group** via `--group <slug>` — see
[.claude/skills/kb-lint/config.yaml](.claude/skills/kb-lint/config.yaml) for the 11 active
groups, or run `/kb-lint --list-groups`.

### Quick start

```
/kb-lint --group competitive                    # Full scan for competitive
/kb-lint --group competitive freshness          # Only check freshness
/kb-lint --group competitive --no-external      # Skip Phase 3 (Perplexity)
/kb-lint --list-groups                          # Print all groups + active flag
```

Output: `outputs/kb-lint-<group>-YYYY-MM-DD.md` — a severity-ranked markdown
report with high/medium/low findings, coverage gaps, and run statistics.
kb-lint does **not** publish to Notion.

To diff new raw sources against canon and stage findings in Notion for team
triage, use [`/kb-update`](#kb-update--raw-vs-canon-triage-in-notion) instead.

### Workflow

1. **Run `/kb-lint --group <slug>`** — indexes the group's canon slice,
   launches subagents in parallel, generates a report
2. **Review the report** — act on findings (staleness, contradictions, broken
   refs, coverage gaps) by editing canon in `hxgtm-mcp-server/context/`
3. **Re-run** to confirm fixes — each run is a complete snapshot, so a finding
   re-appears until canon is fixed

### What it checks

- **Freshness** — files past review cadence, stale date claims
- **Consistency** — internal contradictions across canon
- **Structural** — broken cross-references, orphaned files
- **Template compliance** — persona/product/segment templates
- **Coverage gaps** — topics referenced but never defined
- **External verification** (Phase 3, optional) — verifies high-churn factual claims (competitors, execs, market data) against current web data via Perplexity MCP. Auto-skipped if MCP is unavailable.

### Requirements

- **Claude Opus** (multi-phase reasoning across 120+ files)
- **Canon access** — hxgtm-context MCP server OR direct filesystem access to `../hxgtm-mcp-server/context/` (auto-detected)
- **Perplexity MCP** (optional) — enables Phase 3 external verification

See [.claude/skills/kb-lint/README.md](.claude/skills/kb-lint/README.md) for full setup, guardrails, and the complete report format.

---

## kb-update — Raw-vs-canon triage in Notion

Companion to kb-lint. kb-update diffs raw source(s) — one or many — against
a group's canonical KB slice and publishes each finding as a row in the
group's Notion database for async team triage.

On every run kb-update unions **every available input surface**:

- **Chat attachments** — `.md` files dragged into the Claude Code desktop chat
- **URL argument** — an HTTP(S) URL (fetched via `WebFetch`, or Glean for `teams.microsoft.com` URLs)
- **Inline paste** — markdown typed after the command
- **Raw directory** — unprocessed `.md` files in `raw/<slug>/` (rows with `Process? = yes` and blank `Last processed` in `INDEX.md`)

If the union resolves to 1 file, single-source mode runs. If ≥2, batch
mode kicks in: parallel waves of 3 concurrent files (Sonnet comparators
per file), cross-file pairing at synthesis, one publish to Notion. After
a successful publish kb-update stamps `Last processed = <today>` back
into `INDEX.md` for every raw-dir file that contributed. kb-update never
edits raw file bodies.

kb-update owns the Notion write path — kb-lint stays markdown-only.

### Quick start

```
# One-time — you manually create a Notion page titled exactly:
#     KB - Updates Review
# at the teamspace / parent of your choice. The MCP cannot create it there.

# One-time — provision the 11 per-group databases under that landing page
/kb-update --notion-setup

# Then run on whatever inputs you have — any combination works:
/kb-update --group competitive                            # Uses attached files / raw-dir / etc.
/kb-update --group competitive https://example.com/post   # URL + whatever else is unioned in
/kb-update --group competitive --batch .claude/skills/kb-update/fixtures/batch-demo   # Explicit batch path

/kb-update                                  # No --group → AskUserQuestion prompt
/kb-update --list-groups                    # Print all groups + active flag
```

Output: one Notion row per finding in `KB - <Group Label>` (nested under the
`KB - Updates Review` landing page). Each row lands with `Status = Pending Review`
and the team walks it through Pending Review → Approved → Rejected → Integrated.

### Workflow

1. **Provide input** — drag `.md` files into the chat, pass an HTTP(S) URL on the command line, paste markdown inline, drop files into `raw/<slug>/` with a `Process? = yes` INDEX.md row, or any combination of these
2. **Run `/kb-update --group <slug>`** — the skill unions all available surfaces, diffs against the group's in-scope canon, and publishes findings (single-source mode for 1 input, batch mode with parallel waves of 3 for ≥2)
3. **Triage in Notion** — filter the group's database by `Date Added = today` to see the new findings, tag yourself in `Reviewer`, set `Status`

URL, attachment, and inline inputs are ephemeral — they're materialised to
`/tmp/kb-update-raw/<run-id>/` and never persisted. Raw-dir files are
left where they are; only their INDEX.md `Last processed` cell is updated.

### Requirements

- **Claude Code desktop** — only required for the attachment input surface. URL / inline / raw-dir inputs work in the CLI too.
- **Claude Opus (1M context)** — orchestrator. Comparator subagents run on Sonnet by default.
- **Notion MCP connector** — discovering the landing page + publishing findings
- **Canon access** — hxgtm-context MCP server OR direct filesystem access to `../hxgtm-mcp-server/context/` (auto-detected)
- **Python 3** on PATH — stdlib-only; no `pip install` needed
- **Glean MCP** (optional) — only required when the input is a `teams.microsoft.com` URL

See [.claude/skills/kb-update/README.md](.claude/skills/kb-update/README.md) for the full Notion setup, data-source-resolution rules, triage workflow, and the 21-column database schema (12 visible + 9 hidden; default view grouped by `Review Bucket`).

---

## kb-integrate — Apply approved Notion rows back to canon

kb-integrate closes the kb-update loop. After the team triages rows in
Notion (`Pending Review → Approved`), kb-integrate reads every Approved
row for a group, applies each row's `Proposed Updated Text` to the referenced
canon file in `hxgtm-mcp-server/context/`, and flips the row to `Integrated`.

Interactive by default — computes the plan, prints a compact summary, and
prompts once (`[a]pply / [p]review full / [c]ancel`) before writing.
`--plan` is a pure dry-run (CI / preview-only, no prompt, no writes).
`--apply` (or its alias `--no-confirm`) writes immediately without
prompting (CI / automated). The user reviews `git diff` in
`hxgtm-mcp-server` and commits manually —
**kb-integrate never git-commits and never pushes.**

### Quick start

```
/kb-integrate --group competitive            # Interactive: plan → prompt → apply if confirmed
/kb-integrate --group competitive --plan     # Pure dry-run preview (no prompt, no writes)
/kb-integrate --group competitive --apply    # Non-interactive write (no prompt)
/kb-integrate --list-groups                  # Print all groups + active flag
```

### Workflow

1. **Run interactively** — `/kb-integrate --group <slug>` reads Approved rows, computes the edit plan, and prompts once before writing. Pick `p` to see full before/after snippets, `a` to apply, `c` to cancel.
2. **Or dry-run first** — `--plan` prints the plan with no prompt and no writes; good for CI or when you just want to eyeball what's queued up.
3. **Apply** — either confirm the interactive prompt or re-run with `--apply`. Canon files are edited in place and each successfully-applied row is flipped to `Status = Integrated` in Notion.
4. **Review `git diff`** in `hxgtm-mcp-server` and commit yourself

Failed and skipped rows stay `Approved` for retry. kb-integrate reuses
`.claude/skills/kb-update/config.yaml` as its single source of truth for groups and
`notion_data_source_id` — there is no separate kb-integrate config.

### Requirements

- **Claude Opus**
- **Notion MCP connector** — `notion-fetch` to read the database, `notion-update-page` to flip Status after apply
- **Filesystem access to `hxgtm-mcp-server/context/`** — MCP-read-only mode is **not** sufficient; kb-integrate writes files. Resolution order: `--mcp-server-path` CLI arg → `HXGTM_MCP_SERVER_PATH` env var → `../hxgtm-mcp-server/`
- **Python 3** on PATH — stdlib-only

See [.claude/skills/kb-integrate/README.md](.claude/skills/kb-integrate/README.md) for dry-run vs apply semantics, retry behaviour, and the full workflow.

---

## context-lint — Context wiring audit

Audits the structural wiring between the MCP server (`src/context.ts`),
plugin SKILL.md files, their fallback manifests
(`plugins/*/context/mcp-fallback.md`), and the user-facing Notion
`Agents & Skills` page. Catches missing files, orphan context, drifted
fallbacks, duplicate loads in skill chains, bloated skill context, foundation
coverage gaps, and documentation drift. Produces a severity-ranked markdown
report.

### Quick start

```
/context-lint                       # Full audit, all 10 checks
/context-lint --checks=1,2,3        # Run a subset of checks
/context-lint --no-notion           # Skip Check #10 (Notion drift)
/context-lint --threshold=2000      # Override Check #8 size threshold
```

Output: `outputs/context-lint-YYYY-MM-DD.md`

### Workflow

1. Auto-detect MCP server source (`Projects/MCP/` → `../hxgtm-mcp-server/`),
   plugins source (`Projects/Plugins/plugins/` → `../hx-plugins/plugins/`),
   and Notion MCP availability
2. **Phase 1 — Index & parse** (inline) — parse `src/context.ts`, walk the
   context tree, parse plugin `SKILL.md` files and `mcp-fallback.md`
   manifests, fetch the Notion page (if enabled)
3. **Phase 2 — Audit** (parallel subagents) — Server Inspector, Plugin
   Inspector, and (conditionally) Notion Comparator
4. **Phase 3 — Synthesize report** — merge findings, build per-skill
   breakdown, group actionable fixes, save the report

### What it checks

- **Pack integrity** — every file referenced in `SKILL_CONTEXTS`,
  `CONTEXT_PACKS`, `GUIDANCE_MAP`, and `mcp-fallback.md` exists on disk
- **Orphan files** — every `context/**/*.md` is referenced ≥1 place
- **Orphan packs** — every `CONTEXT_PACK` is used by ≥1 skill
- **Fallback-to-server sync** — `mcp-fallback.md` matches resolved
  `SKILL_CONTEXTS`
- **Cross-skill chain duplication** — chained skills not double-loading the
  same files (e.g. `ads → polish`)
- **Unconditional bulk loading** — persona packs loading all variants when
  only one is used
- **Parallelism opportunities** — sequential MCP calls that could batch
- **Context size profiling** — skills exceeding the line-count threshold
  (default 1500)
- **Foundation coverage** — audience ↔ messaging ↔ persona file wiring
- **Notion documentation drift** (optional) — semantic comparison gated by a
  temporal pre-filter

### Requirements

- **MCP server source** — `Projects/MCP/` (production) OR
  `../hxgtm-mcp-server/` (local fallback) — auto-detected. Hard requirement.
- **Plugins source** — `Projects/Plugins/plugins/` (production) OR
  `../hx-plugins/plugins/` (local fallback) — auto-detected. Hard requirement.
- **Notion MCP** — *optional*. Enables Check #10 documentation drift.
  **Non-blocking** — if Notion MCP is unavailable, the user passes
  `--no-notion`, the page can't be found, or the fetch fails, the lint runs
  to completion and the skip is acknowledged in the pre-flight summary,
  executive summary, and Statistics section.
- **Bash + Glob + Read** — for `git log` mtime lookups and filesystem walks.

See [.claude/skills/context-lint/README.md](.claude/skills/context-lint/README.md) for the
full check catalogue, source resolution rules, subagent breakdown, and report
format.

---

## generate-dossier — Account research dossier (single or batch)

Generates a 6-section research report per target insurance company, drawing on
Salesforce, Gong, and the public web. Accounts run in parallel waves of 3; a
single-account run is just a 1-account wave. The skill is resumable via
`_batch-state.json`.

### Generate a single dossier

In Claude Code, run:

```
/generate-dossier "Zurich North America"
```

This uses the same batch skill with a 1-account wave — it checks which MCP tools are available (Notion and local `hxgtm-mcp-server` are required — generation is blocked if either is missing), shows a single Proceed/Cancel gate, runs all 5 section subagents in parallel, generates Section 6 inline, saves to the local MCP server's `context/accounts/`, and publishes to Notion.

### Generate dossiers in bulk

```
/generate-dossier "Zurich North America" "The Hartford" "AXA XL"
/generate-dossier --file inputs/batch-accounts.txt
```

Accounts process in parallel waves of 3 (15 concurrent section subagents per wave). Each dossier is auto-published to Notion and copied to `hxgtm-mcp-server/context/accounts/` — no per-account confirmation prompts. Per-account publish/save failures are logged to `_batch-errors.md` and the account is marked `partial`; the batch never stops mid-wave.

Outputs land in `outputs/generate-dossier/`, copies go to `hxgtm-mcp-server/context/accounts/`, and each account gets a Notion page in the `337802db20a6806f8fdbfe480adc0e4b` database. Both Notion publishing and the local MCP server path are required — the batch will hard-stop at pre-flight if either is unreachable.

### Dossier sections

1. **Account Overview** — company profile from Salesforce
2. **Vision, Mission & Strategic Priorities** — web research + hx alignment
3. **Who's Who** — top 20 key executives
4. **Past Opportunities & Interactions** — commercial history from Salesforce + Gong
5. **What People Are Saying** — public commentary across 10 strategic themes
6. **Discovery Questions** — 3–5 research-informed questions generated inline from Sections 2 + 5

### Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI or IDE extension
- Perplexity Sonar API (optional, preferred) — `PERPLEXITY_API_KEY` + `requests`
- Perplexity MCP (optional fallback)
- Web search and fetch access — built-in Anthropic tools, always available as final fallback (Sections 2, 3, 5)
- Glean MCP with Salesforce + Gong access (Sections 1, 3, 4 — optional, falls back to placeholders)
- **Notion publishing (required)** — either `NOTION_API_KEY` / `NOTION_TOKEN` (preferred, direct REST) or Notion MCP connector
- **Local `hxgtm-mcp-server` clone with write access (required)** — via `HXGTM_MCP_SERVER_PATH` or `../hxgtm-mcp-server`
