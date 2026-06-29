---
name: kb-lint
description: >
  Group-scoped health audit of the canonical GTM knowledge base. kb-lint
  runs against one group at a time (e.g., competitive, messaging,
  audiences) as defined in .claude/skills/kb-lint/config.yaml, finding
  contradictions, stale claims, data gaps, broken references, and template
  compliance issues within the group's canon slice. Produces a
  severity-ranked markdown report at outputs/kb-lint-<group>-YYYY-MM-DD.md.
  Use when asked to "lint the KB", "check for inconsistencies", "find stale
  content", "audit the KB", "run a health check", or "check context freshness".
  A no-argument run audits the WHOLE canon (every file under context/ plus the
  project meta docs) in one sharded, parallel pass and writes a single merged
  report at outputs/kb-lint-all-YYYY-MM-DD.md; pass `--group <slug>` to narrow
  the audit to one group's canon slice. kb-lint does NOT process raw source
  files — to diff raw sources against canon and stage findings in Notion for
  team triage, use the sibling skill `/kb-update` instead.
---

# Knowledge Base Lint

## What this skill does

Scans the canonical KB, cross-references documents against each other, and
writes a severity-ranked markdown report. kb-lint has two **scan modes**,
resolved from the CLI arguments in Step 1:

- **`group` mode** (`--group <slug>`) — audits one group's canon slice and
  writes `outputs/kb-lint-<group>-YYYY-MM-DD.md`. This is the original
  behavior and is unchanged.
- **`all` mode** (no `--group`) — audits the **whole canon** (every `.md`
  under `context/`, by file walk, plus the project meta docs in
  `all_mode.extra_globs`) in one run, sharded across parallel Canon Analyzer
  subagents, and writes a single merged report
  `outputs/kb-lint-all-YYYY-MM-DD.md`. Because all-mode enumerates files
  directly rather than unioning the group globs, it also covers canon files
  no group claims.

The skill runs in phases. In `group` mode: 3 phases by default, or 4 when the
`external` dimension is enabled and Perplexity MCP is available. In `all`
mode there is an additional cross-group consistency pass:

1. **Phase 1 — Index & parse** the canonical KB tree, and in all-mode
   size-shard the in-scope files (inline)
2. **Phase 2 — Internal analysis** of the canonical KB. One Canon Analyzer
   subagent in group-mode; one per shard (launched in parallel waves) in
   all-mode.
3. **Phase 3 — External verification** via Perplexity MCP (subagent, parallel
   with Phase 2 — skipped if Perplexity MCP unavailable or `external`
   dimension excluded by user). Phase 3 is **never blocking** — its absence
   does not stop the lint.
4. **Phase 4 — Synthesize findings into a markdown report** (inline). In
   all-mode this phase also runs a **Cross-Group Consistency** subagent over
   the shards' entity digests to catch contradictions that span shard
   boundaries.

kb-lint is read-only — it never writes to Notion and never touches the raw
source staging area (`raw/<group>/`) or its `INDEX.md`. Raw sources are
entirely the domain of the sibling skill `/kb-update`: to diff raw sources
against canon and stage findings in a Notion database for async team triage,
run `/kb-update --group <slug>`.

## Requirements

- **Claude Opus** — Multi-phase reasoning across ~120+ files.
- **Canon access** — Either the hxgtm-context MCP server (production) or
  direct filesystem access to `../hxgtm-mcp-server/context/` (local testing).
  Resolved in Step 2 (MCP first, filesystem fallback).
- **Filesystem access** — Bash tool required for canon file indexing in
  filesystem mode.
- **Perplexity MCP** (optional — enables Phase 3 external verification) — For
  external claim verification against live web data. Auto-detected in
  Step 2; if unavailable, Phase 3 is silently skipped and the rest of
  the lint runs to completion.

## Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Canon MCP server | `hxgtm-context` | MCP server name for production access |
| Canon filesystem path | `../hxgtm-mcp-server/context/` | Fallback for local testing (relative to repo root) |
| Canon access mode | auto-detected | `mcp` if server responds, `filesystem` otherwise |
| Group config | `.claude/skills/kb-lint/config.yaml` | Source of truth for group → canon globs and `active` flag |
| Canon scope | derived from `groups.<slug>.canon` globs | Only files matching the group's globs are analyzed; full tree is still indexed for cross-reference resolution |
| Output path | `outputs/kb-lint-<group>-YYYY-MM-DD.md` | Markdown report; a `-2`, `-3`, … counter is appended if the file for today already exists |
| Default dimensions | all except `external` | freshness, consistency, structural, template, coverage — `external` excluded by default (Step 0 prompt) |
| Account dossiers | excluded by default | `context/accounts/**` out of scope unless user selects Yes at Step 0 prompt (or passes `--accounts` in batch) |
| Phase 3 | off by default | External verification via Perplexity — disabled by default at Step 0 prompt; auto-skipped if MCP unavailable; never blocks the lint |

