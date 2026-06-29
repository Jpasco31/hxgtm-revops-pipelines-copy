---
name: project-update
description: Generate a persona-tailored project status update by pulling live data from ClickUp and contextual knowledge from Notion. This skill should be used when someone asks for a project update, project status, or progress report on a named customer project (e.g. "How is AIG Onboarding going?").
argument-hint: "[project name, e.g. AIG Onboarding]"
user-invocable: true
---

# Project Update

Generate a tailored status update for a customer project by combining live task data from ClickUp with project management context from Notion. The update is shaped by the persona of the person requesting it.

## Step 1: Identify the Persona

Determine the persona of the person requesting the update. Valid personas are:

- **Project Manager** — owns day-to-day delivery
- **Customer Success Manager** — owns the customer relationship
- **Sales Executive** — owns the commercial relationship
- **Executive Sponsor** — senior leader with strategic oversight

If the persona is not clear from context (e.g. prior conversation, memory, or the way the request is framed), ask directly:

> What is your role on this project? (Project Manager, Customer Success Manager, Sales Executive, or Executive Sponsor)

Load the persona reference for detailed guidance on what each persona needs:

```
${CLAUDE_SKILL_DIR}/references/personas.md
```

## Step 2: Parse the Project Identifier

Projects in ClickUp follow the naming convention `{Client Name} {Project Type}` (e.g. "AIG Onboarding", "Zurich SOW", "Liberty Support+").

Extract the client name and project type from the input. If `$ARGUMENTS` is provided, use that. Otherwise, extract from the conversation context.

If the project name is ambiguous or incomplete, ask for clarification before proceeding.

## Step 3: Authenticate MCP Connectors

Both Notion and ClickUp require authentication via their MCP connectors. If either connector is not yet authenticated, trigger the authentication flow before proceeding.

Look for available tools matching:
- **Notion**: `mcp__*notion*` — for reading project management documentation
- **ClickUp**: `mcp__*clickup*` — for querying project task data

If ClickUp tools are not available, inform the user that the ClickUp connector is required and provide guidance on enabling it. Do not proceed without ClickUp data — it is the primary source for project status.

## Step 4: Retrieve Project Management Context from Notion

Query Notion for the Project Management Hub to understand how projects are structured and managed at hx. This provides the framework for interpreting ClickUp data.

Search Notion for the page: **Project Management Hub**
(URL: `https://www.notion.so/hyperexponential/Project-Management-Hub-0d53bc6541dc4dd9a57c1546b8fe168e`)

Extract relevant context:
- Project lifecycle stages and what each stage means
- Definitions of status indicators used across projects
- Escalation criteria and risk thresholds
- Any project-type-specific processes (onboarding vs SOW vs support)

This context informs how to interpret the raw ClickUp data in the next step.

## Step 5: Retrieve Project Data from ClickUp

Query ClickUp for the project's task data. Projects live in one of three spaces depending on project type:

| Project type | ClickUp space |
|---|---|
| Onboarding | Customer - Onboarding |
| SOW | Customer - SOW |
| Support+ | Customer - Support+ |

Search for the project by name within the appropriate space. If the project type is unclear from the name, search across all three spaces.

Retrieve:
- **Task status breakdown** — count and list of tasks by status (open, in progress, complete, blocked)
- **Overdue tasks** — tasks past their due date, with assignees
- **Blockers** — tasks marked as blocked or flagged, with descriptions
- **Recent activity** — tasks updated in the last 7-14 days
- **Milestones** — key milestones and their completion status
- **Assignees** — who is working on what
- **Timeline** — project start date, target completion, and any deadline shifts

## Step 6: Synthesise the Update

Combine the ClickUp data with the Notion context to produce a status update tailored to the identified persona.

### General principles

- Lead with the overall health assessment — give the reader a clear signal immediately
- Use specific data points from ClickUp (task counts, dates, names) rather than vague statements
- Frame insights through the lens of what matters to this persona (see `references/personas.md`)
- Distinguish between facts (from ClickUp data) and assessments (inferred from patterns)
- Surface blockers and risks proactively — do not bury them
- Keep the language direct and actionable

### Structuring the output

Follow the update structure defined for the identified persona in `references/personas.md`. Each persona has a specific section order and set of priorities.

### Handling sparse data

If ClickUp data is limited (few tasks, no milestones, minimal activity):
- State what data is available and what is missing
- Provide the best update possible with available information
- Recommend specific data gaps to fill (e.g. "No milestones are set — consider adding key dates to ClickUp")

## Step 7: Offer Follow-ups

After delivering the update, offer 2-3 relevant follow-up actions based on the persona and the project state. Examples:

- **PM**: "Want me to list all overdue tasks with assignees so you can follow up?"
- **CSM**: "Should I draft talking points for your next customer check-in based on this status?"
- **Sales**: "Want me to flag this in a format you can share with your account team?"
- **Exec**: "Should I compare this project's trajectory against other active projects?"
