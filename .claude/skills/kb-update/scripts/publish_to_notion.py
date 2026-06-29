#!/usr/bin/env python3
"""
publish_to_notion.py

Transforms a list of kb-update findings (JSON on stdin) into a
notion-create-pages payload (JSON on stdout). Claude reads this output and
passes it to the notion-create-pages MCP tool — auth is handled by the
user's Notion MCP connector, not by this script.

kb-update uses per-group Notion databases. Each group (competitive, messaging,
audiences, …) has its own "KB - <Label>" database nested under the
"KB - Updates Review" landing page. This script picks the correct
data source ID for the target group.

Resolution order for the parent data source ID:
    1. --parent-data-source CLI arg (explicit override)
    2. KB_UPDATE_NOTION_DS_<GROUP_UPPER> environment variable (e.g.
       KB_UPDATE_NOTION_DS_COMPETITIVE)
    3. groups.<group>.notion_data_source_id in .claude/skills/kb-update/config.yaml

Usage:
    python3 publish_to_notion.py \\
        --group competitive \\
        --run-date 2026-04-15 \\
        < findings.json > pages.json

    python3 publish_to_notion.py --group competitive --check-schema

Exits 0 on success. Exits non-zero on schema mismatch (--check-schema),
malformed findings, or missing data source ID.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path


MAX_RICH_TEXT_LEN = 2000
# Notion's notion-create-pages tool accepts up to 100 pages per call.
# 50 keeps headroom under that hard limit while ensuring any typical
# kb-update run (≤50 findings) publishes in a single MCP call. Larger
# batches cut tool-call churn and conversation-context pollution for
# the orchestrator 4–5× vs the prior value of 10.
BATCH_SIZE = 50

# Per-group databases drop the Group and Codeowner columns — they are
# redundant inside a database that only holds findings for one group.
# Status is a SELECT (not Notion's built-in STATUS type) so its options
# are configurable via DDL — that's what lets setup_notion.py create a
# database with the full Pending Review / Approved / Needs Restage /
# Rejected / Integrated lifecycle seeded, with no manual Notion UI
# configuration required.
EXPECTED_COLUMNS = {
    "Name": "title",
    "Entity": "select",
    "Section": "text",
    "Source Tier": "select",
    "Status": "select",
    "Action": "select",
    "Closes Open Question": "text",
    "Proposed Updated Text": "text",
    "Final Updated Text": "text",
    "Date Added": "date",
    "Current Text": "text",
    "Rationale": "text",
    "Source file": "text",
    "Target file": "text",
    "Reviewer": "person",
    "Severity": "select",
    "Category": "select",
    "Source Line": "number",
    "Target Line Start": "number",
    "Target Line End": "number",
    # Review Bucket is a FORMULA derived from Status — the publisher
    # never writes to it, but the schema-drift repair path needs to
    # recognize the column so it isn't flagged as missing on fetch.
    "Review Bucket": "formula",
}

# Per-column DDL fragments. Step 6's reactive schema-drift repair uses
# these to build ADD COLUMN statements for any column that's missing
# from the live Notion data source when a publish batch 400s with
# `property does not exist`. Must stay byte-identical to the
# `"Name" <type>` fragments inside SCHEMA_DDL in setup_notion.py —
# that's the single source of truth for the CREATE TABLE shape;
# this map just carries the per-column slice so the repair path
# doesn't have to parse SCHEMA_DDL at runtime.
COLUMN_DDL = {
    "Name": "TITLE",
    "Entity": "SELECT()",
    "Section": "RICH_TEXT",
    "Source Tier": "SELECT('Tier 1':blue, 'Tier 2':purple, 'Tier 3':yellow, 'Tier 4':gray, 'Tier 5':red)",
    "Status": "SELECT('Pending Review':gray, 'Approved':blue, 'Needs Restage':orange, 'Rejected':red, 'Integrated':green)",
    "Action": "SELECT('Append':green, 'Replace':orange)",
    "Closes Open Question": "RICH_TEXT",
    "Proposed Updated Text": "RICH_TEXT",
    "Final Updated Text": "RICH_TEXT",
    "Date Added": "DATE",
    "Current Text": "RICH_TEXT",
    "Rationale": "RICH_TEXT",
    "Source file": "RICH_TEXT",
    "Target file": "RICH_TEXT",
    "Reviewer": "PEOPLE",
    "Severity": "SELECT('High':red, 'Medium':yellow, 'Low':gray)",
    "Category": "SELECT('raw-canon-conflict':red, 'freshness':yellow, 'cross-reference':blue, 'consistency':orange, 'template':purple, 'coverage-gap':gray)",
    "Source Line": "NUMBER",
    "Target Line Start": "NUMBER",
    "Target Line End": "NUMBER",
    # Review Bucket collapses Pending Review + Needs Restage into a
    # single "Needs Decision" bucket; other statuses pass through.
    # Drives group_by in the default triage view (see setup_notion.py).
    "Review Bucket": 'FORMULA(if(prop("Status") == "Pending Review" or prop("Status") == "Needs Restage", "Needs Decision", prop("Status")))',
}

assert set(COLUMN_DDL.keys()) == set(EXPECTED_COLUMNS.keys()), (
    "COLUMN_DDL and EXPECTED_COLUMNS must cover the same columns"
)

DEFAULT_STATUS = "Pending Review"

REQUIRED_FINDING_FIELDS = [
    "finding_id",
    "title",
    "category",
    "severity",
    "source_tier",
    "target_file",
    "target_line_start",
    "target_line_end",
    "entity",
    "rationale",
    "source_file",
    "group",
    "run_date",
]

# kb-update only produces raw-canon-conflict findings (it's the only
# dimension kb-update runs). The other categories are carried forward
# as a superset in case the schema is ever reused by a sibling skill.
VALID_CATEGORIES = {
    "raw-canon-conflict",
    "freshness",
    "cross-reference",
    "consistency",
    "template",
    "coverage-gap",
    "external",
}

VALID_SEVERITIES = {"high", "medium", "low"}
VALID_SOURCE_TIERS = {"tier_1", "tier_2", "tier_3", "tier_4", "tier_5"}
VALID_ACTIONS = {"append", "replace"}


# ---------------------------------------------------------------------------
# Markdown escape for Notion rich_text properties
# ---------------------------------------------------------------------------
#
# The Notion MCP fetch path strips markdown-significant characters
# (`*`, `_`, leading `#`, backticks) from rich_text property values
# during publish → fetch round-trips. When canon snippets like
# `*Weaknesses:*` or `**Lead claim**` land in a property and are
# fetched back at integrate time, the markers are gone — which would
# silently drop formatting when applied back to canon.
#
# Escape-on-write + unescape-on-read keeps the round-trip lossless.
# The placeholders use ⟪⟫ (U+27EA / U+27EB) brackets, which do not
# occur in canon, GTM prose, or any known markdown source.
#
# apply_integrations.py mirrors unescape_markdown_from_notion_property.

_MARKDOWN_PLACEHOLDERS = [
    ("*", "⟪ast⟫"),
    ("_", "⟪us⟫"),
    ("#", "⟪hash⟫"),
    ("`", "⟪bt⟫"),
    ("~", "⟪tld⟫"),
]


def escape_markdown_for_notion_property(value):
    """Wrap markdown-significant characters with placeholders for rich_text
    properties before writing. Pair with the unescape helper at fetch time."""
    if not value:
        return value
    out = value
    for raw, placeholder in _MARKDOWN_PLACEHOLDERS:
        out = out.replace(raw, placeholder)
    return out


# ---------------------------------------------------------------------------
# Data source resolution (per-group)
# ---------------------------------------------------------------------------


def resolve_data_source_id(cli_arg, group):
    """
    Return the parent data source ID for the target group.

    Resolution order:
        1. --parent-data-source CLI arg (explicit override — used by
           --notion-setup right after creating a fresh database)
        2. KB_UPDATE_NOTION_DS_<GROUP_UPPER> env var (per-env override
           so the same repo can target testing vs production without
           config edits)
        3. .kb-local.json.notion_ids.<group> cache (populated by the
           auto-reconcile fallback in SKILL.md Step 2 when a config
           ID resolves stale)
        4. groups.<group>.notion_data_source_id in config.yaml
    """
    if cli_arg:
        return cli_arg

    if not group:
        sys.exit(
            "ERROR: --group is required (or pass --parent-data-source to "
            "override group lookup)."
        )

    env_key = f"KB_UPDATE_NOTION_DS_{group.upper().replace('-', '_')}"
    env_value = os.environ.get(env_key)
    if env_value:
        return env_value

    cached = _read_local_notion_id(group)
    if cached:
        return cached

    config_path = Path(__file__).resolve().parents[1] / "config.yaml"
    if config_path.exists():
        value = _read_yaml_scalar(
            config_path, ("groups", group, "notion_data_source_id")
        )
        if value:
            return value

    sys.exit(
        f"ERROR: no Notion data source ID for group '{group}'. "
        f"Set --parent-data-source, {env_key} env var, "
        f"write to .kb-local.json.notion_ids.{group}, or set "
        f"groups.{group}.notion_data_source_id in .claude/skills/kb-update/config.yaml. "
        f"SKILL.md Step 2 auto-reconciles this on a normal run; you're "
        f"only expected to see this error if you ran publish_to_notion.py "
        f"directly without orchestration."
    )


def _read_local_notion_id(group):
    """Read .kb-local.json.notion_ids.<group>, or "" if not set. Stdlib only."""
    local = Path(__file__).resolve().parents[4] / ".kb-local.json"
    if not local.exists():
        return ""
    try:
        with local.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    return (data.get("notion_ids") or {}).get(group, "") or ""


def _read_yaml_scalar(path, key_path):
    """
    Minimal YAML reader for nested scalar values. Avoids adding PyYAML as a
    dependency — config.yaml uses simple indented keys and we only need to
    read one scalar at a time.
    """
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


def _read_yaml_scalar_from_group(path, group, field):
    """Lookup groups.<group>.<field> as a scalar string, or None."""
    return _read_yaml_scalar(path, ("groups", group, field))


def resolve_codeowner(group):
    """Look up the codeowner for a group from config.yaml (best-effort)."""
    if not group:
        return None
    config_path = Path(__file__).resolve().parents[1] / "config.yaml"
    if not config_path.exists():
        return None
    return _read_yaml_scalar_from_group(config_path, group, "codeowner")


# ---------------------------------------------------------------------------
# Schema check
# ---------------------------------------------------------------------------


def expected_schema_hash():
    """
    Stable hash of the expected column set. Used to cache a "schema
    verified" receipt in `.kb-local.json` so SKILL.md Step 2d can skip
    the notion-fetch diff on runs where the expected schema hasn't
    changed since the last successful verify.

    Hash is deterministic: JSON of EXPECTED_COLUMNS sorted by key,
    SHA-256, first 16 hex chars (8 bytes — plenty for collision-free
    bucketing of a finite schema space). Any edit to column names or
    types invalidates every cached receipt on the next run, forcing
    a re-verify — exactly what we want when SCHEMA_DDL bumps.
    """
    payload = json.dumps(EXPECTED_COLUMNS, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def build_select_seed_ddl(column, existing_options, run_values):
    """
    Build a color-less `ALTER COLUMN "<column>" SET SELECT(...)` DDL that is
    safe to run against an existing SELECT column during reactive repair.

    Two invariants enforced here (learned the hard way during the
    2026-04-22 competitive run — see /Users/jericho/.claude/plans/
    name-apiresponseerror-code-validation-e-cozy-robin.md):

    1. **No colors.** Notion treats `(option_name, color)` as immutable
       after provisioning. Any `SET SELECT('Name':color, ...)` that
       references an existing option with a different color fails with
       `Cannot update color of select with name: <X>`. The color-less
       form preserves every existing option's color and auto-assigns
       defaults to new options.

    2. **Union, never replace.** `SET SELECT(...)` has replace-set
       semantics. If a reviewer has added an option directly in Notion
       since the last run and that option isn't in `run_values`, naive
       DDL would drop it (and empty any rows that referenced it). The
       final DDL always includes the union of `existing_options` and
       `run_values`, sorted for stable output.

    `existing_options` and `run_values` are iterables of bare option
    names (no colors). Empty strings and None are filtered out.
    """
    def _clean(values):
        return {v for v in (values or []) if isinstance(v, str) and v.strip()}

    final = sorted(_clean(existing_options) | _clean(run_values))
    if not final:
        raise ValueError(
            f"Cannot build SELECT seed DDL for {column!r}: no options "
            f"(existing={list(existing_options) or []!r}, "
            f"run={list(run_values) or []!r})"
        )
    options_sql = ", ".join(f"'{name}'" for name in final)
    return f'ALTER COLUMN "{column}" SET SELECT({options_sql})'


def cli_build_select_ddl(column, existing_csv, values_csv):
    """Emit the DDL string on stdout. Orchestrator invokes this after
    fetching the column's current options from Notion."""
    existing = [v.strip() for v in (existing_csv or "").split(",") if v.strip()]
    values = [v.strip() for v in (values_csv or "").split(",") if v.strip()]
    try:
        print(build_select_seed_ddl(column, existing, values))
    except ValueError as exc:
        sys.exit(f"ERROR: {exc}")
    return 0


