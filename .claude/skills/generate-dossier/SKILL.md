---
name: generate-dossier
template_version: "1.0"
argument-hint: "[account names...] | --file <path>"
description: >
  Generate one or more comprehensive Account Dossiers for target insurance
  companies. Handles 1-account or N-account runs identically — a
  single-account invocation is just a 1-account batch wave. For each
  account, launches 5 parallel section subagents plus dependent synthesis
  phases, assembles a dossier with 6 core sections plus a conditional
  "Why Anything" section, copies it to hxgtm-mcp-server/context/accounts/,
  and publishes it to Notion. Accounts run in parallel waves of 3.
  Resumable via _batch-state.json.
---

## Usage

```
/generate-dossier "Account Name"
/generate-dossier "Account A" "Account B" "Account C"
/generate-dossier --file inputs/batch-accounts.txt
```

Accounts: $ARGUMENTS

`$ARGUMENTS` is one of:
- A single quoted account name (1-account batch wave)
- Space-separated account names, each quoted (e.g., `"Zurich North America" "The Hartford" "AXA XL"`)
- A flag `--file <path>` pointing to a text file with one account name per line

The skill is near-non-interactive: a single Proceed/Cancel gate runs once
at the end of pre-flight, then the per-account loop runs without prompts.
The batch auto-resumes on rerun by skipping accounts already marked `done`
in `_batch-state.json`.

# Account Dossier — Batch (Parallel)

## What this skill does

Given a list of one or more target insurance companies, this skill produces a
comprehensive Account Dossier per account and writes it to three destinations
(local `outputs/`, local `hxgtm-mcp-server/context/accounts/`, and Notion).

Each dossier contains 6 baseline sections, plus 1 conditional section:

1. **Account Overview** — Company profile and key metrics from Salesforce
2. **Vision, Mission & Potential Sales Plays** — Public strategy translated into
   source-grounded potential sales plays
3. **Potential Champions and Influencers** — Top 10–20 stakeholders ranked into
   economic sponsors, technical users, and influencers, with a Databricks-sourced
   "already in our orbit" overlay
4. **Past Opportunities & Interactions** — Commercial history from Salesforce and Gong
5. **What People Are Saying on Topics We Care About** — Public commentary across 10 strategic themes
6. **Discovery Questions You Might Consider Asking** — 3–5 research-informed questions tailored to the account's strategic context
7. **Why Anything** — Conditional cost-of-inaction table generated only when the
   highest open opportunity is at Stage 3 or later

All dossier sections are produced by subagents per account. Each subagent
reads a section-specific prompt from `references/`, **writes its section
markdown directly to a per-section file via the `Write` tool**, and returns
only a short status string (≤300 chars) to the orchestrator. The orchestrator
never holds full section content in working memory — it concatenates the
per-section files via `cat` to assemble the final dossier.

Sections 1–5 run in parallel (Phase 1). Section 6 (Discovery Questions) runs
in Phase 2 after Sections 2 and 5 are on disk. Section 7 (Why Anything) runs
in Phase 3, conditionally, after Phase 2 once the orchestrator parses the
deal-stage comment from Section 4.

Accounts run in parallel **waves of 3**. Each account uses 6 baseline
subagents plus an optional Section 7 subagent. Phase 1 of a full wave launches
15 concurrent subagents (3 accounts × 5 sections). Phase 2 launches 3
(3 accounts × Section 6). Phase 3 launches up to 3 conditional Section 7
subagents. The skill is resumable via `_batch-state.json`: rerunning the same
slash command skips `done` accounts and retries `partial` / `failed` /
`running` accounts.

This per-section-file design is deliberate — it prevents the orchestrator
from ever generating a >2KB single tool-call payload, which is what trips
Claude Code's stream-idle timeout when the dossier is assembled.

A single-account invocation is just a 1-account wave — the loop, pre-flight
gate, and resume logic all still apply.

## Requirements

- **Web research tool chain** (used in Sections 2, 3, 5) — tiered, tried in order:
  1. **Perplexity Sonar API** (preferred) — invoked via
     `python3 .claude/skills/generate-dossier/scripts/perplexity-sonar.py`. Requires
     `PERPLEXITY_API_KEY` env var and the `requests` Python package. If the env
     var or package is missing, the script exits non-zero and the subagent
     drops to tier 2.
  2. **Perplexity MCP** (optional) — server `project-0-gtmos-perplexity` or
     any MCP tool whose name contains "perplexity". On failure, drops to tier 3.
  3. **Built-in `WebSearch` + `WebFetch`** — Anthropic-native, always available.
     Final fallback so Sections 2, 3, 5 can still run if both Perplexity tiers
     are down.
- **Databricks MCP** (optional) — Sections 1 and 4 use Databricks for
  Salesforce/Gong data; Section 3 uses Databricks to overlay Salesforce/Gong
  contact evidence on the public-web stakeholder list and surface any
  Databricks-sourced contacts already in hx's orbit who clear the
  seniority/relevance bar. If unavailable, Sections 1 and 4 produce structured
  placeholders and Section 3 emits a clear `databricks_available: false` note
  instead of blank relationship columns.
- **Notion publishing** (**required**) — each account is published to the
  `337802db20a6806f8fdbfe480adc0e4b` database. Two transports are supported;
  the first available one is used:
  1. **Direct Notion REST API** (preferred) — `NOTION_API_KEY` (or
     `NOTION_TOKEN`) env var set and non-empty. The batch script handles the
     full create_page + append sequence itself via `--publish`, bypassing the
     MCP serializer entirely. Faster and not subject to the ~4.8KB per-call
     stringification limit.
  2. **Notion MCP** (fallback) — `notion-create-pages` tool available. Uses
     the multi-payload publish loop described in Step 6.

  Missing **both** transports is a pre-flight hard stop. A *per-account*
  publish failure during the batch is logged and the account is marked
  `partial` — the batch continues.
- **Local `hxgtm-mcp-server` clone with write access** (**required**) — resolved
  via `HXGTM_MCP_SERVER_PATH` env or `../hxgtm-mcp-server`. Each dossier is
  copied to `$HXGTM_MCP_SERVER_PATH/context/accounts/[slug]-dossier.md`.
  Missing path is a pre-flight hard stop. A *per-account* copy failure is
  logged and the account is marked `partial`.
- **Git + `hxgtm-mcp-server` repo URL** (optional) — additionally cloned at
  `/tmp/hxgtm-mcp-server-clone/` for read-side hx capability, persona,
  positioning, and discovery-question context (Sections 2, 3, 6, and 7).
  Fallbacks: WebFetch of `hyperexponential.com` then hardcoded capability
  strengths. On local runs this clone is redundant with `HXGTM_MCP_SERVER_PATH`
  but harmless.
- **Bash tool** — for git clone, file copies, and atomic writes.
- **Claude Opus** recommended for the orchestrator; section subagents are
  pinned to Sonnet (see Step 3c).

