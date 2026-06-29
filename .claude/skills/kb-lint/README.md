# kb-lint

Group-scoped health audit of the canonical GTM knowledge base for
staleness, contradictions, and structural issues. Produces a
severity-ranked markdown report at
`outputs/kb-lint-<group>-YYYY-MM-DD.md`.

kb-lint is a pure read-only **canon audit** skill — it does not scan the
raw staging area (`raw/<group>/`) or touch `INDEX.md`. If you want raw
sources diffed against canon and staged in a Notion database for async
team triage, use the sibling skill [/kb-update](../kb-update/README.md)
instead — it unions raw inputs and owns the Notion write path.

## Requirements

| Requirement | Purpose | Required? |
|---|---|---|
| **Claude Code** (CLI or IDE extension) with **Claude Opus** model | Multi-phase reasoning across 120+ files | **Required** |
| **Canon access**: either the `hxgtm-context` MCP server configured OR the `hxgtm-mcp-server` repo cloned at `../hxgtm-mcp-server/` | Reading the canonical GTM KB (~120 files) | **Required** — resolved at startup (Step 2) |
| **Perplexity MCP** | Phase 3 external claim verification | Optional — skipped silently if unavailable |

## Quick start

```
/kb-lint --group competitive                    # Full scan for competitive group
/kb-lint --group competitive freshness          # Only check freshness in competitive
/kb-lint --group competitive --no-external      # Skip Phase 3 (Perplexity)
/kb-lint --list-groups                          # Print all groups + active flag
```

**Output:** `outputs/kb-lint-<group>-YYYY-MM-DD.md` — a markdown report
with an executive summary, high/medium/low severity findings, coverage
gaps, and run statistics. Multiple runs on the same day are preserved
with a `-2`, `-3`, … counter appended to the filename.

## Group scoping

kb-lint requires an explicit `--group <slug>`. Each group maps to a
slice of the canonical KB, defined in [config.yaml](config.yaml).

| Slug | Label | Codeowner | Active |
|---|---|---|---|
| `competitive` | Competitive Intelligence | competitive-intelligence | yes |
| `messaging` | Product & Segment Messaging | product-segment-messaging | yes |
| `audiences` | Audiences & Personas | audiences-personas | yes |
| `company-policies` | Company Policies & Platform Commitments | company-policies-platform-commitments | yes |
| `company-overview` | Company Overview & Narrative | company-overview-narrative | yes |
| `marketing-strategy` | Marketing Strategy | marketing-strategy | yes |
| `brand-voice` | Brand, Voice & Positioning | brand-voice-positioning | yes |
| `channel-playbooks` | Channel Playbooks | channel-playbooks | yes |
| `sales-methodology` | Sales Methodology | sales-methodology | yes |
| `accounts` | Account & Opp-level Context | account-opp-context | yes |
| `rfp` | RFP Responses | rfp-responses | yes |

All 11 groups are active — kb-lint runs directly against any of them
via `/kb-lint --group <slug>`. The `active` flag in config.yaml is
informational (kb-lint does not gate on it); it records whether a
group is considered ready.

Linting a group is just:

1. Ensure the group's `canon` globs in [config.yaml](config.yaml) point
   at the right slice of `../hxgtm-mcp-server/context/`
2. Run `/kb-lint --group <slug>`

kb-lint reads canon only — there is no raw-source onboarding step. Raw
sources are handled separately by [/kb-update](../kb-update/README.md).

---

## Setup in hxgtm-revops-pipelines (Claude Code CLI / IDE)

### Prerequisites

- **Claude Opus** — required for multi-phase reasoning across 120+ files
- **Repository layout** — this repo must be cloned alongside `hxgtm-mcp-server`:
  ```
  hx-projects/
  ├── hxgtm-revops-pipelines/    ← this repo
  │   ├── .claude/skills/kb-lint/
  │   └── outputs/
  └── hxgtm-mcp-server/
      └── context/               ← canonical KB (~120 files)
  ```
- The skill auto-detects whether to use MCP or filesystem access (see below)

### How it works

The skill runs straight through with no interactive gate. It:

