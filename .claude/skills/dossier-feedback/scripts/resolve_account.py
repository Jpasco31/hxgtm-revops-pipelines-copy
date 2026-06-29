#!/usr/bin/env python3
"""
Resolve an account name (or Notion URL) to {name, slug, page_id, notion_url}
using the dossier batch-state file as the primary source of truth.

Resolution order:
  1. --notion-url <url>  → strip hyphens to get page_id; slug derived from
     the user-supplied --name if any, else left null (the per-account
     subagent will derive a slug from the page title).
  2. Match the --name against accounts in --state-file (slug match, then
     exact human name, then case-insensitive name).
  3. Otherwise: print an empty-result JSON {"resolved": false, ...} and
     exit 1 — the orchestrator handles the notion-search fallback.

The notion-search fallback is intentionally NOT performed by this script
because notion-search is an MCP tool, not an HTTP endpoint we can call
from a plain Python helper. The orchestrator owns that fallback.

Usage:
  python3 resolve_account.py --name "Zurich North America" \
      --state-file outputs/generate-dossier-batch-parallel/_batch-state.json

  python3 resolve_account.py --notion-url https://www.notion.so/.../<page_id>

Output (stdout, on success):
  {"resolved": true,
   "name": "Zurich North America",
   "slug": "zurich-north-america",
   "page_id": "abc123def456...",
   "notion_url": "https://www.notion.so/...",
   "source": "state-file" | "url-bypass"}

Output (stdout, on miss):
  {"resolved": false,
   "name": "<input name or null>",
   "reason": "not-in-state-file" | "state-file-missing" | "no-input"}
  + exit code 1
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional


PAGE_ID_RE = re.compile(r"([0-9a-f]{32})", re.IGNORECASE)
PAGE_ID_HYPHENATED_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def page_id_from_url(url: str) -> Optional[str]:
    """Extract a 32-char hex page id from any Notion URL form."""
    m = PAGE_ID_HYPHENATED_RE.search(url)
    if m:
        return m.group(1).replace("-", "").lower()
    m = PAGE_ID_RE.search(url)
    if m:
        return m.group(1).lower()
    return None


def load_state(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def find_in_state(state: dict, name: str) -> Optional[dict]:
    accounts = state.get("accounts") or {}
    if not isinstance(accounts, dict):
        return None

    target_slug = slugify(name)
    target_lower = name.lower().strip()

    if target_slug in accounts:
        rec = accounts[target_slug]
        return {"slug": target_slug, **(rec or {})}

    for slug, rec in accounts.items():
        if not isinstance(rec, dict):
            continue
        rec_name = (rec.get("name") or "").strip()
        if rec_name == name.strip():
            return {"slug": slug, **rec}

    for slug, rec in accounts.items():
        if not isinstance(rec, dict):
            continue
        rec_name = (rec.get("name") or "").strip().lower()
        if rec_name == target_lower:
            return {"slug": slug, **rec}

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="Account display name")
    parser.add_argument("--notion-url", help="Notion page URL (overrides --name)")
    parser.add_argument(
        "--state-file",
        default="outputs/generate-dossier-batch-parallel/_batch-state.json",
        help="Path to _batch-state.json",
    )
    args = parser.parse_args()

    if args.notion_url:
        page_id = page_id_from_url(args.notion_url)
        if not page_id:
            print(
                json.dumps(
                    {
                        "resolved": False,
                        "name": args.name,
                        "reason": "url-missing-page-id",
                    }
                )
            )
            return 1
        slug = slugify(args.name) if args.name else None
        out = {
            "resolved": True,
            "name": args.name or "(URL bypass)",
            "slug": slug,
            "page_id": page_id,
            "notion_url": args.notion_url,
            "source": "url-bypass",
        }
        print(json.dumps(out))
        return 0

    if not args.name:
        print(json.dumps({"resolved": False, "name": None, "reason": "no-input"}))
        return 1

    state_path = Path(args.state_file)
    state = load_state(state_path)
    if state is None:
        print(
            json.dumps(
                {
                    "resolved": False,
                    "name": args.name,
                    "reason": "state-file-missing",
                }
            )
        )
        return 1

    rec = find_in_state(state, args.name)
    if rec is None:
        print(
            json.dumps(
                {
                    "resolved": False,
                    "name": args.name,
                    "reason": "not-in-state-file",
                }
            )
        )
        return 1

    notion_url = rec.get("notion_url")
    if not notion_url:
        print(
            json.dumps(
                {
                    "resolved": False,
                    "name": args.name,
                    "reason": "account-has-no-notion-url",
                }
            )
        )
        return 1

    page_id = page_id_from_url(notion_url)
    if not page_id:
        print(
            json.dumps(
                {
                    "resolved": False,
                    "name": args.name,
                    "reason": "notion-url-unparseable",
                }
            )
        )
        return 1

    out = {
        "resolved": True,
        "name": rec.get("name") or args.name,
        "slug": rec.get("slug"),
        "page_id": page_id,
        "notion_url": notion_url,
        "source": "state-file",
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