def check_schema(data_source_id, group):
    """
    Emit the expected schema (and per-column DDL) as JSON on stdout. Called
    reactively by the orchestrator when Step 6 publish hits a missing-column
    400 — the `column_ddl` map keyed by column name is the lookup table for
    composing `ADD COLUMN "<Name>" <ddl>` statements passed to
    `notion-update-data-source`.

    This subcommand makes zero Notion calls (this script has no Notion
    auth — the MCP connector lives in Claude's process, not ours). It is
    no longer invoked on the happy path; kb-update assumes schema
    correctness and only consults `column_ddl` when reactive repair is
    needed.

    `schema_hash` is retained in the payload for diagnostic parity with
    earlier RCs; no caller compares it against a cached value under the
    current design.
    """
    payload = {
        "check_schema": True,
        "group": group,
        "data_source_id": data_source_id,
        "expected_columns": EXPECTED_COLUMNS,
        "column_ddl": COLUMN_DDL,
        "schema_hash": expected_schema_hash(),
    }
    print(json.dumps(payload, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Rich text helpers (copied from save-dossier-to-notion.py pattern)
# ---------------------------------------------------------------------------


def _plain(content):
    return {"type": "text", "text": {"content": content}}


def _split_text(text, max_len):
    """Split text into <= max_len chunks, breaking at newlines or spaces."""
    chunks = []
    while len(text) > max_len:
        split_pos = text.rfind("\n", 0, max_len)
        if split_pos == -1:
            split_pos = text.rfind(" ", 0, max_len)
        if split_pos == -1:
            split_pos = max_len
        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


def rich_text_from_string(value):
    """Build a list of Notion rich_text objects from a plain string."""
    if value is None or value == "":
        return []
    chunks = _split_text(str(value), MAX_RICH_TEXT_LEN)
    return [_plain(chunk) for chunk in chunks]


def paragraph_blocks_from_string(value):
    """Build one or more paragraph blocks from a multi-paragraph string."""
    if not value:
        return [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": []},
        }]
    blocks = []
    for para in value.split("\n\n"):
        para = para.rstrip()
        if not para:
            continue
        for chunk in _split_text(para, MAX_RICH_TEXT_LEN):
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [_plain(chunk)]},
            })
    return blocks or [{
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": []},
    }]