1. Resolves canon access mode (MCP server, falling back to filesystem) and Perplexity MCP availability
2. Indexes the canon tree
3. Launches 1-2 subagents in parallel:
   - **Canon Analyzer** — freshness, cross-refs, consistency, templates, gaps
   - **External Verifier** (Phase 3, conditional) — verifies high-churn factual claims against Perplexity. Skipped if Perplexity MCP is unavailable or `--no-external` was passed. Never blocks the lint.
4. Synthesizes findings into a structured JSON list in memory
5. Renders the JSON list into the markdown report template (see
   [references/output-format.md](references/output-format.md))
6. Writes the report to `outputs/kb-lint-<group>-YYYY-MM-DD.md`

### Canon access: dual-mode (filesystem / MCP)

The skill supports two modes for accessing the canonical KB, resolved at
startup in Step 2 (MCP first, filesystem fallback):

| Mode | When used | How it works |
|------|-----------|-------------|
| **MCP** | hxgtm-context MCP server is configured and responding | Uses `ListMcpResourcesTool` / `ReadMcpResourceTool` with `context://` URIs |
| **Filesystem** | MCP server unavailable (local testing) | Reads directly from `../hxgtm-mcp-server/context/` via Glob + Read tools |

No configuration change is needed to switch modes — the skill detects which is
available and adapts. Subagents receive file content identically in both modes.

### Connecting the MCP server in Claude Code

To enable MCP mode, the hxgtm-context server must be registered in your Claude
Code MCP configuration. There are two options:

**Option A: Project-level config (recommended)**

Create `.mcp.json` in the repo root:

```json
{
  "mcpServers": {
    "hxgtm-context": {
      "type": "streamableHttp",
      "url": "http://localhost:3000/mcp"
    }
  }
}
```

This is checked into the repo so all team members get the same config.

**Option B: User-level config**

Add the server to your user MCP settings at `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "hxgtm-context": {
      "type": "streamableHttp",
      "url": "http://localhost:3000/mcp"
    }
  }
}
```

**Starting the server:**

The MCP server must be running before invoking `/kb-lint`:

```bash
# From the hxgtm-mcp-server directory
cd ../hxgtm-mcp-server

# Development (with hot reload)
npm run dev

# Production (requires build first)
npm run build && npm start
```

The server starts on port 3000 by default (configurable via `PORT` env var).
It requires Entra ID (Azure AD) credentials in `.env` for authentication.

**Verifying the connection:**

After starting the server and configuring Claude Code, run `/kb-lint` and
check the report header (and run log). It should show:

```
**Canon access:** mcp
```

If it shows `filesystem` instead, the MCP server is not reachable — check that
it's running and the URL in your config matches.

---

## Scan dimensions

| Dimension | What it checks | Default |
|-----------|---------------|---------|
| `freshness` | Files past review cadence, stale date claims | On |
| `consistency` | Cross-document contradictions within canon | On |
| `structural` | Broken cross-references, orphaned files | On |
| `template` | Template compliance for templated directories | On |
| `coverage` | Topics referenced but never defined | On |
| `external` | Phase 3 — verifies high-churn factual claims (competitors, execs, market data) against current web data via Perplexity MCP | On (auto-skipped if MCP unavailable) |

Run a subset: `/kb-lint --group competitive freshness consistency`

Skip Phase 3 explicitly: `/kb-lint --group competitive --no-external` (lint runs to completion without Perplexity calls).

---

## Report format

The report follows a fixed structure (see
[`references/output-format.md`](references/output-format.md)):

1. **Header** — group, paths, date, file counts, finding summary
2. **Summary** — 2–3 sentence health assessment
3. **High Severity** — internal contradictions
4. **Medium Severity** — staleness, broken refs, template issues
5. **Low Severity** — orphans, missing metadata, gaps
6. **Coverage Gaps** — table of missing dedicated articles
7. **Statistics** — aggregated metrics

### Severity classification

| Severity | Criteria |
|----------|----------|
| High | Internal contradiction within canon, or externally disproven claim (Phase 3) |
| Medium | Stale content, broken reference, template violation, externally outdated claim (Phase 3) |
| Low | Orphaned file, missing metadata, coverage gap |

---

## Reviewing findings

1. **Open the report** at `outputs/kb-lint-<group>-YYYY-MM-DD.md` and
   walk each finding.
2. **Address findings** (staleness, broken refs, orphans, contradictions,
   coverage gaps) by editing the canon files directly in
   `../hxgtm-mcp-server/context/`.
