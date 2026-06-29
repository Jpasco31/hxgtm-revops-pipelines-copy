# PRD: scaffold-skill

**Status:** Draft
**Author:** DS (spec), JP (PRD)
**Date:** 2026-04-11
**Skill location:** `.claude/skills/scaffold-skill/`

**Reference:** David's initial SKILL.md covers the 7-step wiring workflow and serves as the starting specification.

---

## 1. Problem

The GTM OS spans two interlocking repos with six wiring points that must all connect for a skill to work in production:

| # | Wiring Point | Repo |
|---|---|---|
| 1 | SKILL.md (skill definition + context loading block) | hx-plugins |
| 2 | Content-type playbook (editorial or lint-based guidance) | hxgtm-mcp-server |
| 3 | `context.ts` loader function + `SKILL_CONTEXT_MAP` entry | hxgtm-mcp-server |
| 4 | `GUIDANCE_MAP` entry per content type | hxgtm-mcp-server |
| 5 | Command wrapper(s) | hx-plugins |
| 6 | `mcp-fallback.md` section with accurate file counts | hx-plugins |

Plus three supporting updates: README index, save-to-Notion routing (if content-producing), and Notion "Agents & Skills" documentation.

Today, skills are created ad-hoc. Authors must remember every wiring point, copy-paste from existing skills, and manually count files for fallback manifests. Missing any single point causes a silent production failure — the skill appears to work but loads wrong context, can't fall back offline, or never triggers from a slash command. These failures are invisible until they reach a customer or until context-lint catches them after the fact.

The problem is compounded by:

- **No invocation path** — the scaffold-skill exists as a reference document but has no slash command, no conversational planning phase, and no pre-flight checks
- **No Notion documentation step** — skills ship without user-facing docs, immediately failing context-lint Check #10
- **No quality gate on descriptions** — poor trigger descriptions mean skills don't fire when users need them. Claude's built-in skill-creator has established best practices for this that scaffold-skill doesn't reference
- **No testing step** — scaffolded skills ship without any test cases to verify they trigger and behave correctly
- **Abbreviated content-type flow is a stub** — adding a content type to an existing skill requires reverse-engineering from the full 7-step workflow

---

## 2. Goal

Ship scaffold-skill as a runnable, conversational skill that generates everything needed for a new skill, content-type, or command wrapper to work correctly across both repos. The author provides a brief; the skill asks clarifying questions, presents a wiring plan for approval, executes across both repos, publishes documentation to Notion, and runs validation.

A cleanly scaffolded skill passes context-lint on first run with zero errors and zero warnings.

---

## 3. Scope

### In scope

| Capability | Description |
|---|---|
| **Full skill creation** | 7-step workflow: gather inputs → create SKILL.md → create playbooks → wire context.ts → create commands → update support files → validate |
| **Content-type-only creation** | Abbreviated flow for adding a format variant to an existing skill |
| **Conversational planning** | Step 0: ask targeted questions to fill gaps from a minimal brief, present wiring plan before touching files |
| **Pre-flight check** | Detect which repos are accessible (two-tier path resolution), report source modes |
| **Two-tier path resolution** | Check `Projects/` paths first, fall back to `../` local paths (same pattern as context-lint) |
| **Notion documentation** | Publish a skill entry to the "Agents & Skills" Notion page as part of the workflow |
| **Description quality enforcement** | Apply Claude skill-creator best practices: imperative form, 100-200 words, concrete trigger phrases, should-not-trigger redirects |
| **Test prompt generation** | Generate 3 realistic test prompts as a final step (what a user would say to invoke the skill) |
| **Validation** | Run `validate-context.sh` and cross-check against wiring checklist |
| **Slash command** | `/scaffold-skill` provided directly by `.claude/skills/scaffold-skill/SKILL.md` (auto-discovered) and documented in CLAUDE.md |

### Out of scope (v1)

