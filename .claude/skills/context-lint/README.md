# context-lint

Audit the structural wiring between the MCP server, plugin SKIL# PRD: Context Lint

*Created: 2026-04-04*
*Updated: 2026-04-09 — reconciled with David's writeup; added Notion scope, orphan-file & orphan-pack checks, production-first / local-fallback source resolution.*

---

## Problem

Context wiring degrades silently across three sources of truth:

1. **MCP server wiring** in `hxgtm-mcp-server/src/context.ts` (`SKILL_CONTEXTS`,
   `CONTEXT_PACKS`, `GUIDANCE_MAP`)
2. **Plugin SKILL.md files** in `hx-plugins/plugins/*/skills/*/SKILL.md` plus
   their fallback manifests at `plugins/*/context/mcp-fallback.md`
3. **User-facing documentation** in the Notion `Agents & Skills` page

Files get renamed or removed, packs grow, chains accumulate duplicate loads,
fallback manifests drift from server definitions, context files orphan when
the skills that referenced them are deleted, and Notion docs go stale when
skills change behavior. None of this triggers an error. The cost compounds:
inflated token budgets, unnecessary round trips, slower skill runs, subtle
quality issues when stale or missing context is loaded, and new users
following docs that no longer reflect reality.

The ads skill optimization exposed this firsthand. A single audit surfaced a
missing file (`platform.md`), all three persona packs loading unconditionally,
a polish chain duplicating 343 lines already in memory, a fallback manifest
pointing at a completely different file set than the server, and zero
parallelism in loading instructions. None of these triggered an error.
Together they nearly doubled the context load.

This happened in one skill. It is happening across the system right now.

---

## Goal

Ship a maintenance skill that audits the structural wiring between skills,
context packs, MCP tools, and user-facing documentation. Every check is
deterministic except Check #10's semantic comparison — file existence, set
comparison, line counting, git mtime lookups. The semantic comparison uses
LLM reasoning but is gated behind a temporal pre-filter so most runs skip it.

A clean run means **zero errors and zero warnings**. Every newly added skill
passes the audit before it ships.

---

## Scope

### In scope

- Structural integrity of pack definitions, fallback manifests, and on-disk
  context files (forward direction)
- Reverse-direction wiring: every context file must be referenced by at
  least one skill, pack, or guidance entry
- Orphan packs: every `CONTEXT_PACK` must be referenced by at least one
  `SKILL_CONTEXT` (directly or via another pack)
- Cross-skill duplication analysis for chained skills
- Unconditional bulk loading detection
- Parallelism opportunities in SKILL.md loading instructions
- Context size profiling and ranking
- Foundation coverage cross-references (audience-to-pillar,
  segment-to-persona)
- Notion documentation drift: every plugin skill has a Notion entry, every
  Notion entry has a plugin skill, and descriptions semantically match
  current SKILL.md behavior

### Non-goals

- Content quality, tone, or factual accuracy of foundation docs — that is
  `kb-lint`'s job
- Runtime performance profiling of MCP server responses
- Automated fixes — this skill reports; a human (or a separate skill) acts
- Tracking when individual canonical claims become factually outdated —
  that is `kb-lint`'s Phase 3 (external verification)

---

## Source resolution

Two independent sources, each with the same fallback rule:

| Source | Production (preferred) | Local fallback |
|---|---|---|
| MCP server / context.ts / context tree | `Projects/MCP/` | `../hxgtm-mcp-server/` |
| Plugins (SKILL.md + fallback manifests) | `Projects/Plugins/plugins/` | `../hx-plugins/plugins/` |

