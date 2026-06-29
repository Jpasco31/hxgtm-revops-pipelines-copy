# GTM OS Skill Wiring Checklist

Use this after completing all steps for a new skill or content type. Every item must pass before the work is considered production-ready.

> **Path note:** This checklist names paths in the production CoWork layout
> (`Projects/Plugins/...`, `Projects/MCP/...`). When running from a sibling
> checkout (e.g. `~/Desktop/Huw/hx-projects/`), substitute `../hx-plugins/`
> for `Projects/Plugins/` and `../hxgtm-mcp-server/` for `Projects/MCP/`.
> The skill's runtime auto-detects the correct root — the substitution is
> only needed when manually following this checklist.

---

## Full Skill Checklist

### 1. Plugin Skill File

- [ ] `Projects/Plugins/plugins/<plugin>/skills/<skill-name>/SKILL.md` exists
- [ ] YAML frontmatter has `name` and `description` fields
- [ ] `name` matches the directory name exactly
- [ ] `description` includes trigger phrases (what a user would say)
- [ ] `## Context Loading` block is present
  - [ ] `load_skill_context` call uses correct skill key (matches `SKILL_CONTEXT_MAP` key in `context.ts`)
  - [ ] `load_guidance` calls listed for each supported content type
  - [ ] MCP fallback hard-stop paragraph is present verbatim
- [ ] `## Mandatory Workflow` block is present (if skill chains to polish) OR omitted entirely (if not)
- [ ] `## Output Format` section lists sections in a numbered, fixed order
- [ ] `## Examples` section has at least 2 examples
- [ ] `## Quality Gate` block present (if writing skill) OR omitted (if not)
- [ ] `## Skill Chaining — Required Final Step` block present (if chaining to polish) OR omitted (if not)
- [ ] All `${CLAUDE_PLUGIN_ROOT}` path references resolve (e.g., `skills/polish/SKILL.md` exists)
- [ ] No second-person writing ("you should..." → use imperative form)

### 2. MCP Content-Type Playbook

- [ ] Playbook file(s) exist at the correct path(s) in `Projects/MCP/context/`
- [ ] YAML frontmatter has `type: guidance`, `scope: [<slug>]`, `last_reviewed: <date>`
- [ ] `scope` slug exactly matches the `GUIDANCE_MAP` key in `context.ts`
- [ ] Template type is correct for the channel (Editorial for social/web/ads; Lint-based for email)
- [ ] If sub-variants exist (company/exec), both files exist and have distinct GUIDANCE_MAP keys
- [ ] No references to internal tool names, skill enforcement language, or workflow logic inside a content-type file (content-types are editorial guidance only)

### 3. context.ts — SKILL_CONTEXTS Entry

- [ ] New entry added to the `SKILL_CONTEXTS` object in `Projects/MCP/src/context.ts`
  - [ ] Entry uses existing packs where possible (e.g., `pack:marketing-content-base`)
  - [ ] All referenced files actually exist on disk at the paths given
  - [ ] File paths are relative to `context/` (no leading slash, no `context/` prefix)
- [ ] Key is lowercase with hyphens, matches the skill's directory name exactly
  - [ ] Key matches the string used in the skill's `load_skill_context` call exactly
- [ ] No separate `SKILL_CONTEXT_MAP` registration — it is auto-generated from `SKILL_CONTEXTS` keys via `Object.fromEntries(...)`

### 4. context.ts — GUIDANCE_MAP

- [ ] New content-type entries added to `GUIDANCE_MAP`
  - [ ] Added to existing channel object (not a duplicate top-level key)
  - [ ] Each slug key matches the `load_guidance` call in the SKILL.md exactly
  - [ ] Each file path is correct and the file exists on disk
  - [ ] `examples` key present if the skill will ever load labeled examples

### 5. MCP Fallback File

- [ ] Skill section added to `Projects/Plugins/plugins/<plugin>/context/mcp-fallback.md`
- [ ] Section heading matches the skill name exactly
- [ ] Expected file count is accurate:
  - [ ] Base context file count matches the resolved file count of the `SKILL_CONTEXTS` entry (with packs expanded)
  - [ ] Guidance file count matches the number of `GUIDANCE_MAP` entries
  - [ ] Total = base + guidance count