def quote_blocks_from_string(value, empty_placeholder):
    """Build quote blocks from a multi-paragraph string, or a single fallback."""
    if not value:
        return [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [_plain(empty_placeholder)]},
        }]
    blocks = []
    for para in value.split("\n\n"):
        para = para.rstrip()
        if not para:
            continue
        for chunk in _split_text(para, MAX_RICH_TEXT_LEN):
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": [_plain(chunk)]},
            })
    if not blocks:
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [_plain(empty_placeholder)]},
        })
    return blocks


# ---------------------------------------------------------------------------
# Finding validation and normalization
# ---------------------------------------------------------------------------


def validate_finding(finding, index):
    """
    Check required fields. Return a list of warning strings (empty if valid).
    Missing fields do not skip the finding — we emit a best-effort row and
    flag the title with [MALFORMED].
    """
    warnings = []

    # Fields that may legitimately be numeric zero or integer — check
    # for presence, not truthiness.
    numeric_required = {"target_line_start", "target_line_end"}

    for field in REQUIRED_FINDING_FIELDS:
        value = finding.get(field)
        if field in numeric_required:
            if not isinstance(value, int):
                warnings.append(
                    f"finding {index} ({finding.get('finding_id', '?')}): "
                    f"missing integer {field}"
                )
            continue
        if field not in finding or value in (None, ""):
            warnings.append(
                f"finding {index} ({finding.get('finding_id', '?')}): "
                f"missing {field}"
            )

    severity = (finding.get("severity") or "").lower()
    if severity and severity not in VALID_SEVERITIES:
        warnings.append(
            f"finding {index} ({finding.get('finding_id', '?')}): "
            f"severity '{severity}' not in {sorted(VALID_SEVERITIES)}"
        )

    source_tier = (finding.get("source_tier") or "").lower()
    if source_tier and source_tier not in VALID_SOURCE_TIERS:
        # tier_4 publishes to Notes / open questions only; approval gate
        # is in Notion. Unknown tiers still land as [MALFORMED] so
        # reviewers see them.
        warnings.append(
            f"finding {index} ({finding.get('finding_id', '?')}): "
            f"source_tier '{source_tier}' not in {sorted(VALID_SOURCE_TIERS)}"
        )

    action = (finding.get("action") or "").lower()
    if action and action not in VALID_ACTIONS:
        warnings.append(
            f"finding {index} ({finding.get('finding_id', '?')}): "
            f"action '{action}' not in {sorted(VALID_ACTIONS)}"
        )

    category = finding.get("category") or ""
    if category and category not in VALID_CATEGORIES:
        warnings.append(
            f"finding {index} ({finding.get('finding_id', '?')}): "
            f"category '{category}' not in {sorted(VALID_CATEGORIES)}"
        )

    return warnings


