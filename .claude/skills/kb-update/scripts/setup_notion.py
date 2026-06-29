#!/usr/bin/env python3
"""
setup_notion.py

First-run provisioner for kb-update's Notion database structure. Reads
.claude/skills/kb-update/config.yaml and emits JSON instructions that Claude
consumes to create the full Notion layout:

  KB - Updates Review                        (landing page, workspace-level)
  ├── KB - Competitive Intelligence          (database, per group)
  ├── KB - Product & Segment Messaging
  ├── …
  └── KB - RFP Responses

The script itself does NOT call the Notion API — it has no auth. Claude
reads the emitted JSON and calls the `notion-create-pages` and
`notion-create-database` MCP tools to execute the plan, then edits
config.yaml to write back the resulting data source IDs.

Two modes:

    setup_notion.py --status
        JSON: which groups are already provisioned, which are missing.
        Exit 0 if all provisioned, 1 if any are missing. Use this as a
        pre-flight guard in SKILL.md.

    setup_notion.py --plan
        JSON: full provisioning plan — landing page spec + per-group
        database specs (title, description, schema DDL, group slug).
        Claude executes each entry against the Notion MCP tools.

Only groups whose `notion_data_source_id` is missing (or empty) are
included in the plan. Running --plan after a partial provisioning only
creates the missing databases; existing ones are left alone.
"""

import argparse
import json
import re
import sys
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"

# Landing-page template — reference only. The user must create the
# landing page manually in Notion at their chosen location (teamspace,
# team-visible root, etc.) because the Notion MCP can only create pages
# in the caller's Private workspace section. setup_notion.py never
# creates this page; it only emits the template so the SKILL.md
# guardrail banner and README instructions stay in sync with the
# expected title/icon/body copy.
LANDING_PAGE_TEMPLATE = {
    "title": "KB - Updates Review",
    "icon": "📚",
    "body_markdown": (
        "kb-update publishes per-finding rows into the group-specific "
        "databases below. Each database corresponds to one group from "
        "`.claude/skills/kb-update/config.yaml`. Find your group's database, filter "
        "by **Date Added = today** to see the latest uploaded source, then "
        "triage each row.\n"
        "\n"
        "## Workflow\n"
        "\n"
        "1. Find your group below (11 total)\n"
        "2. Open its database\n"
        "3. Filter by **Date Added = today** to see the latest uploaded source\n"
        "4. For each row, decide:\n"
        "   - **Approved** — apply the Proposed Updated Text to the "
        "Target file in canon, then set Status to `Integrated`\n"
        "   - **Rejected** — set Status to `Rejected`, comment with your "
        "reason\n"
        "   - **Defer** — leave Status as `Pending Review` until you're "
        "ready to triage\n"
        "5. Tag yourself in the **Reviewer** column so teammates know "
        "who handled it\n"
        "\n"
        "## Status lifecycle\n"
        "\n"
        "- **Pending Review** — new row, awaiting triage (default)\n"
        "- **Approved** — triage decision made; waiting on canon edit\n"
        "- **Integrated** — canon updated, finding resolved\n"
        "- **Rejected** — finding dismissed (raw source invalid, stale, "
        "or out of scope)\n"
        "\n"
        "---\n"
        "\n"
        "## Groups\n"
        "\n"
        "Each of the databases below corresponds to one group in "
        "`.claude/skills/kb-update/config.yaml`. kb-update populates them with "
        "findings when you upload a raw source file and run "
        "`/kb-update --group <slug>`.\n"
    ),
}