### Scan dimensions

Users can request a subset of checks:

| Dimension | What it checks |
|-----------|---------------|
| `freshness` | Files past review cadence, stale date claims |
| `consistency` | Cross-document contradictions within canon |
| `structural` | Broken cross-references, orphaned files |
| `template` | Template compliance for files in templated directories |
| `coverage` | Topics referenced but never defined |
| `external` | Phase 3 — verifies high-churn factual claims (competitors, execs, market data) against current web data via Perplexity MCP. **Excluded by default** (Step 0 prompt defaults to No). Auto-skipped if MCP unavailable even when enabled. |

---

## Workflow

### Step 0 — Confirm run options

Before collecting arguments or resolving access, ask the user two binary questions using `AskUserQuestion`. Present them together in a single prompt titled "KB Lint — Run Options":

1. **External validation (Perplexity)** — "Run Phase 3 external verification using Perplexity MCP? Verifies high-churn factual claims (competitor data, market figures, exec names) against live web data. Adds time and API cost." Default: **No**
2. **Account dossiers** — "Include account dossiers (`context/accounts/`) in the audit? These are high-volume files that significantly increase run time, especially in all-mode." Default: **No**

Record the answers as two flags:
- `user_wants_external` — `true` if the user selected Yes, `false` (default) otherwise
- `user_wants_accounts` — `true` if the user selected Yes, `false` (default) otherwise

**Batch mode / non-interactive:** Skip this step entirely. Set `user_wants_external = false` and `user_wants_accounts = false` as the defaults and proceed directly to Step 1.

These flags propagate into the rest of the workflow:
- `user_wants_external = false` → behaves exactly as if `--no-external` was passed; `external` is removed from `scan_dimensions` before Step 2c runs, and `phase_3_enabled` is set to `false` with reason "excluded by user (default)".
- `user_wants_accounts = false` → in Step 3a, mark every file matching `context/accounts/**` as `in_scope: false`, regardless of scan mode or group globs. The files are still indexed so cross-references from in-scope files into `accounts/` are resolvable, but they are never sent as full content to Canon Analyzer subagents and no findings are raised against them. In group-mode with `--group accounts`, add a note to the report header: "Account dossiers excluded by user at run start. Re-run and select Yes at the prompt to include them."

### Step 1 — Collect input

kb-lint has two scan modes. Resolve `scan_mode` from the arguments:

- **`--list-groups`** — short-circuits everything: print the group table
  (see below) and exit without linting. Does not need `--group`.
- **`--group <slug>`** — sets `scan_mode = group`. Identifies which single
  group to lint (e.g., `competitive`, `messaging`). This is the original
  behavior; everything downstream that says "the group" applies as before.
- **Neither `--group` nor `--list-groups`** — sets `scan_mode = all`. A
  no-argument `/kb-lint` audits the **whole canon** — every `.md` under
  `context/` (enumerated by file walk, not by unioning group globs, so
  files no group claims are still covered) plus the project meta docs in
  `all_mode.extra_globs`. All-mode shards the content across parallel Canon
  Analyzer subagents and writes one merged report. There is no halt — the
  absence of `--group` is itself the request for an all-canon scan.

Parse arguments:

- **`--list-groups`** — print all groups from `config.yaml` with their
  labels, codeowners, and `active` flag, then exit without linting:
  ```
  Slug                  Label                                     Owner                          Active
  competitive           Competitive Intelligence                  competitive-intelligence       yes
  messaging             Product & Segment Messaging               product-segment-messaging      yes
  audiences             Audiences & Personas                      audiences-personas             yes
  ...
  ```

- **Dimension filter** — e.g., "just freshness", "consistency only". If
  provided, restrict scanning to those dimensions. Default: all dimensions
  (including `external`).
- **`external` dimension toggle** — Phase 3 external verification via
  Perplexity MCP is **disabled by default** (the Step 0 prompt defaults to No).
  It can also be skipped by passing `--no-external` or using a positive
  dimension list that omits `external` (e.g., `/kb-lint --group competitive
  freshness consistency`). If `user_wants_external = false` from Step 0, treat
  it as equivalent to `--no-external` — remove `external` from
  `scan_dimensions` now, before Step 2c. Phase 3 also auto-skips when
  Perplexity MCP is unavailable — see Step 2c.
- **Subtree focus** (group-mode only) — e.g., "just truth/market/". If
  provided, **further** restricts scanning within the group's declared canon
  globs. Must fall under at least one of the group's canon paths, else warn
  and ignore. Default: use the full set of canon globs for the group. Ignored
  in all-mode (all-mode always scans the whole canon).

There is no required argument. With `--group <slug>` kb-lint runs group-mode;
with no `--group` it runs all-mode; `--list-groups` short-circuits. All other
arguments fall back to their defaults.

