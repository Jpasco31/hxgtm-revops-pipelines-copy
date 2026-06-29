---
name: new-product-research
description: Identify new product expansion opportunities for hx customer accounts by combining internal intelligence (Glean, Teams, Salesforce, Notion CRM) with external research (competitor tech stacks, vendor websites, press releases). Use when researching which new products to sell to a customer, finding displacement opportunities, or building an expansion pipeline page.
metadata:
  version: "1.0.0"
  tier: "T1"
  author: "hx Automation Team"
  derived_from: "Production research session: New Product Expansion Opportunities page (Apr 2026). 55 customers researched, 19 tech stacks mapped, 4 competitor customer lists cross-referenced."
  last_updated: "2026-04-12"
---

## Commands

```bash
# Notion GTM CRM database (ground truth for product stages)
# Database ID: 294802db-20a6-805d-b338-e5dded17e6ff
# Data source: collection://294802db-20a6-8037-8114-000bca7fc17c

# Query all customer product stages
SELECT "Customer Name", "Licensed Products", "IA stage", "AA stage",
       "Portfolio Intelligence", "UA Stage", "Triage Stage", "Priority",
       "Pod", "Relationship"
FROM "collection://294802db-20a6-8037-8114-000bca7fc17c"

# Reference Notion page (New Product Expansion Opportunities)
# Page ID: 340802db-20a6-81bf-a532-d06f61c0ed22
```

## When to Use This Skill

- Researching new product expansion opportunities for one or more accounts
- Preparing for a revenue review, QBR, or pipeline planning session
- Identifying competitor displacement opportunities (SEND, Kalepa, Cytora, Federato)
- Mapping a customer's external technology stack against hx products
- Cross-referencing internal signals with CRM ground truth
- Building or updating a Notion page for sales team consumption

## Boundaries

- ✅ **Always**: Query GTM CRM database as ground truth before asserting product status
- ✅ **Always**: Cite sources (URLs, channel names, dates) for every finding
- ✅ **Always**: Distinguish between purchased, beta, opportunity, and no signal
- ✅ **Always**: Use structured tables, not prose, for multi-customer output
- ⚠️ **Ask first**: Before writing findings to Notion
- ⚠️ **Ask first**: Before asserting a competitor relationship without a cited source
- 🚫 **Never**: Assume product status without checking CRM
- 🚫 **Never**: List customers who've already purchased a product as "opportunities"
- 🚫 **Never**: Use em dashes in output

---

## The Five Products

| Abbr | Product | Competes With |
|------|---------|---------------|
| ST | Submission Triage | SEND, Kalepa (triage), Cytora (intake), ConvR |
| PI | Portfolio Intelligence | Earnix (pricing optimisation), internal BI tools |
| AA | Actuarial Agent | Optalitix, Coherent, in-house Python/R tools |
| UA | Underwriting Agent | Federato (UW workbench), Artificial Labs, Cytora (risk assessment) |
| IA | Ingestion Agent | Kalepa (ingestion), Roots Automation, Indico Data, FurtherAI, Ping |

---

## Research Pipeline

Run these steps in order. For single-account research, run all 5 steps. For batch/portfolio research, run steps 1-2 first to identify priority accounts, then steps 3-5 for those accounts.

### Step 1: CRM Ground Truth

Query the GTM CRM Pre-Beta Product Tracking database to get the customer's actual product stages.

```
Tool: mcp3_notion-query-data-sources
Data source: collection://294802db-20a6-8037-8114-000bca7fc17c
```

**Stage meanings** (from CRM):
| Stage | Meaning | Page Status |
|-------|---------|-------------|
| Paying customer | Purchased | ✅ (not an opportunity) |
| Onboarding | Purchased, being set up | ✅ (not an opportunity) |
| Beta Tester | Active beta user | 🎯 (close to purchase) |
| Beta Opportunity | Approved for beta, not yet started | 🎯 (active opportunity) |
| Discovery / Demo / Qualification | In sales process | 🎯 (active opportunity) |
| Prospecting | Early stage | 🎯 (early opportunity) |
| Waitlist | Interested but queued | 🎯 (future opportunity) |
| Not started / Not now | No activity | ⬜ (research needed) |

### Step 2: Internal Intelligence (Glean)

Search Glean for signals across these sources, filtered to the last 6 months:

**Search 1 - Teams channels:**
```
Tool: mcp0_company_search
Query: "[Customer Name] new products OR triage OR ingestion OR actuarial agent OR underwriting agent OR portfolio intelligence OR workbench"
Datasources: ["teams"]
```

**Search 2 - Salesforce opportunities:**
```
Tool: mcp0_company_search
Query: "[Customer Name] opportunity triage OR ingestion OR actuarial OR portfolio"
Datasources: ["salesforce"]
```

**Search 3 - Gong calls:**
```
Tool: mcp0_company_search
Query: "[Customer Name] new products OR AI OR agent OR triage"
Datasources: ["gong"]
```

**What to look for:**
- Explicit product mentions (positive or negative)
- Competitor mentions (SEND, Kalepa, Cytora, Federato, Indico, Majesco)
- Workbench/platform consolidation discussions
- Budget/timing signals ("H2", "next year", "not now")
- Champion identification (who is pushing for new products internally)
- Displacement signals ("move off", "replace", "not happy with")

### Step 3: External Tech Stack Research

Search the web for the customer's technology partnerships and vendor stack.

```
Tool: search_web or mcp2_web_search_exa
Query: "[Customer Name] insurance technology platform AI underwriting digital transformation [current year]"
```

