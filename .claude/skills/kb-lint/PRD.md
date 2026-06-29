# PRD: kb-lint

**Status:** Draft (historical — see "Superseded scope" below)
**Author:** DS
**Date:** 2026-04-05
**Skill location:** `.claude/skills/kb-lint/` (in `hxgtm-revops-pipelines`)

**Reference:** [Karpathy on systematic knowledge maintenance](https://x.com/karpathy/status/2039805659525644595?s=46) — why proactive KB linting matters.

---

> ## ⚠️ Superseded scope — raw handling moved to kb-update
>
> This PRD describes kb-lint's **original** design, which scanned *both* the
> canonical KB and the raw source staging area (`raw/<group>/`). Raw-vs-canon
> comparison has since been removed from kb-lint and is owned entirely by the
> sibling skill **`/kb-update`** (which unions raw inputs, diffs them against
> canon, and stages findings in Notion for team triage, closed by
> `/kb-integrate`).
>
> **kb-lint today is a pure canon-internal + external-verification audit.** It
> never reads `raw/<group>/` or `INDEX.md` and never writes raw state. The
> following parts of this document are therefore **obsolete** and retained only
> for historical context — treat `SKILL.md`, `README.md`, and
> `references/output-format.md` as the source of truth:
>
> - §2 "Architecture: raw → context pipeline" and all raw-directory / frontmatter
>   / status-model / INDEX.md detail
> - "Raw vs canon conflicts" and "Unprocessed backlog" scope rows (§3)
> - "Requires Human Review" (`R` findings) and "Unprocessed Raw Backlog" report
>   sections (§6)
> - Phase 2b (raw vs canon comparison), Phase 5 (human review loop), and the
>   Raw–Canon Comparator subagent (§7, §9)
>
> The still-current dimensions are freshness, internal consistency, structural
> integrity, template compliance, coverage gaps, and external verification.

---

## 1. Problem

The GTM OS knowledge base (`../hxgtm-mcp-server/context/`) is ~99 markdown files across
topics like brand positioning, personas, messaging pillars, competitive intel,
marketing strategy, and sales methodology. Multiple skills and workflows consume
these files as source-of-truth context.

Over time, the KB accumulates drift:

- **Stale claims** — a strategy doc says "2025-26" but it's now Q2 2026.
- **Internal contradictions** — one file describes a competitor one way, another
  file contradicts it.
- **Outdated market data** — public facts (funding rounds, product launches,
  exec moves) go stale without anyone noticing.
- **Orphaned content** — files that nothing references, or references to files
  that no longer exist.
- **Gaps** — topics the KB should cover but doesn't, discoverable by looking at
  what other files assume exists.
- **Unprocessed raw sources** — new source material (clipped articles, research,
  internal docs) lands in a staging area but never gets compiled into the
  canonical KB.

Today, catching these problems requires a human to manually re-read the entire KB.
Nobody does this. The result is that skills produce outputs grounded in stale or
contradictory context, and the errors are invisible until they reach a customer.

## 2. Architecture: raw → context pipeline

```
<repo-root>/raw/                ← ingest: unprocessed source material
        │
        ▼  [kb-lint scans both, compares, produces report]
        │
../hxgtm-mcp-server/context/    ← canon: compiled, skill-ready KB
```

Raw source material (clipped articles, research reports, internal docs) lands in
this repo's `raw/` directory. The compiled, skill-ready KB lives in the sibling
`hxgtm-mcp-server` repo at `../hxgtm-mcp-server/context/`. Raw files never move
to canon — they stay in the pipeline as a permanent audit trail. A future
`kb-compile` skill would read `raw/` and write to `context/`.

### Raw directory structure

`raw/` is organized by source type — how the material was collected — not by
topic. The `topic` field in each file's frontmatter maps it to the corresponding
area of the canonical KB for comparison.

```
<repo-root>/
├── raw/
│   ├── INDEX.md                  ← manifest of all raw files with dates + status
│   ├── deep-research/            ← Perplexity/web research outputs
│   ├── transcripts/              ← Gong calls, meeting notes, interviews
│   ├── notion/                   ← Notion page exports, internal docs
│   ├── clippings/                ← Web articles clipped via Obsidian/browser
│   └── teams-chats/              ← Teams/Slack conversations, chat exports
├── .claude/skills/
├── scripts/
└── outputs/
```

This structure is natural at ingest time — you know what kind of source you
have before you know which part of the canon tree it feeds. The `topic`
frontmatter field handles the mapping to canon (e.g., `topic: truth/market`
tells kb-lint to compare against `context/truth/market/*.md`).

### Raw file frontmatter

Each raw file carries lightweight metadata:

```yaml
---
source_title: "Guidewire Q4 2025 Earnings Call Transcript"
source_url: https://example.com/guidewire-q4-2025
source_published: 2026-01-22
retrieved: 2026-03-15
topic: truth/market            # maps to context/truth/market/ for canon comparison
status: new
---
```

The `topic` field is required — it tells kb-lint which canonical files to compare
against, since the directory structure groups by source type, not topic.

### Raw file status model

| Status | Meaning |
|--------|---------|
| `new` | Just ingested, not yet reviewed or incorporated |
| `pending-review` | kb-lint flagged a conflict with canon; awaiting human decision |
| `processed` | Human approved; content compiled into the canonical KB |
| `rejected` | Human reviewed and determined this source should not update canon |

Only a human (or a human-approved automation) moves a file from `pending-review`
to `processed` or `rejected`. The LLM proposes, the human disposes.

### INDEX.md

A flat manifest auto-maintained by the ingest process (or by kb-lint as a side
effect of Phase 1). Allows the LLM to scan recency without opening every file:

```markdown
| File | Source Published | Retrieved | Topic | Status |
|------|-----------------|-----------|-------|--------|
| clippings/2026-03-15_insuretech-connect-recap.md | 2026-03-15 | 2026-03-16 | truth/market | new |
| transcripts/2026-01-22_guidewire-q4-earnings.md | 2026-01-22 | 2026-02-01 | truth/market | processed |
```

---

## 3. Proposed solution

A single skill — `kb-lint` — that scans both the canonical KB and the raw
staging area, cross-references documents against each other and against current
external data, and produces a structured markdown report of findings ranked by
severity. Conflicts between raw sources and canonical content are surfaced for
human review — the skill never overwrites canon autonomously.

### Skill metadata

```yaml
name: kb-lint
description: >
  This skill should be used when the user asks to "lint the knowledge base",
  "check for inconsistencies", "find stale content", "audit the KB",
  "run a health check", "compare new vs old sources", or "check context freshness".
  It scans a markdown knowledge base and its raw source staging area to compare
  newer source documents against existing compiled articles, surfacing
  contradictions, outdated claims, data gaps, unprocessed sources, and missed
  connections. The output is a structured markdown report with prioritized
  findings and suggested remediation actions requiring human review.
  Supersedes the hx-ops `audit-foundation` skill (consistency, staleness,
  gaps, and template compliance checks are now dimensions of kb-lint).
```

## 3. Scope

### In scope

| Dimension | What it checks |
|-----------|---------------|
| **Freshness** | Documents with `Last updated` or date metadata older than their stated review cadence. Claims containing specific dates, quarters, or years that are now in the past. |
| **Raw vs canon conflicts** | Raw files with `status: new` whose content contradicts or updates claims in the corresponding canonical file. These are flagged for human review, not auto-resolved. |
| **Unprocessed backlog** | Raw files with `status: new` that have not been reviewed at all. Sorted by age to surface the most overdue sources. |
| **Internal consistency** | Cross-document contradictions within canon: e.g., two files describing the same competitor, persona, or product capability differently. Conflicting numbers (market size, customer counts, pricing tiers). |
| **External accuracy** | Key factual claims (competitor positioning, market trends, exec names/titles) verified against current web data via Perplexity. |
| **Structural integrity** | Broken internal references (file A links to file B, but B doesn't exist or has moved). Orphaned files not referenced by any other file. Template compliance: canon files in templated directories must contain all required sections in the correct order (see §7 Phase 2 for template registry). Sections containing `[NEEDS COMPLETION]` are acceptable; missing sections are flagged. |
| **Coverage gaps** | Topics referenced by multiple files but never defined in their own document. Personas, competitors, or product areas with thin coverage relative to their importance. |

### Out of scope (v1)

- Automatically updating the canonical KB (report only; human decides what to action).
- Evaluating quality of prose, tone, or brand compliance (that's the `polish` skill).
- Generating new KB articles (a future `kb-compile` skill could handle this).

## 5. Inputs

| Input | Required | Default | Notes |
|-------|----------|---------|-------|
| Canon path | No | `../hxgtm-mcp-server/context/` | The compiled, skill-ready KB |
| Raw path | No | `raw/<group>/` (from config) | The raw source staging area |
| Scan dimensions | No | All 7 | User can request a subset, e.g., "just check freshness" or "just check raw backlog" |
| External verification | No | Enabled | Can be disabled to skip Perplexity calls (faster, offline) |

## 6. Output

A single markdown file saved to `outputs/kb-lint-YYYY-MM-DD.md` containing:

```
# Knowledge Base Lint Report

**Canon:** ../hxgtm-mcp-server/context/
**Raw:** raw/<group>/
**Date:** 2026-04-05
**Canon files scanned:** 99
**Raw files scanned:** 12
**Findings:** 18 (4 high, 8 medium, 6 low)

---

## Summary

[2–3 sentence executive summary of KB health]

---

## Requires Human Review

Findings where raw source material conflicts with canonical content. These
cannot be auto-resolved — a human must decide whether the raw source should
update canon or be rejected.

### [R1] Raw source contradicts competitor positioning
- **Raw file:** `raw/clippings/2026-03-15_insuretech-connect-recap.md` (status: new)
- **Canon file:** `context/truth/market/competitors.md` (line 42)
- **Conflict:** Raw source reports Acme launched an AI pricing module in March 2026; canon describes them as "legacy pricing tool with no AI capability"
- **Recommendation:** Verify the Acme AI launch claim; if confirmed, update competitors.md
- **Action required:** Mark raw file as `processed` or `rejected` after review

### [R2] ...

---

## Unprocessed Raw Backlog

Raw files with `status: new` that have not been incorporated into canon.

| Raw file | Source published | Retrieved | Topic | Days pending |
|----------|-----------------|-----------|-------|-------------|
| truth/market/2026-03-15_insuretech-connect-recap.md | 2026-03-15 | 2026-03-16 | truth/market | 21 |
| ... | ... | ... | ... | ... |

---

## High Severity

### [H1] Internal contradiction in competitor positioning
- **Files:** `context/truth/market/competitors.md` (line 42) vs `context/guidance/competitive/positioning.md` (line 18)
- **Finding:** competitors.md describes Acme as "legacy pricing tool" while positioning.md calls them "emerging AI-native platform"
- **Suggested action:** Reconcile competitor description; check which is current

### [H2] ...

---

## Medium Severity

### [M1] Stale review date
- **File:** `context/marketing/marketing-strategy.md`
- **Finding:** States "Last updated: January 2025" with "Review cadence: quarterly" — now 15 months overdue
- **Suggested action:** Review and update strategy doc for current quarter

### [M2] ...

---

## Low Severity

### [L1] Orphaned file
- **File:** `context/truth/messaging/segments/admitted.md`
- **Finding:** No other file in the KB references this document
- **Suggested action:** Verify still relevant; add cross-references or archive

---

## Coverage Gaps

| Topic | Referenced by | Dedicated article exists? |
|-------|--------------|--------------------------|
| Reinsurance segment | 3 files | No |
| ... | ... | ... |

---

## Statistics

| Metric | Value |
|--------|-------|
| Canon files scanned | 99 |
| Raw files scanned | 12 |
| Raw files pending (status: new) | 8 |
| Total words (canon) | ~85,000 |
| Avg canon file age (by last_reviewed) | 4.2 months |
| Canon files with no date metadata | 23 |
| Raw–canon conflicts found | 3 |
| External claims verified | 31 |
| External claims flagged | 5 |
```

## 7. Workflow (high-level)

The skill runs in 5 phases. Phases 1–3 can be parallelized; phase 4 is
synthesis; phase 5 is the human review loop.

### Phase 1 — Index & parse (both trees)

Scan both the canonical KB and the raw staging area:

**Canon tree** (`../hxgtm-mcp-server/context/`):

1. Recursively scan for all `.md` files.
2. For each file, extract:
   - Metadata: `last_reviewed`, `Review cadence`, `Status`, `Owner`, `Type`
     (from YAML frontmatter or inline conventions like marketing-strategy.md)
   - Internal references: links to other KB files (`[text](relative-path)`,
     `**filename.md**`, or prose references like "see product-marketing-context.md")
   - Factual claims: dates, numbers, named entities (competitors, people, products)
   - Topic tags: inferred from directory path + headings
3. Build an index: file → metadata + claims + references + topics.

**Raw tree** (`raw/<group>/`):

1. Recursively scan for all `.md` files (excluding INDEX.md).
2. For each file, extract frontmatter: `source_published`, `retrieved`, `topic`,
   `status`.
3. Build a raw index: file → metadata + topic mapping.
4. Update `raw/INDEX.md` if any new files were found that aren't listed.

### Phase 2 — Internal analysis (canon)

Using the canon index from Phase 1, run these checks:

- **Freshness:** Flag files where `today - last_reviewed > review_cadence`.
  Flag any file with no date metadata at all (informational, low severity).
  Flag claims referencing specific past dates/quarters.
- **Cross-references:** Build a reference graph. Identify broken links (target
  doesn't exist) and orphaned files (zero inbound references).
- **Internal consistency:** For each entity (competitor, persona, product,
  market segment) mentioned in multiple files, compare descriptions. Flag
  contradictions or significant divergence.
- **Template compliance:** Validate files in templated directories against
  their canonical templates (see registry below). Check that all required
  sections exist and are in the correct order. Sections containing
  `[NEEDS COMPLETION]` are acceptable; missing sections are flagged as medium
  severity.
- **Coverage gaps:** Find entities referenced by 2+ files that have no dedicated
  article. Look for directory-level patterns (e.g., all other products have a
  messaging pillar file, but one doesn't).

#### Structural template registry

Files in these directories are validated against their corresponding template:

| Directory | Template | Owned by |
|-----------|----------|----------|
| `truth/audiences/*.md` (excluding `_template-*`) | `truth/audiences/_template-persona.md` | refresh-personas, refresh-icp |
| `truth/messaging/products/*.md` (excluding `_template-*`) | `truth/messaging/_template-product.md` | refresh-messaging |
| `truth/messaging/segments/*.md` (excluding `_template-*`) | `truth/messaging/_template-segment.md` | refresh-messaging |

#### Foundation files read

Phase 2 reads across all foundation files owned by the hx-ops refresh skills.
This scope was previously covered by the standalone `audit-foundation` skill,
which kb-lint supersedes.

- All `context/truth/audiences/*.md` (owned by refresh-personas, refresh-icp)
- All `context/truth/brand/*.md` (owned by refresh-positioning)
- All `context/truth/market/*.md` (owned by refresh-positioning)
- All `context/truth/messaging/products/*.md` (owned by refresh-messaging)
- All `context/truth/messaging/segments/*.md` (owned by refresh-messaging)
- `context/truth/messaging/eval-rubric.md` (quality standard reference)
- All `context/marketing/truth/brand/*.md` (owned by refresh-voice)

Plus all other `context/**/*.md` files (marketing strategy, sales methodology,
competitive guidance, etc.).

### Phase 2b — Raw vs canon comparison

Using both indexes from Phase 1, compare raw sources against their
corresponding canonical files:

1. For each raw file with `status: new`, identify the matching canon subtree
   using the `topic` field (e.g., `topic: truth/market` maps to
   `context/truth/market/*.md`).
2. Compare the raw source's content against the canonical file(s) in that
   subtree. Look for:
   - **Direct contradictions** — the raw source states something the canon
     file explicitly contradicts (e.g., competitor launched a new product
     that canon says doesn't exist).
   - **Superseding data** — the raw source has newer numbers, dates, or facts
     that update what's in canon.
   - **Net-new information** — the raw source covers something canon doesn't
     mention at all.
3. For each conflict or update found, mark the raw file as `pending-review`
   and create a finding in the "Requires Human Review" section of the report.

**Important:** The LLM never decides whether raw data should override canon.
It only surfaces the conflict and recommends a course of action. Raw sources
can be noisy, outdated-at-arrival, or from unreliable origins. Only a human
(or human-approved automation) promotes raw content into canon.

### Phase 3 — External verification (optional)

For high-value factual claims identified in Phase 1 (competitor descriptions,
market positions, named executives, market sizing), verify against current web
data using Perplexity.

Prioritize:
1. Competitor claims (highest churn rate in reality)
2. Named people + titles (execs move frequently)
3. Market data and trends
4. Product capabilities of third parties

Cap at ~30 external verification calls per run to manage cost/time.

### Phase 4 — Synthesize report

1. Rank all findings by severity:
   - **Requires human review:** Raw–canon conflicts (reported separately at top)
   - **High:** Internal contradictions within canon, externally disproven claims
   - **Medium:** Stale content past review cadence, broken references
   - **Low:** Orphaned files, missing metadata, coverage gaps
2. List unprocessed raw backlog (all `status: new` files, sorted by age).
3. Assemble into the output format (Section 6).
4. Save to `outputs/kb-lint-YYYY-MM-DD.md`.
5. Present summary to user.

### Phase 5 — Human review loop

After the report is generated, the human reviews each finding in the "Requires
Human Review" section and decides per raw file:

| Decision | What happens |
|----------|-------------|
| **Accept** | Human (or kb-compile skill) updates the canonical file, then sets raw file `status: processed` |
| **Reject** | Human sets raw file `status: rejected` — the source is kept for audit trail but will not trigger future findings |
| **Defer** | Raw file stays `status: pending-review` — it will appear again in the next lint run |

Phase 5 happens outside the skill's execution. The skill produces the report;
the human acts on it asynchronously. A future version could provide an
interactive review mode where the skill walks the user through each finding
and updates statuses in real time.

## 8. Dependencies

| Dependency | Required | Purpose |
|------------|----------|---------|
| Claude Opus | Yes | Multi-phase reasoning across ~99+ files |
| Perplexity MCP | No (but recommended) | Phase 3 external verification |
| File system access | Yes | Read canon + raw trees; update raw file frontmatter status |

No Glean or Notion integration needed for v1.

## 9. Subagent strategy

Follow the generate-dossier pattern:

| Subagent | Phase | Responsibility |
|----------|-------|---------------|
| Indexer | 1 | Parse both canon and raw trees, build structured indexes |
| Canon Analyzer | 2 | Freshness, cross-refs, consistency, gaps within canon |
| Raw–Canon Comparator | 2b | Compare new raw sources against matching canon files |
| External Verifier | 3 | Perplexity-based claim checking |
| Synthesizer | 4 | Rank findings, assemble report |

Phases 2, 2b, and 3 can run in parallel once Phase 1 completes (all consume
the index). Phase 4 waits for all three. Phase 5 (human review) happens
outside the skill.

For a simpler v1, Phases 1 + 2 + 2b can be a single subagent (internal scan)
and Phase 3 a second (external verification), with Phase 4 running inline.

## 10. Future extensions (not v1)

- **Interactive review mode:** Instead of an async report, walk the user through
  each "Requires Human Review" finding in-session, updating raw file statuses
  and canon files in real time with human approval per change.
- **kb-compile companion skill:** Read accepted raw sources and compile/update
  the corresponding canonical files, with human approval before writing.
- **Scheduled runs:** Integrate with batch-dossier.sh pattern for weekly/monthly
  automated linting.
- **Diff-aware mode:** Accept a list of recently changed files and lint only those
  plus their dependents, instead of full scan.
- **Notion publishing:** Push the lint report to a Notion database for team tracking.
- **Trend tracking:** Compare successive lint reports to show whether KB health is
  improving or degrading over time.
- **Ingest skill:** A companion skill that clips a URL or document into raw/ with
  proper frontmatter and filename conventions, and updates INDEX.md.

## 11. Open questions

1. **Severity thresholds** — What makes something "high" vs "medium"? The PRD
   proposes a heuristic (contradictions = high, staleness = medium, gaps = low).
   Should this be configurable?
2. **Verification budget** — Phase 3 proposes a cap of ~30 Perplexity calls.
   Is that the right balance of thoroughness vs cost?
3. **Scope creep guard** — Should the skill accept an explicit file allowlist/blocklist
   to focus on a subtree (e.g., "just lint truth/market/")?
4. **Metadata convention** — Not all canon files follow the `last_reviewed` /
   `Review cadence` pattern (23 files have no date metadata at all). Should the
   first run include a "Phase 0" that flags and proposes standardizing metadata
   on non-conforming files?
5. **Cross-KB references** — Some skills reference files outside `../hxgtm-mcp-server/context/`.
   v1 should stay scoped to canon + raw only.
6. **Raw file trust level** — Should raw files carry a `source_reliability` field
   (e.g., `official`, `press`, `blog`, `unverified`) to help the human reviewer
   prioritize which conflicts to investigate first?
7. **Rejection granularity** — When a raw file is rejected, should the entire file
   be rejected, or should individual claims within it be accept/reject-able?
   (v1 proposes whole-file; claim-level is a future extension.)