Pre-flight hard stops only apply if (a) neither Notion transport is
available or (b) the local hxgtm-mcp-server path is missing. Once the batch
loop is running, no per-account issue stops the batch — publish/save
failures are logged and the account is marked `partial`.

**Related:** To query an existing dossier in Notion with read-only Q&A, use
the `ask-dossier` skill (`skills/ask-dossier/SKILL.md`).

## Configuration

| Setting | Value |
|---|---|
| Output directory | `outputs/generate-dossier/` |
| Per-section staging files | `outputs/generate-dossier/[slug]-section-N.md` for baseline `N` in `1..6`, plus optional `7` when the stage gate is met |
| Final dossier file | `outputs/generate-dossier/[slug]-dossier.md` (written via bash `cat`, never via the orchestrator's `Write` tool) |
| Batch state file | `outputs/generate-dossier/_batch-state.json` |
| Error log | `outputs/generate-dossier/_batch-errors.md` |
| Summary report | `outputs/generate-dossier/_batch-summary.md` |
| hxgtm-mcp-server clone location (read) | `/tmp/hxgtm-mcp-server-clone/` |
| hxgtm-mcp-server repo URL (for the clone) | env `HXGTM_MCP_SERVER_REPO_URL` (default: `git@github.com:hx-gtm/hxgtm-mcp-server.git`) |
| hxgtm-mcp-server local path (write) | env `HXGTM_MCP_SERVER_PATH` OR `../hxgtm-mcp-server` (resolved during Step 1) |
| Notion database URL | `https://www.notion.so/hyperexponential/337802db20a6806f8fdbfe480adc0e4b?v=337802db20a68183877e000c4dca331b` |
| Notion database ID | `337802db20a6806f8fdbfe480adc0e4b` |
| Notion parser script | `.claude/skills/generate-dossier/scripts/save-dossier-to-notion.py` |
| Template version | Read at runtime from this skill's frontmatter `template_version` (currently `1.0`) and stamped on every Notion page in the `Template Version` text property. To bump, change the frontmatter only. |
| Batch concurrency | `3` accounts per wave. Each account uses 6 baseline subagents plus optional Section 7. Phase 1 launches 15 concurrent subagents (Sections 1–5 across 3 accounts); Phase 2 launches 3 (Section 6); Phase 3 launches up to 3 conditional Section 7 subagents. |
| Per-subagent soft timeout | 8 minutes |
| Rate-limit retry | 3 attempts, 30s backoff |
| Subagent model | `sonnet` (pinned on every Agent call) |

---

## Workflow

### Step 0 — Collect inputs

Parse the account list from the slash command. Accept either:

- Space-separated quoted args: `"Zurich North America" "The Hartford" "AXA XL"`
- File path flag: `--file inputs/batch-accounts.txt` (one account per line; blanks and `#`-prefixed lines ignored)
- A single account name (treated as a 1-account batch wave)

For each account name, derive a kebab-case slug (e.g., `"Zurich North America"` → `zurich-north-america`). If the list is empty, stop.

### Step 0.5 — Clone hxgtm-mcp-server for reads (best-effort, one-shot)

```bash
REPO_URL="${HXGTM_MCP_SERVER_REPO_URL:-git@github.com:hx-gtm/hxgtm-mcp-server.git}"
CLONE_PATH="/tmp/hxgtm-mcp-server-clone"
rm -rf "$CLONE_PATH"
git clone --depth 1 "$REPO_URL" "$CLONE_PATH"
```

- On success (and `$CLONE_PATH/context/` exists): set `hx_context_path = /tmp/hxgtm-mcp-server-clone`.
- On failure: set `hx_context_path = ""`. Sections that rely on local hx context
  (2, 3, 6, and 7) fall back to whatever hx-owned web context or reduced
  local context is still available.

Never fatal. This clone is used for **reads only** (persona, positioning,
product, and discovery-question context). Writes go to the resolved
`HXGTM_MCP_SERVER_PATH` in Step 1.

### Step 1 — Pre-flight status report (non-interactive)

Check which connectors are live and print a status table. **Do not gate on
operator input.** The whole batch runs autonomously: pre-flight either passes
(record the connector flags and continue to Step 2) or hits a hard stop (one
of the two required-connector failures below) and exits with an actionable
error message. There is **no `AskUserQuestion` step** anywhere in this skill.

Detection:
- **Perplexity Sonar API**: all of (a) `PERPLEXITY_API_KEY` env var is set and non-empty, (b) helper script exists at `.claude/skills/generate-dossier/scripts/perplexity-sonar.py`, (c) `python3 -c "import requests"` exits 0. If (c) fails but (a) and (b) pass, attempt a one-shot best-effort install: `python3 -m pip install --quiet requests` (or `pip3 install --quiet requests`); re-run the import check. If still failing, mark Sonar unavailable. Record the **exact reason** (which of a/b/c failed) for the printout below.
- **Perplexity MCP**: server `project-0-gtmos-perplexity` OR any tool name containing "perplexity".
- **WebSearch / WebFetch**: always available (built-in Anthropic tools).
- **Databricks MCP**: any MCP server whose name contains "databricks" OR any tool name containing "databricks", "sql", or "warehouse". (Exact server id to be confirmed on the first real run — match broadly, prefer server-name detection.)
- **Notion API key**: `NOTION_API_KEY` env var set and non-empty, else `NOTION_TOKEN` set and non-empty. If either is present, record `notion_mode = "api"` and skip MCP detection for gating purposes.
- **Notion MCP**: look for `notion-create-pages` (or any tool with "notion" in the name). If no API key was found but MCP is present, record `notion_mode = "mcp"`.
- **hxgtm-mcp-server local path (write)**: try `$HXGTM_MCP_SERVER_PATH` first, else `../hxgtm-mcp-server`. Must contain a `context/` subdirectory and be writable. Record the resolved **absolute** path.
- **hxgtm-mcp-server clone (read)**: success from Step 0.5.

Implementation note for Cursor environments: an MCP server's name (for example,
one containing `databricks`) is the reliable identifier, while its tool names may
be generic (`query`, `run_sql`, `list_tables`) and not include "databricks".
Prefer server-name detection first, then fall back to tool-name matching.

Print the table **verbatim** (do not paraphrase the impact text and do not omit rows — every row below must appear, even those marked ✗):

```
Pre-flight status:

| Connector                   | Status | Impact if unavailable                                        |
|-----------------------------|--------|--------------------------------------------------------------|
| Perplexity Sonar API        | ✓/✗    | Primary web-research tier; cascade to MCP then WebSearch     |
| Perplexity MCP              | ✓/✗    | Secondary web-research tier; cascade to WebSearch            |
| WebSearch / WebFetch        | ✓      | Final fallback — always on. Required so Sections 2, 3, 5 can still run if both Perplexity tiers fail |
| Databricks MCP              | ✓/✗    | Sections 1, 4 → placeholders; S3 emits no-overlay note       |
| Notion API key              | ✓/✗    | Preferred Notion transport (direct REST). Skipped if ✗ and MCP is ✓ |
| Notion MCP                  | ✓/✗    | Fallback Notion transport. Used only if API key is ✗         |
| Notion publishing           | ✓/✗    | ⛔ REQUIRED — pre-flight hard stop if BOTH API key and MCP are ✗ |
| hxgtm-mcp-server local path | ✓/✗    | ⛔ REQUIRED — pre-flight hard stop if ✗                       |
| hxgtm-mcp-server clone      | ✓/✗    | Sections 2, 3, 6, 7 use reduced local context / fallbacks    |
```