### Step 2 — Resolve access (optimistic)

kb-lint runs straight through — there is no pre-flight validation wall
and no proceed gate. Assume canon and (optionally) Perplexity are
present, resolve access, and proceed directly to indexing. If something is
genuinely missing, it surfaces reactively at the step that needs it (see
Error handling).

**Load config**

Read `.claude/skills/kb-lint/config.yaml` from the repo root.

- **Group mode** (`scan_mode = group`) — look up the group specified by
  `--group`. Assume it is present. Only if the lookup genuinely returns
  nothing, halt with:

  > Unknown group `<slug>`. Run `/kb-lint --list-groups` to see available
  > groups.

  Record the resolved group record (label, codeowner, canon globs) for use
  in Steps 3, 5, and 7. The `active` flag is informational — kb-lint does
  not gate on it.

- **All mode** (`scan_mode = all`) — there is no group record to look up.
  Use the synthetic values `slug = all`, `label = "Whole Canon"`,
  `codeowner = "all-codeowners"` for the report header and Step 7 summary.
  Read the `all_mode` block (`extra_globs`, `shard_max_files`,
  `shard_max_bytes`, `wave_size`) for Steps 3 and 4. If the `all_mode` block
  is missing, fall back to built-in defaults (`extra_globs: []`,
  `shard_max_files: 25`, `shard_max_bytes: 120000`, `wave_size: 5`).

**2a. Canon access resolution**

Resolve how to read the canonical KB (this sets the report header; it is
not a gate):

1. Attempt `ListMcpResourcesTool(server: "hxgtm-context")`
2. If it returns resources:
   - Set `canon_access_mode = mcp`
   - Count the returned resources as `canon_file_count`
   - Record the MCP server name for use in Step 3
3. If it fails or is unavailable:
   - Resolve the filesystem path `../hxgtm-mcp-server/context/`
   - Set `canon_access_mode = filesystem`
   - Count `.md` files with Glob (`**/*.md` under the canon path) as
     `canon_file_count`

If neither MCP nor filesystem turns out to be readable when Step 3 tries
to read, report the error and stop (see Error handling) — canon access is
the one hard requirement.

**2b. Repo-root resolution for project meta docs (all-mode only)**

In `scan_mode = all`, kb-lint also scans the project meta docs in
`all_mode.extra_globs` (e.g. `README.md`, `AGENTS.md`, `docs/**`). These
live at the **hxgtm-mcp-server repo root** — the parent directory of the
canon `context/` folder — and are **filesystem-only**: the `hxgtm-context`
MCP server serves `context://` resources, not repo-root files.

- Resolve `repo_root` = parent of the canon filesystem path
  (`../hxgtm-mcp-server/` when the canon path is `../hxgtm-mcp-server/context/`).
- In `filesystem` canon mode, `repo_root` is always available.
- In `mcp` canon mode, attempt to resolve `repo_root` on disk anyway (the
  repo is usually checked out at the sibling path). If it is not reachable,
  set `meta_files_available = false`, skip the meta globs, and record a
  header note: "Project meta docs skipped — repo not on disk in MCP mode."
- This is **never blocking**; missing meta docs only narrow the scan.

Skip 2b entirely in `scan_mode = group`.

**2c. Perplexity MCP detection (Phase 3)**

If the user excluded the `external` dimension in Step 1 (via `--no-external`
or a positive dimension list that omits `external`), set
`phase_3_enabled = false` and skip detection. Record reason as
"excluded by user".

Otherwise, try to detect whether Perplexity MCP is available:

1. Check the available tools for any MCP tool whose name contains
   "perplexity" (e.g., `mcp__project_0_gtmos_perplexity__*`)
2. If found: set `phase_3_enabled = true`, record the tool name(s) for use
   in Step 4
3. If not found: set `phase_3_enabled = false`, record reason as
   "not configured"

**Phase 3 is optional and never blocks the lint.** When Perplexity MCP is
unavailable OR the `external` dimension is excluded, the External Verifier
subagent is skipped and no `E` findings appear in the report. kb-lint runs
to completion regardless. The skip is acknowledged in:
- The executive summary in Step 5e
- The Statistics section ("Phase 3 status: skipped (reason)")

Detection failures themselves never raise errors — if the tool-listing
mechanism fails for any reason, default to `phase_3_enabled = false`,
record reason as "detection failed", and proceed.

### Step 3 — Phase 1: Index & parse (inline)

Build a structured index of the canon tree. This step runs
inline (not as a subagent) because the orchestrator needs the index to
prepare subagent inputs.

The orchestrator always indexes the **full canon tree** (needed for cross-ref
resolution so broken links into out-of-scope files are still detected). Which
files are marked **in scope** for deep analysis depends on `scan_mode`:

- **Group mode** — only files matching the group's `canon` globs are in
  scope. Out-of-scope files flow to subagents as reference metadata only.