def _title_case(value):
    return value[:1].upper() + value[1:].lower() if value else value


def _source_tier_label(tier):
    """tier_1 → 'Tier 1'. Returns None for missing / invalid inputs."""
    if not tier:
        return None
    tier = tier.strip().lower()
    if tier.startswith("tier_"):
        suffix = tier[5:]
        return f"Tier {suffix}"
    return None


def _strip_line_suffix(path):
    """Remove a trailing '(line N)' or ':N' suffix from a file path."""
    if not path:
        return path
    path = re.sub(r"\s*\(line\s+\d+\)\s*$", "", path)
    path = re.sub(r":\d+\s*$", "", path)
    return path.strip("`").strip()


def _set_rich_text_property(properties, column, value):
    """
    Assign a (possibly long, possibly markdown-bearing) string to a Notion
    rich_text property. Escapes markdown-significant chars with placeholders
    so the round-trip back through `notion-fetch` at integrate time keeps
    them intact. No hard truncation — the Notion MCP can handle multi-chunk
    rich_text behind the string interface, so leave capacity handling to it
    rather than pre-emptively slicing at 2000 chars (the old design here
    silently truncated canon snippets and broke integrate-time matching).
    """
    if value is None or value == "":
        return
    properties[column] = escape_markdown_for_notion_property(str(value))