Immediately under the table, print these lines (always, even when everything is ✓):

```
Perplexity tier selected: sonar | mcp | websearch-only
Sonar reason (only if ✗): <PERPLEXITY_API_KEY missing | helper script missing | requests package not importable>
Notion mode: api | mcp
```

`Perplexity tier selected` is the highest-tier path that's currently green: `sonar` if Sonar API is ✓, else `mcp` if Perplexity MCP is ✓, else `websearch-only`. The `Sonar reason` line is omitted when Sonar is ✓; when Sonar is ✗ it is **required** and must name which of the three detection conditions failed.

**Hard-stop conditions (the only two reasons pre-flight terminates):**

1. Neither Notion transport is available (no `NOTION_API_KEY`/`NOTION_TOKEN`
   AND no Notion MCP).
2. The local `hxgtm-mcp-server` path (`$HXGTM_MCP_SERVER_PATH` or
   `../hxgtm-mcp-server`) does not exist or is not writable.

If either fires, print an actionable error message naming what's missing and
how to fix it (e.g., `export NOTION_API_KEY=...` or connect the Notion MCP
server, or `export HXGTM_MCP_SERVER_PATH=/absolute/path`), then exit. Do NOT
ask the user anything — just stop.

If neither hard stop fires, also print a summary of what's about to run:

```
About to process N account(s):
  1. [Account name A]
  2. [Account name B]
  ...

Output directory: outputs/generate-dossier/
MCP server write path: [resolved absolute path]/context/accounts/
Notion database: 337802db20a6806f8fdbfe480adc0e4b
Resume: K account(s) already done, will be skipped.

Proceeding (autonomous mode — no confirmation required).
```

Also extract the template version from this skill's own frontmatter and
record it for use during Notion publish:

```bash
TEMPLATE_VERSION=$(awk '
  /^---$/ { f++; next }
  f==1 && /^template_version:/ {
    sub(/^template_version:[[:space:]]*/, "")
    gsub(/"/, "")
    print
    exit
  }
' .claude/skills/generate-dossier/SKILL.md)
```

If the value is empty (frontmatter missing or malformed), fall back to
`"1.0"` and log a warning row to `_batch-errors.md` — never hard-stop on
this; the version stamp is metadata, not a gating concern.

Then record `sonar_available`, `perplexity_available`, `databricks_available`,
`hx_context_path`, `notion_available`, `notion_mode` (`"api"` or `"mcp"`),
`mcp_server_path`, `template_version` and continue **directly** to Step 2.
`WebSearch` / `WebFetch` are always assumed available and do not need a
recorded flag.

**Do NOT use `AskUserQuestion`. Do NOT ask the operator to type "Proceed"
or "Cancel" in chat as a fallback.** This skill is designed to run
autonomously — operator approval is built into invoking the slash command,
not into a mid-skill prompt. The only valid reasons to stop are the two
hard-stop conditions above.

This non-interactive design applies once at start and never again — not
between accounts, not on errors, not on resume of already-pending accounts.

### Step 2 — Load batch state and filter

Ensure `outputs/generate-dossier/` exists (`mkdir -p`).

Check for `_batch-state.json`:
- **Exists**: for each input account, skip if `done`; reset to `pending` if `partial`, `failed`, or `running`; add as `pending` if absent.
- **Missing**: initialize fresh state with all accounts `pending`.

State schema:

```json
{
  "started_at": "2026-04-15T10:00:00Z",
  "last_updated_at": "2026-04-15T10:00:00Z",
  "accounts": {
    "zurich-north-america": {
      "name": "Zurich North America",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "sections_complete": 0,
      "sections_total": 6,
      "mcp_server_saved": false,
      "notion_url": null,
      "error": null,
      "issues": []
    }
  }
}
```

Treat `sections_total` as informational only. It represents the baseline
required sections (`1..6`). Completion logic must inspect the actual section
files on disk and the conditional Section 7 stage gate rather than relying on a
fixed integer.

Report: `N accounts in queue (M done, skipped). Processing K remaining.`

### Step 3 — Wave-based parallel account loop

Process accounts in waves of **3**. Each account uses 6 baseline subagents plus
an optional Section 7 subagent. **Phase 1** of a wave launches Sections 1–5 in
parallel (15 concurrent across 3 accounts). **Phase 2** launches Section 6 once
Sections 2 and 5 are written to disk. **Phase 3** conditionally launches
Section 7 once the deal-stage comment can be parsed from Section 4.

Repeat until no `pending` accounts remain:

#### 3a. Build the wave

Take up to **3** next `pending` accounts in list order. If fewer remain, take
what's left. This set is the current wave.

#### 3b. Mark the whole wave running

For every account in the wave, set `status = running` and `started_at = <now>`.
**One atomic state write for the whole wave** — not one write per account.

#### 3c. Phase 1 — launch Sections 1–5 in a single parallel Agent call

In ONE Agent tool message, launch `wave_size × 5` subagents — one per
(account, section) pair for sections 1–5. **Set `model: "sonnet"` on every
Agent call** so section subagents run on Sonnet regardless of the
orchestrator's model. They all run concurrently. When the results come back,
the `tool_use_id` → request mapping tells you which subagent belonged to
which (account, section), so you can route the **status strings** (not
section content — see below) correctly.

**Subagent assignments (per account):**

| Subagent | Reference file | Description |
|---|---|---|
| Section 1 | `.claude/skills/generate-dossier/references/section-1-overview.md` | Account Overview (Salesforce via Databricks) |
| Section 2 | `.claude/skills/generate-dossier/references/section-2-strategic.md` | Vision/Mission + Potential Sales Plays (web research + context loading) |
| Section 3 | `.claude/skills/generate-dossier/references/section-3-whos-who.md` | Potential Champions and Influencers (web research + Databricks cross-ref) |
| Section 4 | `.claude/skills/generate-dossier/references/section-4-opportunities.md` | Past Opportunities & Interactions (Salesforce/Gong via Databricks) |
| Section 5 | `.claude/skills/generate-dossier/references/section-5-themes.md` | What People Are Saying (web research) |

Each subagent:
- Receives the account name and its absolute `section_output_path`.
- Reads its section-specific prompt.
- **Writes its full section markdown to `section_output_path` via the Write
  tool.**
- Returns ONLY a short status string (≤300 chars) to the orchestrator —
  never the section content. See each reference file's "Status Return Schema"
  for the exact format.
