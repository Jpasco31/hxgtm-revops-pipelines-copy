---
name: lead-scoring
description: >
  Score one or more sales leads from a few simple attributes into a 0-100 score
  and a Hot/Warm/Cold tier. Use when the user asks to score a lead, rank leads,
  prioritize a lead list, or assign lead grades/tiers. Outputs a single markdown
  table to outputs/lead-scoring/. Intentionally minimal — no scripts, no CRM
  integration, no external services.
---

# Lead Scoring

## What this skill does
Turns a handful of lead attributes into a transparent numeric score and a tier,
so a list of leads can be quickly prioritized. Everything runs in-session — no
scripts, MCP calls, or external lookups.

## When to use
- "score this lead" / "score these leads"
- "rank / prioritize this lead list"
- "assign lead tiers / grades"

## Inputs
- **leads** — one or more leads, each with any of: company size, industry fit,
  budget signal, engagement level, seniority of contact.
- **weights** (optional) — custom weighting; otherwise use the defaults below.

## Scoring model (default weights, 0-100)
- Industry/ICP fit — 30
- Company size — 20
- Budget signal — 20
- Engagement level — 20
- Contact seniority — 10

Tiers: Hot ≥ 70, Warm 40-69, Cold < 40.

## Workflow
1. Read the lead(s) and any custom weights from the request.
2. Score each attribute 0-1, multiply by its weight, sum to a 0-100 score.
3. Map the score to a Hot/Warm/Cold tier.
4. Write a markdown table (Lead, Score, Tier, one-line rationale) to
   `outputs/lead-scoring/<slug>.md`.
5. Report the file path and a short summary.

## Output format
| Lead | Score | Tier | Rationale |
|------|-------|------|-----------|
| Acme Co | 82 | Hot | Strong ICP fit, enterprise size, active engagement |

## Out of scope / guardrails
- No CRM / Salesforce / external data — scores only what the user provides.
- No scripts, no MCP, no publishing. File output only.
- Deterministic, transparent math — always show the per-attribute contribution
  when asked.