# Schema DDL template — every per-group database shares this shape.
# Status is a SELECT (not a Notion STATUS) so its options are
# configurable via DDL, which makes first-run setup fully automated.
#
# Column order = field-panel order reviewers see when they open a row,
# and it mirrors VISIBLE_COLUMNS (the default view) followed by
# HIDDEN_COLUMNS. Visible-first keeps the row detail panel aligned with
# what reviewers see in the table view.
#
# Entity is a SELECT column whose options are created on demand at
# write time (one per distinct canon filename stem). Seeds with no
# options; reactive repair at publish time (publish.md §1) unions
# current-run values with live options.
#
# Review Bucket is a FORMULA derived from Status — it collapses
# `Pending Review` + `Needs Restage` into a single "Needs Decision"
# bucket and passes the other statuses through unchanged. It drives
# `group_by` in the default view so reviewers see one stack per
# decision state (Needs Decision / Approved / Rejected / Integrated)
# instead of one stack per entity.
SCHEMA_DDL = (
    "CREATE TABLE ("
    # Visible by default (12) — order matches VISIBLE_COLUMNS
    '"Name" TITLE, '
    "\"Status\" SELECT('Pending Review':gray, 'Approved':blue, "
    "'Needs Restage':orange, 'Rejected':red, 'Integrated':green), "
    '"Reviewer" PEOPLE, '
    '"Current Text" RICH_TEXT, '
    '"Proposed Updated Text" RICH_TEXT, '
    '"Final Updated Text" RICH_TEXT, '
    '"Rationale" RICH_TEXT, '
    '"Entity" SELECT(), '
    "\"Source Tier\" SELECT('Tier 1':blue, 'Tier 2':purple, "
    "'Tier 3':yellow, 'Tier 4':gray, 'Tier 5':red), "
    '"Section" RICH_TEXT, '
    '"Closes Open Question" RICH_TEXT, '
    '"Source file" RICH_TEXT, '
    # Hidden by default (9) — order matches HIDDEN_COLUMNS
    '"Target file" RICH_TEXT, '
    "\"Action\" SELECT('Append':green, 'Replace':orange), "
    '"Review Bucket" FORMULA('
    'if(prop("Status") == "Pending Review" or '
    'prop("Status") == "Needs Restage", '
    '"Needs Decision", prop("Status"))), '
    "\"Category\" SELECT('raw-canon-conflict':red, 'freshness':yellow, "
    "'cross-reference':blue, 'consistency':orange, 'template':purple, "
    "'coverage-gap':gray), "
    "\"Severity\" SELECT('High':red, 'Medium':yellow, 'Low':gray), "
    '"Date Added" DATE, '
    '"Source Line" NUMBER, '
    '"Target Line Start" NUMBER, '
    '"Target Line End" NUMBER'
    ")"
)


# Columns visible by default in the database's default view. Reviewers
# see only the decision-relevant fields; the rest are one-click away
# on the row detail panel. Ordering is load-bearing — setup_notion.py
# forwards this list verbatim to `notion-update-view`.
VISIBLE_COLUMNS = [
    "Name",
    "Status",
    "Reviewer",
    "Current Text",
    "Proposed Updated Text",
    "Final Updated Text",
    "Rationale",
    "Entity",
    "Source Tier",
    "Section",
    "Closes Open Question",
    "Source file",
]

# Columns hidden by default. `Target file` is kept for `/kb-integrate`
# but stays off the triage surface. `Review Bucket` is the group_by
# column — Notion renders it as the group header so hiding it from the
# table avoids a redundant column on every row.
HIDDEN_COLUMNS = [
    "Target file",
    "Action",
    "Review Bucket",
    "Category",
    "Severity",
    "Date Added",
    "Source Line",
    "Target Line Start",
    "Target Line End",
]


def default_view_config():
    """
    Return the configuration to apply to the database's built-in
    default view. No separate view is created — Notion auto-creates a
    default view on `notion-create-database`, and the pipeline calls
    `notion-update-view` on it with this payload to set column
    visibility, filter, grouping, and sort.

    Reviewers land on one surface: rows awaiting decision (Pending
    Review + Needs Restage), grouped by Review Bucket so both statuses
    stack under a single "Needs Decision" header, newest first.
    Decided rows (Approved / Rejected / Integrated) are reachable via
    ad-hoc Notion filter on the same view — each lands in its own
    Review Bucket group.
    """
    return {
        "filter": "Status = 'Pending Review' OR Status = 'Needs Restage'",
        "group_by": "Review Bucket",
        "sort": [{"column": "Date Added", "direction": "descending"}],
        "visible_columns": VISIBLE_COLUMNS,
        "hidden_columns": HIDDEN_COLUMNS,
    }


