#!/usr/bin/env python3
"""
synthesize_findings.py

Post-comparator synthesis for kb-update. Reads per-subagent outputs that
each carry a ``<FINDINGS_JSON>`` / ``<STATS_JSON>`` fenced block, merges
them, renumbers contiguously, computes
``canon_context_preview`` against canon on disk, validates required
fields, and emits a single JSON array to stdout ready for
``publish_to_notion.py``.

Dedup is NOT in this script. Cross-subagent dedup is performed by the
orchestrator (the model) in Step 4.5 before this script runs. This
script is a mechanical validator: parse, validate, resolve paths,
renumber.

Usage
-----

Stdin mode only (subagent responses arrive as a JSON array of strings)::

    echo '["<subagent response 1>", "<subagent response 2>", ...]' \\
      | python3 synthesize_findings.py \\
          --group competitive \\
          --run-date 2026-04-22 \\
          --mcp-root /abs/path/to/hxgtm-mcp-server \\
          --subagent-outputs-stdin \\
        > /tmp/kb-update-findings.json

Each subagent response is one raw comparator output. The script locates
the FINDINGS_JSON / STATS_JSON fenced blocks via regex. Responses
without a FINDINGS_JSON block are logged as malformed and skipped;
remaining subagents still contribute.

Output JSON shape::

    {
      "findings": [ <normalised finding>, ... ],
      "stats":    { <aggregated counters + phase timings> },
      "warnings": [ <parse/validation warning lines> ]
    }

``publish_to_notion.py`` unwraps this shape automatically — piping the
full object straight in works end-to-end, no ``jq .findings`` required.
Bare arrays (e.g. from an external pipeline) still work too.

Exit codes
----------

* 0 on success (even when some subagents were malformed — their
  failures are logged and counted in ``stats.warnings`` / ``stats.dropped_malformed_subagents``).
* 1 only when no findings at all can be emitted (all subagents malformed
  OR required args missing).
"""

from __future__ import annotations

import argparse
import functools
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]

FINDINGS_FENCE_RE = re.compile(
    r"<FINDINGS_JSON>\s*(?P<body>.*?)\s*</FINDINGS_JSON>",
    re.DOTALL,
)
STATS_FENCE_RE = re.compile(
    r"<STATS_JSON>\s*(?P<body>.*?)\s*</STATS_JSON>",
    re.DOTALL,
)


# Required fields on every finding before it's considered well-formed.
# Missing fields don't skip the finding — the row is tagged [MALFORMED]
# by publish_to_notion.py so reviewers see it and retag manually.
REQUIRED_FIELDS = (
    "title",
    "entity",
    "source_tier",
    "section",
    "action",
    "claim_scope",
    "target_file",
    "target_line_start",
    "target_line_end",
    "severity",
    "proposed_text",
    "rationale",
    "evidence_basis",
)


VALID_SOURCE_TIERS = {"tier_1", "tier_2", "tier_3", "tier_5"}
VALID_CLAIM_SCOPES = {"structural", "niche", "unscoped"}
VALID_ACTIONS = {"append", "replace"}
VALID_SEVERITIES = {"high", "medium", "low"}
VALID_EVIDENCE_BASES = {"structural", "single-deployment", "corroborated-multi"}


# ---------------------------------------------------------------------------
# Minimal YAML reader (no pyyaml dep — mirrors resolve_mcp_path.py)
# ---------------------------------------------------------------------------


def _read_config_list(config_path: Path, key_path: tuple[str, ...]) -> list[str]:
    """Read a YAML list under key_path from config.yaml.

    Returns [] when missing. Handles the simple ``key:\\n  - value`` shape
    used by config.yaml's ``always_include`` / ``canon`` sections.
    """
    if not config_path.exists():
        return []
    lines = config_path.read_text(encoding="utf-8").splitlines()
    items: list[str] = []
    path_stack: list[tuple[str, int]] = []
    in_list = False
    list_indent: int | None = None

    for raw in lines:
        stripped = raw.rstrip()
        if not stripped.strip() or stripped.strip().startswith("#"):
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        content = stripped.strip()

        if in_list:
            # Bail out of the list when indent returns to or above the
            # list's key indent.
            if list_indent is not None and indent <= list_indent and not content.startswith("-"):
                in_list = False
                list_indent = None
            elif content.startswith("-"):
                item = content.lstrip("-").strip().strip('"').strip("'")
                if item:
                    items.append(item)
                continue

        if ":" not in content:
            continue

        key, _, value = content.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        while path_stack and path_stack[-1][1] >= indent:
            path_stack.pop()
        path_stack.append((key, indent))

        if tuple(k for k, _ in path_stack) == key_path and not value:
            in_list = True
            list_indent = indent

    return items


