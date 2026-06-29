#!/usr/bin/env python3
"""
save-dossier-to-notion.py

Parses an Account Dossier markdown file into Notion block objects and prints
them as JSON to stdout. Claude reads this output and passes the blocks to the
notion-create-pages MCP tool — auth is handled by the user's own Notion MCP
connector, not by this script.

Usage:
    python3 save-dossier-to-notion.py --file outputs/definity-dossier.md
    python3 save-dossier-to-notion.py --file outputs/definity-dossier.md --multi
    python3 save-dossier-to-notion.py --file outputs/definity-dossier.md --multi --byte-limit 4500

Output:
    Default: JSON array of Notion block objects.
    --multi: JSON object with a `payloads` list, each payload a page create or
             append operation sized under `--byte-limit` (see PAYLOAD SHAPE
             section below). Designed for the MCP serializer stringification
             limit (~4.8KB per tool call).

PAYLOAD SHAPE (with --multi):

    {
      "version": 2,
      "byte_limit": 4500,
      "payloads": [
        {"op": "create_page", "children": [...]},
        {"op": "append", "parent": "page", "children": [...]},
        {"op": "append", "parent": "page", "capture": "table_1",
         "children": [<table block with header-only children>]},
        {"op": "append", "parent": "$table_1", "children": [<row>, <row>]},
        {"op": "append", "parent": "page", "children": [...]}
      ]
    }

    - First payload is always `create_page`. Subsequent payloads are `append`.
    - `parent` is either "page" (the page_id returned by create_page) or
      "$<capture_key>" (a block id captured from a prior payload's response).
    - `capture` (optional) tells the consumer to store
      `response.results[0].id` under that key for later reference.

Exits 0 on success. Exits 1 if the file is not found.
"""

import argparse
import json
import os
import re
import sys

MAX_RICH_TEXT_LEN = 2000

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# MCP serializer stringification cap is ~4.8KB per tool call. Leave headroom.
DEFAULT_BYTE_LIMIT = 4500

# Envelope overhead reserved for create_page (parent + properties) vs append
# (just block_id). Create_page payloads get a tighter children budget.
CREATE_PAGE_ENVELOPE = 500


# ---------------------------------------------------------------------------
# Inline markdown parser -> Notion rich_text objects
# ---------------------------------------------------------------------------

def parse_inline(text):
    """
    Convert a text string with **bold**, *italic*, `code`, and [text](url)
    patterns into a list of Notion rich_text objects.
    """
    rich_text = []
    pattern = re.compile(
        r'\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)'
    )
    pos = 0
    for m in pattern.finditer(text):
        start, end = m.start(), m.end()
        if pos < start:
            rich_text.append(_plain(text[pos:start]))
        if m.group(1) is not None:
            rich_text.append(_annotated(m.group(1), bold=True))
        elif m.group(2) is not None:
            rich_text.append(_annotated(m.group(2), italic=True))
        elif m.group(3) is not None:
            rich_text.append(_annotated(m.group(3), code=True))
        else:
            label, url = m.group(4), m.group(5)
            rich_text.append(_linked(label, url))
        pos = end
    if pos < len(text):
        rich_text.append(_plain(text[pos:]))
    return rich_text if rich_text else [_plain("")]


def _plain(content):
    return {"type": "text", "text": {"content": content}}


def _annotated(content, bold=False, italic=False, code=False):
    obj = {"type": "text", "text": {"content": content}, "annotations": {}}
    if bold:
        obj["annotations"]["bold"] = True
    if italic:
        obj["annotations"]["italic"] = True
    if code:
        obj["annotations"]["code"] = True
    if not obj["annotations"]:
        del obj["annotations"]
    return obj


def _linked(label, url):
    return {"type": "text", "text": {"content": label, "link": {"url": url}}}


# ---------------------------------------------------------------------------
# Rich text splitting (2000-char limit per element)
# ---------------------------------------------------------------------------