# ---------------------------------------------------------------------------
# config.yaml reading (minimal, no PyYAML)
# ---------------------------------------------------------------------------


def read_groups():
    """
    Return [{slug, label, codeowner, notion_data_source_id|None}, ...] from
    config.yaml. Order matches the order groups appear in the file, so the
    setup plan and READMEs stay consistent.
    """
    if not CONFIG_PATH.exists():
        sys.exit(f"ERROR: {CONFIG_PATH} not found.")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    groups = []
    in_groups = False
    current = None
    current_indent = None
    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))

        if not in_groups:
            if stripped == "groups:":
                in_groups = True
            continue

        # Top-level key outside `groups:` ends the section.
        if indent == 0 and stripped.endswith(":"):
            break

        # A group header looks like "  <slug>:" at indent 2.
        if indent == 2 and stripped.endswith(":"):
            if current is not None:
                groups.append(current)
            slug = stripped[:-1].strip()
            current = {
                "slug": slug,
                "label": None,
                "codeowner": None,
                "notion_data_source_id": None,
            }
            current_indent = indent
            continue

        if current is None or ":" not in stripped:
            continue

        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key == "label":
            current["label"] = value
        elif key == "codeowner":
            current["codeowner"] = value
        elif key == "notion_data_source_id":
            current["notion_data_source_id"] = value or None

    if current is not None:
        groups.append(current)

    return groups


# ---------------------------------------------------------------------------
# Plan construction
# ---------------------------------------------------------------------------


def database_spec_for(group):
    """Build a single-database setup descriptor for one group."""
    label = group["label"] or group["slug"]
    codeowner = group["codeowner"] or "unknown"
    return {
        "group": group["slug"],
        "title": f"KB - {label}",
        "description": (
            f"kb-update findings for the {group['slug']} group. "
            f"Codeowner: {codeowner}."
        ),
        "schema": SCHEMA_DDL,
        "default_view_config": default_view_config(),
        "config_yaml_field": f"groups.{group['slug']}.notion_data_source_id",
    }


def status(groups):
    provisioned = [g["slug"] for g in groups if g["notion_data_source_id"]]
    missing = [g["slug"] for g in groups if not g["notion_data_source_id"]]
    return {
        "all_provisioned": len(missing) == 0,
        "total_groups": len(groups),
        "provisioned_groups": provisioned,
        "missing_groups": missing,
    }


