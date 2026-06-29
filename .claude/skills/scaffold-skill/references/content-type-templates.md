# Content-Type Playbook Templates

Two templates depending on the channel type. Annotation lines beginning with `# →` are instructions — delete before saving.

---

## Template 1 — Editorial Playbook

Use for: social (LinkedIn/X), web, ads content types.

These playbooks define structure, voice, and editorial standards. They are loaded on-demand via `load_guidance` when the skill detects the content type.

```markdown
---
type: guidance
scope: [<content-type-slug>]
# → slug must exactly match the GUIDANCE_MAP key in context.ts
last_reviewed: <YYYY-MM-DD>
---

# Content type — <Display Name> (<Channel>)

**Definition:** <One sentence defining what this content type is.>
**Purpose:** <What job it does for the reader or business. One sentence.>
**Author voice:** <Company / Exec / Company or Exec / Named expert>
**When to use:** <The situation that calls for this type.>

---

## Core Principle

**<A single bolded sentence distilling the editorial philosophy for this type.>**

# → One sentence, bolded. This is the line a writer internalises above all others.
# → Example: "An events landing page is a decision page."
# → Example: "Blog promo posts should teach or provoke — not announce."

---

## Required Structure

### 1. <Section name>

**Purpose**
<What this section achieves for the reader.>

**Guidelines**
- <Rule 1>
- <Rule 2>
- <Format or length constraint>

**Avoid**
- <Anti-pattern 1>
- <Anti-pattern 2>

---

### 2. <Section name>

**Purpose**
<What this section achieves.>

**Guidelines**
- <Rule 1>
- <Rule 2>

**Avoid**
- <Anti-pattern 1>

---

### 3. <Section name> (Mandatory)
# → Mark mandatory sections explicitly. Readers scan for this.

<...>

---

## Do's and Don'ts

**Do:**
- <Positive rule 1>
- <Positive rule 2>
- <Positive rule 3>

**Don't:**
- <Anti-pattern 1>
- <Anti-pattern 2>
- <Anti-pattern 3>

---

## Formats
# → Optional section. Include only for content types with multiple visual formats.
- <Format 1 (e.g., Carousel, Loom clip, Text post)>
- <Format 2>

**Repurpose:** <How to extend this content type into related formats.>

---

## Tone + Style Checklist

- ✅ <Positive requirement>
- ✅ <Positive requirement>
- ✅ <Positive requirement>
- ✅ No buzzwords or vague abstractions
- ✅ Human, conversational tone
- ✅ Scannable structure (headings, bullets, white space)

---

## Success Signals
# → Optional section. Include when meaningful engagement signals exist.
- <Signal 1 (e.g., Saves, Demo requests, Click-through rate)>
- <Signal 2>

---

## Final QA Checklist
# → Optional but recommended for web and structured content types.

Before publishing, confirm:

- [ ] <Requirement 1>
- [ ] <Requirement 2>
- [ ] <Requirement 3>

---

## Enforcement

This structure is enforced by the <skill-name> skill when `content_type = <content-type-slug>`.

## Related Documentation

- **<Reference type>:** See `<path-to-file>`
- **Annotated examples:** See `examples/labeled/<content-type-slug>.md` (selective loading only)
# → "selective loading only" means the file is not in always-on context — loaded via load_guidance("examples").
```

---

## Template 2 — Lint-Based Playbook

Use for: email content types.

These playbooks define numbered lint rules with severity, detection patterns, and deterministic rewrite macros. They are loaded on-demand via `load_guidance`.