# ---------------------------------------------------------------------------
# Page construction
# ---------------------------------------------------------------------------


def build_page(finding, is_malformed):
    """Build a single Notion page descriptor for one finding."""
    title = finding.get("title", "Untitled finding")
    # Phase 2: title already carries the `R{n}:` prefix — do not
    # re-wrap with `[R{n}]`. Malformed rows get the [MALFORMED] tag so
    # reviewers can filter them out.
    name = f"[MALFORMED] {title}" if is_malformed else title

    properties = {
        "Name": name,
        # New rows always land in Pending Review. Humans transition them
        # to Approved / Rejected / Integrated during triage — the
        # publisher never updates Status after creation (publish_to_notion
        # only creates rows, it does not update existing ones).
        # `Needs Restage` is written by kb-integrate when canon drifts.
        "Status": DEFAULT_STATUS,
    }

    # --- Triage-critical columns (visible in the default view) -------
    entity = finding.get("entity")
    if entity:
        # Entity is a SELECT column; options self-populate on write.
        properties["Entity"] = entity

    # Section is the exact canon heading the finding will land under
    # (e.g. "Weaknesses / watch-outs", "Where they show up",
    # "Notes / open questions"). Rich_text rather than SELECT because
    # the section set varies per group's canon template — a SELECT
    # would have to carry the union across every group DB provisioned
    # from the shared SCHEMA_DDL.
    section = finding.get("section")
    if section:
        _set_rich_text_property(properties, "Section", section)

    source_tier_label = _source_tier_label(finding.get("source_tier"))
    if source_tier_label:
        properties["Source Tier"] = source_tier_label

    # Action drives what kb-integrate will do with this row:
    #   Append  → insert proposed_text after target_line_end
    #   Replace → swap canon[target_line_start..target_line_end] for proposed_text
    action = (finding.get("action") or "").lower()
    if action == "append":
        properties["Action"] = "Append"
    elif action == "replace":
        properties["Action"] = "Replace"

    # Closes Open Question flags replace-type findings that would
    # resolve an existing Notes / open questions bullet. Rejecting
    # such a finding leaves canon with a known-stale open question —
    # surface it prominently so reviewers weigh the cost of rejection.
    closes_open_question = finding.get("closes_open_question")
    if closes_open_question and closes_open_question.lower() != "null":
        _set_rich_text_property(
            properties, "Closes Open Question", closes_open_question
        )

    # Rich_text properties carrying prose / canon snippets go through
    # _set_rich_text_property → markdown escape + no pre-emptive slice.
    _set_rich_text_property(
        properties, "Proposed Updated Text", finding.get("proposed_text")
    )
    # Final Updated Text is NEVER written by the publisher — reviewers
    # type partial-approval tweaks there in Notion; kb-integrate reads
    # it at apply time (prefers Final Updated Text over Proposed Updated
    # Text when non-empty). See output-format.md "Final Updated Text
    # invariant."

    # --- Provenance / debug columns (hidden in the default view) -----
    # For append actions with no current_text, write a sentinel so the
    # column isn't blank in Notion — makes it obvious to reviewers that
    # the finding is net-new content rather than a replacement.
    current_text_value = finding.get("current_text")
    if not current_text_value and action == "append":
        current_text_value = "(addition to canon — no existing text replaced)"
    _set_rich_text_property(
        properties, "Current Text", current_text_value
    )
    _set_rich_text_property(
        properties, "Rationale", finding.get("rationale")
    )

    severity = finding.get("severity")
    if severity and severity.lower() in VALID_SEVERITIES:
        properties["Severity"] = _title_case(severity)

    category = finding.get("category")
    if category and category in VALID_CATEGORIES:
        properties["Category"] = category

    run_date = finding.get("run_date")
    if run_date:
        properties["date:Date Added:start"] = run_date

    source_file = _strip_line_suffix(finding.get("source_file"))
    if source_file:
        properties["Source file"] = source_file

    target_file = _strip_line_suffix(finding.get("target_file"))
    if target_file:
        properties["Target file"] = target_file

    source_line = finding.get("source_line")
    if isinstance(source_line, int):
        properties["Source Line"] = source_line

    tls = finding.get("target_line_start")
    if isinstance(tls, int):
        properties["Target Line Start"] = tls
    tle = finding.get("target_line_end")
    if isinstance(tle, int):
        properties["Target Line End"] = tle

    content = _render_body_markdown(finding, source_file, target_file)

    return {
        "properties": properties,
        "content": content,
    }