def _read_config_scalar(config_path: Path, key_path: tuple[str, ...]) -> str | None:
    """Read a scalar value at key_path from config.yaml, or None."""
    if not config_path.exists():
        return None
    lines = config_path.read_text(encoding="utf-8").splitlines()
    path_stack: list[tuple[str, int]] = []
    for raw in lines:
        stripped = raw.rstrip()
        if not stripped.strip() or stripped.strip().startswith("#"):
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        content = stripped.strip()
        if ":" not in content:
            continue
        key, _, value = content.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        while path_stack and path_stack[-1][1] >= indent:
            path_stack.pop()
        path_stack.append((key, indent))
        if tuple(k for k, _ in path_stack) == key_path and value:
            return value
    return None


# ---------------------------------------------------------------------------
# Subagent output parsing
# ---------------------------------------------------------------------------


def _extract_fenced_json(
    subagent_output: str,
    pattern: re.Pattern[str],
    label: str,
) -> tuple[Any, str | None]:
    """Return (parsed_json, error_message). error_message is None on success."""
    match = pattern.search(subagent_output)
    if not match:
        return None, f"missing {label} fence"
    body = match.group("body").strip()
    try:
        return json.loads(body), None
    except json.JSONDecodeError as exc:
        snippet = body[:200].replace("\n", "\\n")
        return None, f"{label} JSON parse error: {exc} (near: {snippet!r})"


def _parse_subagent_output(
    filename: str,
    body: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    """Parse one subagent's output.

    Returns (findings, stats, warnings). ``findings`` is [] when the
    FINDINGS_JSON fence is absent or malformed; ``warnings`` lists every
    issue with the subagent's output.
    """
    warnings: list[str] = []
    findings, err = _extract_fenced_json(body, FINDINGS_FENCE_RE, "FINDINGS_JSON")
    if err:
        warnings.append(f"[subagent_malformed] {filename}: {err}")
        findings = []
    elif not isinstance(findings, list):
        warnings.append(
            f"[subagent_malformed] {filename}: FINDINGS_JSON is not an array"
        )
        findings = []

    stats, stats_err = _extract_fenced_json(body, STATS_FENCE_RE, "STATS_JSON")
    if stats_err:
        warnings.append(f"[subagent_stats_missing] {filename}: {stats_err}")
        stats = {}
    elif not isinstance(stats, dict):
        warnings.append(
            f"[subagent_malformed_stats] {filename}: STATS_JSON is not an object"
        )
        stats = {}

    return findings, stats or {}, warnings


def _load_subagent_outputs_from_stdin_json() -> list[tuple[str, str]]:
    """Parse ``stdin`` as a JSON array of strings (one per subagent response)
    and return [(synthetic_name, text), ...]. Synthetic names are ``01.md``,
    ``02.md``, … so downstream logs match the dir-mode experience.

    Orchestrator pipes subagent outputs directly via heredoc or the equivalent;
    orchestrator pipes subagent outputs directly via heredoc or the
    equivalent — no /tmp file handoff."""
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.exit(
            f"ERROR: --subagent-outputs-stdin expects a JSON array of "
            f"strings on stdin (got invalid JSON: {exc})"
        )
    if not isinstance(payload, list) or not all(isinstance(s, str) for s in payload):
        sys.exit(
            "ERROR: --subagent-outputs-stdin expects a JSON array of strings, "
            "each string being one subagent's raw <FINDINGS_JSON>/<STATS_JSON> "
            "response."
        )
    if not payload:
        sys.exit("ERROR: --subagent-outputs-stdin received an empty array.")
    width = max(2, len(str(len(payload))))
    return [(f"{i + 1:0{width}d}.md", text) for i, text in enumerate(payload)]


# ---------------------------------------------------------------------------
# Canon I/O with intra-run memoization
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=None)
def _read_canon_lines(abs_path: str) -> tuple[str, ...]:
    """Read a canon file once per run. Cached across findings."""
    return tuple(Path(abs_path).read_text(encoding="utf-8").splitlines())


