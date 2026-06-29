#!/usr/bin/env python3
"""download_child_db_rows.py — query the rows of a Notion customer-quotes
database, then resolve each quote's photo input to a local file path.

Two ways to locate the database:
  - Legacy: an inline child database on a page body (--page-id + --child-db-name).
  - Direct: a database queried by id (--database-id) — use this for a per-step
    form-inputs database placed as a *full-page child* of the card, which the
    page-body scan cannot see.

Two ways to read quotes from the located rows:
  - Legacy: one row per quote (the `Customer Quotes` inline child DB).
  - Form-input model (--explode-groups): a single submission row carrying N
    numbered groups (`Customer Quote 1: Text`, `Customer Quote 2: Text
    [Optional]`, ...). Combine with --latest-only to take the newest submission.
Both paths emit an identical per-row manifest, so consumers don't change.

The legacy inline `Customer Quotes` child DB carries, per row:
  - Quote text       (title, required)
  - Customer name    (rich_text, required for attribution)
  - Customer title   (rich_text, optional)
  - Company name     (rich_text, optional)
  - Customer Photo   (files, file attachment)
  - Customer LinkedIn URL (url, fallback when no photo file)
  - Order            (number, optional; rendering order)

NOTE: This DB's property names have a trailing tab character in Notion
(`Customer name\\t`, `Customer Photo\\t`, etc.). All property name comparisons
strip trailing whitespace.

Resolution order per row:
  1. `Customer Photo` files property → download the first file.
  2. Otherwise, `Customer LinkedIn URL` → hand off to fetch_linkedin_image.sh.
  3. If both are blank → that row is skipped with `status: skipped` and a
     reason — it does NOT fail the whole run. The orchestrator can decide
     whether a skipped row should block the card.

Stdout: single-line JSON object:
  {
    "child_db_id": "...",
    "rows": [
      {
        "row_id": "...",
        "order": 1,
        "quote_text": "...",
        "customer_name": "...",
        "customer_title": "...",
        "company_name": "...",
        "avatar_local_path": "/abs/path",
        "avatar_source": "file" | "linkedin_url" | "missing",
        "linkedin_url": "...",   # only when source == "linkedin_url"
        "status": "ok" | "skipped",
        "reason": "..."          # only when status == "skipped"
      }
    ]
  }

Rows are sorted by Order ascending, then created_time. Skipped rows are kept
in the list so the orchestrator can report them.

Exit codes:
  0  success (even if some rows skipped)
  3  hard failure (page/DB not found, API error, LinkedIn fetch error on a
     row that had a URL set — caller decided to surface those verbatim)
  4  bad input / missing dependency
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

def _require_requests():
    """Lazy-import `requests` so --help works even when the dep is missing."""
    try:
        import requests  # noqa: F401
        return requests
    except ImportError:
        print(
            "download_child_db_rows: missing `requests` Python package. "
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

# Property names in the production Customer Quotes DB have trailing tabs.
# We compare on the stripped form throughout.
PROP_QUOTE = "quote text"
PROP_CUSTOMER_NAME = "customer name"
PROP_CUSTOMER_TITLE = "customer title"
PROP_COMPANY = "company name"
PROP_PHOTO = "customer photo"
PROP_LINKEDIN = "customer linkedin url"
PROP_ORDER = "order"


def die(code: int, msg: str) -> None:
    print(f"download_child_db_rows: {msg}", file=sys.stderr)
    sys.exit(code)


def headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def fetch_blocks(api_key: str, parent_id: str) -> list[dict]:
    out: list[dict] = []
    cursor: Optional[str] = None
    while True:
        url = f"{NOTION_API_BASE}/blocks/{parent_id}/children"
        params: dict[str, str] = {"page_size": "100"}
        if cursor:
            params["start_cursor"] = cursor
        r = _require_requests().get(url, headers=headers(api_key), params=params, timeout=30)
        if r.status_code != 200:
            die(3, f"GET {url} returned {r.status_code}: {r.text[:200]}")
        body = r.json()
        out.extend(body.get("results") or [])
        if not body.get("has_more"):
            return out
        cursor = body.get("next_cursor")


def find_child_db(blocks: list[dict], target_name: str) -> Optional[dict]:
    target = target_name.strip().lower()
    for b in blocks:
        if b.get("type") != "child_database":
            continue
        title = ((b.get("child_database") or {}).get("title") or "").strip().lower()
        if title == target:
            return b
    return None


def query_db_rows(api_key: str, db_id: str) -> list[dict]:
    out: list[dict] = []
    cursor: Optional[str] = None
    while True:
        url = f"{NOTION_API_BASE}/databases/{db_id}/query"
        body: dict[str, Any] = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = _require_requests().post(url, headers=headers(api_key), data=json.dumps(body), timeout=30)
        if r.status_code != 200:
            die(3, f"POST {url} returned {r.status_code}: {r.text[:200]}")
        page = r.json()
        out.extend(page.get("results") or [])
        if not page.get("has_more"):
            return out
        cursor = page.get("next_cursor")


def _norm(name: str) -> str:
    """Normalize a property name for comparison: strip surrounding whitespace,
    lowercase, and drop a trailing `[Optional]` label (the form-input convention
    for marking optional fields, e.g. `Customer Quote 2: Text [Optional]`)."""
    s = (name or "").strip().lower()
    if s.endswith("[optional]"):
        s = s[: -len("[optional]")].strip()
    return s


def prop_by_norm_name(props: dict, target: str) -> Optional[dict]:
    """Look up a property by name, ignoring trailing whitespace, case, and a
    trailing `[Optional]` label."""
    target = _norm(target)
    for name, val in props.items():
        if _norm(name) == target:
            return val
    return None


def prop_plain_text(prop: Optional[dict]) -> str:
    if not prop:
        return ""
    t = prop.get("type")
    if t == "title":
        return "".join((b.get("plain_text") or "") for b in (prop.get("title") or []))
    if t == "rich_text":
        return "".join((b.get("plain_text") or "") for b in (prop.get("rich_text") or []))
    if t == "url":
        return prop.get("url") or ""
    return ""


def prop_first_file_url(prop: Optional[dict]) -> Optional[str]:
    if not prop or prop.get("type") != "files":
        return None
    files = prop.get("files") or []
    if not files:
        return None
    f = files[0]
    if f.get("type") == "file":
        return (f.get("file") or {}).get("url")
    if f.get("type") == "external":
        return (f.get("external") or {}).get("url")
    return None


def prop_number(prop: Optional[dict]) -> Optional[float]:
    if not prop or prop.get("type") != "number":
        return None
    return prop.get("number")


def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    out = []
    for c in s:
        if c.isalnum():
            out.append(c)
        elif c in " -_":
            out.append("-")
    slug = "".join(out).strip("-") or "row"
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug


def download_url_to(path: Path, url: str) -> tuple[int, str]:
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
        die(4, f"fetch_linkedin_image.sh is not executable")
    proc = subprocess.run(
        [str(FETCH_LINKEDIN_IMAGE_SH), "--url", url, "--output", str(out_path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise RuntimeError(proc.stderr.strip() or "fetch_linkedin_image failed")
    try:
        return json.loads(proc.stdout.strip())
    except json.JSONDecodeError as e:
        die(3, f"fetch_linkedin_image stdout was not JSON: {e}")
    return {}


def build_entry(
    row_id: Optional[str],
    created_time: Optional[str],
    order: Optional[float],
    quote: str,
    cust_name: str,
    cust_title: str,
    company: str,
    photo_url: Optional[str],
    linkedin_url: str,
    out_dir: Path,
) -> dict:
    """Resolve one quote's avatar (photo file → LinkedIn URL fallback → skip) and
    return the manifest entry. Shared by the legacy one-row-per-quote path and the
    numbered-column exploder so both emit an identical entry shape."""
    entry: dict[str, Any] = {
        "row_id": row_id,
        "created_time": created_time,
        "order": order,
        "quote_text": quote,
        "customer_name": cust_name,
        "customer_title": cust_title,
        "company_name": company,
        "linkedin_url": linkedin_url or None,
        "avatar_local_path": None,
        "avatar_source": "missing",
        "status": "skipped",
        "reason": "",
    }

    if not quote.strip():
        entry["reason"] = "Quote text is blank"
        return entry

    slug = slugify(cust_name) or slugify(quote[:24]) or "row"
    local_name = f"{slug}-{uuid.uuid4().hex[:8]}"

    if photo_url:
        local_path = out_dir / f"{local_name}.bin"
        try:
            bytes_written, mime = download_url_to(local_path, photo_url)
        except SystemExit:
            raise
        except Exception as e:
            entry["reason"] = f"Customer Photo download failed: {e}"
            return entry
        entry["avatar_local_path"] = str(local_path)
        entry["avatar_source"] = "file"
        entry["bytes"] = bytes_written
        entry["mime"] = mime
        entry["status"] = "ok"
        return entry

    if linkedin_url and linkedin_url.strip():
        local_path = out_dir / f"{local_name}.jpg"
        try:
            manifest = fetch_linkedin_image(linkedin_url.strip(), local_path)
            entry["avatar_local_path"] = manifest.get("local_path", str(local_path))
            entry["bytes"] = manifest.get("bytes")
            entry["mime"] = manifest.get("mime")
            entry["avatar_source"] = "linkedin_url"
            entry["status"] = "ok"
        except RuntimeError as e:
            entry["reason"] = f"LinkedIn fetch failed: {e}"
        return entry

    entry["reason"] = "Customer Photo file and Customer LinkedIn URL are both blank"
    return entry


def rows_from_child_db(api_key: str, page_id: str, child_db_name: str) -> tuple[str, list[dict]]:
    """Legacy locator: find an inline child database by title on a page body and
    return (db_id, rows)."""
    page_blocks = fetch_blocks(api_key, page_id.replace("-", ""))
    child = find_child_db(page_blocks, child_db_name)
    if not child:
        die(3, f"no child_database titled '{child_db_name}' on page {page_id}")
    db_id = child["id"]
    return db_id, query_db_rows(api_key, db_id)


def explode_numbered_groups(
    rows: list[dict],
    prefix: str,
    max_groups: int,
    out_dir: Path,
) -> list[dict]:
    """Form-input model: each submission row carries N numbered field groups
    (`<prefix> i: Text`, `<prefix> i: Customer Name`, `<prefix> i: Customer
    Title`, `<prefix> i: Photo`, `<prefix> i: LinkedIn URL`). Emit one manifest
    entry per non-blank group, preserving the legacy per-row entry shape. The
    group number carries the order; a group whose Text is blank is treated as
    not-filled-in and skipped silently (the marketer used fewer than N quotes)."""
    pfx = prefix.strip().lower()
    entries: list[dict] = []
    order = 0
    for row in rows:
        props = row.get("properties") or {}
        row_id = row.get("id")
        created_time = row.get("created_time")
        for i in range(1, max_groups + 1):
            base = f"{pfx} {i}:"
            quote = prop_plain_text(prop_by_norm_name(props, f"{base} text"))
            if not quote.strip():
                continue
            order += 1
            entries.append(
                build_entry(
                    row_id,
                    created_time,
                    float(order),
                    quote,
                    prop_plain_text(prop_by_norm_name(props, f"{base} customer name")),
                    prop_plain_text(prop_by_norm_name(props, f"{base} customer title")),
                    prop_plain_text(prop_by_norm_name(props, f"{base} company name")),
                    prop_first_file_url(prop_by_norm_name(props, f"{base} photo")),
                    prop_plain_text(prop_by_norm_name(props, f"{base} linkedin url")),
                    out_dir,
                )
            )
    return entries


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Resolve customer-quote rows from a Notion database into per-row avatar "
            "files. Locate the DB either inline on a page (legacy --page-id/--child-db-name) "
            "or directly by id (--database-id, e.g. a per-step form-inputs database placed as "
            "a full-page child). With --explode-groups, read N numbered quote groups from a "
            "single form-submission row instead of one row per quote."
        )
    )
    ap.add_argument("--api-key", required=True, help="Notion integration token")
    ap.add_argument(
        "--database-id",
        help="Query this database directly (skip the page-body scan). Use for a per-step "
        "form-inputs database placed as a full-page child of the card.",
    )
    ap.add_argument(
        "--page-id",
        help="Notion page ID holding an inline child database (legacy locator; ignored when "
        "--database-id is given)",
    )
    ap.add_argument(
        "--child-db-name",
        default="Customer Quotes",
        help="Title of the inline child database to read (legacy locator; default: 'Customer Quotes')",
    )
    ap.add_argument(
        "--latest-only",
        action="store_true",
        help="Keep only the most recent row (by created_time). Forms accumulate one row per "
        "submission; this selects the latest submission.",
    )
    ap.add_argument(
        "--explode-groups",
        action="store_true",
        help="Read N numbered quote groups (`<group-prefix> i: ...`) from each row instead of "
        "treating each row as one quote.",
    )
    ap.add_argument(
        "--group-prefix",
        default="Customer Quote",
        help="Field-group name prefix for --explode-groups (default: 'Customer Quote')",
    )
    ap.add_argument(
        "--max-groups",
        type=int,
        default=4,
        help="Number of numbered groups to read for --explode-groups (default: 4)",
    )
    ap.add_argument("--output-dir", required=True, help="Absolute dir to write resolved photo files into")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        die(4, f"--output-dir must be absolute: {args.output_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.database_id:
        db_id = args.database_id.replace("-", "")
        raw_rows = query_db_rows(args.api_key, db_id)
    elif args.page_id:
        db_id, raw_rows = rows_from_child_db(args.api_key, args.page_id, args.child_db_name)
    else:
        die(4, "provide either --database-id or --page-id")

    if args.latest_only and raw_rows:
        raw_rows = [max(raw_rows, key=lambda r: r.get("created_time") or "")]

    if args.explode_groups:
        enriched = explode_numbered_groups(raw_rows, args.group_prefix, args.max_groups, out_dir)
    else:
        enriched = []
        for row in raw_rows:
            props = row.get("properties") or {}
            enriched.append(
                build_entry(
                    row.get("id"),
                    row.get("created_time"),
                    prop_number(prop_by_norm_name(props, PROP_ORDER)),
                    prop_plain_text(prop_by_norm_name(props, PROP_QUOTE)),
                    prop_plain_text(prop_by_norm_name(props, PROP_CUSTOMER_NAME)),
                    prop_plain_text(prop_by_norm_name(props, PROP_CUSTOMER_TITLE)),
                    prop_plain_text(prop_by_norm_name(props, PROP_COMPANY)),
                    prop_first_file_url(prop_by_norm_name(props, PROP_PHOTO)),
                    prop_plain_text(prop_by_norm_name(props, PROP_LINKEDIN)),
                    out_dir,
                )
            )

    # Sort by order (None last) then created_time. Exploder entries already carry
    # a sequential order; legacy rows may have a null Order and sort last.
    def sort_key(r: dict) -> tuple:
        o = r.get("order")
        return (o is None, o if o is not None else 0, r.get("created_time") or "")

    enriched.sort(key=sort_key)

    print(json.dumps({"child_db_id": db_id, "rows": enriched}))


if __name__ == "__main__":
    main()