def _render_body_markdown(finding, source_file, target_file):
    """Build the detail-page markdown body for a single finding.

    The body is sent as markdown to the Notion MCP, which converts it
    into Notion blocks (paragraphs, code blocks, etc.). Body content is
    NOT routed through the rich_text property escape path — Notion
    preserves fenced code blocks verbatim, so canon snippets with
    `**bold**` markers render faithfully inside the Landing preview.
    """
    finding_id = finding.get("finding_id", "?")
    severity = _title_case(finding.get("severity") or "unknown")
    source_tier_label = _source_tier_label(finding.get("source_tier")) or "unknown"
    entity = finding.get("entity") or "—"
    section = finding.get("section") or "—"
    group = finding.get("group") or "unknown"
    codeowner = finding.get("codeowner") or "unknown"
    run_date = finding.get("run_date") or "unknown"

    source_line = finding.get("source_line")
    source_suffix = f" line {source_line}" if isinstance(source_line, int) else ""

    tls = finding.get("target_line_start")
    tle = finding.get("target_line_end")
    if isinstance(tls, int) and isinstance(tle, int):
        line_range = f" line {tls}" if tls == tle else f" lines {tls}-{tle}"
    elif isinstance(tls, int):
        line_range = f" line {tls}"
    else:
        line_range = ""

    canon_preview = finding.get("canon_context_preview") or ""
    current_text = finding.get("current_text") or ""
    proposed_text = finding.get("proposed_text") or ""
    rationale = finding.get("rationale") or "_(no rationale provided)_"
    suggested_action = (
        finding.get("suggested_action") or "_(no suggested action)_"
    )
    action = (finding.get("action") or "").lower()
    category = finding.get("category") or "unknown"

    current_empty_placeholder = (
        "_(no current text — append action)_"
        if action == "append"
        else "_(no current text — net-new information)_"
    )
    current_block = current_text if current_text else current_empty_placeholder
    proposed_empty_placeholder = (
        "(no textual replacement — human author needed or append action)"
    )

    lines = [
        f"**Finding ID:** {finding_id} · **Severity:** {severity} · "
        f"**Source Tier:** {source_tier_label}",
        f"**Entity:** {entity} · **Section:** {section} · "
        f"**Action:** {_title_case(action) if action else '—'}",
        f"**Group:** {group} · **Codeowner:** {codeowner} · "
        f"**Run date:** {run_date}",
        "",
        "---",
        "",
        "## Landing preview",
        "",
        f"_`{target_file or 'unknown'}`{line_range}_",
        "",
    ]
    if canon_preview:
        lines.extend([
            "```",
            canon_preview,
            "```",
            "",
        ])
    else:
        lines.append(
            "_(canon context preview not available — see Current Text below)_"
        )
        lines.append("")
    lines.extend([
        "**Proposed replacement:**",
        "",
        "```",
        proposed_text or proposed_empty_placeholder,
        "```",
        "",
        "_Edit the `Final Updated Text` column above to tweak before approval._",
        "",
        "---",
        "",
        "## Current text (preview)",
        "",
        f"> {current_block}",
        "",
        f"_Source: `{source_file or 'unknown'}`{source_suffix}_",
        "",
        "## Rationale",
        "",
        rationale,
        "",
        "## Suggested action",
        "",
        suggested_action,
        "",
        "---",
        "",
        "## Triage checklist",
        "",
        "- [ ] Verify current_text matches source at cited line",
        "- [ ] Review proposed_text for accuracy and style fit",
        "- [ ] Tweak via the `Final Updated Text` column if partial approval",
        "- [ ] Apply change to target_file or reject",
        "- [ ] Update Status column when done",
        "",
        "## Provenance",
        "",
        f"- **Source file:** `{source_file or 'unknown'}`{source_suffix}",
        f"- **Target file:** `{target_file or 'unknown'}`{line_range}",
        f"- **Category:** {category}",
        "- **Generated by:** kb-update",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Transform kb-update findings into a notion-create-pages payload."
    )
    parser.add_argument(
        "--group",
        help="Group slug (e.g. competitive). Used to resolve the per-group "
        "data source ID when --parent-data-source isn't set, and to tag "
        "findings that don't already have a group field.",
    )
    parser.add_argument("--run-date", help="Run date, YYYY-MM-DD")
    parser.add_argument(
        "--parent-data-source",
        help="Notion data source ID. Overrides env var and config.yaml.",
    )
    parser.add_argument(
        "--check-schema",
        action="store_true",
        help="Print the expected schema for the orchestrator to verify.",
    )
    parser.add_argument(
        "--build-select-ddl",
        metavar="COLUMN",
        help="Emit a color-less, union-safe `ALTER COLUMN SET SELECT(...)` "
        "DDL for reactive repair of a SELECT column. Pair with "
        "--existing (the column's current options from a Notion fetch) "
        "and --values (the current run's distinct values).",
    )
    parser.add_argument(
        "--existing",
        default="",
        help="Comma-separated existing option names for --build-select-ddl. "
        "Fetch from Notion before calling.",
    )
    parser.add_argument(
        "--values",
        default="",
        help="Comma-separated run-value option names for --build-select-ddl.",
    )
    args = parser.parse_args()

    if args.build_select_ddl:
        return cli_build_select_ddl(args.build_select_ddl, args.existing, args.values)

    data_source_id = resolve_data_source_id(args.parent_data_source, args.group)

    if args.check_schema:
        return check_schema(data_source_id, args.group)

    try:
        findings = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: stdin is not valid JSON: {exc}")

    # synthesize_findings.py emits {findings, stats, warnings} — unwrap so
    # the documented `synth | publish` pipe works end-to-end without a
    # manual `jq .findings` step. Bare-array input still accepted for
    # backward compat.
    if isinstance(findings, dict) and isinstance(findings.get("findings"), list):
        print(
            "NOTICE: stdin is a {findings, stats, warnings} object; "
            "unwrapping .findings",
            file=sys.stderr,
        )
        findings = findings["findings"]

    if not isinstance(findings, list):
        sys.exit("ERROR: stdin must be a JSON array of findings.")

    # Codeowner is still attached to the finding for page-body rendering
    # (it shows up in the "**Group:** <slug> · **Codeowner:** <owner>" line
    # of the detail page), but it is no longer a column property in the
    # per-group database schema.
    codeowner_from_config = resolve_codeowner(args.group)

    pages = []
    total_warnings = 0
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            print(f"WARNING: finding {index} is not an object, skipping.", file=sys.stderr)
            continue

        if args.group and not finding.get("group"):
            finding["group"] = args.group
        if args.run_date and not finding.get("run_date"):
            finding["run_date"] = args.run_date
        if codeowner_from_config and not finding.get("codeowner"):
            finding["codeowner"] = codeowner_from_config

        warnings = validate_finding(finding, index)
        if warnings:
            total_warnings += len(warnings)
            for w in warnings:
                print(f"WARNING: {w}", file=sys.stderr)

        pages.append(build_page(finding, is_malformed=bool(warnings)))

    batches = [pages[i : i + BATCH_SIZE] for i in range(0, len(pages), BATCH_SIZE)]

    payload = {
        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
        "pages": pages,
        "batches": [
            {
                "parent": {"type": "data_source_id", "data_source_id": data_source_id},
                "pages": batch,
            }
            for batch in batches
        ],
        "stats": {
            "group": args.group,
            "data_source_id": data_source_id,
            "total_findings": len(findings),
            "pages_built": len(pages),
            "batch_count": len(batches),
            "warnings": total_warnings,
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
