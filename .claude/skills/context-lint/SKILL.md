---
name: context-lint
description: >
  Audit the structural wiring between skills, context files, plugin SKILL.md
  files, MCP fallback manifests, and the Notion "Agents & Skills" documentation
  page. Catches missing files, orphaned context, drifted fallbacks, duplicate
  loads in skill chains, bloated skill context, foundation coverage gaps, and
  documentation drift. Produces a severity-ranked markdown report with
  actionable fixes. Use when asked to "lint context", "audit skill wiring",
  "check for orphan context files", "check fallback drift", "audit context
  packs", or "check documentation drift". Sibling skill to kb-lint — kb-lint
  audits content quality, context-lint audits structural wiring.
---

# Context Lint

## What this skill does

Audits the three sources of truth that define how hx skills load context and
how that wiring is documented:

1. **MCP server wiring** (`hxgtm-mcp-server/src/context.ts`) — `SKILL_CONTEXTS`,
   `CONTEXT_PACKS`, `GUIDANCE_MAP` declarations
2. **Plugin SKILL.md files** (`hx-plugins/plugins/*/skills/*/SKILL.md`) —
   skill-side context loading instructions, chain declarations, fallback
   manifests in `plugins/*/context/mcp-fallback.md`
3. **Notion "Agents & Skills" page** — user-facing documentation of what
   skills exist and what they do

The skill cross-references these three sources, runs 10 deterministic
structural checks, and produces a severity-ranked report at
`outputs/context-lint-YYYY-MM-DD.md`.

A clean run means **0 errors and 0 warnings**. Every newly added skill or
context file should pass the audit before it ships.

## Phases

The skill runs **optimistically** — it starts straight into the work with no
plan-mode prompt, no pre-flight validation wall, and no proceed gate. Assume
the sources are present, resolve access, and proceed directly to indexing. If
something is genuinely missing, it surfaces reactively at the step that needs
it (see Error handling): the MCP server source is the one hard requirement;
everything else degrades gracefully and the skip is acknowledged in the report.

3 phases:

1. **Phase 1 — Index & parse** (inline) — parses `src/context.ts`, walks the
   context tree, parses plugin `SKILL.md` files, parses fallback manifests,
   and (if Notion MCP available) fetches the `Agents & Skills` page
2. **Phase 2 — Audit** (parallel subagents) — Server Inspector, (if plugins
   source present) Plugin Inspector, and (if Notion enabled) Notion Comparator
   run their assigned checks
3. **Phase 3 — Synthesize report** (inline) — merge findings, build per-skill
   breakdown, group actionable fixes, save report

## Requirements

- **MCP server source — the one hard requirement.** Read access to one of:
  `Projects/MCP/` (production) OR `../hxgtm-mcp-server/` (local fallback).
  Without `src/context.ts` there is no wiring to audit; a genuinely
  unreachable source surfaces reactively at the first read (Step 3a) and stops
  the run — not as a pre-flight wall.