def split_rich_text_list(rt_list):
    """
    Split any rich_text objects whose content exceeds MAX_RICH_TEXT_LEN.
    Returns a flat list of rich_text objects, each within the limit.
    """
    result = []
    for rt in rt_list:
        content = rt["text"]["content"]
        if len(content) <= MAX_RICH_TEXT_LEN:
            result.append(rt)
            continue
        chunks = _split_text(content, MAX_RICH_TEXT_LEN)
        for chunk in chunks:
            new_rt = {"type": "text", "text": {"content": chunk}}
            if "link" in rt["text"]:
                new_rt["text"]["link"] = rt["text"]["link"]
            if "annotations" in rt:
                new_rt["annotations"] = rt["annotations"]
            result.append(new_rt)
    return result


def _split_text(text, max_len):
    """Split text into chunks of at most max_len chars, breaking at \\n or space."""
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


def rt_list_to_blocks(block_type, rt_list):
    """
    Convert a list of rich_text objects into one or more Notion blocks,
    ensuring no block's total content exceeds MAX_RICH_TEXT_LEN.
    """
    rt_list = split_rich_text_list(rt_list)
    blocks = []
    current_rt = []
    current_len = 0
    for rt in rt_list:
        content_len = len(rt["text"]["content"])
        if current_len + content_len > MAX_RICH_TEXT_LEN and current_rt:
            blocks.append(_make_block(block_type, current_rt))
            current_rt = []
            current_len = 0
        current_rt.append(rt)
        current_len += content_len
    if current_rt:
        blocks.append(_make_block(block_type, current_rt))
    return blocks


def _make_block(block_type, rich_text):
    return {
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": rich_text},
    }


# ---------------------------------------------------------------------------
# Table parser -> Notion `table` block
# ---------------------------------------------------------------------------

_SEPARATOR_RE = re.compile(r'^\|[\s\-:|]+\|$')


