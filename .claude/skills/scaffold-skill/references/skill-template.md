# GTM OS SKILL.md Template

Annotated, copy-ready template. Replace every `<placeholder>` with real values.
Annotation lines beginning with `# →` are instructions — delete them before saving.

---

## Template

```markdown
---
name: <skill-name>
# → kebab-case, e.g. edit-press-release, draft-case-study
description: "<One-sentence summary of what the skill does and when to use it. NOT for creating X from scratch. Use for Y and Z. Trigger phrases: 'review a ...', 'improve a ...', 'draft a ...'>"
# → Quoted string. Include both WHAT (capability) and WHEN (trigger phrases).
---

## Context Loading

Call `load_skill_context` with skill `"<skill-name>"` to load base context.

# → Replace <skill-name> with the exact key registered in SKILL_CONTEXT_MAP in context.ts.
# → Then list each content-type load_guidance call. Copy the pattern below for each type.

Based on the detected <content type / mode>, call `load_guidance` with category `"<channel>"` and the matching content type:
- `"<content-type-slug-1>"` for <description of when to use it>
- `"<content-type-slug-2>"` for <description of when to use it>
- `"examples"` only when user explicitly requests examples

# → Channel values: "social", "email", "web", "ads", "voice-guides", "personas", "persona-guides", "personal-email"
# → If the skill has no content-type variants (e.g. polish, punch-up), omit the load_guidance lines entirely.

If either MCP tool is unavailable: STOP. Do not generate any output. Do not attempt to work from the task content alone. The context files contain mandatory brand guardrails, quality standards, and messaging constraints that are required for compliant output - they cannot be substituted by the content submitted by the user. Follow the fallback procedure in `${CLAUDE_PLUGIN_ROOT}/context/mcp-fallback.md` and do not proceed until all context files are loaded.

## Mandatory Workflow

This skill always runs in two sequential steps. Do not combine them.

1. **<Skill Name> skill** — follow the instructions in this skill
2. **Polish skill** — once step 1 is complete, check for the polish skill at `${CLAUDE_PLUGIN_ROOT}/skills/polish/SKILL.md` and run it on the <final output label>

Step 2 must always run after step 1. Skipping or merging them is a critical failure. See **Skill Chaining** at the bottom of this file for the exact behavior.

# → "final output label" examples: "Final Post", "final email rewrite", "Final Copy", "final output"
# → If the skill does NOT chain to polish (research skills, save skills, utility skills), delete this entire
#    "## Mandatory Workflow" section entirely. Do not leave it empty.

# ─────────────────────────────────────────────────────────────────────────────
# SKILL BODY STARTS HERE
# ─────────────────────────────────────────────────────────────────────────────

# <Skill Display Name>
# → Use title case. This is what users and the system see as the skill heading.

## Purpose
<2–3 sentences. What the skill does, what problem it solves, what it produces.>
# → Do NOT include what the skill does NOT do here — save that for When to Use.

## When to Use
- <Use case 1>
- <Use case 2>
- <Use case 3>
# → Include explicit redirects if relevant. Example:
#    > **Personal sales emails** (1:1 outreach from a named rep) are handled by the `draft-outreach` skill.

## Inputs

### Required
- **<Input name>**: <description>
- **<Input name>**: <description>

### Optional (if provided, must be used)
- <input>: <description>
- <input>: <description>
# → Use this exact two-section structure. If everything is required, omit the Optional section.
# → If any optional input changes output behavior, note it with "(if provided, must be used)"

## <Content-Type Detection / Mode Detection>
# → Include this section only if the skill behaves differently based on detected input type.
# → For email: this is "Content-Type Detection" with heuristic fallback rules.
# → For ads: this is "Mode Detection" (Draft / Improve / Critique / Examples).
# → For simple skills with no detection logic, omit this section.

<Detection rules...>

## Output Format

For each <request type>, return sections in this **exact order**:

1. **<Section Name>**
   - <What goes here>
   - <Format notes>

2. **<Section Name>**
   - <What goes here>

3. **<Section Name>**
   - <What goes here>

4. **<Final Output Label>**
   - Complete, copy-ready <output type>
   - <Any format constraints>

5. **<Section Name>** (optional)
   - Only include when <condition>

# → "exact order" is literal. Skills enforce section order strictly.
# → Mark optional sections clearly with "(optional)" and a condition.
# → The copy-ready output section should always be second-to-last or last.

## Examples

### Example 1: <User intent / scenario>
User: <What the user says>
Assistant: <Describes what the skill does — detection, guidance loaded, key decisions, output produced.>

### Example 2: <User intent / scenario>
User: <What the user says>
Assistant: <...>

### Example 3: <User intent / scenario — edge case or redirect>
User: <What the user says>
Assistant: <...>

# → 2–4 examples is standard. Include at least one edge case or redirect if applicable.
# → Examples should be realistic — use plausible content from the insurance/hx domain.
# → Don't write out full copy in examples — describe what the assistant produces.

## Guidelines
- <Behavioral rule 1>
- <Behavioral rule 2>
- Load content-type playbooks via `load_guidance` with category `"<channel>"` and the detected content type
- If the <type> is ambiguous or cannot be inferred from the user's input, use AskUserQuestion to present the available content types. If the user selects a type with no matching playbook, state that no playbook exists for that type
- <Anti-rule: what the skill does NOT do>
- <Skill-chaining redirect: "For X, use the Y skill instead">

# → Include the load_guidance instruction if the skill uses content-type routing.
# → Include the AskUserQuestion fallback instruction if there are cases where the content type is ambiguous.

## Quality Gate
Before outputting final copy, apply all anti-AI writing rules from the loaded context. Key requirements:
- Remove padding/filler and avoid banned AI vocabulary
- Use human pacing (varied sentence length, active voice)
- No meta commentary ("In this post..." / "Let's explore...")
- Light formatting only (no template look)

# → This block is identical across all writing skills. Copy verbatim. Adjust the meta commentary
#    examples to match the skill's output type if useful (e.g., "In this email..." for email skills).
# → For non-writing skills (research, save, utility), omit this section.

## Skill Chaining — Required Final Step

After completing this skill, check for the polish skill at:

`${CLAUDE_PLUGIN_ROOT}/skills/polish/SKILL.md`

**If the file exists:** read it and apply it to the <final output label> as a separate sequential step. Output only the polished result.

**If the file does not exist:** do not proceed as if it ran, and do not apply polish criteria inline as a substitute. Open your response with this warning before showing any output:

> ⚠️ **Polish skill not found** at `${CLAUDE_PLUGIN_ROOT}/skills/polish/SKILL.md`. This output has not been through a final QA pass. Install the `polish` skill and re-run for a fully reviewed result.

Then output the pre-polish <final output label>. Do not label it as polished.

# → This block is identical across all chaining skills. Replace <final output label> with the
#    same label used in "## Mandatory Workflow" and "## Output Format" (e.g., "Final Post",
#    "final email rewrite", "Final Copy", "final output").
# → If the skill does NOT chain to polish, delete this entire section.
```