**Follow-up searches if initial results are thin:**
- "[Customer Name] Guidewire OR Duck Creek OR Majesco OR Sapiens"
- "[Customer Name] insurtech partnership"
- "[Customer Name] CTO OR CIO technology strategy"

**Key information to extract:**
| Field | Why It Matters |
|-------|---------------|
| Core platform (Guidewire, Duck Creek, etc.) | Determines integration story |
| UW workbench vendor (Federato, Cytora, etc.) | Direct competitor for UA/ST |
| Data ingestion vendor (Roots, Indico, etc.) | Direct competitor for IA |
| AI strategy (in-house vs vendor) | "Build vs buy" resistance indicator |
| Key tech exec (CIO, CTO, Head of Digital) | Stakeholder for new products |

### Step 4: Competitor Customer Cross-Reference

Check whether the customer appears on competitor websites or in competitor press releases.

**Websites to check:**

| Competitor | URL | What to Look For |
|------------|-----|-----------------|
| SEND | send.technology | Case studies, customer spotlight |
| Kalepa | kalepa.com | Case studies, press releases, newsroom |
| Cytora | cytora.com | Customer logos, case studies, blog posts |
| Federato | federato.ai | Case studies, customer quotes, press releases |
| Artificial Labs | artificial.io | Customer mentions, portfolio page, blog |

**Search pattern:**
```
Tool: search_web
Query: "[Competitor] [Customer Name] partnership OR customer OR underwriting"
```

**Also search Glean for internal competitor intel:**
```
Tool: mcp0_company_search
Query: "[Customer Name] [Competitor Name]"
```

### Step 5: Synthesise and Output

Combine all findings into a structured output. Format depends on scope:

**Single account output:**
```markdown
## [Customer Name] - New Product Expansion Analysis

### CRM Status
| Product | Stage | Status |
|---------|-------|--------|
| IA | [stage] | [icon] |
| AA | [stage] | [icon] |
| PI | [stage] | [icon] |
| UA | [stage] | [icon] |
| ST | [stage] | [icon] |

### Internal Signals
- [Finding 1] (Source: Client-[X] Teams channel, [date])
- [Finding 2] (Source: Gong call, [date])

### External Tech Stack
| Vendor | Product | hx Overlap | Source |
|--------|---------|------------|--------|
| [Vendor] | [What they do] | [Which hx product competes/complements] | [URL] |

### Competitor Overlap
- [Competitor] is embedded for [function] ([source URL])

### Recommended Products (Priority Order)
1. [Product] - [Why, based on evidence]

### Next Steps
- [Action 1] - [Owner]
```

**Multi-account output:**
Use the customer matrix table format:
```markdown
| Customer | IA | AA | PI | UA | ST | Notes |
|----------|----|----|----|----|----|----- |
| [Name] | [icon] | [icon] | [icon] | [icon] | [icon] | [Key finding] |
```

Icons: ✅ = purchased, 🎯 = opportunity, ⬜ = no signal

---

## Competitor Displacement Playbooks

### SEND Displacement
**hx products**: ST (primary), IA (supporting)
**Known SEND customers**: Bowhead, Westfield, W.R. Berkley, Argenta
**Key signals to find**: Performance complaints (delays, 15-25s load times), desire to bypass SEND (e.g. Moody's direct integration), negative sentiment in Teams channels
**Pitch angle**: hx Triage is purpose-built for pricing-aware submission triage, not generic document routing. Integrates natively with Decision Engine models.

### Kalepa Displacement
**hx products**: IA (primary), ST (supporting)
**Known Kalepa customers**: Bowhead, Canopius
**Key signals to find**: Ingestion quality complaints, casualty-specific limitations, desire for pricing integration
**Pitch angle**: hx IA extracts data directly into Decision Engine models. Kalepa is a standalone tool requiring separate integration.

### Cytora Displacement
**hx products**: ST (primary), IA (supporting), UA (adjacent)
**Known Cytora customers**: Arch, Convex, Markel
**Key context**: Cytora acquired by Applied Systems (Sep 2025). This may create switching opportunities as product direction changes.
**Pitch angle**: hx covers submission intake AND pricing/rating in one platform. Cytora handles intake only, requiring separate pricing tools.

### Federato Displacement
**hx products**: UA (primary), PI (supporting)
**Known Federato customers**: Ascot. Trying to work with Antares.
**Key context**: Federato raised $100M Series D (Goldman Sachs, Nov 2025). They're expanding from UW workbench to full policy lifecycle.
**Pitch angle**: hx is actuarial-native and pricing-first. Federato is UW workflow-first. Different value prop for different stakeholders (actuaries vs underwriters).

---

## Data Sources Reference

| Source | Tool | What It Contains |
|--------|------|-----------------|
| GTM CRM (Notion) | mcp3_notion-query-data-sources | Ground truth product stages per customer |
| Teams channels | mcp0_company_search (teams) | Real-time customer conversations, product demos, feedback |
| Salesforce | mcp0_company_search (salesforce) | Active opportunities, pipeline data |
| Gong | mcp0_company_search (gong) | Call recordings, meeting notes, action items |
| AE Account Plans | mcp3_notion-search | Strategy docs, relationship maps, budget info |
| Web/Press | search_web / mcp2_web_search_exa | Public tech partnerships, vendor announcements |
| Competitor sites | read_url_content / search_web | Customer lists, case studies, logos |

---

## Quality Checklist

Before delivering findings, verify:
- [ ] CRM database queried (not assumed)
- [ ] Every product status cited with source
- [ ] Purchased products NOT listed as opportunities
- [ ] Competitor claims backed by public URLs
- [ ] Tables used for multi-customer output (not prose)
- [ ] Confirmation requested before Notion writes
- [ ] No em dashes in output