For each source, check the production path first. If ANY required file is
missing under production, fall back to the local path **for the whole
source** (don't mix sources mid-audit). The two sources resolve
independently — production MCP + local plugins is a valid combination.
Stamp both source modes into the report header.

---

## Check Catalogue

### 1. Pack integrity (forward)

- Every file referenced in `SKILL_CONTEXTS`, `CONTEXT_PACKS`, and
  `GUIDANCE_MAP` (in `context.ts`) exists on disk in the context directory
- Every file listed in `mcp-fallback.md` exists on disk
- Flag any `[Context file not found: ...]` that `readContext` would return
  at runtime

**Severity: Error.** Reported by Server Inspector (Subagent A).

### 2. Orphan files (reverse)

- Every `context/**/*.md` file is referenced by at least one
  `SKILL_CONTEXTS`, `CONTEXT_PACKS`, `GUIDANCE_MAP`, or `mcp-fallback.md`
  entry
- Excluded from this check: `_template-*.md`, `README.md`, files under
  `**/data/` (raw data, not narrative content)

**Severity: Warning.** Reported by Server Inspector (Subagent A).

**Real example to be caught on day one:** `truth/audiences/coo-persona.md`
exists but is referenced by nothing in `SKILL_CONTEXTS`, `GUIDANCE_MAP`, or
any fallback manifest.

### 3. Orphan packs

- Every key in `CONTEXT_PACKS` is referenced by at least one skill in
  `SKILL_CONTEXTS` (directly or transitively via another pack)

**Severity: Warning.** Reported by Server Inspector (Subagent A).

**Real example to be caught on day one:** `CONTEXT_PACKS["deep-personas"]`
and `CONTEXT_PACKS["all-persona-guides"]` are defined but referenced by
zero skills.

### 4. Fallback-to-server sync

- Compare each skill's section in `mcp-fallback.md` against the resolved
  file list from `SKILL_CONTEXTS` + `CONTEXT_PACKS`
- Flag mismatches: files in one but not the other, different file paths
  for the same logical content, stale expected-file-count totals
- Persona/format/chain dimensions in fallback manifests are NOT diffed
  against `SKILL_CONTEXTS` (they're conditional and live in `GUIDANCE_MAP`)
  but their referenced files ARE checked against the on-disk inventory

**Severity: Warning** for drift, **Error** for fallback files referencing
non-existent on-disk paths. Reported by Plugin Inspector (Subagent B).

### 5. Cross-skill duplication in chains

- For each skill that chains to another (e.g., `ads → polish`), resolve
  the full context loaded by both skills
- Flag files loaded twice across the chain
- Estimate wasted lines (sum of duplicated file line counts)

**Severity: Warning.** Reported by Plugin Inspector (Subagent B).

**Real example to be caught on day one:** `ads → polish` chain — `ads` loads
`truth/company/policies.md` and `guidance/anti-ai-guardrails.md` via the
`marketing-content-base` pack; standalone polish loads them again.

### 6. Unconditional bulk loading

- For each skill, check whether persona packs or other large conditional
  context loads unconditionally
- Flag packs where the skill's instructions indicate audience- or
  format-dependent content but the server loads everything regardless
- Recommend moving to on-demand `load_guidance` calls

**Severity: Warning.** Reported by Server Inspector (Subagent A).

### 7. Parallelism opportunities

- Parse each SKILL.md's Context Loading section for sequential loading
  patterns
- Flag cases where `load_skill_context` and `load_guidance` are independent
  and could be called in a single batch
- Do NOT flag dependent sequential calls (e.g., "after detecting the
  audience, load the persona pair")

**Severity: Info.** Reported by Plugin Inspector (Subagent B).

### 8. Context size profiling

- For each skill, resolve and sum line counts of all files loaded
  (base + guidance + chain)
- Rank skills by total context weight
- Flag skills above a configurable threshold (default: 1,500 lines)
- Break down by category: truth, guardrails, persona, guidance, chain
  overhead

**Severity: Warning** when over threshold. Reported by Server Inspector
(Subagent A); chain overhead numbers come from Plugin Inspector (Subagent B).

### 9. Foundation coverage

Lightweight structural cross-references that verify the foundation file
tree is internally complete. These are file-existence and naming-convention
checks, not semantic analysis.

- For every audience file in `context/truth/audiences/`, verify a
  corresponding messaging file exists under `context/truth/messaging/products/`
  or `context/truth/messaging/segments/`
- For every segment referenced in positioning docs, verify a matching
  persona file exists
- Flag orphaned pillars (pillar directory with no matching audience file)
  and orphaned audiences (audience file with no corresponding pillar)

**Severity: Warning.** Reported by Server Inspector (Subagent A).

### 10. Notion documentation drift

- Look up the Notion `Agents & Skills` page by name (portable across
  workspaces)
- Adaptively parse the page structure at runtime (no hardcoded layout
  assumptions)
- For each plugin skill, verify a corresponding Notion entry exists
  (structural)
- For each Notion entry, verify a corresponding plugin skill exists
  (structural)
- For matched pairs, run a temporal pre-filter: if no underlying context
  file has changed since the Notion block's `last_edited_time`, skip the
  semantic check
- For surviving pairs, use LLM reasoning to compare the Notion description
  against the actual SKILL.md description, "When to Use", and resolved
  context. Flag semantic drift (purpose, inputs, outputs, capabilities).

**Severity: Error** for structural drift (missing entry on either side),
**Warning** for semantic drift. Reported by Notion Comparator (Subagent C).

**This check is optional.** If Notion MCP is unavailable or the user passes
`--no-notion`, Subagent C is not launched and the lint runs to completion
with a clearly marked "Notion checks skipped" status. This matches the
non-blocking pattern established by `kb-lint`'s Phase 3.

---

## Output Spec

A structured audit report (see `references/output-format.md` for the canonical
format) with the following sections:

1. **Header** — date, source modes, file/skill counts, finding counts,
   overall status (PASS / NEEDS ATTENTION / FAIL)
2. **Summary** — 2–3 sentence executive summary
3. **Per-skill breakdown** — table sorted by total line count, with category
   columns and over-threshold flags
4. **Errors** — every error finding with check number, file, suggested fix
5. **Warnings** — every warning finding
6. **Info** — every info finding
7. **Actionable fixes** — same findings re-grouped by fix type so a human
   can address related issues together
8. **Statistics** — counts and subagent status lines

---

## Trigger Cadence

| Trigger | When |
|---|---|
| On demand | Debugging a slow skill, after adding a new skill or context file, after any plugin SKILL.md change |
| Periodic | Monthly, or after any batch of context file changes |
| Post-deploy | After MCP server deploys, to catch regressions |
| Post-Notion-edit | After updating the `Agents & Skills` page in Notion |
| Pre-merge gate | Every new skill passes the audit before it ships |

---

## Implementation Guidance

### What it reads

| Source | Path (production / local fallback) | Purpose |
|---|---|---|
| MCP server context wiring | `Projects/MCP/src/context.ts` / `../hxgtm-mcp-server/src/context.ts` | Pack definitions, skill contexts, guidance map |
| MCP server context tree | `Projects/MCP/context/` / `../hxgtm-mcp-server/context/` | Actual files on disk |
| Plugin SKILL.md files | `Projects/Plugins/plugins/*/skills/*/SKILL.md` / `../hx-plugins/plugins/*/skills/*/SKILL.md` | Skill definitions, chain declarations, context loading patterns |
| Plugin fallback manifests | `Projects/Plugins/plugins/*/context/mcp-fallback.md` / `../hx-plugins/plugins/*/context/mcp-fallback.md` | Per-skill expected file lists for offline mode |
| Notion `Agents & Skills` page | Notion API via `mcp__claude_ai_Notion__notion-search` then `notion-fetch` | User-facing documentation |
| Git log | `git log` against `${mcp_source_root}` | File mtimes for temporal pre-filter |

### Architecture

The skill runs as an orchestrator with 3 parallel subagents:

- **Subagent A — Server Inspector** — runs Checks #1, #2, #3, #6, #8, #9
- **Subagent B — Plugin Inspector** — runs Checks #4, #5, #7
- **Subagent C — Notion Comparator** — runs Check #10 (only if Notion MCP available)

Phase 1 indexing happens inline in the orchestrator so all three subagents
can receive pre-parsed data instead of duplicating the parse work.

### Complexity

Low-to-medium. Every check is structural comparison and file existence
except Check #10's semantic sub-pass, which uses LLM reasoning gated behind
a temporal pre-filter (so most runs skip it for most skills).

### Where it lives

`.claude/skills/context-lint/` in this repo (`hxgtm-revops-pipelines`), alongside
`kb-lint`. Sibling skills with a clean division of responsibility — see
"Relationship to kb-lint" below.

---

## Relationship to kb-lint

These are sibling skills with a clean division of responsibility:

| | Context lint (this skill) | KB lint |
|---|---|---|
| **Focus** | Structural / efficiency | Semantic / consistency |
| **Question answered** | "Are the right files loaded, efficiently? Are the docs in sync?" | "Is the content in those files correct, current, and consistent?" |
| **LLM reasoning** | Only for Check #10 semantic sub-pass (gated by temporal pre-filter) | Required throughout |
| **Reads** | `src/context.ts`, plugin SKILL.md, fallback manifests, Notion docs | Canon `.md` files, raw source staging |
| **Speed** | Fast (deterministic for 9 of 10 checks) | Slow (LLM reasoning across ~120 files) |
| **Home** | `.claude/skills/context-lint/` (this repo) | `.claude/skills/kb-lint/` (this repo) |

Both skills are in this repo. They do NOT share code — each maintains its
own MCP-detection helper, file walker, and report formatter. The patterns
mirror each other (phase model, optimistic resolve with no pre-flight wall or
proceed gate, reactive error handling, non-blocking optional phases, output
format separation) but the implementations are independent so neither skill
becomes coupled to the other.

The context-lint Check #7 (Foundation coverage) intentionally overlaps with
kb-lint's coverage gap detection. The difference: this skill checks that the
*files exist* and follow naming conventions; kb-lint checks that the *content
is consistent and complete*. Both checks are valuable; neither replaces the
other.

---

## Appendix: Known Issues This Would Have Caught

Issues already confirmed during plan exploration that the lint will surface
on its first run:

| Issue | Check | Severity |
|---|---|---|
| `truth/audiences/coo-persona.md` exists but is unreferenced | #2 | Warning |
| `truth/audiences/actuary-job-profile-uk.md` exists but is unreferenced | #2 | Warning |
| `CONTEXT_PACKS["deep-personas"]` is defined but referenced by zero skills | #3 | Warning |
| `CONTEXT_PACKS["all-persona-guides"]` is defined but referenced by zero skills | #3 | Warning |
| `ads → polish` chain re-loads `truth/company/policies.md` + `guidance/anti-ai-guardrails.md` | #5 | Warning |

Issues from the original ads skill optimization (illustrative, may or may
not still apply depending on current state):

| Issue | Check | Severity |
|---|---|---|
| `truth/messaging/platform.md` referenced but does not exist | #1 | Error |
| All 3 persona packs loaded unconditionally (~287 lines) when only 1 needed | #6 | Warning |
| `load_skill_context` and `load_guidance` called sequentially despite being independent | #7 | Info |
| `marketing-strategy.md` (233 lines) loaded for ads where it adds negligible value | #8 | Warning |
L.md files,
fallback manifests, and the Notion `Agents & Skills` page. Produces a
severity-ranked markdown report.

## Quick start

```
/context-lint                       # Full audit, all 10 checks
/context-lint --checks=1,2,3        # Run a subset of checks
/context-lint --no-notion           # Skip Check #10 (Notion drift)
/context-lint --threshold=2000      # Override Check #8 size threshold
```

Output: `outputs/context-lint-YYYY-MM-DD.md`

A clean run means **0 errors and 0 warnings**. Every newly added skill or
context file should pass the audit before it ships.

---

## Setup in hxgtm-revops-pipelines (Claude Code CLI / IDE)

### Prerequisites

- **Claude Opus** — recommended for the orchestrator (matches kb-lint guidance)
- **Source layout** — context-lint resolves two independent sources, each with
  a production path and a local fallback:

  ```
  # Production layout (preferred)
  Projects/
  ├── MCP/                       ← src/context.ts + context tree
  └── Plugins/plugins/           ← */skills/*/SKILL.md + */context/mcp-fallback.md

  # Local-fallback layout (sibling clones)
  hx-projects/
  ├── hxgtm-revops-pipelines/    ← this repo
  ├── hxgtm-mcp-server/          ← MCP source
  └── hx-plugins/                ← plugin source
  ```

  Each source resolves independently — production MCP + local plugins is a
  valid combination. The skill stamps both source modes into the report header.

### How it works

The skill runs **optimistically** — no plan-mode prompt, no pre-flight wall, no
proceed gate. It starts straight into the work and surfaces a missing
dependency reactively at the step that needs it. It:

1. Resolves MCP server and plugin sources (production first, local fallback)
   to stamp the report header, and detects whether the Notion MCP is available
2. **Phase 1 — Index & parse** (inline) — parses `src/context.ts`
   (`SKILL_CONTEXTS`, `CONTEXT_PACKS`, `GUIDANCE_MAP`), walks the context
   tree, parses plugin `SKILL.md` files, parses each plugin's
   `mcp-fallback.md`, and (if Notion is enabled) fetches the `Agents & Skills`
   page
3. **Phase 2 — Audit** (parallel subagents) — Server Inspector, (if plugins
   source present) Plugin Inspector, and (if Notion enabled) Notion Comparator
   run their assigned checks
4. **Phase 3 — Synthesize report** (inline) — merge findings, build the
   per-skill breakdown, group actionable fixes, save the report
5. Saves to `outputs/context-lint-YYYY-MM-DD.md`

---

## Requirements

- **MCP server source** — `Projects/MCP/` (production) **OR**
  `../hxgtm-mcp-server/` (local fallback). The one hard requirement —
  context-lint cannot run without `src/context.ts` to audit. A genuinely
  unreachable source surfaces reactively at the first read (not as a
  pre-flight wall) and stops the run.
- **Plugins source** — `Projects/Plugins/plugins/` (production) **OR**
  `../hx-plugins/plugins/` (local fallback). **Best-effort / non-blocking** —
  if neither resolves, the Plugin Inspector (Checks #4/#5/#7) is skipped and
  the Server Inspector checks still run off `context.ts` + the context tree,
  producing a useful partial audit. The skip is acknowledged in the executive
  summary and Statistics section.
- **Notion MCP** — *optional*. Enables Check #10 (documentation drift)
  against the `Agents & Skills` page. **Non-blocking** — if the Notion MCP is
  unavailable, the user passes `--no-notion`, the page can't be found, or the
  fetch/parse fails, the lint runs to completion without Check #10. The skip
  is acknowledged in the executive summary and Statistics section.
- **Bash** (for `git log` mtime lookups in the temporal pre-filter) plus
  **Glob** and **Read** for filesystem walks.

---

## Source resolution

Two independent sources, each with the same production-first / local-fallback
rule:

| Source | Production (preferred) | Local fallback |
|---|---|---|
| MCP server (`context.ts` + context tree) | `Projects/MCP/` | `../hxgtm-mcp-server/` |
| Plugins (`SKILL.md` + `mcp-fallback.md`) | `Projects/Plugins/plugins/` | `../hx-plugins/plugins/` |

Rules:

- Each source is resolved **independently** — you can audit production MCP
  against local plugins, or any other combination
- Sources do **not** mix mid-audit — if production MCP is incomplete, the
  whole MCP source falls back to the local clone (no per-file mixing)
- Both source modes are stamped into the report header so the reader knows
  which world they're auditing
- If the **MCP server** source is unresolvable (neither production nor local),
  the run stops reactively at the first read — it is the one hard requirement.
  If the **plugins** source is unresolvable, the run continues with the Plugin
  Inspector skipped and the skip acknowledged in the report.

---

## Check catalogue

| # | Check | Severity | Subagent |
|---|---|---|---|
| 1 | Pack integrity (forward) — every referenced file exists on disk | Error | Server Inspector |
| 2 | Orphan files (reverse) — every `context/**/*.md` is referenced ≥1 place | Warning | Server Inspector |
| 3 | Orphan packs — every `CONTEXT_PACK` is used by ≥1 skill | Warning | Server Inspector |
| 4 | Fallback-to-server sync — `mcp-fallback.md` matches resolved `SKILL_CONTEXTS` | Warning (Error if file missing) | Plugin Inspector |
| 5 | Cross-skill chain duplication — chained skills not double-loading the same files | Warning | Plugin Inspector |
| 6 | Unconditional bulk loading — persona packs loading all variants when only one is used | Warning | Server Inspector |
| 7 | Parallelism opportunities — sequential MCP calls that could batch | Info | Plugin Inspector |
| 8 | Context size profiling — skills exceeding the line-count threshold | Warning | Server Inspector |
| 9 | Foundation coverage — audience ↔ messaging ↔ persona file wiring | Warning | Server Inspector |
| 10 | Notion documentation drift (semantic, gated by temporal pre-filter) | Mixed (Error structural, Warning semantic) | Notion Comparator |

Run a subset: `/context-lint --checks=1,2,3`

Skip Notion explicitly: `/context-lint --no-notion`

Override the size threshold for Check #8 (default `1500` lines):
`/context-lint --threshold=2000`

---

## Subagents

The skill orchestrates 2-3 parallel subagents during Phase 2:

| Subagent | Reference | Checks | Status |
|---|---|---|---|
| Server Inspector | [references/server-inspector.md](references/server-inspector.md) | #1, #2, #3, #6, #8, #9 | Always active |
| Plugin Inspector | [references/plugin-inspector.md](references/plugin-inspector.md) | #4, #5, #7 | Always active |
| Notion Comparator | [references/notion-comparator.md](references/notion-comparator.md) | #10 | Only if Notion MCP available |

Phase 1 indexing happens **inline in the orchestrator** so all subagents
receive pre-parsed indexes instead of duplicating the parse work.

In Claude Code, all enabled subagents launch simultaneously in a single
message. In Cursor, they launch sequentially.

---

## Notion check (Check #10) — non-blocking

Check #10 compares the user-facing Notion `Agents & Skills` page against
actual plugin SKILL.md behavior:

- **Structural drift** (Error) — a plugin skill has no Notion entry, or a
  Notion entry has no matching plugin skill
- **Semantic drift** (Warning) — purpose, inputs, outputs, or capabilities
  in the Notion description no longer match the SKILL.md after a temporal
  pre-filter shows the underlying context has changed

### How it activates

1. **Auto-detected at Step 2** by sniffing for any tool whose name
   contains `notion-search` (e.g., `mcp__claude_ai_Notion__notion-search`)
2. **Adaptively parses** the Notion page at runtime — no hardcoded layout
   assumptions, so it survives page restructures
3. **Page lookup by name** (`Agents & Skills`) — portable across workspaces

### Non-blocking guarantee

Check #10 is skipped — silently and without error — when:

- The Notion MCP isn't configured
- The user passes `--no-notion`
- The page can't be found in the workspace
- Detection itself fails for any reason
- The fetch / parse / search call fails mid-run

In every one of these cases, context-lint runs to completion with just the
Server Inspector (and the Plugin Inspector if its source resolved). The skip
is acknowledged in two places:

- The executive summary in Step 5
- The Statistics section (`Notion status: skipped (reason)`)

This matches the non-blocking pattern established by `kb-lint`'s Phase 3:
optional checks must never stop the lint from completing.

---

## Report format

The report follows a fixed structure (see
[references/output-format.md](references/output-format.md)):

1. **Header** — date, source modes, file/skill counts, finding counts,
   overall status (PASS / NEEDS ATTENTION / FAIL)
2. **Summary** — 2-3 sentence executive summary
3. **Per-skill breakdown** — table sorted by total line count, with category
   columns and over-threshold flags
4. **Errors** — every error finding with check number, file, suggested fix
5. **Warnings** — every warning finding
6. **Info** — every info finding
7. **Actionable fixes** — same findings re-grouped by fix type so a human
   can address related issues together
8. **Statistics** — counts and per-subagent status lines

### Severity classification

| Severity | Criteria |
|---|---|
| Error | Missing files referenced by `SKILL_CONTEXTS` / `CONTEXT_PACKS` / `GUIDANCE_MAP` / `mcp-fallback.md`; structural Notion drift (missing on either side) |
| Warning | Orphan files, orphan packs, fallback drift, chain duplication, bulk loading, size over threshold, foundation gaps, semantic Notion drift |
| Info | Parallelism opportunities |

---

## Relationship to kb-lint

context-lint and [kb-lint](../kb-lint/) are sibling skills with a clean
division of responsibility:

| | context-lint (this skill) | kb-lint |
|---|---|---|
| **Focus** | Structural / efficiency | Semantic / consistency |
| **Question answered** | "Are the right files loaded, efficiently? Are the docs in sync?" | "Is the content in those files correct, current, and consistent?" |
| **LLM reasoning** | Only Check #10 semantic sub-pass (gated by temporal pre-filter) | Required throughout |
| **Reads** | `src/context.ts`, plugin SKILL.md, `mcp-fallback.md`, Notion docs | Canon `.md` files, raw source staging |
| **Speed** | Fast (deterministic for 9 of 10 checks) | Slow (LLM reasoning across ~120 files) |

Both skills live in this repo. They follow the same patterns (phase model,
optimistic resolve with no pre-flight wall or proceed gate, reactive error
handling, non-blocking optional phases, output format separation) but share
**no code** — neither skill becomes coupled to the other. Check #9 (Foundation coverage) intentionally overlaps with
kb-lint's coverage gap detection: context-lint checks that the *files exist*
and follow naming conventions, kb-lint checks that the *content is consistent
and complete*.

---

## File structure

```
.claude/skills/context-lint/
├── SKILL.md                     ← Main orchestrator
├── PRD.md                       ← Design document
├── README.md                    ← This file
└── references/
    ├── server-inspector.md      ← Subagent A — Checks #1, #2, #3, #6, #8, #9
    ├── plugin-inspector.md      ← Subagent B — Checks #4, #5, #7
    ├── notion-comparator.md     ← Subagent C — Check #10 (conditional)
    └── output-format.md         ← Report structure specification
```