- Runs without user interaction (no AskUserQuestion).

**Why the file-write pattern:** if subagents returned the full markdown as
their Agent response, the orchestrator would have to hold 5 large strings in
working memory and emit them in subsequent tool calls — which trips
stream-idle timeouts in Claude Code. By writing each section to disk and
returning only a status, the orchestrator's heaviest turn is bounded by the
size of 15 short status strings, which is ~5KB total.

**Section 2 note:** This subagent uses the same two-phase methodology as the
find-strategic-priorities CoWork skill. Phase 1 produces four research tables
(Vision/Mission, Strategic Pillars, What They're Saying about Topics of Interest,
Direct Quotes from People who Matter) written to a scratch file. Phase 2 re-renders
those four tables into the final section file, followed by three to five Potential
Sales Play blocks. It reads `section-2-phase-1.md` and `section-2-phase-2.md`,
plus hx truth files, persona guides, marketing strategy, anti-AI guardrails, and
the discovery question bank via `{{hx_context_path}}`.

**Section 3 note:** This subagent loads buyer/user persona context from
`{{hx_context_path}}/context/truth/audiences/*.md` and
`{{hx_context_path}}/context/marketing/persona-guides/*.md`. After building
the public-web stakeholder list, it executes two Databricks queries when
`databricks_available: true`: (1) list all Salesforce contacts at the account to
surface Databricks-sourced contacts, and (2) run a per-name cross-reference for
each public-web stakeholder. Output is three tiered blocks plus an
`Already in our orbit` overflow block. The total list is capped at 10–20
**Potential Champions and Influencers**: anyone below the seniority bar
(Director-equivalent or higher) is dropped unless they have active deal
engagement (recent Gong calls, Coach OCR, or open Opportunity Contact Role).
CIO goes in Tier 3.

**How to launch each subagent:**

For each (account, section) pair in the wave:

1. Read the corresponding reference file from
   `.claude/skills/generate-dossier/references/`.
2. Replace `{{account_name}}` with the actual account name.
3. Replace `{{section_output_path}}` with the absolute path
   `outputs/generate-dossier/[slug]-section-N.md` (substitute
   the account slug and section number, then expand to an absolute path).
4. Replace `{{hx_context_path}}` with the clone path from Step 0.5 (empty
   string if clone failed — the reference files' fallback language handles
   that).
5. Prepend the **Tool-guidance block** below to the prompt.
6. For Section 3 only, include a line `databricks_available: true` (or `false`) in
   the prompt body.
7. Launch the Agent with `subagent_type: "general-purpose"` and
   `model: "sonnet"`.

**Tool-guidance block** (prepended to every subagent prompt):

```
## Environment notes (batch runner)

- Web research tool chain — try these tiers in order, only drop down on failure:

  1. **Perplexity Sonar API** — invoke via Bash:
     ```
     python3 .claude/skills/generate-dossier/scripts/perplexity-sonar.py \
       --query "<your research query>"
     ```
     Optional flags: `--recency month|week|day|year`, `--model sonar-pro`.
     Success → parse stdout JSON (`response` + `citations`). Non-zero exit →
     cascade to tier 2.
  2. **Perplexity MCP** — tools on server `project-0-gtmos-perplexity` or any
     tool whose name contains "perplexity". On failure → cascade to tier 3.
  3. **Built-in `WebSearch` + `WebFetch`** — always available. Prefer
     `WebSearch` to discover primary sources (annual reports, IR pages, press
     releases) and `WebFetch` to retrieve their contents. Either tool can be
     used directly if that split isn't useful for a particular query.

- Do not stall a section because one tier is down. The goal is the content;
  the transport is interchangeable.
- Rate limits / transient errors: sleep ~30 seconds and retry the same tier up
  to 3 times before dropping to the next tier. If all three tiers fail for a
  query, move on with what you have rather than stalling the section.
- Soft time budget: aim to complete within 8 minutes. If budget is spent and
  a topic still lacks coverage, return what you have with "Not found in
  primary sources" for missing cells rather than continuing to dig.
- Section 3 only: the orchestrator will pass `databricks_available: true|false`.
  Only attempt the Databricks cross-reference step when true.
- **Output handling (CRITICAL):** Write your full section markdown to
  `{{section_output_path}}` via the **Write tool**. Do NOT use bash heredoc
  or echo redirection. Do NOT echo the section markdown anywhere in your
  response — return ONLY the short status string defined in your reference
  file's "Status Return Schema" (≤300 chars). The orchestrator never reads
  the section content from your response; it reads the file you wrote.
  Echoing the markdown back will trip a stream-idle timeout in the parent
  turn.
```

#### 3d. Dependent phases after Phase 1

After Phase 1 returns, run the dependent phases in this order:

1. Phase 2 — Section 6
2. Phase 3 — Section 7 (conditional)

Each phase uses the same file-write pattern as Phase 1: subagents write their
full markdown directly to disk and return only short status strings.

##### 3d.i. Phase 2 — launch Section 6 subagents in a single parallel Agent call

Launch one Section 6 subagent per account in the wave — **all in a single
parallel Agent call**, `wave_size × 1` subagents. Each subagent reads its
account's Section 2 and Section 5 files from disk, generates 3–5 discovery
questions, and writes the result to its own file.

**Subagent assignment:**

| Subagent | Reference file | Description |
|---|---|---|
| Section 6 | `.claude/skills/generate-dossier/references/section-6-discovery.md` | Discovery Questions (reads Sections 2 & 5 from disk + question bank + product-marketing context) |

**How to launch:**

For each account in the wave:

1. Read `.claude/skills/generate-dossier/references/section-6-discovery.md`.
2. Replace `{{account_name}}` with the account name.
3. Replace `{{section_2_path}}` with the absolute path
   `outputs/generate-dossier/[slug]-section-2.md`.
4. Replace `{{section_5_path}}` with the absolute path
   `outputs/generate-dossier/[slug]-section-5.md`.
5. Replace `{{section_6_output_path}}` with the absolute path
   `outputs/generate-dossier/[slug]-section-6.md`.
6. Replace `{{hx_context_path}}` with the clone path from Step 0.5 (empty
   string if clone failed).
7. Prepend the Tool-guidance block from 3c.
8. Launch the Agent with `subagent_type: "general-purpose"` and
   `model: "sonnet"`.

**Skip-section-6 conditions:** If an account's Section 2 file is missing OR
Section 5 file is missing, do not launch Section 6 for that account. The
orchestrator will substitute the standard placeholder text in 3e.i.

##### 3d.ii. Phase 3 — conditionally launch Section 7 subagents

After Phase 2 returns, inspect the first line of each account's Section 4 file
to determine the stage gate for Section 7.

The orchestrator expects Section 4 to have already normalized any Salesforce
stage-name label (for example, `Prospecting`, `Needs Analysis (SQO)`, `Proof`,
or `Closed Won`) into the integer stored in the HTML comment.

