#!/usr/bin/env python3
"""
apply_integrations.py

Plans and applies canon edits from a list of Approved kb-update rows (JSON
on stdin) read from a per-group Notion database. The orchestrator (SKILL.md)
is responsible for:
  1. Calling notion-fetch, filtering to Status = Approved, and flattening
     each row into the input schema this script expects.
  2. Piping that list to this script with --plan to render a dry-run preview.
  3. Piping the same list back with --apply to execute the edits.
  4. Calling notion-update-page for every row this script returns as
     status=success, flipping it from Approved to Integrated.

This script never talks to Notion directly — the Notion MCP lives in the
Claude process, not here. It also never runs git commands. It only reads
and writes canon files inside the MCP server repo's context/ directory.

Input row schema (one JSON array on stdin):

    [
      {
        "page_id": "<notion page id>",
        "finding_id": "R1",
        "title": "R1: Akur8 agentic roadmap",
        "section": "Weaknesses / watch-outs",          # existing canon h2 the
                                                       # finding attaches under
                                                       # (from Notion's
                                                       # `Section` column).
                                                       # Comparator guardrail
                                                       # restricts findings to
                                                       # existing section_schema
                                                       # headings — appends
                                                       # merge into this
                                                       # section.
        "action": "replace" | "append",                # optional; inferred
                                                       # from current_text
                                                       # emptiness if missing
        "target_file": "context/guidance/competitive/akur8.md",
        "target_line_start": 117,
        "target_line_end": 121,
        "current_text": "<≤400 char preview — not used for matching>",
        "proposed_text": "<paraphrased replacement from the comparator>",
        "final_updated_text": "<reviewer-typed tweak in Notion — wins over
                                proposed_text via effective_text() helper>",
        "category": "raw-canon-conflict" | ...,
        "source_file": "akur8-q1-2026.md",
        "source_line": 12
      },
      ...
    ]

Prose fields (current_text, proposed_text, final_updated_text,
rationale, section) are passed through
`unescape_markdown_from_notion_property` on ingest to undo the
`⟪ast⟫ / ⟪us⟫ / …` placeholders `publish_to_notion.py` emits.
Orchestrator may hand rows through as-is.

Resolution order for the MCP server repo root (the parent of `context/`):
    1. --mcp-server-path CLI arg (explicit override)
    2. HXGTM_MCP_SERVER_PATH env var
    3. ../hxgtm-mcp-server/ relative to this repo root

Usage:
    python3 apply_integrations.py --group competitive --plan < rows.json
    python3 apply_integrations.py --group competitive --apply < rows.json
    python3 apply_integrations.py --list-groups
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
KB_UPDATE_CONFIG = REPO_ROOT / ".claude" / "skills" / "kb-update" / "config.yaml"

VALID_CATEGORIES_APPEND = {"coverage-gap"}

# How many context lines to show on either side of the match in a dry-run
# preview snippet. Kept small so the stdout summary stays scannable.
PREVIEW_CONTEXT_LINES = 3


# ---------------------------------------------------------------------------
# Markdown unescape (mirror of publish_to_notion.escape)
# ---------------------------------------------------------------------------
#
# publish_to_notion.py wraps markdown-significant characters with
# ⟪…⟫ placeholders before writing to Notion rich_text properties,
# because the Notion MCP fetch path strips the raw markers during
# publish → fetch round-trips. Unescape here returns the placeholders
# to their original characters so the text kb-integrate writes back
# into canon matches what the comparator originally produced.

_UNESCAPE_PLACEHOLDERS = [
    ("⟪ast⟫", "*"),
    ("⟪us⟫", "_"),
    ("⟪hash⟫", "#"),
    ("⟪bt⟫", "`"),
    ("⟪tld⟫", "~"),
]


def unescape_markdown_from_notion_property(value):
    """Idempotent reverse of publish_to_notion.escape_markdown_for_notion_property."""
    if not value:
        return value
    out = value
    for placeholder, raw in _UNESCAPE_PLACEHOLDERS:
        out = out.replace(placeholder, raw)
    return out


def _unescape_prose_fields(row):
    """Unescape markdown placeholders in prose fields of a Notion row in-place."""
    for field in (
        "current_text",
        "proposed_text",
        "final_updated_text",
        "rationale",
        "section",
    ):
        if field in row and row.get(field):
            row[field] = unescape_markdown_from_notion_property(row[field])
    return row


# ---------------------------------------------------------------------------
# Effective-text resolution (Final Updated Text → Proposed Updated Text)
# ---------------------------------------------------------------------------


def effective_text(row):
    """Return the text that should actually be written to canon.

    Reviewers type partial-approval tweaks in the `Final Updated Text`
    column in Notion; when it's non-empty, it wins over
    `Proposed Updated Text`. Every downstream site — replace, append,
    Landing preview rendering — reads through this helper so they
    can't disagree about which version applies. Do NOT inline this
    logic elsewhere.
    """
    final = (row.get("final_updated_text") or "").strip()
    if final:
        return final
    return (row.get("proposed_text") or "").strip()


# ---------------------------------------------------------------------------
# Section heading resolution
# ---------------------------------------------------------------------------


def _strip_leading_hashes(s):
    """Strip leading '#' characters (and surrounding whitespace) from `s`.

    Defensive against malformed rows where `section` was stored with a
    literal '## ' prefix — we always re-add the prefix at write time,
    so leaving it in place produces '## ## Heading' in canon.
    """
    if not s:
        return s
    return re.sub(r"^\s*#+\s*", "", s).strip()


def _resolve_append_heading(row):
    """Return the heading to target for an append.

    `section` is the existing canon h2 the finding was tagged with at
    publish time (from Notion's `Section` column). The comparator
    guardrail restricts findings to existing `section_schema`
    headings, so this should always match a real section in the
    target file. Appends merge into it.

    Title minus `R{n}: ` prefix is a last-resort fallback for rows
    missing `section`.
    """
    section = _strip_leading_hashes((row.get("section") or "").strip())
    if section:
        return section
    title = (row.get("title") or "").strip()
    return re.sub(r"^R\d+:\s*", "", title) or "kb-integrate-addition"


def _find_section_insert_idx(lines, heading):
    """Return the splice index where new content should be inserted at
    the end of the first '## <heading>' (h2) section found in `lines`.

    Returns None if no matching heading exists.

    The index points at the position after the last non-blank line of
    the section — i.e. `lines[:idx] + new + lines[idx:]` inserts the
    new content at the bottom of the existing section and before any
    trailing blank lines that separate it from the next section.

    Heading match is case-sensitive, whitespace-trimmed, and compared
    after stripping '#' markers so '## Snapshot' in-file matches a
    row whose `section` is either 'Snapshot' or '## Snapshot'.
    """
    target = _strip_leading_hashes(heading or "")
    if not target:
        return None

    heading_idx = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## ") and _strip_leading_hashes(stripped) == target:
            heading_idx = idx
            break
    if heading_idx is None:
        return None

    end_idx = len(lines)
    for idx in range(heading_idx + 1, len(lines)):
        stripped = lines[idx].lstrip()
        # Next h1 or h2 closes the current section.
        if stripped.startswith("## ") or (
            stripped.startswith("# ") and not stripped.startswith("## ")
        ):
            end_idx = idx
            break

    # Trim trailing blank lines inside the section so the splice lands
    # against real content, not against the blank separator before the
    # next heading.
    while end_idx > heading_idx + 1 and lines[end_idx - 1].strip() == "":
        end_idx -= 1
    return end_idx


# ---------------------------------------------------------------------------
# Config lookup (copy of the kb-update helper — keeps this script stdlib-only)
# ---------------------------------------------------------------------------


def _read_yaml_scalar(path, key_path):
    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    path_stack = []
    for raw in lines:
        stripped = raw.rstrip("\n")
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

        current_keys = tuple(k for k, _ in path_stack)
        if current_keys == key_path and value:
            return value
    return None


def _list_group_slugs(config_path):
    slugs = []
    with config_path.open("r", encoding="utf-8") as f:
        in_groups = False
        for raw in f:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            if stripped.startswith("groups:"):
                in_groups = True
                continue
            if in_groups and indent == 2 and stripped.endswith(":"):
                slug = stripped[:-1].strip()
                if slug:
                    slugs.append(slug)
    return slugs


def load_group_record(group):
    if not KB_UPDATE_CONFIG.exists():
        sys.exit(f"ERROR: kb-update config not found at {KB_UPDATE_CONFIG}")
    label = _read_yaml_scalar(KB_UPDATE_CONFIG, ("groups", group, "label"))
    codeowner = _read_yaml_scalar(KB_UPDATE_CONFIG, ("groups", group, "codeowner"))
    active = _read_yaml_scalar(KB_UPDATE_CONFIG, ("groups", group, "active"))
    data_source_id = _read_yaml_scalar(
        KB_UPDATE_CONFIG, ("groups", group, "notion_data_source_id")
    )
    if not label:
        sys.exit(
            f"ERROR: group '{group}' not found in {KB_UPDATE_CONFIG}. "
            f"Run 'python3 {Path(__file__).name} --list-groups' to see available groups."
        )
    return {
        "slug": group,
        "label": label,
        "codeowner": codeowner,
        "active": (active or "").strip().lower() == "true",
        "notion_data_source_id": data_source_id,
    }


# ---------------------------------------------------------------------------
# MCP server repo resolution
# ---------------------------------------------------------------------------


def resolve_mcp_server_path(cli_arg):
    """Resolve the hxgtm-mcp-server path.

    CLI override (`--mcp-server-path`) short-circuits everything and
    wins — it's explicit user intent, sometimes used to test against
    a throwaway clone. Otherwise delegate to
    `scripts/resolve_mcp_path.py` which handles .kb-local.json cache
    → env var → adjacent → dev-root scan with proper zip-not-git
    halts and cache write-back. Keeps the resolver in one place
    instead of drifting across kb-update / kb-integrate.
    """
    if cli_arg:
        candidate = Path(cli_arg).expanduser().resolve()
        if not candidate.is_dir() or not (candidate / "context").is_dir():
            sys.exit(
                f"ERROR: --mcp-server-path {candidate} is not a directory "
                f"containing `context/`."
            )
        if not (candidate / ".git").is_dir():
            sys.exit(
                f"ERROR: hxgtm-mcp-server at {candidate} is not a git "
                f"clone — kb-integrate needs git diff/commit to work. "
                f"Run:\n  git clone "
                f"git@github.com:hx-gtm/hxgtm-mcp-server.git"
            )
        return candidate

    resolver = REPO_ROOT / ".claude" / "skills" / "kb-update" / "scripts" / "resolve_mcp_path.py"
    try:
        result = subprocess.run(
            ["python3", str(resolver), "mcp-path", "--quiet"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        sys.exit(f"ERROR: failed to invoke {resolver}: {exc}")

    if result.returncode != 0:
        # Resolver already printed a clear halt to stderr; mirror it
        # through so the user sees it.
        sys.stderr.write(result.stderr)
        sys.exit(result.returncode or 1)

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        sys.exit(
            f"ERROR: {resolver} returned invalid JSON: {exc}\n"
            f"stdout: {result.stdout!r}"
        )

    return Path(payload["path"])


# ---------------------------------------------------------------------------
# Global config lookup (provenance toggle)
# ---------------------------------------------------------------------------


def _include_provenance_comment():
    """Read global.include_provenance_comment from kb-update's config.yaml.

    Returns True by default (the HTML comment is invisible in rendered
    Notion and GitHub markdown; it shows up in git blame and raw views
    for traceability).
    """
    if not KB_UPDATE_CONFIG.exists():
        return True
    value = _read_yaml_scalar(
        KB_UPDATE_CONFIG, ("global", "include_provenance_comment")
    )
    if value is None:
        return True
    return value.strip().lower() == "true"


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


def _strip_line_suffix(path):
    if not path:
        return path
    path = re.sub(r"\s*\(line\s+\d+\)\s*$", "", path)
    path = re.sub(r":\d+\s*$", "", path)
    return path.strip("`").strip()


def _strip_autolink(s):
    """Peel any markdown auto-link wrapping off the path components of `s`.

    The Notion MCP rewrites filename-shaped substrings in rich_text
    properties as `[<filename>](<url>)` on read, even though
    `publish_to_notion.py` writes plain text. Reduce `[X](Y)` back to
    `X` everywhere it appears so path/source fields ingest cleanly.
    """
    if not s:
        return s
    return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)


def _resolve_canon_path(target_file, mcp_root):
    """Resolve a row's target_file to an absolute path under <mcp_root>/context/.
    Returns (abs_path, rel_path) or (None, reason_string) on rejection.

    Tolerant ingest:
      - strips markdown auto-link wrapping (`[X](Y)` → `X`) — Notion's
        rich_text renderer inserts these on read.
      - accepts both `context/<rel>` and `<rel>` forms for `target_file`.
        The synthesis contract and the output-format spec disagree on
        whether the prefix is carried in the Notion column; we collapse
        both shapes to the same on-disk resolution.
    """
    if not target_file:
        return None, "target_file is empty"
    cleaned = _strip_autolink(_strip_line_suffix(target_file)).lstrip("/")
    rel_to_context = cleaned[len("context/"):] if cleaned.startswith("context/") else cleaned
    if not rel_to_context:
        return None, "target_file resolves to an empty canon path"
    canon_root = (mcp_root / "context").resolve()
    abs_path = (canon_root / rel_to_context).resolve()
    # Confinement check: abs_path must live under mcp_root/context.
    try:
        abs_path.relative_to(canon_root)
    except ValueError:
        return None, f"target_file '{cleaned}' escapes the canon root"
    # Return a rel path that is always `context/`-prefixed so downstream
    # logging, previews, and result payloads are consistent.
    return abs_path, "context/" + rel_to_context


def _snippet_around(lines, start, end, context=PREVIEW_CONTEXT_LINES):
    """±context lines around [start..end], 1-indexed inclusive. Pure preview."""
    lo = max(1, start - context)
    hi = min(len(lines), end + context)
    return "\n".join(lines[lo - 1 : hi])


def _provenance_comment(finding_id, source_file, source_line, run_date):
    bits = [f"finding: {finding_id}"]
    if source_file:
        if isinstance(source_line, int) and source_line > 0:
            bits.append(f"source: {source_file}:{source_line}")
        else:
            bits.append(f"source: {source_file}")
    if run_date:
        bits.append(f"integrated: {run_date}")
    bits.append("via: kb-integrate")
    return "<!-- " + " · ".join(bits) + " -->"


def _infer_action(row):
    """Derive `replace` vs `append` from the row.

    Honours an explicit `action` field if present; otherwise:
      - empty `current_text` OR the append-sentinel → `append`.
      - non-empty `current_text` → `replace`.

    The comparator emits `action` explicitly and the publisher persists
    it in the Notion `Action` column; inference is the legacy-row
    fallback for pre-Phase-3 rows without the column populated.
    """
    explicit = (row.get("action") or "").strip().lower()
    if explicit in {"replace", "append"}:
        return explicit
    ct = (row.get("current_text") or "").strip()
    # Publisher writes this sentinel on append rows so Notion's Current
    # Text column isn't blank. Treat it as "no existing text" for the
    # inference fallback.
    if ct.startswith("(addition to canon"):
        return "append"
    return "replace" if ct else "append"


def _plan_row(row, mcp_root, run_date, provenance_on):
    """Build a plan entry for one Notion row.

    Replace uses line anchoring only: the comparator emitted
    `target_line_start / end` at publish time and we write
    `effective_text` (Final Updated Text or Proposed Updated Text)
    at that range unconditionally. No drift check — we assume canon
    is not edited concurrently during the triage window.
    """
    _unescape_prose_fields(row)

    row_id = row.get("finding_id") or row.get("page_id") or "?"
    title = (row.get("title") or "").strip()
    target_file = row.get("target_file") or ""
    # Notion auto-links filename-shaped strings in rich_text on read;
    # `_resolve_canon_path` does the same on target_file, but the
    # provenance comment prints source_file verbatim so strip it here.
    source_file = _strip_autolink(row.get("source_file") or "")
    source_line = row.get("source_line")
    page_id = row.get("page_id") or ""

    entry = {
        "page_id": page_id,
        "finding_id": row_id,
        "title": title,
        "target_file": target_file,
        "action": None,
        "target_path": None,
        "will_succeed": False,
        "needs_restage": False,
        "reason": "",
        "preview_before": "",
        "preview_after": "",
    }

    abs_path, rel_or_reason = _resolve_canon_path(target_file, mcp_root)
    if abs_path is None:
        entry.update(action="skip", reason=rel_or_reason)
        return entry
    entry["target_path"] = str(abs_path)
    entry["target_rel"] = rel_or_reason

    action = _infer_action(row)
    entry["action"] = action

    eff_text = effective_text(row)

    if action == "append":
        if not eff_text:
            entry.update(reason="effective_text is empty — nothing to append")
            return entry
        existing = ""
        if abs_path.exists():
            try:
                existing = abs_path.read_text(encoding="utf-8")
            except OSError as exc:
                entry.update(reason=f"cannot read target file: {exc}")
                return entry
        heading = _resolve_append_heading(row)
        prov = (
            _provenance_comment(row_id, source_file, source_line, run_date)
            if provenance_on
            else ""
        )

        # Block to splice INTO an existing '## <heading>' section — no
        # heading line, since the section already has one.
        insert_lines = []
        if prov:
            insert_lines.extend([prov, ""])
        insert_lines.append(eff_text.rstrip())

        # Block to APPEND at EOF when no matching section exists — a
        # full new '## <heading>' section with provenance + body.
        new_parts = [f"## {heading}", ""]
        if prov:
            new_parts.extend([prov, ""])
        new_parts.extend([eff_text.rstrip(), ""])
        new_block = "\n\n" + "\n".join(new_parts)

        existing_lines = existing.splitlines() if existing else []
        insert_idx = (
            _find_section_insert_idx(existing_lines, heading)
            if existing_lines
            else None
        )

        if insert_idx is not None:
            # Merge preview: show a few lines of context above the
            # insertion point so the reviewer can see where content lands.
            ctx_start = max(0, insert_idx - 4)
            before_snippet = "\n".join(existing_lines[ctx_start:insert_idx])
            entry["preview_before"] = before_snippet or "(top of section)"
            entry["preview_after"] = "\n".join(insert_lines)
            entry["reason"] = f"merge into existing '## {heading}' section"
        else:
            entry["preview_before"] = existing[-400:] if existing else "(new file)"
            entry["preview_after"] = new_block.strip()
            entry["reason"] = (
                f"append new '## {heading}' section at EOF"
                if existing
                else f"create new file with '## {heading}' section"
            )

        entry["will_succeed"] = True
        entry["_insert_lines"] = insert_lines
        entry["_append_block"] = new_block
        entry["_file_existed"] = bool(existing)
        entry["_effective_text"] = eff_text
        entry["_heading"] = heading
        return entry

    # Replace path — line range only (no drift check).
    if not abs_path.exists():
        entry.update(
            reason=f"target file does not exist: {entry['target_rel']}",
            needs_restage=True,
        )
        return entry
    if not eff_text:
        entry.update(
            reason="effective_text is empty — refusing to blank canon"
        )
        return entry

    tls = row.get("target_line_start")
    tle = row.get("target_line_end")
    if not isinstance(tls, int) or not isinstance(tle, int):
        entry.update(
            reason="missing target_line_start / target_line_end on row",
            needs_restage=True,
        )
        return entry
    if tls < 1 or tle < tls:
        entry.update(
            reason=f"invalid line range: start={tls} end={tle}",
            needs_restage=True,
        )
        return entry

    try:
        body = abs_path.read_text(encoding="utf-8")
    except OSError as exc:
        entry.update(reason=f"cannot read target file: {exc}")
        return entry

    lines = body.splitlines()
    if tle > len(lines):
        entry.update(
            reason=(
                f"target_line_end {tle} beyond file length ({len(lines)} "
                f"lines)"
            ),
            needs_restage=True,
        )
        return entry

    entry["will_succeed"] = True
    entry["reason"] = f"line match at lines {tls}-{tle}"
    entry["preview_before"] = _snippet_around(lines, tls, tle)
    entry["preview_after"] = eff_text.rstrip()
    entry["_target_line_start"] = tls
    entry["_target_line_end"] = tle
    entry["_effective_text"] = eff_text
    entry["_file_trailing_newline"] = body.endswith("\n")
    return entry


def build_plan(rows, mcp_root, run_date):
    provenance_on = _include_provenance_comment()
    return [_plan_row(row, mcp_root, run_date, provenance_on) for row in rows]


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def _build_result(entry, *, status, reason):
    return {
        "page_id": entry.get("page_id", ""),
        "finding_id": entry.get("finding_id", "?"),
        "action": entry.get("action"),
        "target_rel": entry.get("target_rel"),
        "status": status,
        "reason": reason,
    }


def _apply_replace_line_range(lines, start, end, new_text):
    """Replace lines[start-1 : end] with new_text split on '\\n', in place.

    Returns a new list of lines. `start` / `end` are 1-indexed and
    inclusive. `new_text` is NOT stripped — callers control trailing
    whitespace.
    """
    new_lines = new_text.split("\n")
    # Drop a trailing empty element that split produces when new_text
    # ends with '\n' — it would insert a blank line we didn't intend.
    if new_lines and new_lines[-1] == "" and new_text.endswith("\n"):
        new_lines = new_lines[:-1]
    return lines[: start - 1] + new_lines + lines[end:]


def _run_replaces_bottom_up(replaces_desc, lines):
    """Apply replace entries to a line buffer in descending line-start order.

    Processing top-down from the bottom of the file means earlier
    replacements don't shift the line positions of later ones — no
    bookkeeping needed. Returns (new_lines, pending) where pending is a
    list of (entry_index, status, reason) tuples, one per replace
    entry.
    """
    pending = []
    for i, entry in replaces_desc:
        start = entry["_target_line_start"]
        end = entry["_target_line_end"]

        if end > len(lines):
            pending.append((
                i, "skipped",
                f"apply-time: lines beyond buffer ({end} > {len(lines)})",
            ))
            continue

        lines = _apply_replace_line_range(
            lines, start, end, entry["_effective_text"]
        )
        pending.append((
            i, "success", f"line replace at lines {start}-{end}",
        ))
    return lines, pending


def _apply_appends(entries, lines, results_sink):
    """Apply append entries against the live `lines` state.

    For each entry, re-check whether a '## <heading>' section already
    exists; if it does, splice the pre-computed `_insert_lines` into
    the end of that section (deduplicating headings). Otherwise,
    concatenate the pre-computed `_append_block` at EOF, creating a
    new section.

    Entries are processed in input order so that a new section created
    by an earlier entry is reused by any later entry with the same
    heading — e.g. two 'Weaknesses / watch-outs' adds against a file
    that currently has no such section land under a single new heading
    rather than producing two duplicates.
    """
    dirty = False
    for i, entry in entries:
        heading = entry.get("_heading") or ""
        insert_idx = _find_section_insert_idx(lines, heading) if heading else None

        if insert_idx is not None:
            insert_lines = list(entry.get("_insert_lines") or [])
            # Separate from preceding paragraph with a blank line if
            # the section body doesn't already end on one.
            if insert_idx > 0 and lines[insert_idx - 1].strip() != "":
                insert_lines = [""] + insert_lines
            lines = lines[:insert_idx] + insert_lines + lines[insert_idx:]
            dirty = True
            results_sink[i] = _build_result(
                entry,
                status="success",
                reason=f"merge into existing '## {heading}' section",
            )
            continue

        block = entry.get("_append_block", "")
        buffer = "\n".join(lines)
        if buffer and not buffer.endswith("\n"):
            buffer += "\n"
        if not buffer:
            block = block.lstrip("\n")
        buffer = buffer + block
        lines = buffer.split("\n")
        # split('\n') on text ending with '\n' leaves a trailing ""; OK.
        dirty = True
        reason = entry.get("reason") or "appended"
        if heading and not reason.startswith("append"):
            reason = f"append new '## {heading}' section at EOF"
        results_sink[i] = _build_result(
            entry, status="success", reason=reason
        )
    return lines, dirty


def _verify_post_apply(abs_path, entries, results_sink):
    """Re-read the file after write and assert the effective_text is
    present for each success-marked entry. Failures flip the row to
    `failure` so kb-integrate leaves the Notion row at Approved for
    retry instead of flipping it to Integrated."""
    try:
        post_body = abs_path.read_text(encoding="utf-8")
    except OSError as exc:
        for i, entry in entries:
            if results_sink[i] and results_sink[i].get("status") == "success":
                results_sink[i] = _build_result(
                    entry,
                    status="failure",
                    reason=f"post-apply readback failed: {exc}",
                )
        return

    for i, entry in entries:
        result = results_sink[i]
        if not result or result.get("status") != "success":
            continue
        eff_text = entry.get("_effective_text") or ""
        if eff_text and eff_text not in post_body:
            results_sink[i] = _build_result(
                entry,
                status="failure",
                reason="post-apply verification failed: effective_text not present in file",
            )


def apply_plan(plan, mcp_root):
    """Apply the plan to disk.

    Rows are grouped by target file. Within each file:
      1. Sort replace entries by target_line_start DESC so earlier edits
         don't shift later ones' anchors.
      2. Run appends at the bottom of the file, in input order, AFTER
         all replaces have settled.
      3. Write the resulting buffer.
      4. Re-read the file and verify each successful entry's
         effective_text is present (post-apply readback).
    """

    results = [None] * len(plan)

    # Pre-populate skip results for entries that never reached will_succeed.
    for i, entry in enumerate(plan):
        if entry.get("will_succeed"):
            continue
        status = "needs_restage" if entry.get("needs_restage") else "skipped"
        results[i] = _build_result(
            entry, status=status, reason=entry.get("reason", "")
        )

    # Group remaining (executable) entries by target file.
    by_file = {}
    for i, entry in enumerate(plan):
        if not entry.get("will_succeed"):
            continue
        target_path = entry.get("target_path")
        if not target_path:
            results[i] = _build_result(
                entry, status="failure",
                reason="missing target_path on planned entry",
            )
            continue
        by_file.setdefault(target_path, []).append((i, entry))

    for target_path, entries in by_file.items():
        abs_path = Path(target_path)
        try:
            original_body = (
                abs_path.read_text(encoding="utf-8") if abs_path.exists() else ""
            )
        except OSError as exc:
            for i, entry in entries:
                results[i] = _build_result(
                    entry, status="failure",
                    reason=f"cannot read target file: {exc}",
                )
            continue

        lines = original_body.splitlines() if original_body else []

        # Replaces first, bottom-up.
        replaces = [(i, e) for i, e in entries if e["action"] == "replace"]
        appends = [(i, e) for i, e in entries if e["action"] == "append"]
        replaces_desc = sorted(
            replaces, key=lambda pair: pair[1]["_target_line_start"], reverse=True
        )

        lines, pending = _run_replaces_bottom_up(replaces_desc, lines)
        replace_entry_by_i = {i: e for i, e in replaces}
        for i, status, reason in pending:
            entry = replace_entry_by_i.get(i, {})
            results[i] = _build_result(entry, status=status, reason=reason)

        # Appends next, in input order.
        if appends:
            lines, _ = _apply_appends(appends, lines, results)

        # Did anything actually change?
        new_body = "\n".join(lines)
        if original_body.endswith("\n") and not new_body.endswith("\n"):
            new_body += "\n"
        elif not lines and not original_body:
            new_body = ""

        any_success = any(
            (results[i] or {}).get("status") == "success"
            for i, _ in entries
        )
        if any_success and new_body != original_body:
            try:
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                abs_path.write_text(new_body, encoding="utf-8")
            except OSError as exc:
                for i, entry in entries:
                    if (results[i] or {}).get("status") == "success":
                        results[i] = _build_result(
                            entry, status="failure",
                            reason=f"write failed: {exc}",
                        )
                continue

            # Post-apply readback verification (RC 8e). Downgrades any
            # `success` whose effective_text isn't actually present in
            # the re-read file. kb-integrate leaves those rows at
            # Approved for a retry instead of flipping to Integrated.
            _verify_post_apply(abs_path, entries, results)

    return results




# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--group", help="Group slug (e.g. competitive)")
    parser.add_argument(
        "--mcp-server-path",
        help="Absolute path to the hxgtm-mcp-server repo root. "
        "Overrides HXGTM_MCP_SERVER_PATH and the default sibling lookup.",
    )
    parser.add_argument("--run-date", help="Run date, YYYY-MM-DD")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--plan",
        action="store_true",
        help="Read-only: compute and print the edit plan as JSON. No writes.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Execute the edit plan on disk and print per-row results as JSON.",
    )
    mode.add_argument(
        "--list-groups",
        action="store_true",
        help="Print available group slugs from kb-update/config.yaml and exit.",
    )
    parser.add_argument(
        "--emit-group-record",
        action="store_true",
        help="Print the resolved group record as JSON and exit. Used by SKILL.md.",
    )
    args = parser.parse_args()

    if args.list_groups:
        if not KB_UPDATE_CONFIG.exists():
            sys.exit(f"ERROR: {KB_UPDATE_CONFIG} not found")
        for slug in _list_group_slugs(KB_UPDATE_CONFIG):
            record = load_group_record(slug)
            active = "active" if record["active"] else "inactive"
            print(f"  {slug:<20} {record['label']} — owner: {record['codeowner']} ({active})")
        return 0

    if not args.group:
        sys.exit("ERROR: --group is required (or pass --list-groups)")

    group_record = load_group_record(args.group)

    if args.emit_group_record:
        print(json.dumps(group_record, indent=2))
        return 0

    if not (args.plan or args.apply):
        sys.exit("ERROR: pass --plan or --apply (or --list-groups / --emit-group-record)")

    mcp_root = resolve_mcp_server_path(args.mcp_server_path)

    try:
        rows = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: stdin is not valid JSON: {exc}")
    if not isinstance(rows, list):
        sys.exit("ERROR: stdin must be a JSON array of Notion row objects")

    plan = build_plan(rows, mcp_root, args.run_date)

    if args.plan:
        # Strip internal fields (prefixed with `_`) before emitting.
        public_plan = [
            {k: v for k, v in entry.items() if not k.startswith("_")}
            for entry in plan
        ]
        payload = {
            "group": group_record,
            "mcp_server_path": str(mcp_root),
            "plan": public_plan,
            "stats": _plan_stats(plan),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    # Apply mode.
    results = apply_plan(plan, mcp_root)
    payload = {
        "group": group_record,
        "mcp_server_path": str(mcp_root),
        "results": results,
        "stats": _apply_stats(results),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _plan_stats(plan):
    return {
        "rows": len(plan),
        "will_replace": sum(
            1 for e in plan
            if e.get("action") == "replace" and e.get("will_succeed")
        ),
        "will_append": sum(
            1 for e in plan
            if e.get("action") == "append" and e.get("will_succeed")
        ),
        "needs_restage": sum(
            1 for e in plan if e.get("needs_restage")
        ),
        "skipped": sum(
            1 for e in plan
            if not e.get("will_succeed") and not e.get("needs_restage")
        ),
    }


def _apply_stats(results):
    return {
        "rows": len(results),
        "success": sum(1 for r in results if r.get("status") == "success"),
        "skipped": sum(1 for r in results if r.get("status") == "skipped"),
        "needs_restage": sum(
            1 for r in results if r.get("status") == "needs_restage"
        ),
        "failure": sum(1 for r in results if r.get("status") == "failure"),
    }


if __name__ == "__main__":
    sys.exit(main())
