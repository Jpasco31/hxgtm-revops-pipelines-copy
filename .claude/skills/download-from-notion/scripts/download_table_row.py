#!/usr/bin/env python3
"""download_table_row.py — resolve a singleton input from a Notion page's
body-table block into a local file path.

Used by press-release cards (Customer Press Release playbook) where input
fields live in an inline body-table block rather than as page properties.
Each table row has a left-column label cell and a right-column value cell.
The value cell may contain either:
  - one or more attached files (Notion file blocks / mentions), OR
  - a plain-text URL (typically a LinkedIn profile/company URL).

Resolution order for a given --row-label:
  1. Any attached file in the row's value cell → download via the Notion
     signed URL exposed by the API.
  2. Otherwise, look for a sibling row whose left cell matches
     "<row-label> LinkedIn URL"; if present, treat its value cell text as a
     LinkedIn URL and hand off to fetch_linkedin_image.sh.
  3. If still unresolved, exit 3 with a clear "attach <row-label>" message.

Stdout: single-line JSON manifest:
  {
    "row_label": "...",
    "source": "file" | "linkedin_url",
    "local_path": "/abs/path",
    "bytes": 12345,
    "mime": "image/png",
    "linkedin_url": "..."   # only when source == "linkedin_url"
  }

Exit codes:
  0  success
  3  full failure (row missing, value empty, file download failed, LinkedIn
     fallback failed)
  4  bad input / missing dependency

Required env: none.
Required tools: python3 with requests + curl on PATH (curl is invoked by the
shelled-out fetch_linkedin_image.sh helper).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional

def _require_requests():
    """Lazy-import `requests` so --help works even when the dep is missing."""
    try:
        import requests  # noqa: F401
        return requests
    except ImportError:
        print(
            "download_table_row: missing `requests` Python package. "
            "Install with `pip install requests` (cloud routines have it preinstalled).",
            file=sys.stderr,
        )
        sys.exit(4)


NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"
FETCH_LINKEDIN_IMAGE_SH = (
    Path(__file__).resolve().parent.parent.parent
    / "fetch-linkedin-image"
    / "scripts"
    / "fetch_linkedin_image.sh"
)


def die(code: int, msg: str) -> None:
    print(f"download_table_row: {msg}", file=sys.stderr)
    sys.exit(code)


def normalise_label(s: str) -> str:
    """Strip leading/trailing whitespace and collapse internal whitespace.
    Notion body-table cells frequently carry trailing tabs or formatting
    artefacts that would otherwise prevent label matching.
    """
    return " ".join(s.split())


def rich_text_to_plain(rt_list) -> str:
    if not rt_list:
        return ""
    return "".join((b.get("plain_text") or "") for b in rt_list)


def fetch_blocks(api_key: str, parent_id: str) -> list[dict]:
    """List all direct children of a block/page, paging through cursors."""
    out: list[dict] = []
    cursor: Optional[str] = None
    while True:
        url = f"{NOTION_API_BASE}/blocks/{parent_id}/children"
        params: dict[str, str] = {"page_size": "100"}
        if cursor:
            params["start_cursor"] = cursor
        r = _require_requests().get(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": NOTION_API_VERSION,
            },
            params=params,
            timeout=30,
        )
        if r.status_code != 200:
            die(3, f"GET {url} returned {r.status_code}: {r.text[:200]}")
        body = r.json()
        out.extend(body.get("results") or [])
        if not body.get("has_more"):
            return out
        cursor = body.get("next_cursor")


def find_table_block(blocks: list[dict]) -> Optional[dict]:
    for b in blocks:
        if b.get("type") == "table":
            return b
    return None


def find_row(rows: list[dict], target_label: str) -> Optional[dict]:
    """rows are table_row blocks. The left cell is rows[i]['table_row']['cells'][0]
    — a list of rich_text spans. Match by normalised plain-text equality.
    """
    target = normalise_label(target_label).lower()
    for row in rows:
        cells = (row.get("table_row") or {}).get("cells") or []
        if not cells:
            continue
        label = normalise_label(rich_text_to_plain(cells[0])).lower()
        if label == target:
            return row
    return None


def extract_value_files_and_text(row: dict) -> tuple[list[dict], str]:
    """Return (file_objects, plain_text_url_or_blank) for the value cell.
    The value cell is cells[1] — a list of rich_text spans, possibly
    containing mentions. Notion body-table cells cannot directly hold
    file_object spans, so attached files would be represented as link or
    mention spans pointing at the file URL.
    """
    cells = (row.get("table_row") or {}).get("cells") or []
    if len(cells) < 2:
        return [], ""
    spans = cells[1] or []
    files: list[dict] = []
    text_bits: list[str] = []
    for span in spans:
        # Notion rich_text shapes: text, mention (with file mention type), equation, etc.
        # File mentions in body-table cells are rare in practice — files are
        # typically embedded as separate blocks. We still try to surface any
        # URL-shaped text we find.
        if span.get("type") == "mention":
            mention = span.get("mention") or {}
            if mention.get("type") == "file":
                files.append({"url": (mention.get("file") or {}).get("url")})
                continue
        if span.get("href"):
            text_bits.append(span.get("href"))
            continue
        plain = span.get("plain_text") or ""
        if plain.strip():
            text_bits.append(plain.strip())

    return files, " ".join(text_bits).strip()


def find_image_block_in_row(api_key: str, row_id: str) -> Optional[dict]:
    """Body-table cells render images as child image blocks of the row in
    practice. Walk the row's children for an image block."""
    children = fetch_blocks(api_key, row_id)
    for b in children:
        if b.get("type") in ("image", "file"):
            return b
    return None