Use this parsing pattern:

```bash
DEAL_STAGE=$(head -1 "$OUT_DIR/${SLUG}-section-4.md" \
  | grep -oP '(?<=deal-stage: )\d')
```

Rules:

- If the comment is absent, unreadable, or Section 4 is missing, treat
  `DEAL_STAGE` as `0`.
- Do not attempt to parse raw Salesforce stage-name prose here; Section 4 owns
  the label-to-integer mapping and must emit the normalized numeric comment.
- If `DEAL_STAGE >= 3`, launch the Section 7 subagent for that account.
- If `DEAL_STAGE < 3`, do not launch Section 7 and record it as intentionally
  omitted at assembly time.

Launch all eligible Section 7 subagents for the wave in a single parallel Agent
call.

**Subagent assignment:**

| Subagent | Reference file | Description |
|---|---|---|
| Section 7 | `.claude/skills/generate-dossier/references/section-7-why-anything.md` | Why Anything (Databricks-only, stage-gated) |

**How to launch when the gate is met:**

For each eligible account:

1. Read `.claude/skills/generate-dossier/references/section-7-why-anything.md`.
2. Replace `{{account_name}}` with the account name.
3. Replace `{{section_7_output_path}}` with the absolute path
   `outputs/generate-dossier/[slug]-section-7.md`.
4. Replace `{{section_1_path}}`, `{{section_2_path}}`, and `{{section_3_path}}`
   with the corresponding absolute section paths.
5. Replace `{{deal_stage}}` with the parsed integer deal stage for that account.
6. Replace `{{hx_context_path}}` with the clone path from Step 0.5 (empty
   string if clone failed).
7. Prepend the Tool-guidance block from 3c.
8. Launch the Agent with `subagent_type: "general-purpose"` and
   `model: "sonnet"`.

Record one of these outcomes per account:

- `Section 7 written: [W] words. Path: [absolute path]. Stage gate: [N] (threshold met).`
- `Section 7 skipped: stage gate not met (deal-stage: [N], threshold: 3).`
- `Section 7 FAILED: [one-line reason]`

#### 3e. Per-account assemble, save, publish

For each account in the wave independently (order doesn't matter — accounts
don't depend on each other), run the following sub-steps in order. The
assembly here is **bash-only** — `cat` of the per-section files written by
the subagents — so the orchestrator never materializes the dossier as a
generated tool-call payload.

##### 3e.i. Verify section files and classify

For each baseline section `N in 1..6`, check for the existence of
`outputs/generate-dossier/[slug]-section-N.md`.

Also check Section 7 conditionally:

- If the Section 7 stage gate was met, inspect
  `outputs/generate-dossier/[slug]-section-7.md`.
- If the stage gate was not met, classify Section 7 as `Omitted` and do **not**
  create a placeholder file.

- File exists and the subagent's status string indicated success →
  classify as `Complete`. Use the file as-is.
- File exists but the status string contained placeholder cells (e.g., `P >
  0` for fields that should have real data, or themes that fell back to
  "Not found in primary sources") → classify as `Placeholder`. Use the
  file as-is.
- File does not exist OR the subagent's status string was
  `Section N FAILED: <reason>` → classify as `Failed`. Write a
  one-line placeholder file at the section's path:
  ```bash
  printf '_[Section %d could not be generated. Please retry or fill in manually.]_\n' N \
    > "outputs/generate-dossier/[slug]-section-N.md"
  ```
  (This keeps the cat in 3e.ii uniform for baseline sections and gated
  sections that were expected to exist.)

Record each section's classification on the account's state record so 3f can
compute the final `done` / `partial` / `failed` status from satisfied sections
rather than a hardcoded count.

##### 3e.ii. Assemble the dossier via bash `cat`

Concatenate the baseline dossier sections into the final dossier file using a
single bash command. The orchestrator emits this command as a normal small
tool call — no large `Write` payload is generated, and no section content
is ever held in working memory.

```bash
SLUG="[account slug]"
ACCOUNT="[Account Name]"
TODAY="$(date -u +%Y-%m-%d)"
QUARTER="[current quarter, e.g., Q2 2026]"
OUT_DIR="outputs/generate-dossier"

{
  printf '# %s\n\n**Generated:** %s | **Quarter:** %s\n\n---\n\n## 1. Account Overview\n\n' \
    "$ACCOUNT" "$TODAY" "$QUARTER"
  cat "$OUT_DIR/${SLUG}-section-1.md"
  printf '\n---\n\n## 2. Vision, Mission & Potential Sales Plays\n\n'
  cat "$OUT_DIR/${SLUG}-section-2.md"
  printf '\n---\n\n## 3. Potential Champions and Influencers\n\n'
  cat "$OUT_DIR/${SLUG}-section-3.md"
  printf '\n---\n\n## 4. Past Opportunities & Interactions\n\n'
  tail -n +2 "$OUT_DIR/${SLUG}-section-4.md"
  printf '\n---\n\n## 5. What People Are Saying on Topics We Care About\n\n'
  cat "$OUT_DIR/${SLUG}-section-5.md"
  printf '\n---\n\n## 6. Discovery Questions You Might Consider Asking\n\n'
  cat "$OUT_DIR/${SLUG}-section-6.md"
  if [ -f "$OUT_DIR/${SLUG}-section-7.md" ]; then
    printf '\n---\n\n## 7. Why Anything (First Draft)\n\n'
    cat "$OUT_DIR/${SLUG}-section-7.md"
  fi
  printf '\n---\n\n*Generated by hx GTM OS — Account Dossier v1*\n'
} > "$OUT_DIR/${SLUG}-dossier.md.tmp" \
  && mv "$OUT_DIR/${SLUG}-dossier.md.tmp" "$OUT_DIR/${SLUG}-dossier.md"
```

The `> tmp && mv` pattern makes the write atomic — no partial file is ever
visible.

**Stream-idle invariant — read carefully.** Do NOT use the `Write` tool to
emit the assembled dossier. Do NOT echo any section content (or the
assembled dossier) in the assistant's user-visible text. The whole point of
the per-section-file design is that the orchestrator's tool-call payloads
during assembly stay tiny — a ~50-line bash command, regardless of dossier
size. Echoing or `Write`-ing the full content is exactly what trips the
stream-idle timeout the design is here to prevent.

If an assembly bash call fails (filesystem error), append a row to
`_batch-errors.md`, mark the account `failed`, and continue.

##### 3e.iii. Save to MCP server

Copy the dossier to `[mcp_server_path]/context/accounts/` so downstream
skills (e.g. `create-initiative-slides`, `ask-dossier`) can discover it.

**Target:** `[mcp_server_path]/context/accounts/[slug]-dossier.md`, where
`mcp_server_path` is the absolute path resolved during Step 1.

1. If `context/accounts/` does not exist at the resolved path: create it via
   `mkdir -p`.
2. Copy the dossier:
   ```bash
   cp outputs/generate-dossier/[slug]-dossier.md \
     [mcp_server_path]/context/accounts/[slug]-dossier.md
   ```
3. **Soft-fail semantics** (batch-mode): on copy failure, append a row to
   `_batch-errors.md`, set `mcp_server_saved = false` on the account
   record, and continue to 3e.iv. Do **not** hard-stop — the account's
   status is finalized in 3f.
4. On success, set `mcp_server_saved = true`.

##### 3e.iv. Extract assignee name

Use a small bash pipeline to read the AE / Owner row from the assembled
dossier — do NOT Read the dossier into the orchestrator's context (the
file is large; the orchestrator has no need for its content).