def _split_row(line):
    """Split a markdown table row into raw cell strings, stripping the
    leading/trailing pipes produced by pipe-terminated rows."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [c.strip().replace("<br>", "\n") for c in stripped.split("|")]


def build_table_block(table_lines):
    """Convert a contiguous run of pipe-prefixed markdown lines into a single
    Notion `table` block with `table_row` children. Returns None for an empty
    or header-only table. The first non-separator row is treated as the column
    header when a separator row (`| --- | --- |`) follows it; otherwise
    `has_column_header` is False. All rows are padded or truncated to match
    `table_width`."""
    rows = []
    has_header = False
    for idx, line in enumerate(table_lines):
        if _SEPARATOR_RE.match(line.strip()):
            if idx == 1 and rows:
                has_header = True
            continue
        rows.append(_split_row(line))

    if not rows:
        return None

    table_width = max(len(r) for r in rows)

    table_rows = []
    for cells in rows:
        padded = cells + [""] * (table_width - len(cells))
        padded = padded[:table_width]
        table_rows.append({
            "object": "block",
            "type": "table_row",
            "table_row": {
                "cells": [split_rich_text_list(parse_inline(c)) for c in padded],
            },
        })

    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": table_width,
            "has_column_header": has_header,
            "has_row_header": False,
            "children": table_rows,
        },
    }


# ---------------------------------------------------------------------------
# Markdown parser -> Notion blocks
# ---------------------------------------------------------------------------

def parse_markdown_to_blocks(content):
    """Parse dossier markdown content into a list of Notion block dicts."""
    lines = content.splitlines()
    blocks = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Heading 1
        if line.startswith("# ") and not line.startswith("## "):
            text = line[2:].strip()
            blocks.extend(rt_list_to_blocks("heading_1", parse_inline(text)))
            i += 1
            continue

        # Heading 2
        if line.startswith("## ") and not line.startswith("### "):
            text = line[3:].strip()
            blocks.extend(rt_list_to_blocks("heading_2", parse_inline(text)))
            i += 1
            continue

        # Heading 3
        if line.startswith("### ") and not line.startswith("#### "):
            text = line[4:].strip()
            blocks.extend(rt_list_to_blocks("heading_3", parse_inline(text)))
            i += 1
            continue

        # Heading 4+ — Notion only supports H1-H3 natively, so render deeper
        # headings as a bold paragraph block. Without this, the paragraph
        # fallback below would `break` on the leading "#" without advancing
        # `i`, looping forever.
        m_hx = re.match(r'^(#{4,6}) ', line)
        if m_hx:
            text = line[len(m_hx.group(1)) + 1:].strip()
            inline = parse_inline(text)
            for rt in inline:
                rt.setdefault("annotations", {})
                rt["annotations"]["bold"] = True
            blocks.extend(rt_list_to_blocks("paragraph", inline))
            i += 1
            continue

        # Blockquote — merge consecutive quote lines
        if line.startswith("> ") or line == ">":
            quote_lines = []
            while i < len(lines) and (lines[i].startswith("> ") or lines[i] == ">"):
                quote_line = lines[i][2:] if lines[i].startswith("> ") else ""
                quote_lines.append(quote_line)
                i += 1
            while quote_lines and not quote_lines[-1].strip():
                quote_lines.pop()
            text = "\n".join(quote_lines)
            if text.strip():
                blocks.extend(rt_list_to_blocks("quote", parse_inline(text)))
            continue

        # Divider
        if line.strip() == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            i += 1
            continue

        # Table — buffer consecutive pipe-prefixed lines and emit a real
        # Notion `table` block with `table_row` children.
        if line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            table_block = build_table_block(table_lines)
            if table_block is not None:
                blocks.append(table_block)
            continue

        # Bulleted list item — "- " or "* " at line start. Consecutive
        # bullet lines emit separate bulleted_list_item blocks; a soft
        # continuation (indented follow-on text) is merged into the
        # preceding item.
        if _BULLET_RE.match(line):
            item_text = _BULLET_RE.sub("", line, count=1)
            i += 1
            while i < len(lines) and _is_list_continuation(lines[i]):
                item_text += "\n" + lines[i].strip()
                i += 1
            blocks.extend(
                rt_list_to_blocks("bulleted_list_item", parse_inline(item_text))
            )
            continue

        # Numbered list item — "1. ", "2. ", etc.
        if _NUMBERED_RE.match(line):
            item_text = _NUMBERED_RE.sub("", line, count=1)
            i += 1
            while i < len(lines) and _is_list_continuation(lines[i]):
                item_text += "\n" + lines[i].strip()
                i += 1
            blocks.extend(
                rt_list_to_blocks("numbered_list_item", parse_inline(item_text))
            )
            continue

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Plain paragraph — merge consecutive plain lines
        para_lines = []
        while i < len(lines):
            l = lines[i]
            if (not l.strip() or l.startswith("#") or l.startswith(">")
                    or l.strip() == "---" or l.startswith("|")
                    or _BULLET_RE.match(l) or _NUMBERED_RE.match(l)):
                break
            para_lines.append(l)
            i += 1
        text = "\n".join(para_lines).strip()
        if text:
            blocks.extend(rt_list_to_blocks("paragraph", parse_inline(text)))

    return blocks


_BULLET_RE = re.compile(r'^[-*] ')
_NUMBERED_RE = re.compile(r'^\d+\. ')


def _is_list_continuation(line):
    """A continuation line is indented and not itself a new list item,
    heading, quote, divider, or table row."""
    if not line or not line[:1].isspace():
        return False
    stripped = line.strip()
    if not stripped:
        return False
    if _BULLET_RE.match(stripped) or _NUMBERED_RE.match(stripped):
        return False
    if stripped.startswith(("#", ">", "|")) or stripped == "---":
        return False
    return True


# ---------------------------------------------------------------------------
# Payload partitioner (--multi mode)
# ---------------------------------------------------------------------------

def _jsize(obj):
    """Stringified JSON size — the unit the MCP serializer cares about."""
    return len(json.dumps(obj, ensure_ascii=False))


def _table_with_header_only(table_block):
    """Return a shallow copy of a table block whose children contain only the
    header row (if the table declared one) or an empty list otherwise."""
    shell = dict(table_block)
    shell["table"] = dict(table_block["table"])
    rows = table_block["table"].get("children", [])
    if table_block["table"].get("has_column_header") and rows:
        shell["table"]["children"] = [rows[0]]
    else:
        shell["table"]["children"] = []
    return shell


def _table_data_rows(table_block):
    """Return only the data rows of a table block (skipping the header if
    declared)."""
    rows = table_block["table"].get("children", [])
    if table_block["table"].get("has_column_header") and rows:
        return rows[1:]
    return rows


def _bucket_rows(rows, budget):
    """Group table_row blocks into buckets whose stringified JSON size stays
    under `budget`. A single row larger than `budget` is emitted alone so the
    consumer can still try to send it (and fail loudly if Notion rejects)."""
    groups = []
    cur = []
    for row in rows:
        prospective = cur + [row]
        if _jsize(prospective) > budget and cur:
            groups.append(cur)
            cur = [row]
        else:
            cur.append(row)
    if cur:
        groups.append(cur)
    return groups


def partition_blocks_into_payloads(blocks, byte_limit=DEFAULT_BYTE_LIMIT):
    """Walk `blocks` (the flat output of parse_markdown_to_blocks) and emit a
    list of payload dicts, each of which can be sent in a single MCP tool
    call without exceeding `byte_limit`.

    Tables whose stringified size exceeds the append budget are split into a
    header-only shell (captured under key `table_N`) followed by row-group
    append payloads targeting `$table_N`.
    """
    create_budget = byte_limit - CREATE_PAGE_ENVELOPE
    append_budget = byte_limit

    payloads = []
    cur_op = "create_page"
    cur_parent = None   # only meaningful for append payloads
    cur_children = []
    table_counter = 0

    def _cur_budget():
        return create_budget if cur_op == "create_page" else append_budget

    def _flush():
        nonlocal cur_op, cur_parent, cur_children
        if not cur_children:
            return
        if cur_op == "create_page":
            payloads.append({"op": "create_page", "children": cur_children})
        else:
            payloads.append({
                "op": "append",
                "parent": cur_parent,
                "children": cur_children,
            })
        cur_op = "append"
        cur_parent = "page"
        cur_children = []

    def _start_append():
        nonlocal cur_op, cur_parent, cur_children
        cur_op = "append"
        cur_parent = "page"
        cur_children = []

    for block in blocks:
        is_oversize_table = (
            block.get("type") == "table"
            and _jsize(block) > append_budget
        )

        if is_oversize_table:
            _flush()
            table_counter += 1
            capture_key = f"table_{table_counter}"
            shell = _table_with_header_only(block)
            payloads.append({
                "op": "append",
                "parent": "page",
                "capture": capture_key,
                "children": [shell],
            })
            data_rows = _table_data_rows(block)
            for group in _bucket_rows(data_rows, append_budget):
                payloads.append({
                    "op": "append",
                    "parent": f"${capture_key}",
                    "children": group,
                })
            _start_append()
            continue

        # Will `block` fit in the current payload?
        prospective = cur_children + [block]
        if _jsize(prospective) > _cur_budget() and cur_children:
            _flush()

        cur_children.append(block)

    _flush()
    return payloads


# ---------------------------------------------------------------------------
# Direct Notion API publisher (--publish mode)
# ---------------------------------------------------------------------------
#
# Executes the same create_page + append sequence the MCP multi-payload loop
# runs in the batch skill, but talks directly to api.notion.com. Selected
# automatically when NOTION_API_KEY (or NOTION_TOKEN) is set. Keeps the MCP
# serializer out of the path entirely, which avoids the ~4.8KB per-call
# stringification limit that motivated the multi-payload split in the first
# place — the script still partitions for safety, but it could send much
# larger payloads to Notion directly if needed.


class PublishError(Exception):
    def __init__(self, message, index=None, partial_url=None, status=None, body=None):
        super().__init__(message)
        self.index = index
        self.partial_url = partial_url
        self.status = status
        self.body = body


def _notion_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _notion_request(method, url, token, body=None):
    import requests  # Imported lazily so --multi / default modes have no dep.

    resp = requests.request(
        method,
        url,
        headers=_notion_headers(token),
        data=json.dumps(body) if body is not None else None,
        timeout=60,
    )
    if resp.status_code >= 400:
        try:
            err_body = resp.json()
        except Exception:
            err_body = {"text": resp.text}
        raise PublishError(
            f"Notion {method} {url} -> {resp.status_code}",
            status=resp.status_code,
            body=err_body,
        )
    return resp.json()


def _clean_name_candidates(display_name):
    """Generate a small ordered list of name candidates to try against
    /v1/users when the upstream value is mildly noisy (role parentheses,
    semicolon-joined co-owners, comma-joined annotations). The
    orchestrator's grep already strips most of this, but defending here
    means a future caller passing a raw cell value still resolves
    cleanly. Order matters — first match wins."""
    if not display_name:
        return []
    candidates = []
    seen = set()

    def _add(value):
        v = (value or "").strip()
        if not v:
            return
        key = v.lower()
        if key in seen:
            return
        seen.add(key)
        candidates.append(v)

    raw = display_name.strip()
    _add(raw)

    no_parens = re.sub(r"\([^)]*\)", "", raw).strip()
    _add(no_parens)

    for sep in (";", ","):
        if sep in no_parens:
            head = no_parens.split(sep, 1)[0]
            head = re.sub(r"\([^)]*\)", "", head).strip()
            _add(head)

    return candidates


def _resolve_user_id(token, display_name):
    """Look up a Notion user by (case-insensitive, exact) display name via
    GET /v1/users. Returns the user id or None. Silent on failure — the
    caller just omits the property.

    Tries a small set of cleaned-up name candidates in order so that a
    cell value like `Mac Macchioni (Account Owner); Joey Goret (...)`
    still resolves to `Mac Macchioni` — the orchestrator's grep cleans
    most of this, but defending here makes the resolver robust to any
    future caller that passes the raw cell."""
    candidates = _clean_name_candidates(display_name)
    if not candidates:
        return None
    targets = {c.lower(): c for c in candidates}
    try:
        cursor = None
        while True:
            url = f"{NOTION_API_BASE}/users?page_size=100"
            if cursor:
                url += f"&start_cursor={cursor}"
            data = _notion_request("GET", url, token)
            for u in data.get("results", []):
                if u.get("type") != "person":
                    continue
                name = (u.get("name") or "").strip().lower()
                if name in targets:
                    return u.get("id")
            if not data.get("has_more"):
                return None
            cursor = data.get("next_cursor")
    except PublishError:
        return None


def _build_properties(account_name, submitter_id, assignee_id, template_version=None):
    props = {
        "Name": {"title": [{"text": {"content": account_name}}]},
        "Type": {"rich_text": [{"text": {"content": "Account Dossier"}}]},
        "Status": {"status": {"name": "Draft"}},
    }
    if submitter_id:
        props["Submitter"] = {"people": [{"id": submitter_id}]}
    if assignee_id:
        props["Assignee"] = {"people": [{"id": assignee_id}]}
    if template_version:
        props["Template Version"] = {
            "rich_text": [{"text": {"content": str(template_version)}}]
        }
    return props


def _construct_notion_url(page_id):
    return f"https://notion.so/{page_id.replace('-', '')}"


def publish(token, database_id, account_name, assignee_name, submitter_name, payloads, template_version=None):
    """Execute the multi-payload sequence against the live Notion API.

    Mirrors the MCP-mode loop in the batch SKILL.md: first payload is always
    create_page; subsequent payloads are appends to the page or to a captured
    table block. `capture` keys are resolved to block IDs from the response.
    """
    assignee_id = _resolve_user_id(token, assignee_name) if assignee_name else None
    submitter_id = _resolve_user_id(token, submitter_name) if submitter_name else None

    page_id = None
    notion_url = None
    captured = {}

    for i, payload in enumerate(payloads):
        op = payload.get("op")
        children = payload.get("children", [])

        try:
            if op == "create_page":
                body = {
                    "parent": {"database_id": database_id},
                    "properties": _build_properties(
                        account_name, submitter_id, assignee_id, template_version
                    ),
                    "children": children,
                }
                data = _notion_request("POST", f"{NOTION_API_BASE}/pages", token, body)
                page_id = data.get("id")
                notion_url = data.get("url") or (_construct_notion_url(page_id) if page_id else None)
            elif op == "append":
                parent_key = payload.get("parent")
                if parent_key == "page":
                    block_id = page_id
                elif isinstance(parent_key, str) and parent_key.startswith("$"):
                    block_id = captured.get(parent_key[1:])
                else:
                    raise PublishError(f"Unknown parent key: {parent_key!r}", index=i, partial_url=notion_url)
                if not block_id:
                    raise PublishError(
                        f"No block id resolved for parent {parent_key!r}",
                        index=i,
                        partial_url=notion_url,
                    )
                data = _notion_request(
                    "PATCH",
                    f"{NOTION_API_BASE}/blocks/{block_id}/children",
                    token,
                    {"children": children},
                )
                cap_key = payload.get("capture")
                if cap_key:
                    results = data.get("results") or []
                    if results:
                        captured[cap_key] = results[0].get("id")
            else:
                raise PublishError(f"Unknown op: {op!r}", index=i, partial_url=notion_url)
        except PublishError as e:
            e.index = i if e.index is None else e.index
            e.partial_url = notion_url if e.partial_url is None else e.partial_url
            raise

    return {"notion_url": notion_url, "page_id": page_id}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse an Account Dossier markdown file into Notion blocks (JSON)."
    )
    parser.add_argument("--file", required=True, help="Path to the dossier .md file")
    parser.add_argument(
        "--multi",
        action="store_true",
        help="Emit a multi-payload object (create_page + append ops), each "
             "sized under --byte-limit, instead of a flat block array.",
    )
    parser.add_argument(
        "--byte-limit",
        type=int,
        default=DEFAULT_BYTE_LIMIT,
        help=f"Max stringified JSON size per payload (default {DEFAULT_BYTE_LIMIT}). "
             "Only used with --multi.",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish directly to the Notion REST API using NOTION_API_KEY "
             "(or NOTION_TOKEN) from the environment. Implies --multi. On "
             "success, prints {\"notion_url\": ..., \"page_id\": ...} to "
             "stdout. On failure, prints an error JSON to stderr and exits "
             "non-zero.",
    )
    parser.add_argument("--database-id", help="Target Notion database ID (required with --publish).")
    parser.add_argument("--account-name", help="Account display name used as page title (required with --publish).")
    parser.add_argument("--assignee", help="Assignee display name. Resolved to a Notion user id via /v1/users; property is omitted if no match.")
    parser.add_argument("--submitter", help="Submitter display name. Resolved the same way as --assignee.")
    parser.add_argument(
        "--template-version",
        help="Template Version stamp written to the Notion 'Template Version' rich_text property. Optional; the property is omitted if absent.",
    )
    args = parser.parse_args()

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    blocks = parse_markdown_to_blocks(content)

    if args.publish:
        token = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
        if not token:
            print(
                json.dumps({"error": "NOTION_API_KEY or NOTION_TOKEN env var required for --publish"}),
                file=sys.stderr,
            )
            sys.exit(2)
        if not args.database_id or not args.account_name:
            print(
                json.dumps({"error": "--database-id and --account-name are required with --publish"}),
                file=sys.stderr,
            )
            sys.exit(2)

        payloads = partition_blocks_into_payloads(blocks, byte_limit=args.byte_limit)
        try:
            result = publish(
                token=token,
                database_id=args.database_id,
                account_name=args.account_name,
                assignee_name=args.assignee,
                submitter_name=args.submitter,
                payloads=payloads,
                template_version=args.template_version,
            )
            print(json.dumps(result))
        except PublishError as e:
            err = {
                "error": str(e),
                "failed_payload_index": e.index,
                "notion_url": e.partial_url,
                "status": e.status,
                "body": e.body,
            }
            print(json.dumps(err), file=sys.stderr)
            sys.exit(1)
        return

    if args.multi:
        payloads = partition_blocks_into_payloads(blocks, byte_limit=args.byte_limit)
        output = {
            "version": 2,
            "byte_limit": args.byte_limit,
            "payloads": payloads,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(blocks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