def _resolve_canon_abs_path(mcp_root: Path, target_file: str) -> Path:
    """Map a finding's ``target_file`` to its on-disk absolute path.

    ``target_file`` can be given as ``context/foo/bar.md`` or
    ``foo/bar.md`` — we normalise by stripping a leading ``context/``
    prefix, then resolving under ``mcp_root/context/``.
    """
    rel = target_file
    if rel.startswith("context/"):
        rel = rel[len("context/"):]
    return (mcp_root / "context" / rel).resolve()


def _build_context_preview(lines: tuple[str, ...], start: int, end: int) -> str:
    """±5 lines around the span, prefixed with 1-indexed line numbers."""
    if not lines:
        return ""
    lo = max(1, start - 5)
    hi = min(len(lines), end + 5)
    return "\n".join(f"{n}: {lines[n - 1]}" for n in range(lo, hi + 1))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_finding(finding: dict[str, Any]) -> list[str]:
    """Return a list of validation warnings for one finding."""
    warnings: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in finding or finding.get(field) in (None, ""):
            warnings.append(f"missing {field}")

    for field in ("target_line_start", "target_line_end"):
        value = finding.get(field)
        if not isinstance(value, int):
            warnings.append(f"{field} must be integer, got {type(value).__name__}")

    source_tier = (finding.get("source_tier") or "").lower()
    if source_tier and source_tier not in VALID_SOURCE_TIERS:
        warnings.append(f"invalid source_tier '{source_tier}'")

    claim_scope = (finding.get("claim_scope") or "").lower()
    if claim_scope and claim_scope not in VALID_CLAIM_SCOPES:
        warnings.append(f"invalid claim_scope '{claim_scope}'")

    action = (finding.get("action") or "").lower()
    if action and action not in VALID_ACTIONS:
        warnings.append(f"invalid action '{action}'")

    severity = (finding.get("severity") or "").lower()
    if severity and severity not in VALID_SEVERITIES:
        warnings.append(f"invalid severity '{severity}'")

    # evidence_basis is required on every finding (added in the
    # 2026-04 kb-update tightening pass). Missing is non-fatal (row
    # publishes [MALFORMED]); an invalid value is caught here.
    evidence_basis = (finding.get("evidence_basis") or "").lower()
    if evidence_basis and evidence_basis not in VALID_EVIDENCE_BASES:
        warnings.append(f"invalid evidence_basis '{evidence_basis}'")

    return warnings


# ---------------------------------------------------------------------------
# Main synthesis pipeline
# ---------------------------------------------------------------------------


