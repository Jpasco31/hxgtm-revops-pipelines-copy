---
name: triage
description: Classify a support ticket against the hx platform capability map and determine the owning team(s). Accepts a ticket title and description (or Jira issue key/URL) and returns the matched capability, owning team(s), confidence level, and routing recommendation.
---

# Triage Support Ticket

This skill classifies an incoming support ticket against the hx platform capability map to determine which team(s) should own it.

## Loading Context

Read the Capability Team Mapping file.

This is the source of truth for classification. Each row is a capability with its resolved team ownership — no inheritance to compute.

## Classification

Match the subject and content against the mapping table using the following approach:

1. **Identify candidate capabilities** — scan the subject and content for references to platform features, UI areas, API behaviour, error contexts, or workflow steps that correspond to rows in the mapping table. Use the Description column to match — subject and content text rarely uses the exact capability name.
2. **Avoid surface-level matches** — some capabilities in the mapping are high-level entry points (e.g. Admin Portal, Developer Portal, Modeller Portal, Headless API). A subject and content that mentions the portal or API is almost always about a specific feature *within* it. Look past the surface-level mention and classify based on what the subject and content is actually about. For example, a subject and content saying "error in the Developer Portal when publishing a model" is about Model Version Deployment, not Developer Portal.
3. **Select the best match** — pick the single most specific capability row. If the subject and content clearly spans multiple capabilities, prefer the one whose description most closely matches the reported issue.
4. **Look up the team** — read the Team column for the matched row.
5. **Assess confidence**:
   - **high** — the subject and content clearly describes behaviour within a single, unambiguous capability
   - **medium** — the subject and content is a reasonable match but could arguably fit a neighbouring capability
   - **low** — the match is a best guess; the subject and content is vague or spans multiple unrelated areas

## Output

Present the classification as a structured summary:

```
Capability:  <matched capability name>
Team(s):     <owning team(s)>
Confidence:  high | medium | low
```

Followed by a one-sentence **Rationale** explaining why this capability was chosen.

Then provide the **Routing recommendation** based on these rules:

### Single team
> Assign to **{team}**.

### Multiple teams (e.g. `Models, Policies`)
> Add all teams as participants: **{team1}**, **{team2}**. Both teams share ownership of this capability and should coordinate on resolution.

### No owner (team is `No-one`, `No one`, or `?`)
> **Do not assign.** Add label `needs-triage`. This capability either has no current owner or ownership has not yet been decided.

### Unrecognised (no capability match found)
> **Do not assign.** Add label `needs-triage`. The ticket could not be matched to a known platform capability — it may relate to an area not covered by the capability map, or the description may need clarification.