- **All mode** — **every** `.md` under `context/` is in scope, plus the
  project meta docs resolved from `repo_root` in Step 2b. Scope is decided by
  file enumeration, not by the group globs, so canon files no group claims
  are still audited.

#### 3a. Canon index

Access files based on `canon_access_mode`:

**MCP mode:**
- Use `ListMcpResourcesTool(server: "hxgtm-context")` to enumerate all
  `context://` URIs
- For each resource, use `ReadMcpResourceTool(server: "hxgtm-context",
  uri: "context://[relative-path]")` to read content

**Filesystem mode:**
- Use Glob for `**/*.md` under the canon filesystem path
- Use Read tool for each file

**All-mode meta docs (filesystem only):** when `scan_mode = all` and
`meta_files_available` is true, also enumerate each pattern in
`all_mode.extra_globs` relative to `repo_root` (e.g. Glob `docs/**/*.md`,
Read `README.md`, `AGENTS.md`). **Dedupe by realpath** — `CLAUDE.md` is a
symlink to `AGENTS.md`, so resolve symlinks and index the target once.
Record these files with paths relative to `repo_root` (e.g. `README.md`,
`docs/release-checklist.md`) so they are visually distinct from
`context/`-relative canon paths in the index.

For each `.md` file, extract and record:

1. **Relative path** (from context root)
2. **Frontmatter fields** — look for YAML frontmatter first (`---` delimited).
   Extract: `type`, `canonical`, `status`, `owner`, `last_reviewed`, `persona`,
   `capability`, `segment`, `positioning_source`, `job_profile`, `references`
3. **Inline metadata** — for files without YAML frontmatter, look for patterns
   like `*Last updated: [date]*`, `*Type: [value] | Status: [value]*`
4. **Section headings** — all `##` level headings (for template compliance)
5. **Internal references** — markdown links, bold file references, backtick
   references, frontmatter cross-references
6. **Word count** — approximate from content length
7. **Byte size** — the file's content length in bytes, recorded for
   all-mode shard packing (Step 3e). Cheap to capture during the read.
8. **Directory classification** — which template registry entry applies (if any)
9. **In-scope flag** — mark each file `in_scope`:
   - **Group mode** — `true` if the file's relative path matches any of the
     group's `canon` glob patterns from `config.yaml`; otherwise `false`.
     Use `fnmatch`-style glob semantics with `**` for recursive wildcards.
   - **All mode** — `true` for every `.md` under `context/` and every meta
     doc enumerated above. (Effectively the whole index is in scope.)
   - **Account dossier override** — after applying the mode-specific rule
     above, if `user_wants_accounts = false` (the default from Step 0),
     override `in_scope: false` for every file whose path matches
     `accounts/**`. This applies in both scan modes. The files remain in
     the index for cross-reference resolution but are never deep-analyzed.

Build the canon index as a compact markdown table:

```markdown
| Path | In scope | Type | Status | Last reviewed | Owner | Word count | Bytes | Template | Refs out | Refs in |
|------|----------|------|--------|--------------|-------|------------|-------|----------|----------|---------|
```

The full tree is always indexed so cross-reference checks can still detect
broken links that point from in-scope files into out-of-scope territory.
Only `in_scope: true` files are deeply analyzed by subagents.

If a `--subtree` focus was also specified in Step 1 (group-mode only),
further restrict the in-scope set to files whose path is under that subtree.
Warn and ignore the subtree if it falls entirely outside the group's canon
globs.

#### 3e. Shard packing (all-mode only)

In `scan_mode = group`, all in-scope files go to a single Canon Analyzer —
skip this step. In `scan_mode = all`, the in-scope set is the whole canon
(~172 files + meta docs), too large for one subagent, so **bin-pack** it
into shards:

1. Order in-scope files by top-level directory (so a shard tends to hold
   related files), then greedily fill the current shard.
2. Close the current shard and start a new one when adding the next file
   would exceed **either** `all_mode.shard_max_files` **or**
   `all_mode.shard_max_bytes` (summing the per-file `Bytes` from 3a).
3. **Never split a single file** across shards. A single file larger than
   `shard_max_bytes` becomes its own one-file shard (log it — large account
   dossiers can hit this).
4. Assign each shard a stable id (`shard-01`, `shard-02`, …) and record a
   **shard manifest**: `shard_id → [file paths]`. Every in-scope file lands
   in exactly one shard (Guardrail G9 in Step 5 verifies this).

Record `shard_count` for the report header and Step 7. With current canon
(~172 files, accounts/ dominating) and the default caps this yields roughly
15–22 shards.

#### 3d. Prepare subagent inputs

Using the canon index, prepare the content payloads for each subagent. In
all-mode you prepare **one payload per shard** (loop the shard manifest from
3e); in group-mode you prepare a single payload.

