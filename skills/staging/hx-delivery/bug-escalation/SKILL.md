---
name: bug-escalation
description: Summarise a bug from a Jira ticket for escalation to engineering. Assesses severity and priority, produces a structured escalation summary, and offers to log the bug in the relevant team's Bug Sync page in Notion.
argument-hint: "[Jira ticket key, e.g. HRSD-1234]"
user-invocable: true
---

# Bug Escalation

Summarise a bug from a Jira ticket, assess its severity and priority using hx's escalation framework, and produce a structured summary ready for engineering escalation. Optionally log the bug in the relevant team's Bug Sync page in Notion.

## Step 1: Parse the Jira Ticket Reference

Extract the Jira ticket key from `$ARGUMENTS` or from conversation context. The key follows the pattern `PROJECT-NUMBER` (e.g. `HRSD-1234`, `MOD-567`).

If the ticket key is ambiguous or missing, ask for it before proceeding.

## Step 2: Authenticate MCP Connectors

The Jira connector is required. The Notion connector is optional (used only if the user wants to log the bug to Bug Sync).

Look for available tools matching:
- **Jira**: `mcp__*jira*` — for reading ticket data
- **Notion**: `mcp__*notion*` — for writing to Bug Sync pages

If Jira tools are not available or not authenticated, trigger the authentication flow. Do not proceed without Jira data.

## Step 3: Fetch the Jira Ticket

Query Jira for the ticket. Retrieve all available fields, paying particular attention to:

- **Summary/title**
- **Description** (full text, including any reproduction steps already provided)
- **Status** and **resolution**
- **Priority** and **severity** (if set)
- **Component(s)** and **Service Catalogue Item**
- **Customer Impacted**
- **Environment Impacted**
- **Reporter** and **assignee**
- **Comments** (scan for additional reproduction details, workarounds, or investigation notes)
- **Attachments** (note any screenshots or logs referenced)
- **Linked issues**
- **Labels** and **custom fields** (SLA Level, Escalated To, Material Functionality, Is System Usable, Is there a Workaround, Breadth of Issue)

If the ticket is sparse, note which fields are missing — these will need to be filled before escalation.

## Step 4: Load Escalation References

Load the reference files that define the investigation and escalation processes:

```
${CLAUDE_SKILL_DIR}/references/investigation-process.md
${CLAUDE_SKILL_DIR}/references/escalation-process.md
```

Use these to assess the bug and structure the summary.

## Step 5: Check Pre-Escalation Readiness

Before producing the escalation summary, verify that the pre-investigation steps from the Customer Support Investigation Process have been addressed. Review the ticket for evidence of:

1. **Documentation review** — Has Renew documentation, Notion, Stack Overflow, or prior Jira tickets been checked?
2. **Log analysis** — Are there references to Sumo Logic, Sentry, or AWS (Sailor) logs?
3. **Replication** — Has the issue been reproduced in a test/demo environment?
4. **Recent changes** — Have deployments or system updates been checked against the issue timeline?

Flag any gaps as action items in the summary. These should be completed before escalating to engineering.

## Step 6: Assess Severity and Priority

Using the escalation process framework, determine the severity and priority:

### Severity Matrix

| Severity | Description |
|---|---|
| S1 | Material functionality unusable with no workaround |
| S2 | Material functionality unusable but with workaround, or issues with usage of material functionality |
| S3 | Non-material functionality unusable with no workaround |
| S4 | Non-material functionality unusable with workaround, other issues with non-material functionality, or minor visual issues |

### Priority Matrix

| Severity | Widespread | Narrow |
|---|---|---|
| S1 | P1 | P2 |
| S2 | P2 | P3 |
| S3 | P3 | P4 |
| S4 | P4 | P4 |

- **Widespread**: Users across an entire team or more than one team are affected. In the worst case, the entire user base is impacted.
- **Narrow**: A single person or portion of a single team within a customer's org is experiencing the issue (e.g. a single policy is impacted).

Compare your assessment against any priority already set on the ticket. If they differ, note this in the summary with your reasoning.

### Response and Resolution Targets

| Priority | Time to Respond (SLA) | Time to Resolution (SLO) |
|---|---|---|
| P1 | 1 hr - 24 hrs | 4h - 3 business days |
| P2 | 4h - 5 business days | 5 - 15 business days |
| P3 | 1 - 10 business days | 10 - 30 business days |
| P4 | 2 - 10 business days | 30 days |

Note: Ranges reflect different tiers of customer support.

## Step 7: Determine the Owning Team

Based on the component, service catalogue item, and the nature of the bug, identify which engineering team should own the bug. The teams are:

