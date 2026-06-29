# hx-customer Plugin Suite — Plan

The Customer function at hx spans 6 teams. Each team gets its own plugin under `plugins/`. This document is the master plan for what skills and agents each plugin will contain.

## Decisions

- **hx-customer/** is NOT a plugin — it holds this plan only (not registered in marketplace)
- **hx-support** stays separate — overlap with hx-customer-support is noted but no migration planned
- Each team plugin starts at version `0.1.0` and skills/agents are built incrementally

---

## 1. hx-customer-support

**Existing work:** `hx-support` plugin already has a `triage` skill with capability-team mapping. Kept separate for now.

| Type | Name | Description |
|------|------|-------------|
| Skill | ticket-triage | Classify incoming support tickets against the capability map and route to the correct team |
| Skill | response-drafter | Draft customer-facing responses to support tickets using past resolution patterns and product docs |
| Skill | escalation-guide | Determine when and how to escalate issues based on severity, SLA, and customer tier |
| Agent | support-knowledge-search | Search Glean/Notion for past ticket resolutions, known issues, and workarounds |

## 2. hx-customer-success

| Type | Name | Description |
|------|------|-------------|
| Skill | qbr-generator | Generate Quarterly Business Review decks from account data, usage metrics, and success milestones |
| Skill | account-health-summary | Produce account health snapshots pulling from Jira, Notion, and usage data |
| Skill | meeting-prep | Generate pre-meeting briefs for customer calls with recent activity, open issues, and talking points |
| Skill | expansion-playbook | Identify upsell/cross-sell opportunities based on current usage patterns and product roadmap |
| Agent | cs-account-researcher | Research an account across Glean, Jira, and Notion to build a comprehensive account picture |

## 3. hx-customer-project-managers

| Type | Name | Description |
|------|------|-------------|
| Skill | status-report | Generate project status reports from Jira tickets, pulling progress, blockers, and timeline updates |
| Skill | meeting-notes | Summarise meeting notes and extract action items with owners and due dates |
| Skill | risk-assessment | Flag project risks based on timeline slippage, blocker patterns, and resource constraints |
| Skill | sow-template | Generate Statement of Work documents from project scope and requirements |
| Agent | pm-project-tracker | Query Jira for project health across multiple workstreams and surface issues |

## 4. hx-customer-model-development

| Type | Name | Description |
|------|------|-------------|
| Skill | model-documentation | Generate documentation for actuarial pricing models built in hx Renew (inputs, assumptions, methodology) |
| Skill | code-review-checklist | Provide a structured review checklist for Python pricing models covering actuarial best practices |
| Skill | excel-migration-guide | Guide the migration of Excel-based pricing models to Python on hx Renew |
| Skill | model-debugging | Structured approach to debugging model execution errors with common failure patterns |
| Agent | model-dev-researcher | Search Glean and internal docs for model development patterns, past implementations, and best practices |

## 5. hx-customer-learning

| Type | Name | Description |
|------|------|-------------|
| Skill | course-builder | Create structured course outlines for hx Renew features with learning objectives and exercises |
| Skill | assessment-generator | Generate quiz questions and certification exam items from course content and product docs |
| Skill | content-freshness-check | Identify stale learning content by cross-referencing courses against recent product changes |
| Skill | workshop-planner | Design interactive workshop agendas with timing, activities, and facilitator notes |
| Agent | learning-content-researcher | Search Glean and product docs to gather material for new learning content |

## 6. hx-customer-bvc (Business Value Consulting)

| Type | Name | Description |
|------|------|-------------|
| Skill | roi-calculator | Build ROI models and business cases for prospects and customers with financial projections |
| Skill | executive-summary | Draft executive-level summaries of platform value and business impact for C-suite audiences |
| Skill | case-study-builder | Generate customer case studies from account data, success metrics, and testimonial inputs |
| Skill | value-narrative | Create value narratives that connect platform capabilities to specific business outcomes |
| Agent | bvc-data-researcher | Research account usage data, industry benchmarks, and competitive context for value analyses |

---

## Next Steps

1. Scaffold `plugin.json` for each team plugin
2. Register team plugins in marketplace.json
3. Build skills and agents per team, starting with highest-priority items
