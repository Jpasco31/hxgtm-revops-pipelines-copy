---
name: newsletter-generator
description: >
  Generate a lightweight markdown newsletter from a topic/title plus a handful
  of items or links. Use when the user asks to create a newsletter, draft a
  newsletter, generate a GTM/team newsletter, or assemble update items into a
  newsletter. Outputs a single markdown file to outputs/newsletter-generator/.
  Intentionally minimal — no scripts, no external services.
---

# Newsletter Generator

A small, self-contained skill that turns a topic plus a few update items into a
clean markdown newsletter.

## What this skill does

Given a title/topic and an optional list of items (each a short headline with a
one- or two-sentence blurb and an optional link), this skill assembles a
formatted markdown newsletter and writes it to disk. If the user provides only a
topic, generate 3–5 plausible items inline so the output is still complete. No
external research, MCP calls, or publishing — everything happens in-session.

## When to use

- "Create a newsletter about …"
- "Draft a newsletter for …"
- "Generate a GTM / team newsletter"
- "Assemble these updates into a newsletter"

## Inputs

- **title / topic** (required) — the newsletter headline or theme.
- **items** (optional) — a list of update entries, each with a headline, a 1–2
  sentence blurb, and an optional link. If absent or sparse, draft 3–5 reasonable
  items from the topic.
- **intro** (optional) — a short opening line; generate one if not supplied.
- **audience** (optional) — who it's for (tunes tone; defaults to a general
  GTM/team audience).

## Workflow

1. Gather the title and any items/links from the user's prompt.
2. If the items are missing or thin, draft 3–5 sensible sections from the topic.
3. Assemble the newsletter using the **Output format** template below.
4. Write it to `outputs/newsletter-generator/<slug>.md`, where `<slug>` is a
   kebab-case slug derived from the title (create the directory if needed).
5. Report the saved path and show a short preview of the result.

## Output format

```markdown
# <Title>

_<Date> · <Audience>_

<One- to two-sentence intro>

## In this issue

- <Item 1 headline>
- <Item 2 headline>
- <Item 3 headline>

### <Item 1 headline>

<1–2 sentence blurb.> [Read more](<link>)

### <Item 2 headline>

<1–2 sentence blurb.> [Read more](<link>)

### <Item 3 headline>

<1–2 sentence blurb.> [Read more](<link>)

---

_That's all for this issue — see you next time._
```

Omit the `[Read more](…)` link when an item has no URL. Keep the whole thing
tight and skimmable.

## Out of scope / guardrails

- No Notion publishing and no HTML/email rendering — markdown file only.
- No external research, web fetches, or MCP calls; stay self-contained.
- Don't invent specific facts, figures, or quotes for real entities — keep
  generated blurbs generic when the user hasn't supplied details.