| Team | Abbreviation | Typical scope |
|---|---|---|
| Models | MOD | Rating engines, model execution, model IDE |
| Policies | POL | Policy lifecycle, renewals, endorsements |
| Kernel | KER | Core platform infrastructure, APIs |
| Model Development Experience | MDX | Model development tooling, debugging |
| SHARC | SHARC | Shared components, auth, permissions |
| Xpression | XPR | UI/UX, frontend, design system |

If the owning team is unclear from the ticket, flag this and suggest the escalation be raised in the **Rev/Eng Teams channel** rather than a specific team channel.

## Step 8: Produce the Escalation Summary

Structure the output as follows:

### Bug Summary

> **[Ticket Key]: [Title]**
> **Priority**: P[n] | **Severity**: S[n] | **Team**: [Team Name]
> **Customer**: [Customer name] | **Environment**: [Environment]

### Issue Description

A clear, concise description of the bug in 2-4 sentences. Describe what the customer experiences, not implementation details.

### Steps to Reproduce

Numbered steps to consistently recreate the issue. If the ticket lacks reproduction steps, flag this as a gap and provide the best approximation from available information.

### Expected vs Actual Behaviour

- **Expected**: What should happen
- **Actual**: What the customer actually experiences

### Impact Assessment

- **Breadth**: Widespread or Narrow, with explanation
- **Material functionality**: Yes/No, with the specific functionality affected
- **Workaround**: Available/Not available — describe if one exists
- **System usable**: Yes/No

### Evidence

- Screenshots/videos referenced (note attachment names)
- Error messages or log excerpts
- Environment details (API version, browser, feature flags)

### Pre-Escalation Checklist

Mark each item as done or flag as outstanding:

- [ ] Documentation reviewed (Renew docs, Notion, Stack Overflow)
- [ ] Logs analysed (Sumo Logic, Sentry, AWS)
- [ ] Issue replicated in test environment
- [ ] Recent changes/deployments checked

### Jira Field Readiness

List any required escalation fields that are not yet set on the ticket:

- Customer Impacted
- Environment Impacted
- SLA Level
- Escalated To
- Service Catalogue Item
- Component
- Material Functionality
- Resolved by First Contact (should be "No")
- hx Priority
- Is the System Usable
- Is there a Workaround
- Breadth of Issue

### Escalation Route

Based on the priority:
- **P1/P2**: On-caller will be notified immediately. Post in the incident channel.
- **P3/P4**: Raise in the team's weekly sync/async session. Update the team's Bug Sync page in Notion ahead of the meeting.

## Step 9: Offer Follow-ups

After delivering the summary, offer relevant next steps:

- "Should I post this summary as an **internal comment** on the Jira ticket?"
- "Should I add this bug to the **[Team Name] Bug Sync** page in Notion for the next sync meeting?"
- "Want me to draft the Teams message for escalating this to [Team Name]?"
- "Should I check for related Jira tickets that might be linked to this issue?"

## Step 10: Post Summary to Jira (If Requested)

If the user asks to post the summary as an internal comment on the Jira ticket, use the Jira connector's `addCommentToJiraIssue` tool with `contentFormat: "markdown"`.

Restrict the comment to internal visibility by setting `commentVisibility` to `{ "type": "role", "value": "Service Desk Team" }` so the customer cannot see it.

The comment body should contain the full escalation summary from Step 8, including the bug summary header, impact assessment, pre-escalation checklist, Jira field readiness, and escalation route.

After posting, confirm the comment was added and link to the ticket.

## Step 11: Add to Bug Sync (If Requested)

If the user asks to add the bug to a team's Bug Sync page, authenticate the Notion connector if not already done, then add an entry to the relevant team's database.

The Bug Sync parent page and team databases are:

| Team | Notion Page |
|---|---|
| Bug Sync (parent) | https://www.notion.so/hyperexponential/Bug-Sync-1f1802db20a6806790e9e426f04f2ecc |
| MOD | https://www.notion.so/1f1802db20a680ee8a90e1de4e0ab97f |
| POL | https://www.notion.so/1f1802db20a68058a4cdf392a3977071 |
| Kernel | https://www.notion.so/21b802db20a68026b484cf848030c068 |
| MDX | https://www.notion.so/26c802db20a680a999fbca59c4ad909b |
| SHARC | https://www.notion.so/272802db20a6809eb1b7e121d2389371 |
| Xpression | https://www.notion.so/281802db20a680c79749f13146e704ea |

When adding an entry, include:
- Jira ticket key and link
- Bug title
- Priority and severity
- Customer impacted
- Brief description of the issue
- Current status