3. **Re-run `/kb-lint --group <slug>`** to confirm fixes landed. Each
   kb-lint run is a complete snapshot — a finding re-appears until canon
   is fixed.

**Reconciling new raw sources?** kb-lint audits canon only. To diff raw
sources against canon and stage findings as Notion rows the whole team
can triage asynchronously, run `/kb-update --group <slug>` — that sibling
skill owns the raw → canon → Notion workflow.

---

## Phase 3 — External Verification

Phase 3 verifies high-churn factual claims across canon (competitor
capabilities, exec titles, market data) against current web data via
Perplexity MCP.

It auto-activates when a Perplexity MCP tool is detected at startup (Step 2c)
AND the `external` scan dimension is enabled (default on). To skip Phase 3
even when Perplexity is available, run `/kb-lint --no-external` or pass an
explicit dimension list that omits `external`.

**Phase 3 is non-blocking.** If Perplexity MCP is unavailable, detection
fails, the verifier crashes mid-run, or you exclude `external`, kb-lint
runs to completion without Phase 3 — the rest of the lint always finishes.
The skip is acknowledged in the executive summary and Statistics section
so you know you got a partial scan.

### What it verifies

Phase 3 reads a **curated allowlist of canon files** where externally
verifiable factual claims live, extracts verifiable claims from that
content, and queries Perplexity to compare against current public data.

**Files in scope:**
- `context/guidance/competitive/competitors/*.md`
- `context/guidance/competitive/positioning.md`
- `context/truth/market/*.md`
- `context/truth/audiences/*.md`
- `context/truth/brand/*.md`
- `context/marketing/marketing-strategy.md`

Files outside this allowlist (templates, voice guides, eval rubrics, sales
methodology, platform procedures) are excluded — they contain no externally
verifiable claims. If a verifiable claim ends up in an excluded file, it
will be silently missed by Phase 3 until the allowlist is updated.

Priority order (highest churn first):
1. **Competitor claims** — product capabilities, positioning, pricing
2. **Named people + titles** — executives, roles
3. **Market data** — sizing, growth rates, regulatory changes
4. **Third-party product capabilities** — features of non-competitor products mentioned in canon

### Cost controls

Hard cap: 30 Perplexity calls per run (Guardrail G7). Claims beyond the cap
are deferred to the next run, with a count logged in Statistics.

### Findings

External Verifier produces findings that get merged into the main report:
- **Contradicted** — direct conflict between canon and current web data → routed to High Severity
- **Outdated** — newer information supersedes the canonical claim → routed to Medium Severity

Every finding includes the Perplexity source URL for traceability (Guardrail G8).
Findings without a source URL are dropped before report assembly.

See [`references/external-verifier.md`](references/external-verifier.md)
for the complete subagent specification.

---

## Guardrails

kb-lint includes 5 guardrails to prevent incorrect findings and missed
issues. See [GUARDRAILS.md](GUARDRAILS.md) for full details.

| ID | Guardrail | What it prevents |
|----|-----------|-----------------|
| G1 | **Finding verification** | Orchestrator spot-checks every High severity finding by reading cited files and confirming quoted text exists. Hallucinated findings are downgraded or removed. |
| G4 | **Coverage confirmation** | Canon Analyzer reports which files it actually read in full vs metadata only — so you can verify nothing was silently skipped. |
| G6 | **Sanity check on 0 findings** | If Canon Analyzer reports 0 findings for 100+ files, a warning flags likely incomplete analysis. |
| G7 | **Perplexity cost cap** | Hard cap of 30 Perplexity calls per Phase 3 run. Claims beyond the cap are deferred to the next run. |
| G8 | **Verification source citation** | Every Phase 3 finding must include the Perplexity source URL. Findings without one are dropped from the report. |

---

## File structure

```
.claude/skills/kb-lint/
├── SKILL.md                    ← Main orchestrator
├── README.md                   ← This file
├── PRD.md                      ← Design document
├── GUARDRAILS.md               ← Guardrails documentation
├── config.yaml                 ← Group definitions (canon globs, active flag)
└── references/
    ├── canon-analyzer.md       ← Subagent A: internal KB analysis
    ├── external-verifier.md    ← Subagent B: Phase 3 external verification
    ├── output-format.md        ← Finding JSON schema + markdown report template
    └── template-registry.md    ← Template-to-directory mapping
```