**For Canon Analyzer (Subagent A — one per shard in all-mode):**
- The full canon index table (all files, with the `in_scope` column). The
  full index is shared by every shard so each can resolve cross-references
  to files it does not hold in full.
- Full content of the **shard's files** (group-mode: every in-scope file;
  all-mode: just this shard's slice of the manifest), grouped by top-level
  directory (`truth/`, `guidance/`, `marketing/`, `sales/`, `platform/`,
  `accounts/`) so the analyzer can navigate related files without
  re-scanning the index.
- **Files not in this payload are not sent as full content** — the analyzer
  works from index metadata (path, status, last_reviewed, refs-in/out) to
  resolve cross-references and detect broken links. This keeps each payload
  bounded.
- The 3 template files (`truth/audiences/_template-persona.md`,
  `truth/messaging/_template-product.md`,
  `truth/messaging/_template-segment.md`) are passed separately as
  `{{template_files}}` for convenience during template-compliance checks.

The analyzer **only raises findings on the files in its payload** but may
reference other files by path when reporting cross-document issues (e.g.
"competitive/akur8.md contradicts truth/market/icp.md"). In all-mode, the
analyzer also emits a compact **`entity_digest`** (see
`references/canon-analyzer.md`) summarizing the salient claims it saw, for
the Cross-Group Consistency pass in Step 4/5.

**For External Verifier (Subagent B, Phase 3 — only if `phase_3_enabled`):**

Bind `{{verification_content}}` to the full content of the **Phase 3
allowlist** — a curated set of canon files where externally verifiable
factual claims live:

| Path | Why included |
|------|--------------|
| `context/guidance/competitive/competitors/*.md` | Competitor profiles |
| `context/guidance/competitive/positioning.md` | Competitive positioning |
| `context/truth/market/*.md` | Market sizing, growth rates, regulatory data |
| `context/truth/audiences/*.md` | Personas — may name real execs/companies |
| `context/truth/brand/*.md` | Brand positioning — may reference competitors |
| `context/marketing/marketing-strategy.md` | Strategic landscape references |

**Loading:**
- **MCP mode:** for each allowlist path, call `ReadMcpResourceTool` with the
  matching `context://` URI. For glob patterns, expand against the
  `ListMcpResourcesTool` result from Step 3a.
- **Filesystem mode:** Glob each allowlist path under the canon filesystem
  path, Read each matched file, concatenate with file path headers as
  separators.

Concatenate all reads as `{{verification_content}}` with file path headers
between files. This pass happens only when `phase_3_enabled = true`. When
Phase 3 is disabled or `external` is excluded, this step is skipped and no
extra reads occur.

**Excluded from Phase 3 (intentional):** templates (`_template-*.md`),
voice/style guides, eval rubrics, anti-AI guardrails, sales methodology
files, platform procedure docs, internal positioning narratives. These
contain no externally verifiable claims. Document any drift as a follow-up
ticket if this assumption breaks.

**Claim extraction:** Step 3a indexing extracts metadata only, not
factual claims. The External Verifier extracts verifiable claims from
the content payload itself — see `references/external-verifier.md`
Step 1 for the in-subagent extraction.

### Step 4 — Launch subagents

Read each reference file, substitute `{{variables}}` with the prepared data
from Step 3d, and launch subagents with `subagent_type: "general-purpose"`.

| Subagent | Reference file | Phase | Status |
|----------|---------------|-------|--------|
| Canon Analyzer | `references/canon-analyzer.md` | Phase 2 | **Active** — 1 in group-mode; 1 per shard in all-mode |
| External Verifier | `references/external-verifier.md` | Phase 3 | **Active only if `phase_3_enabled` from Step 2c** |
| Cross-Group Consistency | `references/cross-group-consistency.md` | Phase 4 | **Active in all-mode only**, after all shards return |

**Template variables (substitute per subagent):**

- `{{today_date}}` → current date (YYYY-MM-DD)
- `{{group_slug}}` → the `--group` slug in group-mode, or `all` in all-mode
- `{{group_label}}` → group label from `config.yaml`, or `Whole Canon`
- `{{group_codeowner}}` → codeowner, or `all-codeowners`
- `{{canon_index}}` → the canon index table from Step 3a (includes `in_scope`)
- `{{scan_dimensions}}` → the active dimensions from Step 1
- `{{scan_mode}}` → `group` or `all`
- `{{shard_id}}` / `{{shard_of}}` → shard label (e.g. `shard-03`) and total
  shard count; in group-mode bind both to `1` (single implicit shard)
- `{{in_scope_canon_files_content}}` → in group-mode, every in-scope file's
  content; in all-mode, **this shard's** files only, grouped by top-level
  directory
- `{{template_files}}` → template file contents from Step 3d
- `{{verification_content}}` → Phase 3 allowlist contents (External Verifier
  only, if `phase_3_enabled`)

**Launch sequence:**