def plan(groups, landing_page_id=None, force_group=None):
    """
    Build the full setup plan.

    The landing page is NEVER created by this script or by the SKILL.md
    flow — the Notion MCP can only create pages in the caller's Private
    workspace section, which is almost never where the user wants the
    landing page to live. The user must create the landing page
    manually in Notion at their chosen teamspace / parent page, then
    re-run `/kb-update --notion-setup` which discovers it via
    notion-search and creates the per-group databases as children.

    Behavior:
    - If `landing_page_id` is None → `requires_landing_page_creation`
      is True, `databases` is empty (nothing to create until we have a
      parent), and `landing_page_template` carries the expected title /
      icon / body copy for the user's reference.
    - If `landing_page_id` is set and `force_group` is None → plan
      includes every group with a blank `notion_data_source_id`.
    - If `force_group` is set → plan targets exactly that group
      regardless of whether it already has a `notion_data_source_id`.
      Used by the publish-time reactive-repair path, where the cached
      ID is known-stale.
    """
    if force_group is not None:
        targets = [g for g in groups if g["slug"] == force_group]
        if not targets:
            raise ValueError(
                f"--group '{force_group}' not found in config.yaml"
            )
        missing = targets
    else:
        missing = [g for g in groups if not g["notion_data_source_id"]]
    needs_landing_page = landing_page_id is None
    databases = [] if needs_landing_page else [database_spec_for(g) for g in missing]
    return {
        "config_path": str(CONFIG_PATH),
        "requires_landing_page_creation": needs_landing_page,
        "landing_page_template": LANDING_PAGE_TEMPLATE,
        "landing_page_id": landing_page_id,
        "databases": databases,
        "stats": {
            "total_groups": len(groups),
            "missing_groups": len(missing),
            "databases_to_create": len(databases),
            "landing_page_needed": needs_landing_page,
        },
        "instructions": (
            [
                (
                    "1. HALT. The landing page does not exist yet in "
                    "Notion. This script will NOT create it — the Notion "
                    "MCP can only create pages in the caller's Private "
                    "workspace, which is almost never the right location. "
                    "The user must create the page manually."
                ),
                (
                    "2. Ask the user to create a new page in Notion titled "
                    "exactly 'KB - Updates Review' at the teamspace "
                    "or parent of their choice. The landing_page_template "
                    "field contains the expected title, icon, and body "
                    "copy the user can paste in."
                ),
                (
                    "3. After the user has created the page, re-run "
                    "`/kb-update --notion-setup`. Step 1a will discover it "
                    "via notion-search, call this script again with "
                    "`--landing-page-id <uuid>`, and this plan will then "
                    "contain the create-database specs."
                ),
            ]
            if needs_landing_page
            else [
                (
                    "1. For each entry in databases, call "
                    "notion-create-database with parent={page_id: "
                    "<landing_page_id>}, title, description, and schema "
                    "from the entry. Capture the returned data source ID "
                    "(the UUID in <data-source "
                    "url=\"collection://UUID\">)."
                ),
                (
                    "2. For each captured data source ID, configure "
                    "the database's built-in default view (auto-created "
                    "by notion-create-database — no separate view) by "
                    "calling notion-update-view on it with the entry's "
                    "`default_view_config` payload. Pass filter, "
                    "group_by, sort, visible_columns, and hidden_columns "
                    "verbatim so reviewers land on the trimmed surface."
                ),
                (
                    "3. For each captured data source ID, edit "
                    ".claude/skills/kb-update/config.yaml and set the group's "
                    "`notion_data_source_id` field to the UUID. Preserve "
                    "existing formatting and quotes."
                ),
                (
                    "4. After all writes, run "
                    "`python3 .claude/skills/kb-update/scripts/setup_notion.py "
                    "--status` to verify every group reports "
                    "all_provisioned=true."
                ),
            ]
        ),
    }


# ---------------------------------------------------------------------------
# View migration (retro-fit existing DBs to the current schema + view)
# ---------------------------------------------------------------------------


# DDL fragment for the Review Bucket formula column. Kept in one place
# so the migration and the full SCHEMA_DDL stay in lock-step.
REVIEW_BUCKET_ALTER_DDL = (
    'ALTER TABLE ADD COLUMN "Review Bucket" FORMULA('
    'if(prop("Status") == "Pending Review" or '
    'prop("Status") == "Needs Restage", '
    '"Needs Decision", prop("Status")))'
)


