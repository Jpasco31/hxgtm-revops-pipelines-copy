#!/usr/bin/env python3
"""
Read _batch-state.json and emit a JSON array of accounts that have a
non-null notion_url. Used by the dossier-feedback skill in sweep mode.

Output shape:
  [
    {"name": "Zurich North America",
     "slug": "zurich-north-america",
     "page_id": "abc...",
     "notion_url": "https://www.notion.so/..."},
    ...
  ]

Accounts without a notion_url are silently dropped — they have no Notion
page to comment on, so there's nothing for the per-account subagent to do.

Usage:
  python3 list_accounts.py [path/to/_batch-state.json]
"""

import json
import re
import sys
from pathlib import Path

PAGE_ID_HYPHENATED_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)
PAGE_ID_RE = re.compile(r"([0-9a-f]{32})", re.IGNORECASE)


def page_id_from_url(url: str):
    m = PAGE_ID_HYPHENATED_RE.search(url)
    if m:
        return m.group(1).replace("-", "").lower()
    m = PAGE_ID_RE.search(url)
    if m:
        return m.group(1).lower()
    return None


def main() -> int:
    if len(sys.argv) > 2:
        print("usage: list_accounts.py [state-file]", file=sys.stderr)
        return 2

    path = Path(
        sys.argv[1]
        if len(sys.argv) == 2
        else "outputs/generate-dossier-batch-parallel/_batch-state.json"
    )

    if not path.exists():
        print(f"state file not found: {path}", file=sys.stderr)
        return 1

    try:
        state = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"failed to read state file: {e}", file=sys.stderr)
        return 1

    accounts = state.get("accounts") or {}
    if not isinstance(accounts, dict):
        print("state file has no accounts dict", file=sys.stderr)
        return 1

    out = []
    for slug, rec in accounts.items():
        if not isinstance(rec, dict):
            continue
        notion_url = rec.get("notion_url")
        if not notion_url:
            continue
        page_id = page_id_from_url(notion_url)
        if not page_id:
            continue
        out.append(
            {
                "name": rec.get("name") or slug,
                "slug": slug,
                "page_id": page_id,
                "notion_url": notion_url,
            }
        )

    out.sort(key=lambda r: r["name"].lower())
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