- **Group mode** — launch the Canon Analyzer and (if `phase_3_enabled`) the
  External Verifier simultaneously in a single message (1 or 2 subagents).
- **All mode** — launch the Canon Analyzer shards in **parallel waves of
  `all_mode.wave_size`** (default 5): put up to `wave_size` Agent calls in one
  message, wait for the wave to return, then launch the next wave, until every
  shard from the 3e manifest has run. Launch the External Verifier once,
  alongside the first wave (it runs independently of the shards). After **all
  shards have returned**, collect their `entity_digest`s and launch the
  **Cross-Group Consistency** subagent once, binding `{{entity_digests}}` to
  the concatenated digests and `{{canon_index}}` to the full index.

**Phase 3 non-blocking guarantee:** If `phase_3_enabled = false`, do not
launch the External Verifier. If it launches but fails or crashes mid-run,
capture the error, continue with the analyzer results, and note the failure
in Step 5a. The lint always completes — Phase 3 failures never stop the run.

**Shard / cross-group resilience (all-mode):** If an individual shard
subagent fails, record the failure (Guardrail G9 surfaces it in Statistics),
keep the other shards' findings, and continue. If the Cross-Group Consistency
subagent fails, note it in Step 5a and proceed with the per-shard findings —
it is additive and never blocks the report.

### Step 5 — Phase 4: Synthesize report (inline)

Once subagents complete, merge their outputs into a single report. The set of
contributing subagents depends on mode: group-mode has 1 Canon Analyzer (+
optional External Verifier); all-mode has N Canon Analyzer shards (+ optional
External Verifier) (+ the Cross-Group Consistency pass).

**5a. Merge and verify findings**

Collect all findings from **every** subagent that returned results — in
all-mode that means concatenating findings across all shards before
renumbering. Re-number them sequentially within each section to avoid ID
collisions:

- **High Severity** — `H1`, `H2`, ... (from Canon Analyzer shards +
  Cross-Group Consistency contradictions + External Verifier `contradicted`)
- **Medium Severity** — `M1`, `M2`, ... (from Canon Analyzer shards +
  Cross-Group Consistency `medium` + External Verifier `outdated`)
- **Low Severity** — `L1`, `L2`, ... (from Canon Analyzer shards)

Cross-Group Consistency findings carry `category: cross-group` and are
routed into High/Medium by their own severity.

External Verifier findings carry the `E` prefix in the subagent output;
during synthesis they are routed by status:
- `status: contradicted` → renumbered into the High Severity section (origin preserved in finding body)
- `status: outdated` → renumbered into the Medium Severity section

**Guardrail G1 — Verify high-severity findings:** For every High severity
finding (H-prefix or `E`-origin), spot-check by reading the cited file(s)
and confirming the quoted text actually exists at the referenced location.
If the quote doesn't match what's in the file:
- Downgrade to medium severity if the finding is directionally correct but
  the quote is inaccurate
- Remove the finding entirely if it appears fabricated
- Add a note: `[UNVERIFIED — quoted text not found at cited location]`

**Guardrail G6 — Sanity check finding counts:** If the Canon Analyzer
returns 0 findings for a KB with 100+ files (group-mode), or **all** shards
collectively return 0 findings across the whole canon (all-mode), add a
warning to the report:

> "Canon Analyzer reported 0 findings across [N] files. This is unusual
> and may indicate the subagent did not complete its analysis. Consider
> re-running `/kb-lint` to verify."

**Guardrail G9 — Shard coverage (all-mode only):** Confirm that every
in-scope file from the 3e manifest appears in exactly one shard and that
every shard returned results. For any shard that failed or did not return,
list the affected files in Statistics:

> "Shard coverage incomplete: [shard-id] ([K] files) did not return. Those
> files were not analyzed this run — re-run `/kb-lint` to cover them."

Never silently drop a shard's files — an unreported shard is a coverage
hole, not a clean bill of health.

**Guardrail G7 — Perplexity cost cap:** If `phase_3_enabled` was true and
the External Verifier reports more than 30 Perplexity calls were made, log
a warning in Statistics. If it reports 0 calls and `phase_3_enabled` was
true, add a note: "External Verifier reported 0 calls — Phase 3 may have
failed silently."

**Guardrail G8 — Verification source citation:** Drop any External
Verifier finding that lacks a Perplexity source URL. Log dropped findings
in the report's Statistics section (e.g., "Phase 3 findings dropped (no
source URL): N").

**Phase 3 failure handling:** If `phase_3_enabled` was true but the
External Verifier subagent crashed mid-run or returned an error, do NOT
fail the synthesis. Add a note in the report:

> "Phase 3 could not be completed. Error: [brief description]. Other
> findings in this report are unaffected."

Continue with the rest of synthesis using the Canon Analyzer's results.
Phase 3 failures NEVER stop the run.