def synthesize(
    group: str,
    run_date: str,
    mcp_root: Path,
    raw_outputs: list[tuple[str, str]],
) -> dict[str, Any]:
    """Mechanical synthesis: parse, renumber, hash, validate.

    ``raw_outputs`` is a list of ``(synthetic_name, text)`` tuples — one
    per subagent response. Cross-subagent dedup is performed by the
    orchestrator before this function is called."""
    t_start = time.perf_counter()

    config_path = REPO_ROOT / ".claude" / "skills" / "kb-update" / "config.yaml"
    codeowner = _read_config_scalar(
        config_path, ("groups", group, "codeowner")
    ) or "unknown"

    # --- Step 1: parse subagent outputs ------------------------------------
    t_parse = time.perf_counter()
    all_findings: list[dict[str, Any]] = []
    subagent_stats: list[dict[str, Any]] = []
    warnings: list[str] = []
    dropped_malformed_subagents = 0

    for filename, body in raw_outputs:
        findings, stats, file_warnings = _parse_subagent_output(filename, body)
        warnings.extend(file_warnings)
        if not findings and any("[subagent_malformed]" in w for w in file_warnings):
            dropped_malformed_subagents += 1
            continue
        subagent_stats.append(stats)
        for f in findings:
            # Preserve provenance of which subagent emitted each finding
            # so a per-file malformed finding can still be published with
            # a [MALFORMED] prefix rather than silently dropped.
            f.setdefault("_subagent_source", filename)
            all_findings.append(f)
    parse_ms = int((time.perf_counter() - t_parse) * 1000)

    if not all_findings:
        return _empty_result(
            group, run_date, codeowner, warnings,
            dropped_malformed_subagents, parse_ms,
        )

    # --- Step 2: renumber ---------------------------------------------------
    t_renumber = time.perf_counter()
    # Stable sort: per-entity groups stay adjacent, then by original
    # subagent-emitted finding_id so the order is predictable.
    all_findings.sort(key=lambda f: (
        (f.get("entity") or "").lower(),
        f.get("_subagent_source", ""),
        str(f.get("finding_id", "")),
    ))
    for new_id, finding in enumerate(all_findings, start=1):
        rid = f"R{new_id}"
        old_title = finding.get("title", "Untitled")
        # Strip any prior R<N>: prefix from the title before re-tagging
        clean_title = re.sub(r"^R\d+:\s*", "", old_title)
        finding["finding_id"] = rid
        finding["title"] = f"{rid}: {clean_title}"
    renumber_ms = int((time.perf_counter() - t_renumber) * 1000)

    # --- Step 3: preview + validate ---------------------------------------
    t_hash = time.perf_counter()
    malformed_count = 0
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    tier_counts = {t: 0 for t in VALID_SOURCE_TIERS}
    scope_counts = {s: 0 for s in VALID_CLAIM_SCOPES}
    entity_counts: dict[str, int] = {}

    enriched: list[dict[str, Any]] = []
    for finding in all_findings:
        f_warnings = _validate_finding(finding)

        target_file = finding.get("target_file") or ""
        start = finding.get("target_line_start")
        end = finding.get("target_line_end")

        canon_context_preview = ""

        if target_file and isinstance(start, int) and isinstance(end, int):
            try:
                abs_path = _resolve_canon_abs_path(mcp_root, target_file)
                lines = _read_canon_lines(str(abs_path))
                n = len(lines)

                # EOF-append idiom: subagents writing "append after the
                # last line" frequently point at line n+1, which has no
                # referent. Clamp to n (the actual last line) so the
                # finding is treated as a normal append to EOF. Log as
                # informational (clamped), not malformed.
                if start == n + 1 and end == n + 1 and n >= 1:
                    finding["target_line_start"] = n
                    finding["target_line_end"] = n
                    start = end = n
                    warnings.append(
                        f"[finding_clamped] {finding.get('finding_id', '?')} "
                        f"({finding.get('_subagent_source', '?')}): append "
                        f"anchor clamped from {n + 1}-{n + 1} to {n}-{n} "
                        f"(EOF append idiom, file has {n} lines)"
                    )
                elif 1 <= start <= n and end == n + 1:
                    finding["target_line_end"] = n
                    end = n
                    warnings.append(
                        f"[finding_clamped] {finding.get('finding_id', '?')} "
                        f"({finding.get('_subagent_source', '?')}): end anchor "
                        f"clamped from {n + 1} to {n} (EOF append idiom, "
                        f"file has {n} lines)"
                    )

                if 1 <= start <= n and 1 <= end <= n:
                    canon_context_preview = _build_context_preview(lines, start, end)
                else:
                    f_warnings.append(
                        f"target_line_start/end {start}-{end} out of bounds "
                        f"(file has {n} lines)"
                    )
            except OSError as exc:
                f_warnings.append(f"canon read failed: {exc}")

        finding["canon_context_preview"] = canon_context_preview

        # Shared fields every finding gets.
        finding.setdefault("category", "raw-canon-conflict")
        finding["group"] = group
        finding["codeowner"] = codeowner
        finding["run_date"] = run_date

        if f_warnings:
            malformed_count += 1
            warnings.append(
                f"[finding_malformed] {finding.get('finding_id', '?')} "
                f"({finding.get('_subagent_source', '?')}): "
                + "; ".join(f_warnings)
            )

        # Tally stats before discarding private fields.
        sev = (finding.get("severity") or "").lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
        tier = (finding.get("source_tier") or "").lower()
        if tier in tier_counts:
            tier_counts[tier] += 1
        scope = (finding.get("claim_scope") or "").lower()
        if scope in scope_counts:
            scope_counts[scope] += 1
        ent = finding.get("entity") or "unknown"
        entity_counts[ent] = entity_counts.get(ent, 0) + 1

        # Strip private bookkeeping field before emit.
        finding.pop("_subagent_source", None)
        enriched.append(finding)
    hash_ms = int((time.perf_counter() - t_hash) * 1000)

    # --- Step 4: aggregate per-subagent stats ------------------------------
    # Pass-through: any counter any subagent emitted whose key starts with
    # ``dropped_`` / ``scope_gate_`` / ``atomic_claims_`` / ``replace_`` /
    # ``section_full_`` is summed automatically. Keeps new per-group gates
    # (e.g. dropped_cosmetic_variant, dropped_editorial,
    # dropped_intra_dedup, dropped_cross_canon_dedup) flowing through
    # without code changes here.
    PASS_THROUGH_PREFIXES = (
        "dropped_",
        "scope_gate_",
        "atomic_claims_",
        "replace_",
        "section_full_",
        "demoted_",
        "style_mismatch_",
    )
    # Explicit pass-through keys for counters that don't share a common
    # prefix (one-off names added during the 2026-04 tightening pass).
    PASS_THROUGH_KEYS = {
        "snapshot_split",
        "closes_open_question",
        "cross_section_dedup_dropped",
    }
    aggregated_counters: dict[str, int] = {}
    for s in subagent_stats:
        for key, value in s.items():
            if not (
                any(key.startswith(p) for p in PASS_THROUGH_PREFIXES)
                or key in PASS_THROUGH_KEYS
            ):
                continue
            try:
                aggregated_counters[key] = (
                    aggregated_counters.get(key, 0) + int(value or 0)
                )
            except (TypeError, ValueError):
                continue

    total_ms = int((time.perf_counter() - t_start) * 1000)

    stats: dict[str, Any] = {
        "group": group,
        "run_date": run_date,
        "codeowner": codeowner,
        "total_findings": len(enriched),
        "malformed_findings": malformed_count,
        "dropped_malformed_subagents": dropped_malformed_subagents,
        "warnings": len(warnings),
        "by_severity": severity_counts,
        "by_tier": tier_counts,
        "by_scope": scope_counts,
        "by_entity": entity_counts,
        "subagents_succeeded": len(subagent_stats),
        "timings_ms": {
            "parse": parse_ms,
            "renumber": renumber_ms,
            "validate": hash_ms,
            "total": total_ms,
        },
    }
    # Merge pass-through counters (dropped_*, scope_gate_*, etc.)
    stats.update(aggregated_counters)

    return {
        "findings": enriched,
        "stats": stats,
        "warnings": warnings,
    }


