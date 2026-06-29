# Tests for new-product-research skill

## Test 1: Single account research
**Prompt:** "Research new product expansion opportunities for Convex"
**Expected:**
- Fetches GTM CRM database for Convex's current product stages
- Searches Glean for Revenue-Customer Teams channel (Client-Convex)
- Searches Glean for Salesforce opportunities mentioning Convex + new products
- Searches web for Convex technology stack and insurtech partnerships
- Checks competitor websites (Cytora, Kalepa, SEND, Federato, Artificial Labs) for Convex as a customer
- Produces a structured summary: current CRM status, internal signals, external tech stack, competitor overlap, displacement angles, recommended products, next steps
**Pass criteria:** Output covers all 5 products, cites sources, identifies Cytora and Artificial Labs as embedded competitors

## Test 2: Multi-account batch research
**Prompt:** "Research new product opportunities across all customers with no Salesforce opp"
**Expected:**
- Queries GTM CRM database to identify customers without active SF opps for new products
- Batches Glean searches across multiple Teams channels
- Produces a customer matrix table with product opportunities per customer
- Identifies tier 1/2/3 priority actions
**Pass criteria:** Output is a structured table, not prose. Includes CRM stages and evidence sources.

## Test 3: Competitor displacement focus
**Prompt:** "Which of our customers use SEND or Kalepa and what are the displacement opportunities?"
**Expected:**
- Searches Glean for SEND and Kalepa mentions in Teams channels
- Searches competitor websites for customer lists
- Cross-references against hx customer list
- Produces displacement opportunity table with specific product recommendations
**Pass criteria:** Identifies at least Bowhead (SEND + Kalepa), Westfield (SEND), Argenta (SEND), Canopius (Kalepa) with cited sources

## Test 4: Tech stack deep dive
**Prompt:** "What technology does Ascot use for underwriting and where can hx displace?"
**Expected:**
- Web search for Ascot + technology/insurtech/AI/underwriting
- Identifies Federato, Guidewire, Roots Automation, Zywave from public sources
- Maps each technology against hx product that competes or complements
- Checks GTM CRM for Ascot's current product stages
**Pass criteria:** Specific vendor names with citations, clear hx product mapping, CRM status included

## Test 5: Notion page output
**Prompt:** "Build a new product expansion page for the Q3 revenue review"
**Expected:**
- Runs full research pipeline across all customers
- Produces structured Notion page with: executive summary, customer matrix, research-identified opps, competitor intelligence, tech stacks, recommended actions
- Asks for confirmation before writing to Notion
**Pass criteria:** Confirms before writing. Output follows the established page structure with tables, not prose.