**Cross-Group Consistency failure handling (all-mode):** If the Cross-Group
Consistency subagent crashed or returned nothing, do NOT fail synthesis. Add
a note ("Cross-group consistency pass could not be completed — per-shard
findings are unaffected") and proceed. The pass is additive.

kb-lint has **no on-disk side effects** beyond writing the markdown
report in Step 6 — it never reads or writes `raw/<group>/INDEX.md` or
any raw file. Raw ingest state is owned entirely by `/kb-update`.

**5c. Deduplicate**

If two subagents flag the same file for different reasons, keep both
findings but note the connection. In all-mode also dedupe **across shards**:
if two shards report the same `target_file` + `target_line` for the same
issue (e.g. both touch a shared file via a cross-reference), collapse to one
finding. A Cross-Group Consistency finding that restates a single-shard
finding should be merged, preferring the cross-group framing.

**5d. Build structured findings list**

Read `references/output-format.md` for the finding JSON schema. Normalize
every subagent finding into that shape — the orchestrator holds the
findings list in memory (JSON) as the single input to Step 5f's
markdown renderer.

Each entry in the findings list carries:

- `finding_id` (renumbered across subagents to avoid collisions — H1, H2,
  …, M1, M2, …, L1, L2, …, E1, E2, …)
- `title` — short descriptive phrase
- `category` — one of: freshness, cross-reference,
  consistency, template, coverage-gap, external, cross-group
- `severity` — high | medium | low
- `confidence` — high | medium | low
- `current_text` — verbatim quote from the flagged content
- `proposed_text` — verbatim replacement, or empty string for structural
  findings (freshness, orphan, coverage-gap, broken-link, template)
- `rationale` — 1–3 sentences
- `suggested_action` — one-line remediation
- `source_file`, `source_line` — evidence file + line
- `target_file`, `target_line` — canon file + line to edit
- `group`, `codeowner`, `run_date` — set by the orchestrator from the
  CLI arg / config.yaml / today's date

If a subagent returns a finding without the required structured fields,
log a warning in Statistics (5e) but still include the finding in the
markdown report — mark its title with `[MALFORMED]` so it's visible
during review.

**5e. Collect run statistics**

Collect counts for the Step 7 user-facing summary and for logging. The
Step 7 message reports:

- Total findings, counts per severity, counts per category
- Scan mode line: `Scan mode: group ([slug])` or `Scan mode: all`
- **All-mode only** — shard line: `Shards: [shard_count] (wave size [W]) —
  all returned` or, if G9 flagged gaps, `[K] shard(s) incomplete`; and a
  cross-group line: `Cross-group pass: N findings` / `skipped` / `failed`
- **All-mode only** — meta-docs line: `Project meta docs: scanned ([N]
  files)` or `skipped ([reason])`
- Phase 3 status line:
  - `Phase 3 status: enabled — N claims verified, X contradicted, Y outdated`
  - `Phase 3 status: skipped (Perplexity MCP unavailable)`
  - `Phase 3 status: skipped (excluded by user via --no-external)`
  - `Phase 3 status: failed mid-run — [error description]`
- Executive summary (2–3 sentences):
  - Overall health assessment (good / needs attention / critical)
  - Most important finding
  - **If Phase 3 was skipped or failed, append:** "Phase 3 external
    verification was skipped (Perplexity MCP unavailable / excluded via
    --no-external / failed mid-run) — factual claims in canon were not
    verified against current web data."

These stats are rendered into the Statistics section of the markdown
report (Step 6) and summarised to the user in Step 7.

**5f. Render the markdown report**

Read `references/output-format.md` for the markdown report template.
Render the in-memory findings list into that template's sections:

1. **Header** — scan mode (group slug or `all`), canon scope, run date,
   access mode, file counts (and shard count + meta-docs flag in all-mode),
   finding summary
2. **Summary** — 2–3 sentence executive summary from Step 5e
3. **High Severity** — H findings (internal contradictions) + Cross-Group
   Consistency contradictions + External Verifier `contradicted` findings
4. **Medium Severity** — M findings (staleness, broken refs, template
   issues) + Cross-Group `medium` + External Verifier `outdated` findings
5. **Low Severity** — L findings (orphans, missing metadata, gaps)
6. **Coverage Gaps** — the coverage gap table
7. **Statistics** — run metrics + scan mode + shard coverage (all-mode) +
   Phase 3 status

Bind the rendered markdown string to `report_markdown` for Step 6.

### Step 6 — Write the markdown report

Compute the target path. The slug is the `--group` slug in group-mode, or
the literal `all` in all-mode:

```
outputs/kb-lint-<group>-YYYY-MM-DD.md      # group-mode
outputs/kb-lint-all-YYYY-MM-DD.md          # all-mode
```

Use Glob to check whether that file already exists. If it does, look
for `...-YYYY-MM-DD-2.md`, `-3.md`, etc., and pick the next free counter.
Multiple runs on the same day are preserved instead of overwriting.

Use the Write tool to save `report_markdown` at the resolved path. If
the write fails, report the error in Step 7 and do not retry.

Record the resolved path for the Step 7 summary.

### Step 7 — Report to user

Output a summary. **Group mode:**

```
KB Lint run complete.

Scan mode: group
Group:  [slug] ([label]) — owner: [codeowner] — active: [yes/no]

Findings: [N] total ([X] high, [Y] medium, [Z] low)

Canon scope: [K] in-scope files (of [N] total in canon tree)
Canon access: [mcp / filesystem]

Report written to: [path from Step 6]
Malformed findings: [N] (titles prefixed with [MALFORMED])

Executive summary: [2–3 sentence summary from Step 5e]
```

**All mode** (replace the Group line and add shard/cross-group/meta lines):

```
KB Lint run complete.

Scan mode: all (Whole Canon)

Findings: [N] total ([X] high, [Y] medium, [Z] low)
  of which cross-group: [C]

Canon scope: [K] in-scope files (context/ + [M] project meta docs)
Canon access: [mcp / filesystem]
Shards: [shard_count] (wave size [W]) — [all returned / K incomplete]
Cross-group pass: [N findings / skipped / failed]
Project meta docs: [scanned (M files) / skipped (reason)]

Report written to: [path from Step 6]
Malformed findings: [N] (titles prefixed with [MALFORMED])

Executive summary: [2–3 sentence summary from Step 5e]
```

If the user has new raw sources to reconcile against canon (and to stage
in Notion for team triage), remind them: "kb-lint audits canon only. To
diff raw sources against canon and publish findings to the
`KB - Updates Review` Notion database, run `/kb-update --group <slug>`."

---

## Error handling

- If a subagent fails or times out, include its findings section as:
  `[Phase N could not be completed. Error: brief description. Please retry.]`
- Continue with the other subagent's output even if one fails.
- If canon access fails entirely (neither MCP nor filesystem readable when
  Step 3 tries to read), report the error and stop — the skill cannot run
  without canon access. This is the one hard requirement and it surfaces
  reactively, not as a pre-flight wall.
- If `--group` is **missing**, that is not an error — it selects all-mode
  (whole-canon scan). Only an **unknown** `--group <slug>` halts, with the
  message from Step 2 (group resolution). The `active` flag is informational
  — kb-lint does not refuse inactive groups.
- **Shard failures (all-mode) are non-fatal.** A shard that fails is reported
  by Guardrail G9 (its files listed as uncovered); the run continues with the
  other shards. The Cross-Group Consistency pass is additive — its failure
  only drops cross-group findings, never the per-shard report.
- **Project meta docs (all-mode) are best-effort.** If `repo_root` is not on
  disk (MCP mode without a sibling checkout), the meta globs are skipped with
  a header note — never a hard stop.
- **Phase 3 (External Verifier) is never blocking.** If Perplexity MCP is
  unavailable, detection fails, the user excluded the `external` dimension,
  or the verifier subagent crashes mid-run, kb-lint completes the rest of
  the lint normally and acknowledges the skip in the report. Phase 3
  failures are NEVER fatal. The skip appears in: executive summary
  (Step 5e) and Statistics (Step 5d).
- If Phase 3 was launched but the verifier crashed mid-run, include in the
  report: "Phase 3 could not be completed. Error: [brief description].
  Other findings in this report are unaffected." Do NOT retry, do NOT stop.
- Report any errors in the Step 7 summary.

---

## Batch mode notes

kb-lint runs the same way interactively and non-interactively — the
`AskUserQuestion` prompt in Step 0 is the only interactive gate, and it is
**skipped entirely in batch / non-interactive mode**. When running via a
batch script:
- Mode follows the same rule as interactive: `--group <slug>` → group-mode;
  no `--group` → all-mode (whole-canon). Batch mode does NOT need any flag —
  a bare `/kb-lint` is a valid non-interactive whole-canon run.
- **Step 0 defaults apply automatically** — `user_wants_external = false`
  (Phase 3 skipped) and `user_wants_accounts = false` (account dossiers
  excluded). To override in batch, pass `--external` to enable Phase 3 or
  `--accounts` to include account dossiers. These flags are parsed in Step 1
  alongside `--group` and `--no-external`.
- Phase 3 runs only when both `--external` is passed AND Perplexity MCP is
  available; skips silently otherwise (non-blocking, same as interactive mode).
- Account dossiers (`context/accounts/**`) are out of scope by default;
  pass `--accounts` to include them.
- All-mode shards run in parallel waves exactly as interactively; the
  Cross-Group Consistency pass runs after the last wave.
- Write the markdown report to `outputs/kb-lint-<group>-YYYY-MM-DD.md`
  (group-mode) or `outputs/kb-lint-all-YYYY-MM-DD.md` (all-mode) and exit.
  If the Step 6 write fails, halt with a non-zero exit.
