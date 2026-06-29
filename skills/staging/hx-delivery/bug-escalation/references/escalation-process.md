# Bug Escalation Process

Source: https://www.notion.so/hyperexponential/Bug-Escalation-Process-1e6802db20a680a19395cd43bd3f4093

## Definition

A bug is a defect or flaw that causes a system to behave in a way that is incorrect, unintended, or not aligned with requirements.

Note that one or more bugs may be the root cause of an incident, but resolving an incident may not involve resolving a bug (as in an incident, the primary goal is to restore service).

## Severity and Priority Matrix

The priority of a bug is defined by the impact it has on material functionality.

### Severity Levels

| Severity | Description | Widespread Example | Narrow Example |
|---|---|---|---|
| S1 | Material functionality unusable with no workaround | P1 — Pricing service down | P2 — User unable to create a model. Customer data loss. |
| S2 | Material functionality unusable but with workaround or issues with usage of material functionality | P2 — User unable to renew a policy but duplicating is sufficient in the short term | P3 |
| S3 | Non-material functionality unusable with no workaround | P3 | P4 — User unable to view licence history or tag management. Customer unable to update their theme. |
| S4 | Non-material functionality unusable with workaround, other issues with non-material functionality, or minor visual issues | P4 | P4 — Cosmetic issue with no functional impact and no damage to brand. |

### Breadth Definitions

- **Widespread**: Users across an entire team or more than one team are experiencing the unusable functionality. In the worst case, the entire user base is impacted.
- **Narrow**: A single person or portion of a single team within a customer's org is experiencing the unusable functionality. e.g. a single policy is impacted, preventing a team in one line of business from finalising policy options in that policy.

### Priority Matrix

| Severity | Widespread | Narrow |
|---|---|---|
| S1 | P1 | P2 |
| S2 | P2 | P3 |
| S3 | P3 | P4 |
| S4 | P4 | P4 |

## SLAs and SLOs

| Priority | Approach | Time to Respond (SLA) | Time to Resolution (SLO) |
|---|---|---|---|
| P1 | Hot-fix | 1 hr - 24 hrs | 4h - 3 business days |
| P2 | Hot-fix / Point release | 4h - 5 business days | 5 - 15 business days |
| P3 | Point release / Major release | 1 - 10 business days | 10 - 30 business days |
| P4 | Point release / Major release | 2 - 10 business days | 30 days |

Note: Ranges reflect different tiers of customer support.

## What Should Be Included When Raising a Bug?

- **A clear and descriptive title** that identifies the issue concisely
- **Steps to reproduce**: precise, numbered steps to consistently recreate the unexplained behaviour observed (e.g. conducted in test environment) — ideally in sequential numbered list form
- **Expected behaviour**: what should happen when everything works as documented/intended by Renew's design
- **Actual behaviour**: what the customer actually experiences when using the feature or functionality in question on Renew — this should necessarily include a comment on usability
- **Screenshots/videos**: an image can communicate the issue more quickly than paragraphs of text
- **Error messages/logs**: a copy of the text of any error messages and relevant logs
- **Details of the environment(s)** where the bug occurred (which environment, which API version, etc.), plus any pre-conditions such as browser, feature flags
- **The impact**: What is the breadth of this issue? Who is affected (which customer/s) and, if relevant, how many are impacted?
- **Priority**: the believed priority based on the above matrix and explanation of choice if it could be unclear (place in title in Teams escalations)
- **SLO/SLA**: any relevant customer expectation known to show the current goal timeline
- **Additional information** that is relevant but not covered above, including specific answers to qualifying questions provided by customers to the Customer Support team. These would include the documentation consulted (e.g. on-app, FENG handbook, etc), the nature of the workaround if available, and the Service Catalogue item.
- **A link to any relevant Teams threads.**

## How Will CS Escalate Bugs to Product Engineering Teams?

All escalations to Product Teams will be raised through Teams:

- **Specific Product Team channel** — used when CS have a best guess to the owning team
- **Rev/Eng Teams channel** — used when CS don't know the owning team

### By Priority

- **P1 and P2**: The on-caller will be notified immediately. P1 process posts in the incident channel with on-callers engaged.
- **P3 and P4**: The CS team will raise them in the weekly sync/async session for MOD/KER/POL/DEX/MDX teams. Pages with active bugs will be updated ahead of the meetings for team visibility in Bug Sync.

## How Bugs Are Raised

Bugs can be raised by internal and external parties:

- **Customers** discover a bug — raise through the support portal
- **Another member of hx** discovers a bug — raise a ticket in the customer support desk on behalf of the customer owning the environment the bug was found in
- **A member of a product engineering team** discovers a bug — raise in your own backlog and inform your Product Manager and Engineering Manager

## Definition of Resolution

A bug is considered resolved by one of:

- Resolving an underlying bug in the code
- Updating documentation to document a known limitation
- Clearing up confusion on the customer/support side that shows this is expected behaviour
- Identifying a workaround that is deemed suitable to provide equivalent functionality with equivalent effort
- Identifying a bug which we deem the effort vs. reward to be too great (e.g. minor disruption, high effort, feature replacement on roadmap)

A summary is added to the next set of technical and feature release notes. The issue is considered resolved once the ticket has been closed with the customer.

## Accountability

- CS are accountable for driving the resolution of incidents.
- The EPD trios are accountable for the burndown of bugs assigned to their team.
- CS will continue to engage with EPD trios throughout the resolution of the bug, including supporting with customer comms and requesting more information where needed.
- Any escalation required by EPD trio should be via TLT through their line manager.

## What Doesn't Change

- P1 process will remain the same with posts in the incident channel and on-callers engaged.
- Customer engineering interrupt process will remain the escalation path for the Customer Engineering team.
- Platform team will not have changes to their escalation process from support (via hx support project) as it is unlikely customer-facing issues relate to their scope; escalations will go through the engineering team owning the observed effect.