- Automated trigger optimization (the `/skill-creator` eval loop — reference it, don't replicate it)
- Template cloning from existing skills (e.g., "like the LinkedIn skill but for X" — v1 always writes from the blank template; cloning is a v2 feature)
- Deleting or renaming existing skills (scaffold creates; a future `refactor-skill` could handle mutations)
- Cross-repo git commits (the skill creates/edits files; the author reviews and commits in each repo separately)
- Runtime testing of the scaffolded skill (that's the author's job post-scaffold)

---

## 4. Inputs

| Input | Required | Default | Notes |
|---|---|---|---|
| Brief | Yes | — | Free-text description of what the skill should do. Can be minimal ("case study skill for marketing") or detailed. |
| Mode | No | Auto-detected | `full-skill` or `content-type-only`. If the brief mentions an existing skill by name + a new format, auto-detect as content-type-only. |
| Target plugin | No | Inferred from brief | `hx-marketing`, `hx-sales`, `hx-sdr`, `hx-core`. If ambiguous, ask. |
| Chains to polish | No | Inferred | Yes for copy-producing skills, no for research/utility. If ambiguous, ask. |
| Notion DB IDs | No | Ask if needed | Working + Reference DB IDs for save-to-Notion routing. Only needed for content-producing skills. |

All other parameters (skill name, content types, MCP base context files, output format sections, command names) are gathered during the conversational planning phase (Step 0).

---

## 5. Output

The skill produces files across both repos plus a Notion entry:

### Full skill mode

**hx-plugins repo:**
- `plugins/<plugin>/skills/<skill-name>/SKILL.md`
- `plugins/<plugin>/commands/<command-name>.md` (one per command)
- Updated `plugins/<plugin>/context/mcp-fallback.md`
- Updated `README.md` (skill + command tables)

**hxgtm-mcp-server repo:**
- `context/<channel>/guidance/content-types/<name>.md` (one per content type)
- Updated `src/context.ts` (loader function + SKILL_CONTEXT_MAP + GUIDANCE_MAP entries)

**Notion:**
- New sub-page on the "Agents & Skills" page with skill name, purpose, trigger phrases, inputs, outputs, and plugin location

**This repo:**
- `.claude/skills/scaffold-skill/evals/<skill-name>-test-prompts.md` — 3 generated test prompts

**Validation:**
- `validate-context.sh` output (pass/fail)
- Wiring checklist results

### Content-type-only mode

**hxgtm-mcp-server repo:**
- `context/<channel>/guidance/content-types/<name>.md`
- Updated `src/context.ts` (`GUIDANCE_MAP` entry only)

**hx-plugins repo:**
- `plugins/<plugin>/commands/<command-name>.md` (optional)
- Updated `plugins/<plugin>/context/mcp-fallback.md` (new guidance key + incremented count)

**Validation:**
- `validate-context.sh` output

---

## 6. Workflow

### Step 0 — Plan mode check + conversational planning

**Plan mode gate:** If not in plan mode, prompt the user to switch. This is a multi-file, cross-repo operation — reviewing the plan before execution prevents wasted work.

**Conversational planning:** From the user's brief, determine what's known and what's missing. Ask targeted questions to fill gaps:

- Skill name (suggest kebab-case from the brief)
- Target plugin (infer from domain; confirm if ambiguous)
- One-line purpose
- Content types supported (each becomes a playbook + GUIDANCE_MAP entry)
- Whether it chains to polish (infer from skill type)
- Input types (required vs optional)
- Output format sections (suggest based on closest existing skill pattern)
- Command wrappers needed
- Whether it saves to Notion (if yes, need DB IDs)

**Convention-driven defaults:** For anything the user doesn't specify, derive from the closest existing skill. E.g., if the new skill is a marketing writing skill, default to the `linkedin` skill's context set + output pattern and let the author adjust.

### Step 1 — Pre-flight check

Three hard-stop checks. If any fail, print a clear message and refuse to proceed — no files are generated.

**1a. Repo access (two-tier detection):**
1. Check `Projects/Plugins/plugins/` → if missing, check `../hx-plugins/plugins/`
2. Check `Projects/MCP/src/context.ts` → if missing, check `../hxgtm-mcp-server/src/context.ts`

If either repo is unreachable via both paths, hard-stop.

**1b. Clean git state:**
Run `git status` in both repos. If either has uncommitted changes, hard-stop. The author must commit or stash before scaffolding — this ensures all scaffold-generated changes are isolated and revertible.

**1c. Notion MCP availability:**
Test Notion MCP connectivity (e.g., attempt `notion-search`). If unavailable, hard-stop. Every scaffolded skill must ship with Notion documentation.

Report source modes (production vs local for each repo) and proceed only when all three checks pass.

### Step 2 — Present wiring plan

Before creating any files, present a complete list of:

- Files to be created (with full paths, resolved to the detected source mode)
- Files to be modified (with what changes)
- Notion entry to be published
- Validation steps to run

Wait for user approval before proceeding.

### Step 3 — Create SKILL.md

Use `references/skill-template.md` as the base. Apply description quality rules from Claude's skill-creator:

- **Imperative form**: "Use this skill when..." not "This skill is for..."
- **100-200 words**: long enough for concrete triggers, short enough for always-in-context
- **Trigger phrases**: include 3-5 realistic phrases a user would say
- **Should-not-trigger redirects**: explicitly name skills that handle adjacent use cases
- **Progressive disclosure**: SKILL.md body under ~500 lines; move detailed content to `references/`

Enforce the mandatory section order from the template (frontmatter → context loading → mandatory workflow → purpose → when to use → inputs → detection → output format → examples → guidelines → quality gate → skill chaining).

### Step 4 — Create content-type playbooks

For each content type, select the correct template from `references/content-type-templates.md`:

- Editorial (Template 1) for social, web, ads
- Lint-based (Template 2) for email

Place in the correct MCP directory. Ensure YAML frontmatter `scope` slug exactly matches the planned `GUIDANCE_MAP` key.

### Step 5 — Wire context.ts (direct edit)

Edit `context.ts` directly with three changes:

1. **Loader function** — add `load<SkillName>Context()` using `joinContext()` after the last existing loader, before `SKILL_CONTEXT_MAP`. Select base context files by examining the closest existing skill's loader.
2. **SKILL_CONTEXT_MAP** — add entry with kebab-case key matching the skill name
3. **GUIDANCE_MAP** — add one entry per content type to the existing channel object (never duplicate top-level keys)

Because the pre-flight check ensures a clean git working tree, the author can review all `context.ts` changes via `git diff` and revert with `git checkout` if anything looks wrong.

### Step 6 — Create command wrappers

One `.md` file per command. Each sets a `Content-type:` header (if content-type-specific) and cats the SKILL.md via `${CLAUDE_PLUGIN_ROOT}`.

### Step 7 — Update support files

1. **mcp-fallback.md** — add skill section with accurate file counts (base + guidance = total)
2. **save-to-Notion routing** — add row to database routing table (content-producing skills only)
3. **README.md** — add to Skills table and Commands table

### Step 8 — Publish to Notion (required)

Create a new sub-page under the "Agents & Skills" parent page containing:

- Skill name and plugin
- One-line purpose (from SKILL.md description)
- Trigger phrases / "When to Use"
- Inputs (required + optional)
- Output description
- Command names
- Whether it chains to polish

Use the Notion MCP tools: `notion-search` to find the "Agents & Skills" parent page, then `notion-create-pages` to create the skill sub-page.

**This step is mandatory.** The pre-flight check (Step 1) verifies Notion MCP availability before any files are created. If Notion is unavailable, the entire workflow stops at Step 1 — no files are generated.

### Step 9 — Validate (auto-fix and report)

1. Run `validate-context.sh` — all file paths in `context.ts` must resolve
2. If validation fails, attempt to auto-fix the issue (e.g., correct a mistyped file path in `context.ts`, create a missing file from template). Re-run validation after each fix attempt.
3. Walk the wiring checklist (`references/wiring-checklist.md`) — all items must pass
4. Report results: list what passed, what was auto-fixed, and any remaining failures the author must address manually

### Step 10 — Generate test prompts

Generate 3 realistic test prompts that a user would say to invoke this skill:

- 1 straightforward invocation ("draft a case study for Zurich based on the recent win")
- 1 edge case or ambiguous phrasing ("can you write up the Zurich deal?")
- 1 should-not-trigger prompt that should redirect to a different skill

Save to a lightweight file alongside the skill. Reference the skill-creator for deeper trigger optimization if needed.

---

## 7. Content-Type-Only Workflow (abbreviated)

When adding a content type to an existing skill:

### Step 0 — Planning

Same conversational planning, but scoped: identify the existing skill, the new content type, the channel, and the playbook template to use. Present the smaller wiring plan.

### Step 1 — Pre-flight

Same two-tier path resolution and hard-stop checks.

### Step 2 — Create playbook

Select the correct template (editorial or lint-based). Place in the correct MCP directory.

### Step 3 — Wire GUIDANCE_MAP

Add one entry to the existing channel object in `context.ts`. Do NOT touch `SKILL_CONTEXT_MAP` or create a new loader function.

### Step 4 — Create command wrapper (if applicable)

Optional but recommended for specific-format content types. The `Content-type:` header must match the new `GUIDANCE_MAP` key.

### Step 5 — Update mcp-fallback.md

Add the new guidance key to the existing skill section. Increment the expected file count.

### Step 6 — Update Notion sub-page

Find the existing skill's sub-page under "Agents & Skills" using `notion-search`, then update it to include the new content type in its supported formats list.

### Step 7 — Validate

Run `validate-context.sh`. Confirm the new content type loads correctly via the existing skill's `load_guidance` call.

---

## 8. Source Resolution

Same pattern as context-lint:

| Source | Production (preferred) | Local fallback |
|---|---|---|
| MCP server + context tree | `Projects/MCP/` | `../hxgtm-mcp-server/` |
| Plugins (SKILL.md + commands + fallback) | `Projects/Plugins/plugins/` | `../hx-plugins/plugins/` |

Check production first. If any required file is missing, fall back to local **for the whole source**. The two sources resolve independently. Stamp both source modes into the wiring plan header.

### Safety: clean-state requirement

Before writing to either repo, the scaffold-skill **must verify both repos have a clean git working tree** (no uncommitted changes). This ensures:

- All scaffold-generated changes are isolated and visible in `git diff`
- The author can revert everything cleanly with `git checkout .` if something goes wrong
- No existing in-progress work is mixed with scaffolded files

If either repo has uncommitted changes, the skill prints a hard-stop message and refuses to proceed until the author commits or stashes their work.

---

## 9. Skill-Creator Integration (Medium)

The scaffold-skill borrows two high-value practices from Claude's built-in skill-creator (`~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/`):

### Description quality rules (Step 3)

Applied during SKILL.md creation, not as a post-hoc optimization:

- Use imperative/infinitive form throughout
- 100-200 word description with concrete trigger phrases
- Include "should-not-trigger" redirects to adjacent skills
- Explain the WHY behind instructions, not just the WHAT
- Prefer smart instructions over rigid MUSTs
- Progressive disclosure: SKILL.md body ≤500 lines, detail in `references/`

### Test prompt generation (Step 10)

Generate 3 realistic test prompts as the final scaffolding step. This provides a baseline for verifying the skill triggers correctly. For deeper optimization (automated trigger scoring, benchmark iteration, blind A/B comparison), reference the skill-creator:

> For trigger optimization and iterative improvement, use `/skill-creator` with the generated test prompts as a starting eval set.

---

## 10. Dependencies

| Dependency | Required | Purpose |
|---|---|---|
| File system access to both repos | Yes | Create/edit files across hx-plugins and hxgtm-mcp-server. Both must be local clones with clean git working trees. |
| `validate-context.sh` | Yes | Step 9 validation |
| Notion MCP | **Yes** | Step 8 Notion documentation. **Hard requirement** — if Notion MCP is unavailable, the workflow prints a hard-stop message and refuses to proceed. Every scaffolded skill must ship with Notion documentation; allowing undocumented skills defeats the purpose of controlled creation. |
| Claude Code CLI or IDE extension | Yes | Execution environment |

### Hard-stop conditions

The scaffold-skill refuses to proceed (no files generated) if **any** of these are missing:

1. **Either repo is unreachable** — both hx-plugins and hxgtm-mcp-server must be accessible via production or local fallback paths
2. **Either repo has a dirty git working tree** — uncommitted changes must be committed or stashed first
3. **Notion MCP is unavailable** — Notion documentation is a mandatory part of the scaffold output, not optional

The pre-flight check (Step 1) tests all three conditions and reports a clear message explaining what to fix before re-running.

---

## 11. Relationship to Other Skills

| | scaffold-skill | context-lint | skill-creator (built-in) |
|---|---|---|---|
| **Focus** | Creation / wiring | Audit / detection | Iteration / optimization |
| **Question answered** | "Are all files created and wired correctly?" | "Has wiring drifted since creation?" | "Is the skill triggering and performing well?" |
| **When to run** | When adding a new skill or content type | After changes, periodically, pre-merge | After scaffold, when optimizing |
| **Reads** | Existing skills (as templates), both repos | context.ts, SKILL.md files, Notion | The skill under test |
| **Writes** | SKILL.md, playbooks, context.ts, commands, fallback, Notion | Report only | Improved SKILL.md, evals |

The intended lifecycle: **scaffold-skill** creates → **context-lint** verifies → **skill-creator** optimizes.

---

## 12. What Exists Today

David's initial spec covers Steps 3-7 (create SKILL.md, playbooks, wire context.ts, commands, support files) with detailed templates and a wiring checklist. These are solid and should be preserved.

| Component | Status | Notes |
|---|---|---|
| `SKILL.md` (orchestrator) | Exists — needs extension | Missing: Step 0 (planning), Step 1 (pre-flight), Step 2 (plan presentation), Step 8 (Notion), Step 10 (test prompts). Paths hardcoded to `Projects/`. No slash command. |
| `references/skill-template.md` | Complete | Annotated, copy-ready. Add description quality rules. |
| `references/content-type-templates.md` | Complete | Both editorial and lint-based templates. No changes needed. |
| `references/wiring-checklist.md` | Exists — needs extension | Missing: Notion documentation checkpoint. |
| `/scaffold-skill` slash command | Provided by `.claude/skills/scaffold-skill/SKILL.md` | Skills auto-register as slash commands; no separate wrapper file needed. |
| CLAUDE.md entry | Does not exist | Needs row in the slash commands table. |
| Abbreviated content-type flow | Stub (5 bare bullets) | Needs expansion to match full workflow detail level. |

---

## 13. Resolved Decisions

| Question | Decision | Rationale |
|---|---|---|
| **Notion page structure** | Sub-pages under "Agents & Skills" parent | Each skill gets its own sub-page via `notion-create-pages` |
| **context.ts editing** | Edit directly | Clean git working tree requirement means changes are isolated and revertible via `git checkout` |
| **Cross-repo commits** | Author commits separately | The skill creates/edits files; the author reviews via `git diff` and commits in each repo on their own schedule |
| **Template cloning** | Not in v1 | Always scaffold from the blank template. "Like skill X but for Y" cloning is a v2 feature. |
| **Notion availability** | Hard requirement (blocks workflow) | Every scaffolded skill must ship documented. No Notion = no scaffold. |
| **Cross-repo writes** | Write directly to both repos | Requires local clones with clean git state. Author can revert with `git checkout .` if needed. |

| **Content-type-only Notion update** | Update the existing sub-page | The abbreviated flow finds the skill's existing Notion sub-page and adds the new content type to it, keeping docs in sync automatically. |
| **Validation failure handling** | Auto-fix and report | If `validate-context.sh` fails, the skill attempts to fix the issue (e.g., correct a file path in `context.ts`), then re-runs validation and reports results. |

## 14. Open Questions

1. **Notion sub-page template** — What sections/blocks should the skill's Notion sub-page contain? Should it mirror the SKILL.md structure, or is there an existing convention on the "Agents & Skills" page we should follow? Need to inspect the current page during implementation.