def migrate_plan(groups):
    """
    Build a migration plan for every group that already has a
    `notion_data_source_id`. Emits two MCP calls per DB:

      1. `notion-update-data-source` with an ALTER TABLE payload that
         adds the `Review Bucket` formula column. Idempotent on the
         Notion side only at the caller's discretion — Claude must
         first read the live schema via `notion-fetch` and skip the
         ALTER if the column already exists.
      2. `notion-update-view` on the built-in default view with the
         current `default_view_config()` — column reorder, Target file
         hidden, group_by = Review Bucket.

    Groups with a blank `notion_data_source_id` are skipped silently;
    they're picked up by --plan instead.
    """
    targets = [g for g in groups if g["notion_data_source_id"]]
    entries = [
        {
            "group": g["slug"],
            "label": g["label"],
            "notion_data_source_id": g["notion_data_source_id"],
            "alter_ddl": REVIEW_BUCKET_ALTER_DDL,
            "default_view_config": default_view_config(),
        }
        for g in targets
    ]
    return {
        "config_path": str(CONFIG_PATH),
        "mode": "migrate-views",
        "databases": entries,
        "stats": {
            "total_groups": len(groups),
            "migrating": len(entries),
            "skipped_unprovisioned": len(groups) - len(entries),
        },
        "instructions": [
            (
                "1. For each entry in databases, call `notion-fetch` on "
                "the data source to read the live column list. If a "
                "column literally named 'Review Bucket' already exists, "
                "skip step 2 for this entry (idempotent re-run)."
            ),
            (
                "2. Otherwise call `notion-update-data-source "
                "<notion_data_source_id>` with the entry's `alter_ddl` "
                "payload to add the Review Bucket formula column."
            ),
            (
                "3. For every entry (even ones that skipped step 2), "
                "call `notion-update-view` on the default view of the "
                "data source with the entry's `default_view_config`. "
                "Pass filter, group_by, sort, visible_columns, and "
                "hidden_columns verbatim. This is what actually "
                "reorders the columns and flips group_by from Entity "
                "to Review Bucket."
            ),
            (
                "4. Spot-check one migrated database in Notion: the "
                "triage view should show a single 'Needs Decision' "
                "group (Pending Review + Needs Restage merged), "
                "'Target file' should be hidden, and the visible "
                "columns should appear in the order declared by "
                "VISIBLE_COLUMNS."
            ),
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Emit a Notion setup plan (or provisioning status) for kb-update. "
            "The script does not call Notion directly — Claude reads the "
            "JSON output and executes the MCP calls."
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--status",
        action="store_true",
        help="Report which groups are provisioned. Exit 0 if all are, "
        "exit 1 if any group is missing notion_data_source_id.",
    )
    mode.add_argument(
        "--plan",
        action="store_true",
        help="Emit a full provisioning plan for all missing groups.",
    )
    mode.add_argument(
        "--migrate-views",
        action="store_true",
        help="Emit a migration plan for already-provisioned groups: "
        "ADD COLUMN 'Review Bucket' (idempotent — caller must check "
        "live schema first) and reapply default_view_config() to each "
        "DB's built-in default view. Safe to re-run.",
    )
    parser.add_argument(
        "--landing-page-id",
        help="Existing landing page ID. Skip landing-page creation in "
        "--plan output and nest new databases under this page. Use "
        "when re-running setup after adding a new group.",
    )
    parser.add_argument(
        "--group",
        help="Force single-group planning. Emit a create-database spec "
        "for this group regardless of whether config.yaml already has "
        "a `notion_data_source_id`. Used by publish-time reactive "
        "repair where the cached ID is known-stale. Requires --plan "
        "and --landing-page-id.",
    )
    args = parser.parse_args()

    groups = read_groups()
    if not groups:
        sys.exit("ERROR: no groups found in config.yaml.")

    if args.status:
        result = status(groups)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["all_provisioned"] else 1

    if args.plan:
        if args.group and not args.landing_page_id:
            sys.exit(
                "ERROR: --group requires --landing-page-id (single-group "
                "planning only makes sense under an existing landing page)."
            )
        try:
            result = plan(
                groups,
                landing_page_id=args.landing_page_id,
                force_group=args.group,
            )
        except ValueError as exc:
            sys.exit(f"ERROR: {exc}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.migrate_views:
        result = migrate_plan(groups)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0


if __name__ == "__main__":
    sys.exit(main())
