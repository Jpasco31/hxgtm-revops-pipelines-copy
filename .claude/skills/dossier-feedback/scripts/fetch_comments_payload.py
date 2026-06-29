#!/usr/bin/env python3
"""
Normalise the output of the Notion `notion-get-comments` MCP tool into a
flat JSON array of:

  [{"discussion_id": "...",
    "parent_block_id": "..." | null,
    "author": "Sarah Chen",
    "created_time": "2026-04-22T14:11:00Z",
    "resolved": false,
    "comment_text": "..." }]

Notion MCP shipments differ in the exact wrapper shape — sometimes
`{"comments": [...]}`, sometimes `{"results": [...]}`, sometimes a bare
list — and individual comment records use a mix of `parent.block_id` /
`parent_block_id`, `created_by.name` / `author.name` / `user.name`, and
either `rich_text` arrays or pre-rendered `plain_text`. This script
collapses all that variation so the per-account subagent can pipe its raw
tool output through and synthesise the truths file from a stable schema.

Usage:
  python3 fetch_comments_payload.py --raw-input -          # stdin
  python3 fetch_comments_payload.py --raw-input <file>     # file
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional


def _coerce_list(payload: Any) -> list:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("comments", "results", "data", "items"):
        v = payload.get(key)
        if isinstance(v, list):
            return v
    return []


def _extract_parent_block(record: dict) -> Optional[str]:
    parent = record.get("parent")
    if isinstance(parent, dict):
        for key in ("block_id", "id"):
            v = parent.get(key)
            if isinstance(v, str) and v:
                ptype = parent.get("type")
                if ptype and "page" in str(ptype).lower():
                    return None
                return v
    for key in ("parent_block_id", "block_id"):
        v = record.get(key)
        if isinstance(v, str) and v:
            return v
    return None


def _extract_author(record: dict) -> str:
    for path in (
        ("created_by", "name"),
        ("author", "name"),
        ("user", "name"),
        ("created_by", "person", "email"),
    ):
        cur: Any = record
        ok = True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok and isinstance(cur, str) and cur.strip():
            return cur.strip()
    for key in ("author_name", "user_name", "created_by_name"):
        v = record.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "Unknown"


def _extract_created_time(record: dict) -> str:
    for key in ("created_time", "created_at", "createdAt", "timestamp"):
        v = record.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _extract_resolved(record: dict) -> bool:
    for key in ("resolved", "is_resolved", "resolved_at"):
        v = record.get(key)
        if isinstance(v, bool):
            return v
        if isinstance(v, str) and v:
            return True
    discussion = record.get("discussion")
    if isinstance(discussion, dict):
        for key in ("resolved", "is_resolved"):
            v = discussion.get(key)
            if isinstance(v, bool):
                return v
    return False


def _extract_comment_text(record: dict) -> str:
    rich = record.get("rich_text")
    if isinstance(rich, list) and rich:
        parts = []
        for item in rich:
            if isinstance(item, dict):
                pt = item.get("plain_text") or item.get("text", {}).get("content")
                if isinstance(pt, str):
                    parts.append(pt)
        if parts:
            return " ".join(p.strip() for p in parts if p.strip()).strip()

    for key in ("plain_text", "text", "body", "comment", "content"):
        v = record.get(key)
        if isinstance(v, str) and v.strip():
            return " ".join(v.split()).strip()
        if isinstance(v, dict):
            inner = v.get("content") or v.get("plain_text")
            if isinstance(inner, str) and inner.strip():
                return " ".join(inner.split()).strip()

    return ""


def _extract_discussion_id(record: dict) -> str:
    for key in ("discussion_id", "thread_id", "id"):
        v = record.get(key)
        if isinstance(v, str) and v.strip():
            return v
    discussion = record.get("discussion")
    if isinstance(discussion, dict):
        v = discussion.get("id")
        if isinstance(v, str) and v:
            return v
    return ""


def normalise(raw: Any) -> list:
    out = []
    for record in _coerce_list(raw):
        if not isinstance(record, dict):
            continue
        comment_text = _extract_comment_text(record)
        if not comment_text:
            continue
        out.append(
            {
                "discussion_id": _extract_discussion_id(record),
                "parent_block_id": _extract_parent_block(record),
                "author": _extract_author(record),
                "created_time": _extract_created_time(record),
                "resolved": _extract_resolved(record),
                "comment_text": comment_text,
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-input",
        required=True,
        help='Path to the JSON output of notion-get-comments, or "-" for stdin',
    )
    args = parser.parse_args()

    if args.raw_input == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.raw_input).read_text()

    text = text.strip()
    if not text:
        print("[]")
        return 0

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"failed to parse raw input as JSON: {e}", file=sys.stderr)
        return 1

    print(json.dumps(normalise(raw), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