- [ ] All file paths listed match what's in `context.ts` exactly
- [ ] All guidance slugs listed match `GUIDANCE_MAP` keys exactly

### 6. Save-to-Notion Routing (content-producing skills only)

- [ ] New row added to the Database Routing table in `Projects/Plugins/plugins/hx-marketing/skills/save-to-notion/SKILL.md`
  - [ ] Skill name matches exactly
  - [ ] Display type label is human-readable (e.g., "Press release")
  - [ ] Working DB ID is a valid Notion database ID (32 hex chars, no hyphens)
  - [ ] Reference DB ID is a valid Notion database ID
- [ ] Content Type Detection section updated with the new skill's type and sub-type logic
- [ ] If skill is not content-producing (research, utility, save), this section is skipped

### 7. README Index

- [ ] Skill added to the correct plugin's **Skills** table in `Projects/Plugins/README.md`
  - [ ] Skill name in bold
  - [ ] Description matches the SKILL.md `description` field (or a shortened version)

### 8. Context Validator

- [ ] `cd Projects/MCP && bash scripts/validate-context.sh` exits with no errors
  - [ ] All file paths in `context.ts` resolve to real files on disk
  - [ ] If any paths fail, fix them in `context.ts` before considering the skill complete

### 6e. Notion Documentation

- [ ] Skill sub-page created under "Agents & Skills" in Notion
  - [ ] Contains skill name, plugin, purpose, trigger phrases
  - [ ] Contains inputs (required + optional), output description
  - [ ] Contains command names and polish chain status
  - [ ] Description semantically matches SKILL.md `description` field

---

## Content-Type Only Checklist (abbreviated)

When adding a content type to an existing skill (no new SKILL.md):

- [ ] Playbook file exists at the correct path in `Projects/MCP/context/`
- [ ] YAML frontmatter correct (type, scope slug, last_reviewed)
- [ ] `GUIDANCE_MAP` entry added to the correct channel object in `context.ts`
  - [ ] Slug key matches the `load_guidance` call in the existing SKILL.md
  - [ ] File path is correct
- [ ] `mcp-fallback.md` updated
  - [ ] New guidance key added to the skill's guidance section
  - [ ] Expected count incremented
- [ ] Existing skill's Notion sub-page updated to include new content type
- [ ] `validate-context.sh` passes

---

## Common Failure Modes

| Failure | Cause | Fix |
|---------|-------|-----|
| Skill loads wrong context | `load_skill_context` key in SKILL.md doesn't match the `SKILL_CONTEXTS` entry key | Make keys identical, case-sensitive |
| Guidance not loaded | `load_guidance` slug in SKILL.md doesn't match `GUIDANCE_MAP` key | Match slug exactly, including hyphens |
| Context file not found at runtime | Path in `context.ts` is wrong | Run `validate-context.sh` and fix mismatches |
| Fallback count wrong | `mcp-fallback.md` expected count doesn't reflect actual file count | Count resolved files in the `SKILL_CONTEXTS` entry (packs expand inline); count guidance entries; update total |
| Polish chain broken | SKILL.md references polish at wrong path | Always use `${CLAUDE_PLUGIN_ROOT}/skills/polish/SKILL.md` |
| Notion save fails silently | Skill not in `save-to-notion` routing table | Add row to routing table with correct DB IDs |
| Validator fails | New context file path doesn't exist on disk | Create the file first, then add the path to `context.ts` |

---

## Quick Reference: Existing Keys

The authoritative list of `SKILL_CONTEXTS` keys and `GUIDANCE_MAP` channel keys lives in `${mcp_source_root}src/context.ts`. This file is **not** kept in sync — read the source before choosing a new key.

To list current `SKILL_CONTEXTS` and `GUIDANCE_MAP` keys:

```bash
grep -nE '^\s+"[a-z-]+":' ${mcp_source_root}src/context.ts
```

New skill keys must be unique. Use the skill's kebab-case directory name as the key. Add new content types to existing channel keys in `GUIDANCE_MAP`; create a new top-level key only when scaffolding a content type in a new channel (e.g., sales, platform).