The Section 1 reference pins the canonical row label to `AE / Owner`,
but subagents occasionally drift to nearby variants (`SF AE / Owner`,
`Salesforce Account Owner / AE`, `Account Owner`, etc.) and sometimes
suffix the value with role annotations (`(Account Owner)`) or
concatenate co-owners with `;` / `,`. The pipeline below tolerates both
kinds of drift: it matches the row by stable tokens (`AE` / `Owner`)
rather than the literal label, and it strips parenthetical annotations
plus everything after the first `;` or `,` to recover a single clean
name. Do not tighten the regex back to a literal label match — keep it
tolerant so a future label rename does not silently break assignee
resolution again.

```bash
ASSIGNEE=$(
  grep -iE '^\| \*\*(SF |Salesforce )?(Account )?(AE|Owner)( ?/ ?(Owner|AE))?\*\*' \
    "outputs/generate-dossier/[slug]-dossier.md" \
    | head -n 1 \
    | awk -F'\\|' 'NF>=4 {print $3}' \
    | sed -E 's/\([^)]*\)//g; s/[;,].*//; s/^[[:space:]]+//; s/[[:space:]]+$//'
)
```

Treat the parsed value as a real name only if all of these hold:

- It is non-empty.
- It does NOT contain `[` brackets (brackets indicate a placeholder such
  as `[Requires Salesforce access via Databricks MCP]`).
- It is not a literal dash/em-dash/`Not found...` string.

If those checks pass, store the value as the assignee name for Step 6.
Otherwise (no row found, bracketed placeholder, dash, or unparseable),
proceed without an assignee — `save-dossier-to-notion.py` already omits
the property when `--assignee` is missing or unresolvable.

##### 3e.v. Publish to Notion

Publish the dossier to the `337802db20a6806f8fdbfe480adc0e4b` Notion
database following **Step 6** below (branches on `notion_mode` — `"api"`
uses the direct-REST `--publish` script call which reads the file from
disk; `"mcp"` uses the multi-payload MCP loop).

- On success, record `notion_url` on the account record.
- On failure, log to `_batch-errors.md`, leave `notion_url = null` (or the
  partial URL if the page was created but appends failed), and continue.
  Never stop the batch.

##### 3e.vi. Self-check (separate orchestrator turn)

**Run this in a fresh orchestrator turn**, after 3e.v completes for the
current account. Splitting it off keeps the assemble+publish turn small
and stream-friendly.

Run through this checklist and record any failures into the account's
`issues` array in `_batch-state.json`. Append matching rows to
`_batch-errors.md` in the wave's error block (3f). **Do NOT print issues
to chat and do NOT block the save/publish** — batch mode never interrupts
for a single account.

For checks that need to inspect dossier content, prefer small bash
commands (`grep`, `head`, `wc -l`) over Read of the full file. The
orchestrator should not pull dossier content into its working memory.

**Output quality:**
- All baseline sections are present in the dossier (Account Overview,
  Potential Sales Plays, Potential Champions and Influencers, Past
  Opportunities, What People Are Saying, Discovery Questions)
- If the Section 7 stage gate was met, `Why Anything` is present after Section 6
- If the Section 7 stage gate was not met, `Why Anything` is absent entirely
- No section is entirely empty or contains only the header with no content
- Placeholder sections (where Databricks was unavailable) are clearly marked as
  placeholders — they should not look like real data
- Discovery questions (Section 6) are specific to this account's research,
  not generic — each question references a named initiative, executive, or
  finding (use `grep` on the section-6 file rather than reading it all)
- The dossier footer `*Generated by hx GTM OS — Account Dossier v1*` is
  present (`tail -n 1` of the dossier file)

**Data accuracy** (sample-checked via `grep`, not full reads):
- Section 1 account name, entity type, and HQ match the intended company
  (not a parent group, subsidiary, or similarly-named competitor)
- Section 3 contacts are employees of this company — not competitors,
  former employees listed elsewhere, or hallucinated names
- Section 5 sources are real, named sources (annual reports, earnings
  calls, press releases) — not vague attributions like "industry sources"

**Process:**
- MCP server: file exists at
  `[mcp_server_path]/context/accounts/[slug]-dossier.md`
- Notion: page URL recorded and accessible
- If Assignee was set in Notion: the AE/Owner name from Section 1 was used

#### 3f. Mark the whole wave completed + log errors

For each account in the wave, determine status from **expected section
satisfaction**, not from a hardcoded section count.

Definitions:

- Baseline expected sections = `1..6`
- Conditional expected section = `7` only when `deal_stage >= 3`
- A section counts as **satisfied** when it is `Complete` or `Placeholder`
- Section 7 also counts as **satisfied** when it is intentionally `Omitted`
  because the stage gate was not met

Then classify:

- All expected sections satisfied **AND** `mcp_server_saved = true` **AND**
  `notion_url != null` → `done`
- A dossier file exists but one or more expected sections are Failed, or
  publish/save failed → `partial`
- Fewer than 4 baseline sections are satisfied (dossier effectively unusable) →
  `failed`

Set `completed_at = <now>` and merge the account's self-check `issues`.

**One atomic state write for the whole wave** covering all accounts'
transitions to `done` / `partial` / `failed`.

If any account has Failed sections, publish/save failures, or self-check
issues, append all rows to `_batch-errors.md` in a **single write** at the end
of the wave:

```markdown
| timestamp | account | section | error |
|---|---|---|---|
| 2026-04-15T10:15:23Z | Zurich North America | Section 3 | Subagent returned empty output |
| 2026-04-15T10:15:23Z | The Hartford | Step 3e.iii | Copy to MCP server failed: permission denied |
| 2026-04-15T10:15:23Z | AXA XL | Step 6 | Notion create_pages returned 403 |
| 2026-04-15T10:15:23Z | Chubb | self-check | Section 5 sources not primary-named |
```

#### 3g. Continue to next wave

Loop back to 3a. Never stop the batch for a per-account failure — failed or
partial accounts are logged and the batch moves on. A session interrupt
mid-wave or mid-phase leaves all in-flight accounts in `running` state and
may leave per-section files partially written; the next resume resets the
accounts to `pending` and retries (Phase 1 subagents will overwrite any
stale per-section files).

### Step 4 — Generate summary