```markdown
---
type: guidance
scope: [<content-type-slug>]
last_reviewed: <YYYY-MM-DD>
---

# Content type — <Display Name> (Email)

<One paragraph defining what this email type is. State the primary job of this email type in plain terms: what it triggers on, what it delivers, and what success looks like.>

---

## Subject Line Guidance
# → Short section. Cross-reference the email best-practices file for general tactics.
# → Focus only on what's specific to this type.

<1–3 sentences on what makes subject lines work for this type. Reference the shared best-practices file for general tactics.>

---

## Lint Rules

### <TYPE-ABBREV>-001: <Rule Name>
**Severity**: <blocker / high / medium / low>
**Detection**: <Observable pattern that triggers this rule — be specific enough for automated detection>
**Why it matters**: <Why this hurts the email — reader psychology or compliance reason>
**Fix**: <Exact, actionable instruction. Not "improve X" — "move X to the top 3 lines.">

### <TYPE-ABBREV>-002: <Rule Name>
**Severity**: <blocker / high / medium / low>
**Detection**: <Detection pattern>
**Why it matters**: <Reason>
**Fix**: <Exact fix>

# → Severity scale:
#    blocker  — legal/compliance issue, or single fatal flaw that makes email unusable. Must fix.
#    high     — significantly reduces conversion or trust. Should fix.
#    medium   — reduces quality. Address before sending.
#    low      — polish-level issue. Fix if time allows.
#
# → Use a consistent abbreviation prefix for the rule IDs (e.g., TXN for transactional,
#    LIFE for lifecycle, EVT for event-marketing, PRE for press-release, etc.)
#
# → Aim for 6–10 rules. Fewer if the type is simple; more if enforcement is complex.

### <TYPE-ABBREV>-003: <Rule Name>
**Severity**: medium
**Detection**: <Detection pattern>
**Why it matters**: <Reason>
**Fix**: <Exact fix>

**Blacklisted phrases (<type name>):**
# → Add a blacklisted-phrases list inside a rule when a rule targets specific vocabulary.
- "<phrase 1>"
- "<phrase 2>"
- "<phrase 3>"

---

## Rewrite Macros

Macros are named, deterministic rewrite procedures applied when a specific lint rule fires.

### Macro 1: <Macro Name>
**When**: <Which rule triggers this / detection condition>
**Action**:
1. <Step 1>
2. <Step 2>
3. <Step 3>

### Macro 2: <Macro Name>
**When**: <Detection condition>
**Action**:
1. <Step 1>
2. <Step 2>

# → Each macro should map to one or more lint rules.
# → Steps should be concrete enough that a different AI instance produces consistent output.

---

## Sequence Escalation Logic (if applicable)
# → Include only for content types that appear in multi-email sequences.
# → Describe the job each position in the sequence should do.

For multi-email sequences, each email should have a distinct job:

1. **Email 1**: <Job>
2. **Email 2**: <Job>
3. **Email 3**: <Job>

**Sequence violations to flag:**
- <Violation 1>
- <Violation 2>

---

## Modified Rule Application (for follow-up emails in a sequence)
# → Include only when certain rules don't apply after the first email in a sequence.

If the email is part of a sequence but the asset/action was already delivered in a prior email, some rules do not apply:

**DO NOT apply to follow-up emails:**
- **<RULE-ID>** (<Rule Name>) — <why it doesn't apply>

**DO apply:**
- **<RULE-ID>** — still critical
- **<RULE-ID>** — still critical

---

## Tone & Voice

- **<Tone quality 1>** (e.g., Calm, confident, helpful)
- **<Tone quality 2>** (e.g., Direct and specific)
- **<Tone quality 3>** (e.g., Human — avoid automation language)
- **<Tone quality 4>** (e.g., Respectful of time — brief, scannable)

---

## Example: Good <Type Name>

**Subject**: <Example subject line>

**Body**:
<Example email body — short, realistic, showing the rules working correctly.>

---

## Example: Bad <Type Name>

**Subject**: <Bad example subject>

**Body**:
<Bad example body showing common violations.>

**Issues**: <Comma-separated list of rule violations this example triggers.>
```

---

## Choosing the Right Template

| Situation | Template |
|-----------|----------|
| LinkedIn post format | Template 1 (Editorial) |
| Web landing page type | Template 1 (Editorial) |
| Ad format | Template 1 (Editorial) |
| Workflow (task-level instructions, not a content format) | Template 1 (adapted — omit tone checklist, success signals) |
| Marketing email type | Template 2 (Lint) |
| Personal sales email type | Template 2 (Lint — stored in `platform/guidance/email/`) |
| Sales one-pager / account brief | Template 1 (Editorial) |

## Where to Store the File

> **Path note:** Base directories are listed in the production CoWork
> layout. Substitute `../hxgtm-mcp-server/context/...` for
> `Projects/MCP/context/...` when running from a sibling checkout.

| Channel | Base directory |
|---------|----------------|
| Social | `Projects/MCP/context/marketing/guidance/social/content-types/` |
| Email (marketing) | `Projects/MCP/context/marketing/guidance/email/content-types/` |
| Web | `Projects/MCP/context/marketing/guidance/web/content-types/` |
| Ads | `Projects/MCP/context/marketing/guidance/ads/content-types/` |
| Workflow | `Projects/MCP/context/marketing/guidance/workflows/` |
| Personal sales email | `Projects/MCP/context/platform/guidance/email/` |
| Sales (one-pagers, briefs) | `Projects/MCP/context/sales/guidance/content-types/` |

### Sub-variant naming (company vs exec, full vs short-form)

When a content type has meaningful voice or format variants, use a subdirectory:

```
content-types/
└── product-announcement/
    ├── company.md     # GUIDANCE_MAP key: "product-announcement-company"
    └── exec.md        # GUIDANCE_MAP key: "product-announcement-exec"
```

Single-variant types use a flat file:

```
content-types/
└── product-use-case.md    # GUIDANCE_MAP key: "product-use-case"
```

## GUIDANCE_MAP Key Naming Conventions

| Pattern | Example slugs |
|---------|---------------|
| Flat file | `product-use-case`, `transactional-nurture`, `events-landing-page` |
| Sub-variant (company) | `product-announcement-company`, `blog-promo` (company is default) |
| Sub-variant (exec) | `product-announcement-exec`, `expert-video-exec` |
| Sub-variant (short-form) | `event-recap-short` |
| Examples (selective loading) | `examples` (always the key name — never load by default) |

The `examples` key is reserved across all channels for labeled annotated examples. Only load when the user explicitly asks to see examples.