---

## Section-by-Section Notes

### YAML Frontmatter

The `description` field is used by Cursor to decide when to surface this skill. Write it as:
> "[Verb phrase what it does]. Use when [trigger scenario 1], [trigger scenario 2]. NOT for [redirect case]."

### Description Quality Rules

These rules are borrowed from Claude's built-in skill-creator and enforced during scaffolding:

- **Imperative form**: "Use this skill when..." not "This skill is for..."
- **100-200 words**: long enough for concrete trigger phrases, short enough for always-in-context
- **3-5 trigger phrases**: realistic things a user would say (e.g., "draft a...", "review the...", "create a...")
- **Should-not-trigger redirects**: explicitly name adjacent skills (e.g., "NOT for personal sales emails — use `draft-outreach`")
- **WHY over WHAT**: explain the reason behind instructions, not just the rule
- **Progressive disclosure**: SKILL.md body ≤500 lines; move detailed content to `references/`

### Context Loading Block

The `load_skill_context` key must exactly match the key in `SKILL_CONTEXT_MAP` in `context.ts`. The keys for existing skills are:

| Skill name | `load_skill_context` key |
|------------|--------------------------|
| linkedin | `"linkedin"` |
| email | `"email"` |
| web-copy | `"web-copy"` |
| ads | `"ads"` |
| blog | `"blog"` |
| press-release | `"press-release"` |
| draft-outreach | `"draft-outreach"` |
| polish | `"polish"` |
| punch-up | `"punch-up"` |
| booth-copy | `"booth-copy"` |
| create-faq | `"create-faq"` |
| clip-podcast | `"clip-podcast"` |
| brainstorm | `"brainstorm"` |
| battle | `"battle"` |
| ask-an-actuary | `"ask-an-actuary"` |

The MCP fallback hard-stop block is always verbatim — copy it exactly from any existing skill. Do not paraphrase.

### Mandatory Workflow Block

Present only when the skill chains to `polish`. If the skill has no chaining, this section is omitted entirely. The two skills that orchestrate other skills (like `webinar-campaign`) replace this with a numbered multi-step workflow block instead.

### Output Format

The section numbers in Output Format map directly to what users see in the response. Changing the order after launch is a breaking change. Get it right the first time by reviewing the existing skill most similar to yours.

Common Output Format patterns:

**Editorial/social pattern** (linkedin, web-copy, ads):
1. Content Type / Page Type / Format & Mode
2. Quick Take / Strategic Angle
3. What Works
4. Key Choices
5. Final Post / Final Copy / Final Output
6. Strategic Notes (optional)

**Review/lint pattern** (email, blog):
1. Overall Severity / Assessment
2. What Works Well
3. Key Improvements
4. Polished Rewrite / Improved Output
5. Additional Notes (optional)

**Research pattern** (find-strategic-priorities, battle):
No fixed output format section — output is a structured table or report defined inline.

### Skill Chaining Block

The chaining block is verbatim across all skills that chain to polish. The only variable is the `<final output label>` — use the exact same label from your Output Format section. Existing values in use:
- `the Final Post`
- `the final email rewrite`
- `the Final Copy`
- `the final output`