After all pending accounts are processed (or the batch naturally ends), write
`outputs/generate-dossier/_batch-summary.md`:

```markdown
# Batch Summary

**Started:** 2026-04-15T10:00:00Z
**Ended:** 2026-04-15T14:37:12Z
**Duration:** 4h 37m

## Totals

- Done: 47
- Partial: 2
- Failed: 1
- Pending (queue exited before processing): 0

## Results

| Account | Status | Sections | MCP save | Notion | Notes |
|---|---|---|---|---|---|
| Zurich North America | done | 7/7 | ✓ | [URL] | Section 7 omitted: stage gate not met |
| The Hartford | partial | 6/7 | ✓ | [URL] | Section 3: Databricks overlay unavailable |
| AXA XL | partial | 7/7 | ✗ | [URL] | MCP copy failed: permission denied |
| Chubb | failed | 3/7 | ✗ | — | See _batch-errors.md |

## Retry

To retry `partial` and `failed` accounts, rerun the same slash command. `done`
accounts are skipped automatically via `_batch-state.json`.

To force a fresh run, delete `_batch-state.json` before invoking.
```

### Step 5 — Report to operator

Print a concise chat summary:

```
Batch complete.

Results: 47 done, 2 partial, 1 failed.
Outputs: outputs/generate-dossier/
MCP server: [mcp_server_path]/context/accounts/
Notion: https://www.notion.so/hyperexponential/337802db20a6806f8fdbfe480adc0e4b
Summary: outputs/generate-dossier/_batch-summary.md
Errors: outputs/generate-dossier/_batch-errors.md

To retry partial/failed accounts, rerun the same slash command.
```

### Step 6 — Publish to Notion

Called from Step 3e.v per account. The Notion MCP tool accepts arguments up
to ~4.8KB once serialized, which breaks any dossier whose blocks collectively
exceed that limit — and most dossiers with rich tables do. So Step 6 branches
on transport.

Branch on `notion_mode` from Step 1:

- **`notion_mode == "api"`** → single-command direct publish via the parser
  script's `--publish` flag. Go to **Step 6 (API mode)** below.
- **`notion_mode == "mcp"`** → multi-payload MCP loop. Go to **Step 6 (MCP
  mode)** below.

Both paths produce a `notion_url` recorded on the account record. Per-account
failure semantics are identical: log to `_batch-errors.md`, finalize the
account as `partial` in Step 3f, never stop the batch.

---

#### Step 6 (API mode) — Direct Notion REST

When `NOTION_API_KEY` (or `NOTION_TOKEN`) is set, the parser script handles
the full create_page + append sequence itself — no MCP serializer in the
path, no payload juggling in chat.

Run via Bash:

```bash
python3 .claude/skills/generate-dossier/scripts/save-dossier-to-notion.py \
  --file "outputs/generate-dossier/[slug]-dossier.md" \
  --publish \
  --database-id 337802db20a6806f8fdbfe480adc0e4b \
  --account-name "[Account Name]" \
  --template-version "[template_version recorded in Step 1]" \
  --assignee "[AE name from Step 3e.iv, if resolved to a real name]"
```

Always pass `--template-version` using the value recorded at Step 1 from
this skill's own frontmatter. The script writes it to the Notion
`Template Version` text property; if the flag is omitted the property is
left blank.

Omit `--assignee` entirely if Step 3e.iv did not produce a real name (i.e.,
the value contained brackets or the row was missing). The script resolves
the name to a Notion user id via `GET /v1/users`; if no match is found, the
Assignee property is silently omitted.

**On success** (exit 0): parse stdout as JSON — `{"notion_url": "...",
"page_id": "..."}`. Record `notion_url` on the account record.

**On failure** (exit non-zero): parse stderr as JSON — `{"error": "...",
"failed_payload_index": N, "notion_url": null|"...", "status": ..., "body":
...}`. Log a row to `_batch-errors.md` including the error message and, if
present, the partial `notion_url` (the page was created but a later append
failed — it exists in Notion but is incomplete). Continue to the next
account.

Skip **Step 6 (MCP mode)** entirely in this branch.

---

#### Step 6 (MCP mode) — Multi-payload publish loop

Used only when `notion_mode == "mcp"`. The parser emits a sequence of
under-budget payloads and we execute them in order via MCP tool calls.

**6a. Parse with --multi:**

```bash
python3 .claude/skills/generate-dossier/scripts/save-dossier-to-notion.py \
  --file "outputs/generate-dossier/[slug]-dossier.md" \
  --multi
```

Capture the stdout JSON. It has the shape:

```json
{
  "version": 2,
  "byte_limit": 4500,
  "payloads": [
    {"op": "create_page", "children": [...]},
    {"op": "append", "parent": "page", "children": [...]},
    {"op": "append", "parent": "page", "capture": "table_1",
     "children": [<table block with header-only children>]},
    {"op": "append", "parent": "$table_1", "children": [<row>, <row>]},
    {"op": "append", "parent": "page", "children": [...]}
  ]
}
```

**6b. Resolve the submitter:** Try to identify the user from the conversation
context. If a name is available, search for a matching Notion user via
`notion-get-users`. If a match is found, record their Notion user ID. If
not, leave Submitter empty.

**6c. Execute payloads in order.** Maintain two pieces of state during the
loop: `page_id` (learned from the `create_page` response) and a `captured`
dict mapping capture keys to block IDs.

For each payload in order:

- **If `op == "create_page"`:** call `notion-create-pages` with:
  - `parent: {database_id: "337802db20a6806f8fdbfe480adc0e4b"}`
  - `properties`: Name / Type / Status / Template Version / Submitter /
    Assignee constructed from the account name ("Account Dossier" type,
    "Draft" status, Template Version set to the `template_version` recorded
    at Step 1 from this skill's frontmatter as a `rich_text` property —
    e.g. `{"rich_text": [{"text": {"content": "1.0"}}]}`, Submitter from 6b
    if resolved, Assignee from Step 3e.iv if resolved and matched to a
    Notion user). Omit Submitter / Assignee if not resolved. Omit Template
    Version only if no value was recorded at Step 1 (the Step 1 fallback
    means this should never happen in practice).
  - `children`: the payload's `children` array verbatim.
  - On success, record `page_id = response.id` and
    `notion_url = response.url` (or reconstruct as
    `https://notion.so/<page_id with hyphens stripped>` if the tool doesn't
    return `url`).
- **If `op == "append"`:** call `API-patch-block-children` with:
  - `block_id`: the resolved parent.
    - `"page"` → `page_id`
    - `"$table_N"` → `captured["table_N"]`
  - `children`: the payload's `children` array verbatim.
  - If the payload has a `capture` key, store `response.results[0].id` under
    that key in `captured`.

Do not reorder payloads and do not parallelise — Notion appends in arrival
order, and row-group appends depend on the table shell having already
returned its block ID.

**6d. Per-account failure handling:**

