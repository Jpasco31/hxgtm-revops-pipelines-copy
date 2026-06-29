# kb-update — Synthesis (Step 5)

## Contents
- When this reference is loaded
- What the script replaces
- Invocation
- Inputs
- Output JSON shape
- Renumbering
- Hash and context preview
- Validation and malformed findings
- Stats block
- Error handling
- Debugging tips

## When this reference is loaded

Read this reference when you need to understand what
`scripts/synthesize_findings.py` does and how the Step 5 pipeline
works. SKILL.md Step 5 only says "pipe subagent outputs into
`synthesize_findings.py`"; this file is the authoritative behaviour
contract.

## What the script replaces

Previously, the orchestrator hand-assembled a per-run Python script
that parsed each subagent's markdown output, merged them, dedup'd,
renumbered, and hashed line spans. That's now the one-shot
`synthesize_findings.py` — deterministic, testable, and identical
across runs.

**Dedup is NOT in this script.** As of the fan-out / per-entity
refactor, cross-subagent dedup is performed by the orchestrator
(the model) in Step 4.5 before this script is invoked. This script is
a mechanical validator: parse, validate, resolve paths, hash, number.

## Invocation

From SKILL.md Step 5:

```bash
python3 -c 'import json, sys; json.dump([<subagent_1_text>, ...], sys.stdout)' \
  | python3 .claude/skills/kb-update/scripts/synthesize_findings.py \
      --group competitive \
      --run-date 2026-04-22 \
      --mcp-root /path/to/hxgtm-mcp-server \
      --subagent-outputs-stdin \
    > /tmp/kb-update-findings.json
```

Required flags:

- `--group` — slug from `config.yaml`. Used to resolve `codeowner` at
  synthesis time.
- `--run-date` — `YYYY-MM-DD`. Stamped on every finding.
- `--mcp-root` — absolute path to `hxgtm-mcp-server`. The script reads
  canon files from `<mcp-root>/context/…` to compute hashes. Resolve
  with `resolve_mcp_path.py mcp-path` before calling.
- `--subagent-outputs-stdin` — reads a JSON array of strings from
  stdin. Each string is one subagent's full text response (markdown
  plus fenced JSON).

Exit codes: **0** on success (even when some subagents were
malformed), **1** only when no findings can be emitted at all.

## Inputs

Stdin carries a JSON array of subagent responses as strings. Each
response must contain two fenced JSON blocks in the comparator output
contract:

```
<FINDINGS_JSON>
[ {...}, {...} ]
</FINDINGS_JSON>

<STATS_JSON>
{ "entity": "...", "findings_emitted": 15, ... }
</STATS_JSON>
```

Text outside the fences is ignored — the script extracts each block
via regex and `json.loads()` it.

If a subagent's response is missing the FINDINGS_JSON block entirely
OR the JSON is malformed, the script logs `[subagent_malformed]
<index>: <error>` and skips that subagent's output. Remaining
subagents still contribute.

If a subagent's FINDINGS_JSON is present but not a JSON array, the
script logs a warning and treats the subagent as empty.

If a subagent's STATS_JSON is missing, the script still keeps the
findings but counts that subagent's stats as zeros.

## Output JSON shape

The script emits a single JSON object to stdout:

```json
{
  "findings": [
    {
      "finding_id": "R1",
      "title": "R1: ...",
      "entity": "Federato",
      "source_tier": "tier_2",
      "section": "Weaknesses / watch-outs",
      "action": "append",
      "claim_scope": "unscoped",
      "core_product": null,
      "target_file": "guidance/competitive/competitors/federato.md",
      "target_line_start": 14,
      "target_line_end": 14,
      "severity": "high",
      "evidence_basis": "corroborated-multi",
      "closes_open_question": null,
      "source_file": "...",
      "source_line": null,
      "current_text": "",
      "proposed_text": "...",
      "rationale": "...",
      "suggested_action": "...",
      "canon_context_preview": "9: ## Strengths\n10: - Clear narrative...\n...",
      "category": "raw-canon-conflict",
      "group": "competitive",
      "codeowner": "product-marketing",
      "run_date": "2026-04-22"
    }
  ],
  "stats": { ...aggregated counters + timings... },
  "warnings": [ "...one line per issue..." ]
}
```

`publish_to_notion.py` accepts either the full object (it reads
`.findings`) or a raw array (legacy). Pipe with:

```bash
cat /tmp/kb-update-findings.json \
  | python3 .claude/skills/kb-update/scripts/publish_to_notion.py --group <slug> --run-date <date> \
  > /tmp/kb-update-pages.json
```