def _empty_result(
    group: str,
    run_date: str,
    codeowner: str,
    warnings: list[str],
    dropped_malformed_subagents: int,
    parse_ms: int,
) -> dict[str, Any]:
    return {
        "findings": [],
        "stats": {
            "group": group,
            "run_date": run_date,
            "codeowner": codeowner,
            "total_findings": 0,
            "malformed_findings": 0,
            "dropped_malformed_subagents": dropped_malformed_subagents,
            "warnings": len(warnings),
            "timings_ms": {"parse": parse_ms, "total": parse_ms},
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--group", required=True)
    parser.add_argument("--run-date", required=True)
    parser.add_argument(
        "--mcp-root",
        required=True,
        help="Absolute path to hxgtm-mcp-server (resolve with resolve_mcp_path.py).",
    )
    parser.add_argument(
        "--subagent-outputs-stdin",
        action="store_true",
        required=True,
        help="Read subagent responses as a JSON array of strings on stdin.",
    )
    args = parser.parse_args()

    mcp_root = Path(args.mcp_root).expanduser().resolve()
    if not mcp_root.is_dir():
        sys.exit(f"ERROR: --mcp-root not a directory: {mcp_root}")

    raw_outputs = _load_subagent_outputs_from_stdin_json()

    result = synthesize(
        group=args.group,
        run_date=args.run_date,
        mcp_root=mcp_root,
        raw_outputs=raw_outputs,
    )

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")

    return 0 if result["findings"] else 1


if __name__ == "__main__":
    sys.exit(main())
