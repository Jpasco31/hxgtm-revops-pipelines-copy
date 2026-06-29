# Customer Support Investigation Process Before Engaging Engineering

Source: https://www.notion.so/hyperexponential/Customer-Support-Investigation-Process-Before-Engaging-Engineering-1bb802db20a68068adadff0e7c7162c7

## Purpose

This covers the pre-investigation steps that Customer Support should follow before escalating an issue to Engineering. The aim is to make sure that all initial checks have been completed and Engineering receives a well-structured summary with a specific question.

## Investigation Steps

Before escalating an issue, perform the following checks at a high level.

### 1. Review Available Documentation (Renew & Customer Support Docs)

- Check Renew Documentation for expected behaviour, limitations, etc.
- Search Notion pages for workarounds, explanations, troubleshooting steps, etc.
- Look at Stack Overflow for previous discussions or solutions.
- Review Jira tickets for any similar past issues or ongoing work.

### 2. Analyse Logs

- **Sumo Logic** — Review logs to identify possible system errors or patterns related to the issue.
- **Sentry** — Check for recorded exceptions or failures.
- **AWS (Sailor logs)** — Look for indicators that may highlight performance or access issues.

### 3. Replication & Validation

- Attempt to replicate the issue in an hx Renew test/demo environment where possible.
- If applicable, check permissions, configurations, or recent changes that may contribute to the problem.
- Identify if the issue is affecting multiple customers, environments, or models, or if it is isolated.

### 4. Check for Recent Changes & External Factors

- Verify if any recent system changes, deployments, or updates align with when the issue began.

## Setting Jira Ticket Fields for Engineering Escalation

When escalating an issue to an engineering team, ensure the following fields are set in the relevant Jira ticket:

| Field | Description |
|---|---|
| Customer Impacted | The customer affected by this issue |
| Environment Impacted | e.g. Production, UAT, Customer-Specific Instance |
| SLA Level | e.g. P1, P2, etc. |
| Escalated To | Engineering team receiving the ticket: Models, Platform, CE, etc. |
| Service Catalogue Item | Relevant service affected: API, UI, Policy, etc. |
| Component | Specific area within the service affected, if applicable |
| Material Functionality? | Does this issue impact critical system functionality? |
| Resolved by First Contact? | Set to "No" |
| hx Priority | Defined priority level based on customer impact |
| Is the System Usable? | If not a request, specify whether the system is completely unusable |
| Is there a Workaround? | If not a request, indicate if an alternative solution exists |
| Breadth of Issue? | Is this widespread or isolated to a specific subset of users/customers? |

## Escalation to Engineering

Follow the escalation process as per the Bug Escalation Process page.