## Renumbering

The script sorts findings by `(entity, subagent_source,
original_finding_id)` and renumbers contiguously (`R1`..`Rn`). The
`title` field is rewritten with the new prefix.

## Context preview

For each finding, the script:

1. Resolves `target_file` to an absolute path under
   `<mcp-root>/context/…`.
2. Reads the file once (cached via `functools.lru_cache` — 13 findings
   targeting `federato.md` cause ONE filesystem read, not 13).
3. Builds `canon_context_preview` = ±5 lines around the anchor span,
   each prefixed with its 1-indexed line number.

If the line range is out of bounds a warning is logged; the finding
still publishes.

For append findings (`action == "append"`) where
`target_line_end > file_length`, the script clamps to EOF and emits
`[finding_clamped]` rather than dropping the finding.

## Validation and malformed findings

Each finding is checked against the required-field list (see the
Output Contract reference SKILL.md links to from Step 5):

- `title`, `entity`, `source_tier`, `section`, `action`,
  `claim_scope`, `target_file`, `target_line_start`,
  `target_line_end`, `severity`, `proposed_text`, `rationale`,
  `evidence_basis`

`closes_open_question` is part of every finding but is allowed to be
`null` — it's only populated on `replace` actions that close a Notes
open-question bullet.

Missing / invalid fields don't skip the finding — the script emits it
anyway, and the warning is logged. `publish_to_notion.py` then
prefixes the Notion row title with `[MALFORMED]` so reviewers can
filter these out in triage.

Enum validations (tier, scope, action, severity) catch typos against
their valid sets.

## Stats block

Aggregated per-run counters the Step 7 report consumes:

```json
{
  "group": "competitive",
  "run_date": "2026-04-22",
  "codeowner": "product-marketing",
  "total_findings": 14,
  "malformed_findings": 0,
  "dropped_malformed_subagents": 0,
  "warnings": 0,
  "by_severity": {"high": 6, "medium": 6, "low": 2},
  "by_tier": {"tier_1": 3, "tier_2": 9, "tier_3": 2, "tier_5": 0},
  "by_scope": {"structural": 4, "niche": 2, "unscoped": 8},
  "by_entity": {"Federato": 8, "Kalepa": 2, "Send": 2, "Convr": 2},
  "dropped_deny_list": 2,
  "dropped_quote_verbatim": 0,
  "dropped_cosmetic_variant": 4,
  "dropped_editorial": 3,
  "dropped_intra_dedup": 1,
  "dropped_cross_canon_dedup": 2,
  "scope_gate_miss": 1,
  "scope_gate_skipped": 5,
  "replace_at_cap": 0,
  "section_full_demoted": 0,
  "snapshot_split": 2,
  "demoted_single_deployment": 1,
  "closes_open_question": 1,
  "style_mismatch_in_section": 3,
  "style_mismatch_with_schema": 0,
  "cross_section_dedup_dropped": 1,
  "subagents_succeeded": 3,
  "timings_ms": {
    "parse": 12,
    "renumber": 1,
    "hash": 18,
    "total": 32
  }
}
```

Per-subagent counters (`dropped_deny_list`, `dropped_cosmetic_variant`,
etc.) are summed from each subagent's STATS_JSON. Counters matching
one of the pass-through prefixes (`dropped_`, `scope_gate_`,
`atomic_claims_`, `replace_`, `section_full_`, `demoted_`,
`style_mismatch_`) or the explicit allowlist
(`snapshot_split`, `closes_open_question`,
`cross_section_dedup_dropped`) flow through without code changes to
the synthesis script. Unrecognised keys are silently dropped — add a
prefix or allowlist entry in `synthesize_findings.py` if a new
counter needs to propagate.

## Error handling

- All-subagents-malformed → exit 1, emit empty `findings: []` with
  warnings populated. The caller (orchestrator) reports this to the
  user and skips publish.
- Canon file missing from disk → warning logged, finding still
  published with empty hash. Reviewer sees the issue via the
  `[MALFORMED]` title prefix.
- Invalid `--mcp-root` → hard error, exit.
- Invalid stdin payload (not a JSON array) → hard error, exit.

## Debugging tips

- Inspect `.warnings` for every non-fatal issue — the UI-level report
  only shows counts, but the JSON has the detail.
- Line numbers in `canon_context_preview` match the original canon
  file 1:1. If they don't match what `Read` shows, the canon was
  edited between comparator time and synthesis time.
- If you see unexpected duplicates making it to publish, check the
  orchestrator's Step 4.5 dedup log — dedup is upstream of this
  script now.