def file_url_from_block(block: dict) -> Optional[str]:
    btype = block.get("type")
    payload = block.get(btype) or {}
    src = payload.get(btype if isinstance(payload.get(btype), dict) else "file") or payload
    # Image/file blocks have shape:
    #   { "type": "file" | "external", "file": {"url": ..., "expiry_time": ...} }
    if not isinstance(src, dict):
        # Try the file/external pattern directly on payload.
        if "file" in payload:
            return (payload["file"] or {}).get("url")
        if "external" in payload:
            return (payload["external"] or {}).get("url")
        return None
    if "file" in src:
        return (src["file"] or {}).get("url")
    if "external" in src:
        return (src["external"] or {}).get("url")
    if "url" in src:
        return src["url"]
    return None


def looks_like_linkedin_url(s: str) -> bool:
    s = s.strip().lower()
    return s.startswith("http") and "linkedin.com/" in s


def download_url_to(path: Path, url: str) -> tuple[int, str]:
    """Stream a URL to a local file using requests. Returns (bytes, mime)."""
    with _require_requests().get(url, stream=True, timeout=60) as r:
        if r.status_code != 200:
            die(3, f"GET {url} returned {r.status_code}")
        mime = (r.headers.get("Content-Type") or "").split(";")[0].strip()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return path.stat().st_size, mime


def fetch_linkedin_image(url: str, out_path: Path) -> dict:
    if not FETCH_LINKEDIN_IMAGE_SH.exists():
        die(4, f"fetch_linkedin_image.sh not found at {FETCH_LINKEDIN_IMAGE_SH}")
    if not os.access(FETCH_LINKEDIN_IMAGE_SH, os.X_OK):
        die(4, f"fetch_linkedin_image.sh is not executable: {FETCH_LINKEDIN_IMAGE_SH}")
    proc = subprocess.run(
        [str(FETCH_LINKEDIN_IMAGE_SH), "--url", url, "--output", str(out_path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        # Surface the verbatim stderr so the orchestrator can mark blocked.
        sys.stderr.write(proc.stderr)
        sys.exit(proc.returncode)
    try:
        return json.loads(proc.stdout.strip())
    except json.JSONDecodeError as e:
        die(3, f"fetch_linkedin_image stdout was not JSON: {e}\nstdout: {proc.stdout}")
    return {}


def main() -> None:
    ap = argparse.ArgumentParser(description="Resolve a singleton input from a Notion body-table row.")
    ap.add_argument("--api-key", required=True, help="Notion integration token")
    ap.add_argument("--page-id", required=True, help="Notion page ID (with or without dashes)")
    ap.add_argument("--row-label", required=True, help="Left-cell label, e.g. 'Customer Logo'")
    ap.add_argument("--output-dir", required=True, help="Absolute dir to write the resolved file into")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        die(4, f"--output-dir must be absolute: {args.output_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    page_id = args.page_id.replace("-", "")
    # Notion API accepts dashed or undashed IDs but its responses use dashed.

    page_blocks = fetch_blocks(args.api_key, page_id)
    table = find_table_block(page_blocks)
    if not table:
        die(3, f"no `table` block found in page {page_id}")
    table_id = table["id"]
    rows = fetch_blocks(args.api_key, table_id)
    if not rows:
        die(3, f"table block {table_id} has no rows")

    target_row = find_row(rows, args.row_label)
    if not target_row:
        die(3, f"row with label '{args.row_label}' not found in body table")

    file_objs, text_value = extract_value_files_and_text(target_row)

    # First try a file mention in the cell.
    chosen_url: Optional[str] = None
    if file_objs:
        chosen_url = file_objs[0]["url"]

    # If no file mention, body-table cells often surface attached images as
    # child image blocks of the row — walk them.
    if not chosen_url:
        img_block = find_image_block_in_row(args.api_key, target_row["id"])
        if img_block:
            chosen_url = file_url_from_block(img_block)

    # If we have a file URL, download it and emit the manifest.
    if chosen_url:
        suffix = Path(chosen_url.split("?")[0]).suffix or ".bin"
        local_name = f"{normalise_label(args.row_label).lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}{suffix}"
        local_path = out_dir / local_name
        bytes_written, mime = download_url_to(local_path, chosen_url)
        print(
            json.dumps(
                {
                    "row_label": args.row_label,
                    "source": "file",
                    "local_path": str(local_path),
                    "bytes": bytes_written,
                    "mime": mime,
                }
            )
        )
        return

    # No file found in this row. Try the sibling "<label> LinkedIn URL" row.
    sibling_label = f"{args.row_label} LinkedIn URL"
    sibling_row = find_row(rows, sibling_label)
    fallback_url: Optional[str] = None
    if sibling_row:
        _, sib_text = extract_value_files_and_text(sibling_row)
        if looks_like_linkedin_url(sib_text):
            fallback_url = sib_text

    # Or maybe the value cell of the *target* row itself contains a LinkedIn URL.
    if not fallback_url and looks_like_linkedin_url(text_value):
        fallback_url = text_value

    if not fallback_url:
        die(
            3,
            f"row '{args.row_label}' has no attached file and no LinkedIn URL fallback "
            f"(checked row value text and sibling '{sibling_label}'). "
            f"Attach the file directly to resolve.",
        )

    local_name = f"{normalise_label(args.row_label).lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}.jpg"
    local_path = out_dir / local_name
    manifest = fetch_linkedin_image(fallback_url, local_path)
    print(
        json.dumps(
            {
                "row_label": args.row_label,
                "source": "linkedin_url",
                "local_path": manifest.get("local_path", str(local_path)),
                "bytes": manifest.get("bytes"),
                "mime": manifest.get("mime"),
                "linkedin_url": fallback_url,
            }
        )
    )


if __name__ == "__main__":
    main()