- **Plugins source — best-effort.** Read access to one of:
  `Projects/Plugins/plugins/` (production) OR `../hx-plugins/plugins/` (local
  fallback). If neither resolves, the skill skips the Plugin Inspector
  (Checks #4/#5/#7) and runs the Server Inspector checks off `context.ts` + the
  context tree, producing a useful partial audit. The skip is acknowledged in
  the report. **Plugins access is never blocking.**
- **Notion MCP** (optional — enables Check #10 documentation drift) — if
  unavailable or excluded by user, the skill skips Check #10 silently and
  the lint runs to completion. **Notion access is never blocking.**
- **Bash tool** (for `git log` mtime lookups in temporal pre-filter) and
  **Glob/Read** for filesystem walks

## Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| MCP server source — production | `Projects/MCP/` | Preferred |
| MCP server source — local fallback | `../hxgtm-mcp-server/` | Used if production unavailable |
| Plugins source — production | `Projects/Plugins/plugins/` | Preferred |
| Plugins source — local fallback | `../hx-plugins/plugins/` | Used if production unavailable |
| Notion page name | `Agents & Skills` | Looked up by name (portable across workspaces) |
| Output path | `outputs/` | |
| Default checks | all 10 | See Check Catalogue below |
| Default size threshold | 1500 lines | Check #8 — flag any skill resolving above this |
| Custom loader exclusions | `guidance/competitive/competitors/*.md` | Files loaded by custom functions (e.g. `loadCompetitorData`), excluded from Check #2 orphan detection |

### Check catalogue

| # | Check | Severity | Subagent | Notes |
|---|---|---|---|---|
| 1 | Pack integrity (forward) — referenced files exist | Error | A | |
| 2 | Orphan files (reverse) — context files referenced ≥1 place | Warning | A | Groups by directory cluster; excludes custom-loader files |
| 3 | Orphan packs — every CONTEXT_PACK is referenced ≥1 place | Warning | A | |
| 4 | Fallback-to-server sync | Warning | B | `SKILL_CONTEXTS` is canonical; fallback should mirror it |
| 5 | Cross-skill chain duplication | Warning | B | |
| 6 | Unconditional bulk loading | Warning | A | |
| 7 | Parallelism opportunities | Info | B | Single grouped finding for all sequential skills |
| 8 | Context size profiling | Warning | A | |
| 9 | Foundation coverage | Warning | A | Writing guide + GUIDANCE_MAP persona coverage only |
| 10 | Notion documentation drift (semantic) | Mixed | C | Pre-filtered skills are a silent count, not individual findings; multi-repo plugins downgraded to Warning |

Subagent **A** (Server Inspector) is always active. Subagent **B** (Plugin
Inspector — Checks #4/#5/#7) is active only when the plugins source resolves;
if it doesn't, those checks are skipped with an acknowledged note. Subagent
**C** (Notion Comparator — Check #10) is active only when Notion MCP is present
and not excluded.

Users can request a subset via `--checks=1,2,3` or skip Notion via
`--no-notion`.

---

## Workflow

### Step 1 — Collect input

Check whether the user specified any arguments:

- **Check filter** — `--checks=1,2,3` to restrict to a subset. Default: all.
- **Notion toggle** — `--no-notion` to skip Check #10 even if Notion MCP is
  available. Default: enabled (auto-detected in Step 2).
- **Size threshold override** — `--threshold=N` to override the default 1500
  line threshold for Check #8. Default: 1500.

If no arguments were provided, proceed with defaults (all checks, Notion
auto-detected, threshold 1500).

### Step 2 — Resolve access (optimistic)

context-lint runs straight through — there is no pre-flight validation wall
and no proceed gate. Assume the sources are present, resolve access (this only
stamps the report header so the reader knows which world they're auditing), and
proceed directly to indexing. Do **not** present a summary and do **not**
prompt. If something is genuinely missing, it surfaces reactively at the step
that needs it (see Error handling).

**2a. MCP server source resolution** (the one hard requirement)

Resolve the MCP server source with production-first, local-fallback:

1. Check if `Projects/MCP/src/context.ts` exists (production path, relative
   to repo root). If yes, set `mcp_source_root = Projects/MCP/`,
   `mcp_source_mode = production`.
2. If not, check if `../hxgtm-mcp-server/src/context.ts` exists (local
   fallback). If yes, set `mcp_source_root = ../hxgtm-mcp-server/`,
   `mcp_source_mode = local`.
3. If neither resolves, do not stop here — proceed optimistically. The
   absence surfaces reactively when Step 3a tries to read `context.ts`
   (report the error and stop). This is the one hard requirement; it is
   handled reactively, not as a pre-flight wall.

Resolve `mcp_context_root = ${mcp_source_root}/context/` for the file tree
walk in Step 3b.

**2b. Plugins source resolution** (best-effort)

Same pattern, independently from 2a:

1. Check if `Projects/Plugins/plugins/` exists. If yes, set
   `plugins_source_root = Projects/Plugins/plugins/`,
   `plugins_source_mode = production`.
2. If not, check if `../hx-plugins/plugins/` exists. If yes, set
   `plugins_source_root = ../hx-plugins/plugins/`,
   `plugins_source_mode = local`.
3. If neither resolves, set `plugins_source_mode = skipped`. **This never
   blocks the lint** — the Plugin Inspector (Checks #4/#5/#7) is skipped and
   the Server Inspector checks still run off `context.ts` + the context tree,
   producing a useful partial audit. The skip is acknowledged in the executive
   summary (Step 5e) and Statistics section (Step 5d).

The two source modes resolve **independently** — production MCP + local
plugins is a valid combination. Stamp both source modes into the report
header.

**2c. Notion MCP detection**

If the user passed `--no-notion` in Step 1, set `notion_enabled = false`,
record reason as "excluded by user", and skip detection.

Otherwise:

1. Check the available tools for any MCP tool whose name contains
   `notion-search` (e.g., `mcp__claude_ai_Notion__notion-search`)
2. If found: set `notion_enabled = true`, record the tool names for use
   in Step 3e
3. If not found: set `notion_enabled = false`, record reason as
   "not configured"

**Notion is optional and never blocks the lint.** When the Notion MCP is
unavailable OR `--no-notion` was passed, Subagent C is not launched and
no Check #10 findings appear in the report. context-lint runs to completion
regardless. The skip is acknowledged in:
- The executive summary in Step 5
- The Statistics section ("Notion status: skipped (reason)")

Detection failures themselves never raise errors — if the tool-listing
mechanism fails for any reason, default to `notion_enabled = false`,
record reason as "detection failed", and proceed.

### Step 2.5 — Detect environment

Check whether you have a `bash` tool available.

- **If yes → Claude Code.** Use `subagent_type: "general-purpose"` and launch
  all enabled subagents simultaneously in a single message.
- **If no → Cursor.** Use `subagent_type: "generalPurpose"` and launch
  subagents sequentially.

Carry the detected `subagent_type` value forward into Step 4.

### Step 3 — Phase 1: Index & parse (inline)

Build structured indexes for all sources. This step runs inline (not as a
subagent) because the orchestrator needs the indexes to prepare subagent
inputs.

#### 3a. Parse `src/context.ts`

Read `${mcp_source_root}/src/context.ts` and extract three structures via
regex (the file uses simple object literals — no full TS AST needed):

1. **`SKILL_CONTEXTS`** — match the block beginning
   `const SKILL_CONTEXTS: Record<string, ContextEntry[]> = {` and parse
   each top-level entry. For each skill, capture an ordered list of
   string entries (file paths or `pack:<name>` references).
2. **`CONTEXT_PACKS`** — match `const CONTEXT_PACKS: Record<string, ContextEntry[]> = {`
   and parse each pack name → list of entries. Packs may contain
   `pack:<name>` references to other packs.
3. **`GUIDANCE_MAP`** — match
   `const GUIDANCE_MAP: Record<string, Record<string, string>> = {`
   and parse each category → content_type → file path.

**Pack expansion:** for each entry in `SKILL_CONTEXTS`, recursively expand
any `pack:<name>` reference using the `CONTEXT_PACKS` table. Deduplicate
the resulting flat file list per skill. Track which entries came from
packs vs. direct skill references for Check #6 (unconditional bulk loading).

Build the parsed structure:

```yaml
skill_contexts_resolved:
  ads:
    direct_files: [...]
    pack_references: [marketing-content-base]
    expanded_files: [...]      # flat, deduplicated
  blog:
    ...
context_packs:
  marketing-content-base:
    entries: [...]
    referenced_by_skills: [ads, blog, ...]
guidance_map:
  ads:
    google-ads-rsa: marketing/guidance/ads/content-types/google-ads-rsa.md
    ...
all_referenced_files:
  - truth/product-marketing-context.md
  - ...                                  # union of all paths from above
```

#### 3b. Walk `context/**/*.md`

Use Glob for `**/*.md` under `${mcp_context_root}`. For each file:

1. Compute the path relative to `${mcp_context_root}`
2. Count lines (use Read or Bash `wc -l`)
3. Capture the git log mtime (last commit that touched the file) via
   Bash: `git -C ${mcp_source_root} log -1 --format=%cI -- <relpath>`
   — needed for the temporal pre-filter in Check #10

Build the file inventory:

```yaml
context_files:
  - path: truth/product-marketing-context.md
    line_count: 412
    git_mtime: 2026-03-15T10:23:00Z
  - ...
```

#### 3c. Walk `plugins/**/SKILL.md`

Use Glob for `**/SKILL.md` under `${plugins_source_root}`. For each file:

1. Extract `name` and `description` from YAML frontmatter
2. Capture the path of the plugin directory (parent of `skills/<name>/`)
3. Extract the **Context Loading section** — the markdown section starting
   with `## Context Loading` (or similar) and ending at the next `##` heading
4. Detect chain declarations — look for "Skill Chaining", "polish skill",
   `${CLAUDE_PLUGIN_ROOT}/skills/<other>/SKILL.md` references, "Mandatory
   Workflow" sections that name a follow-up skill
5. Detect persona-conditional patterns — look for phrases like "after
   detecting the target audience", "load the relevant persona pair",
   "matching the audience"
6. Detect sequential vs. parallel loading patterns — look for "in a single
   tool-call batch" / "in a single batch" (parallel) vs. numbered sequential
   "Step 1 — call X. Step 2 — call Y" without a batch hint (sequential)

Build:

```yaml
plugin_skills:
  - name: ads
    plugin_dir: hx-marketing
    skill_md_path: hx-marketing/skills/ads/SKILL.md
    description: "..."
    context_loading_text: "..."
    chain_targets: [polish]
    persona_conditional: true
    loading_pattern: parallel
  - ...
```

#### 3d. Parse `plugins/**/context/mcp-fallback.md`

For each `mcp-fallback.md` found in `${plugins_source_root}/*/context/`:

1. Split the file into per-skill sections by `### <skill-name>` headings
2. For each skill section, extract:
   - The "Expected: N total" file count
   - Each `**Base context (...)**` block — list of files
   - Each `**Guidance (...)**` block — list of conditional/optional files
   - Each `**Polish chain (...)**` block — files loaded in chained mode
   - Any "Skill-local references" (`${CLAUDE_PLUGIN_ROOT}/...`) — track but
     don't include in the canonical comparison set (these are plugin-local
     references, not MCP-served files)

Build:

```yaml
fallback_manifests:
  - plugin: hx-marketing
    skills:
      ads:
        expected_total: 10
        base_files: [...]
        guidance_options: [...]
        persona_pairs: [...]
        polish_chain_files: [...]
      ...
  - plugin: hx-sdr
    skills:
      draft-outreach:
        ...
```

#### 3e. (if `notion_enabled`) Fetch the Notion `Agents & Skills` page

1. Call `mcp__claude_ai_Notion__notion-search` with query `"Agents & Skills"`
2. From the search results, find the page whose title most closely matches
   `"Agents & Skills"` (exact match preferred, then case-insensitive). If
   multiple candidates, prefer the one in the user's primary workspace.
3. If no match found: log a warning, set `notion_enabled = false` for the
   rest of the run, record reason as "page not found in workspace", and
   proceed without Check #10
4. If found: capture the page ID and `last_edited_time`
5. Call `mcp__claude_ai_Notion__notion-fetch` with the page ID to retrieve
   full content
6. **Adaptive parse**: discover the per-skill block structure at runtime.
   For each plugin skill name from Step 3c, search the Notion page content
   for blocks (headings, table rows, toggle headers, callout titles)
   matching the skill name. Capture for each match:
   - The matched block(s) and surrounding description text
   - The block-level `last_edited_time` if available (otherwise inherit
     from the page)
7. Build a `notion_skill_blocks` map: `skill_name → { description_text, last_edited_time }`
8. Also capture the inverse: any prominent name-shaped blocks in the
   Notion page that did NOT match any plugin skill — these become "Notion
   has skill that doesn't exist in plugins" findings in Check #10

If ANY part of the Notion fetch fails (search timeout, fetch error,
permission denied, parse failure), catch the error, set `notion_enabled = false`
for the rest of the run, record reason as "fetch/parse failed: <error>",
and proceed. **Never block the lint on Notion.**

#### 3f. Prepare subagent inputs

Bundle the indexes from 3a–3e into payloads for each subagent. See
[references/server-inspector.md](references/server-inspector.md),
[references/plugin-inspector.md](references/plugin-inspector.md), and
[references/notion-comparator.md](references/notion-comparator.md) for the
exact `{{variable}}` substitutions each subagent expects.

### Step 4 — Phase 2: Launch subagents

Read each reference file, substitute `{{variables}}` with the prepared data
from Step 3f, and launch subagents using the batch strategy from Step 2.5.

| Subagent | Reference file | Checks | Status |
|----------|---------------|--------|--------|
| Server Inspector | `references/server-inspector.md` | #1, #2, #3, #6, #8, #9 | **Always active** |
| Plugin Inspector | `references/plugin-inspector.md` | #4, #5, #7 | **Active only if plugins source resolved** |
| Notion Comparator | `references/notion-comparator.md` | #10 | **Active only if `notion_enabled`** |

In Claude Code, launch all enabled subagents simultaneously in a single
message — Server Inspector is always one of them; add Plugin Inspector if the
plugins source resolved (`plugins_source_mode != skipped`) and Notion Comparator
if `notion_enabled = true`. In Cursor, launch sequentially.

**Best-effort / non-blocking guarantee:** If `plugins_source_mode = skipped`,
do not launch the Plugin Inspector — proceed with the Server Inspector (and
Notion Comparator if enabled) and note the skip in Step 5 synthesis. If
`notion_enabled = false`, do not launch the Notion Comparator. If any launched
subagent fails or crashes mid-run, catch the error, continue with the other
subagents' results, and note the failure in Step 5 synthesis. The lint always
completes.

### Step 5 — Phase 3: Synthesize report (inline)

Once the launched subagents complete (1–3 depending on which sources resolved),
merge their outputs into a single report.

**5a. Merge and renumber findings**

Collect all findings from each subagent that returned results. Re-number
them sequentially within each section to avoid ID collisions:

- **Errors** — `E1`, `E2`, ... (Check #1 missing files; Check #10 structural)
- **Warnings** — `W1`, `W2`, ... (Checks #2, #3, #4, #5, #6, #8, #9; Check #10 semantic)
- **Info** — `I1`, `I2`, ... (Check #7 parallelism)

Each finding from a subagent carries an origin prefix (e.g., `SI-#1-3`,
`PI-#5-1`, `NC-#10-2`). During synthesis, route by severity into E/W/I
sections and preserve the origin in the finding body.

**5b. Build per-skill breakdown**

For every skill in `SKILL_CONTEXTS`, compute:

- Total resolved file count
- Total resolved line count (sum from 3b file inventory)
- Chain overhead lines (from Check #5 findings — files duplicated in chain)
- Number of issues (errors + warnings + info)

Sort by total line count, descending. Flag any row exceeding the configured
threshold (default 1500 lines) with a ⚠ marker.

**5c. Group actionable fixes**

Group findings by fix type so a human reading the report can address related
issues together:

- Missing files (Check #1)
- Orphan files & packs (Checks #2, #3)
- Fallback drift (Check #4)
- Chain duplication (Check #5)
- Bulk loading (Check #6)
- Sequential loading (Check #7)
- Bloat (Check #8)
- Foundation coverage gaps (Check #9)
- Notion drift (Check #10)

**5d. Assemble report**

Read [references/output-format.md](references/output-format.md) for the
canonical structure. Assemble the report following that format exactly.

In the Statistics section, include status lines for each subagent and the
sources used:

- `Sources: MCP=[mode] (path), Plugins=[mode] (path), Notion=[status]`
- `Server Inspector: N findings`
- `Plugin Inspector: enabled — N findings | skipped (plugins source not reachable) | failed — error`
- `Notion Comparator: enabled — N findings | skipped (reason) | failed — error`

**5e. Generate executive summary**

Write a 2–3 sentence summary that:
- States the overall health assessment (clean / needs attention / critical)
- Highlights the most important finding
- Notes the source modes used and any skipped checks
- **If the plugins source was not reachable, append a sentence:** "Plugin
  Inspector was skipped (plugins source not reachable) — fallback sync (#4),
  chain duplication (#5), and parallelism (#7) were not audited this run; the
  rest of the audit ran off `context.ts` and the context tree."
- **If Notion was skipped or failed, append a sentence:** "Notion
  documentation drift check was skipped (Notion MCP unavailable / excluded
  via --no-notion / fetch failed) — user-facing docs were not compared
  against actual skill behavior."

### Step 6 — Save report

Save the assembled report to `outputs/context-lint-YYYY-MM-DD.md` where the
date is today's date.

If a report for today's date already exists, append a counter:
`outputs/context-lint-YYYY-MM-DD-2.md`

### Step 7 — Report to user

Output a summary:

```
Context Lint report generated.

Findings: [N] total ([X] errors, [Y] warnings, [Z] info)
Skills audited: [N]
Context files audited: [N]
Plugin Inspector: [N findings | skipped (plugins source not reachable)]
Notion status: [enabled (N findings) | skipped (reason) | failed (error)]

Sources:
  MCP server: [production / local] — [path]
  Plugins:    [production / local / skipped] — [path or "not reachable"]

Saved to: outputs/context-lint-YYYY-MM-DD.md
```

---

## Error handling

Failures surface **reactively at the step that needs the resource** — there is
no pre-flight wall and no proceed gate.

- **MCP server source unreachable** — the one hard requirement. If neither
  production nor local fallback resolves, it surfaces when Step 3a tries to
  read `context.ts`: report the error and stop. context-lint cannot run
  without `context.ts` to audit.
- **Plugins source unreachable** — never blocking. The Plugin Inspector
  (Checks #4/#5/#7) is skipped and the Server Inspector checks still run off
  `context.ts` + the context tree. The skip is acknowledged in the executive
  summary (Step 5e) and Statistics section (Step 5d).
- **Subagent failure** — if a subagent crashes or times out, include its
  findings section as: `[Subagent X could not be completed. Error: brief
  description. Please retry.]` and continue with the other subagents'
  output. Do NOT retry, do NOT stop.
- **Notion failure** — never blocking. See "Best-effort / non-blocking
  guarantee" in Step 4. The skip appears in the executive summary (Step 5e)
  and Statistics section (Step 5d).
- **Empty context tree** — if `context/` exists but contains zero `.md`
  files, report an error and stop (the source likely isn't pointing at the
  right directory).
- Report any errors in the Step 7 summary.

---

## Batch mode notes

context-lint runs the same way interactively and non-interactively — there is
no proceed gate or AskUserQuestion in the main path, so the only difference in
a batch script is the absence of a human watching. When running via a batch
script:
- Use default configuration (all checks, Notion auto-detected, threshold 1500)
- Plugins source auto-detects; if unreachable, the Plugin Inspector is skipped
  with an acknowledged note (non-blocking, same as interactive mode)
- Notion still auto-detects and runs Check #10 if available; skips silently
  otherwise (non-blocking, same as interactive mode)
- Save the report and exit without user interaction. If the Step 6 write
  fails, halt with a non-zero exit.
