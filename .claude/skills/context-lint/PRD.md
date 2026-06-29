# PRD: Context Lint

*Created: 2026-04-04*
*Updated: 2026-04-10 — reduced noise from first full run: Check #2 groups orphans by cluster and excludes custom-loader files; Check #7 emits single grouped finding; Check #9 simplified to persona writing-guide and GUIDANCE_MAP coverage; Check #10b downgrades multi-repo plugins to Warning; Check #10c pre-filter is a silent count.*

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
  `SKILL_CONTEXTS`, `CONTEXT_PACKS`, or `GUIDANCE_MAP` entry
- Excluded from this check: `_template-*.md`, `README.md`, files under
  `**/data/` (raw data, not narrative content), and files loaded by custom
  functions in `context.ts` (e.g., `guidance/competitive/competitors/*.md`
  loaded by `loadCompetitorData()`)
- Orphan files are **grouped by directory cluster** (one finding per
  cluster) to reduce noise. Solo orphans get individual findings.

**Severity: Warning.** Reported by Server Inspector (Subagent A).

**Real example to be caught on day one:** `truth/audiences/coo-persona.md`
exists but is referenced by nothing in `SKILL_CONTEXTS` or `GUIDANCE_MAP`.

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

Verify that every audience persona has complete wiring across the persona
ecosystem. These are file-existence checks, not semantic analysis.

- For every audience file in `context/truth/audiences/`, verify a
  corresponding writing guide exists under `marketing/persona-guides/`
- For every audience persona, verify matching entries exist in both
  `GUIDANCE_MAP["personas"]` and `GUIDANCE_MAP["persona-guides"]`

**Severity: Warning.** Reported by Server Inspector (Subagent A).

### 10. Notion documentation drift

- Look up the Notion `Agents & Skills` page by name (portable across
  workspaces)
- Adaptively parse the page structure at runtime (no hardcoded layout
  assumptions)
- For each plugin skill, verify a corresponding Notion entry exists
  (structural)
- For each Notion entry, verify a corresponding plugin skill exists
  (structural). If the entry belongs to a plugin sub-page whose skills
  live in a separate repo outside the configured plugins source, downgrade
  from Error to Warning.
- For matched pairs, run a temporal pre-filter: if no underlying context
  file has changed since the Notion block's `last_edited_time`, skip the
  semantic check silently (count in statistics, no individual findings)
- For surviving pairs, use LLM reasoning to compare the Notion description
  against the actual SKILL.md description, "When to Use", and resolved
  context. Flag semantic drift (purpose, inputs, outputs, capabilities).

**Severity: Error** for structural drift (plugin skill missing from Notion),
**Warning** for Notion entries in multi-repo plugins not found in configured
source, **Warning** for semantic drift. Reported by Notion Comparator
(Subagent C).

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