- If the very first `create_page` fails: mark the account's `notion_url =
  null`, log the error to `_batch-errors.md`, and stop this account's
  publish (no append retries). The Step 3f status for the account will be
  `partial`.
- If an `append` payload fails after `create_page` succeeded: record the
  `notion_url` (the page exists, just incomplete), log the error with the
  payload index, and stop. Account status will be `partial`.
- Never stop the batch. The outer wave loop continues to the next account.

---

## Error handling

| Failure | Behavior |
|---|---|
| Subagent timeout (soft, via prompt guidance) | Subagent returns partial section with "Not found in primary sources" for missing cells. Classified as Placeholder. |
| Subagent returns nothing / errors / no per-section file written | Classified as Failed in 3e.i. A one-line placeholder file is written so the bash `cat` in 3e.ii produces a uniform dossier for required sections. If too few baseline sections are satisfied, account marked `failed`. |
| Section 6 skipped (Section 2 or 5 file missing after Phase 1) | Section 6 subagent is not launched for that account. 3e.i writes the standard placeholder for Section 6. Account finalized as `partial`. |
| Section 7 skipped (stage gate not met) | Section 7 subagent is not launched. No placeholder file is written. The section is omitted from the assembled dossier and counts as satisfied-by-omission in 3f. |
| Section 7 failed after stage gate was met | Log the failure, write the standard placeholder at `section-7.md`, assemble it into the dossier, and finalize the account as `partial`. |
| Rate limit | Subagent sleeps 30s and retries up to 3x on the same tier. If still failing, drops to the next tier in the web research tool chain. |
| Perplexity Sonar API failure (non-zero exit, missing key, HTTP error, timeout) | Non-fatal. Subagent cascades to Perplexity MCP, then to WebSearch/WebFetch. Section does not stall. |
| Perplexity MCP failure | Non-fatal. Subagent cascades to WebSearch/WebFetch. |
| Git clone failure (Step 0.5) | Non-fatal. Sections 2, 3, 6, and 7 run with reduced local context and fallback behavior. |
| Databricks MCP unavailable | Non-fatal. Sections 1 and 4 use placeholder tables. Section 3 emits a no-overlay note and no-record relationship blocks. Section 7 will usually return its Databricks-required fallback block if launched. |
| Both Notion transports missing at pre-flight | **Hard stop at Step 1.** Batch never starts. Fix by exporting `NOTION_API_KEY` / `NOTION_TOKEN` or connecting the Notion MCP server. |
| hxgtm-mcp-server local path missing at pre-flight | **Hard stop at Step 1.** Batch never starts. |
| Step 3e.iii copy fails mid-batch | Log row in `_batch-errors.md`, set `mcp_server_saved = false`, continue to Step 3e.iv / Step 6 for this account. Account finalized as `partial`. |
| Step 3e.ii bash `cat` assembly fails | Append to `_batch-errors.md`, mark account `failed`, continue. Per-section files remain on disk so a manual rebuild is possible. |
| Step 6 Notion publish fails mid-batch (API mode) | Parse stderr JSON from `--publish`. Log row in `_batch-errors.md`, record partial `notion_url` if the page was created (e.g., an append failed after create_page succeeded), else `notion_url = null`, continue. Account finalized as `partial`. |
| Step 6 Notion publish fails mid-batch (MCP mode) | Log row in `_batch-errors.md`, set `notion_url = null` (or the partial URL), continue. Account finalized as `partial`. |
| Write failure (filesystem error on `outputs/`) | Append to `_batch-errors.md`, mark account `failed`, continue. |
| Session interrupted | Everything written so far is atomic and resumable. Operator reruns the same slash command to resume. |

Never hard-stop mid-batch for a per-account issue. Batch-level hard stops only
happen at pre-flight (both Notion transports missing, or MCP server path
missing) or if the output directory can't be created or the account list is
empty.

---

## Atomic writes

Writes should be atomic to avoid partial files being visible after an
interrupt. **Pick the writer based on who is generating the content**:

- **Subagent-generated content (per-section markdown files)** — each
  section subagent uses the `Write` tool itself. The `Write` tool
  overwrites atomically by design. The orchestrator never `Write`s section
  content because it never holds it.

- **Assembled dossier (concatenation of per-section files)** — use
  bash `cat` with `> tmp && mv tmp final`. The orchestrator's tool-call
  payload is a small bash command (no embedded markdown), so this stays
  stream-friendly regardless of dossier size:

  ```bash
  { ...cat sequence... } > "$target.tmp" && mv "$target.tmp" "$target"
  ```

- **Small orchestrator-generated payloads (state, errors, summary, <2KB)**
  — bash heredoc + rename is fine:

  ```bash
  cat > "$target.tmp" <<'EOF'
  ...content...
  EOF
  mv "$target.tmp" "$target"
  ```

Applies to:
- Each per-section file `outputs/.../[slug]-section-N.md` for baseline sections
  `1..6`, plus conditional `section-7.md` when the stage gate is met →
  **subagent's `Write` tool**. Orchestrator never writes these.
- The assembled dossier `outputs/.../[slug]-dossier.md` → **bash `cat` +
  `mv`** (Step 3e.ii). Do NOT use `Write` — it forces the orchestrator to
  generate the entire dossier as a tool-call argument, which trips
  stream-idle.
- The copy to `[mcp_server_path]/context/accounts/` uses `cp` directly
  (the source is already atomic).
- `_batch-state.json` (after every state transition) → heredoc fine.
- `_batch-errors.md` (rewrite full file with new row, then rename) →
  heredoc fine.
- `_batch-summary.md` → heredoc fine for typical batch sizes; switch to
  `Write` if the summary table grows past a few hundred rows.

**Why this matters:** the previous design routed the assembled dossier
through the orchestrator's `Write` call, which serializes a 5K–10K-word
`contents` parameter token-by-token from the model. Under load, that
streams slowly enough to trip Claude Code's stream-idle watchdog. Bash
`cat` of pre-existing files moves the data through the kernel, not through
the model.

---

## Resume behavior

Rerunning the skill with the same (or overlapping) account list:

1. Step 2 loads `_batch-state.json`.
2. Accounts with `status = done` are skipped silently.
3. Accounts with `status = partial` or `failed` are reset to `pending` and processed again. Reprocessing re-runs all Step 3c–3f sub-steps including the per-section subagents, the MCP server copy, and the Notion publish — this means a retry will overwrite all per-section files that are expected for that run, re-publish to Notion (creating a duplicate page), and overwrite the MCP server copy. Accept this as the retry trade-off; if you want to retry only the publish/save, do it manually with the existing dossier file.
4. Accounts with `status = running` (previous run was interrupted) are also reset to `pending`.
5. Accounts in the input but missing from state are added as `pending`.

To force a full rerun, delete `_batch-state.json` and any existing dossier files.
Per-section files (`*-section-N.md`) will be overwritten by the next run when
their sections are expected for that run; the conditional `section-7.md` may be
absent on runs where the stage gate is not met. These files are idempotent
staging artifacts.
