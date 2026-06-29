---
name: market-insights-competitor-scan
description: >
  Scan the Microsoft Teams channel "Market Insights" via Glean for competitor
  intelligence: parallel seed searches, full thread retrieval, deduplication,
  and structured summaries with hx implications. Use when asked for internal
  chatter on competitors, Market Insights channel search, or Teams competitor pulse.
---

# Market Insights — Competitor channel scan

## Purpose

Retrieve **conversation threads** from the internal Teams channel **Market Insights** that mention hyperexponential competitors (or adjacent threats), restricted to a recent window (default **past 30 days**). The goal is not keyword hits alone—it is **actionable competitive intelligence**: what was said, by whom, and what it implies for hx GTM, product positioning, and account risk.

## When to use

- User asks for competitor mentions in **Market Insights**, internal Teams intel, or “what are we saying about [vendor]”
- Quarterly or ad-hoc **competitive pulse** from internal discussion
- Pair with battlecards or dossier work to ground claims in **observable internal commentary**

## Requirements

- **Glean MCP** — Use server `user-glean` (or the session’s equivalent). Primary tools: `search`, `read_document`.
- If Glean is unavailable, say so and do not fabricate threads.

---

## Glean tool constraints (must follow)

These differ from generic “boolean search” examples; violating them causes empty or wrong results.

| Topic | Rule |
|--------|------|
| **Search tool** | Use the MCP `search` tool (not a hardcoded IDE-specific name). |
| **Boolean query** | Do **not** put `OR` / `AND` in `query`. Run **one search per keyword or competitor** and merge results yourself. |
| **`type` filter** | The `search` schema may **not** include `channel message`. Omit `type` unless you have confirmed an enum value that matches Teams channel posts. |
| **Channel + app** | Set `app` to `microsoftteams` and `channel` to `Market Insights` when the user wants this channel. |
| **Date window** | Use `after` as **`YYYY-MM-DD`** (exclusive). Compute from the user’s window (e.g. 30 days before today). Do **not** pass ISO-8601 datetimes if the schema expects a date string. |
| **Recency** | Set `sort_by_recency: true` when the user cares about latest posts. |
| **Coverage** | Use `exhaustive: true` when collecting **all** matching threads in the window (user asks for full coverage, “every mention”, etc.). |
| **Pagination** | If results include `hasMoreResults: true`, note **incomplete coverage** in the output and, if the API exposes a cursor in the tool schema, fetch the next page; otherwise state that additional results may exist. |

---

## Seed competitor list (default)

Run **one `search` per line** (parallelize). Use the exact string as `query` unless a row gives an alias search.

| Query | Notes |
|--------|--------|
| `Akur8` | |
| `Earnix` | |
| `WTW Radar` | If zero results, also search `Radar` and `Radar Live` separately (no OR). |
| `Guidewire` | |
| `Duck Creek` | If zero results, try `DuckCreek` (no space). |
| `Milliman` | |
| `Federato` | Include always; try `Federato` first. |

Treat this as the **default seed**; add or remove competitors if the user names a different list.

---

## Mandatory workflow

### 1) Run parallel seed searches

For each seed query:

```yaml
query: <single competitor or alias>
app: microsoftteams
channel: Market Insights
after: <YYYY-MM-DD start of window>
sort_by_recency: true
exhaustive: true   # when user wants broad collection
```

### 2) Run backup discovery searches (separate queries, no boolean)

Use short keywords, one per search, e.g.:

- `competitor`
- `competitive`
- `pricing platform`
- `rating platform`

Optionally add `market` if noise is acceptable. **Do not** concatenate with OR.

### 3) Deduplicate

- Prefer **`parentConversationId`** when present in Glean results.
- Otherwise normalize Teams URLs (same `thread.skype` + `parentMessageId` / root message id).
- Merge snippets from duplicate hits into one row.

### 4) Filter false positives

**Discard or down-rank** threads where:

- The word is **only** a generic English use (“competitive advantage” in a **survey quote**) with **no** vendor/product story.
- The post is **pure market news** (e.g. insolvency, generic article share) with **no** link to hx product categories unless the user asked for broad market scan.
- The mention is **non-competitive** (e.g. customer’s internal team name collision)—only if context makes that clear.

**Keep** threads with: product overlap, partnership/ecosystem moves, pricing/rating/workbench/triage positioning, personnel moves between **named competitors and carriers/data vendors**, or explicit “direct competitor to hx” language.

### 5) Full thread retrieval (required for rich output)

For **each remaining unique thread**:

- Call **`read_document`** with the Teams message URL(s) so summaries are based on **full message bodies and replies**, not snippets alone.
- If `read_document` returns empty, fall back to snippets and mark **confidence: low**.

### 6) Produce structured output (rich insights)

For **each** qualifying thread, output at minimum:

| Field | Content |
|--------|---------|
| **Date** | Thread start or primary message date (from Glean metadata or message timestamps). |
| **Thread** | Title + link to Teams URL. |
| **Participants** | Names from messages / owners when available. |
| **Competitor(s) / topic** | Named vendors or themes (e.g. OSS “Haute” vs Radar/Akur8). |
| **What was discussed** | 2–4 sentences: facts, claims, links shared—not vague “they talked about X”. |
| **Product overlap map** | Tag which hx areas apply: **workbench / UW workflow**, **pricing**, **rating**, **submission triage**, **data / ecosystem** (Verisk, Guidewire, etc.), **agentic / AI**—or **not applicable**. |
| **Threat posture** | One of: **Watchlist** \| **Active overlap** \| **Ecosystem / partner motion** \| **Talent / people signal** \| **Messaging / outbound only**. |
| **Implication for hx** | **So what**: e.g. enablement need, customer talk track, battlecard update, alliance FAQ, deal risk—not restating the thread. |
| **Suggested follow-up** | Concrete next step (e.g. “monitor Indico×Coherent webinar”, “align with Verisk narrative vs Earnix”). |
| **Confidence** | **High** (full thread read) / **Medium** (partial) / **Low** (snippet only). |

After the thread list, add:

1. **Executive rollup** — 5–7 bullets: strongest themes, biggest risks, biggest opportunities for hx **this week/month**.
2. **Gaps** — Seed competitors with **zero hits** in window; note aliasing retries (e.g. Duck Creek, WTW Radar).
3. **Coverage caveat** — If `hasMoreResults` was true for any search, state that results may be incomplete.

---

## Optional enhancements

- **Alias pass**: For competitors with frequent spelling variants, run extra searches (`DuckCreek`, `Radar Live`, `WTW`).
- **Cross-reference**: If threads link to **Notion competitor pages**, name the page and whether the Notion doc should be updated.
- **Save**: If the user asks to save locally, use workspace rule `Notes/Outputs/<Skill Name>/` → subfolder **`Market Insights`** (or the skill’s human-readable name), markdown, descriptive filename.

---

## What not to do

- Do not invent Teams messages, participants, or links.
- Do not rely on a single mega-query with `OR` for all competitors.
- Do not skip `read_document` for threads you summarize as “key” competitive signal.
