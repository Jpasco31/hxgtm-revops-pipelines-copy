#!/usr/bin/env python3
"""
materialise_ephemeral_input.py

Convert a URL or inline paste into a `.md` tempfile under
`/tmp/kb-update-raw/<run-id>/` that the batch pipeline can consume
alongside raw-dir files and chat attachments.

Usage:
  # URL mode — orchestrator has ALREADY fetched the body via WebFetch /
  # Glean and is passing the markdown on stdin. Filename slug is derived
  # from the URL for filename_prefix scoping compatibility.
  python3 materialise_ephemeral_input.py url \
      --url <https://...> --run-id <run-uuid> \
      [--competitor <stem>] [--date <YYYY-MM-DD>] < body.md

  # Inline paste — body on stdin.
  python3 materialise_ephemeral_input.py inline \
      --run-id <run-uuid> [--date <YYYY-MM-DD>] < body.md

Prints the absolute path of the materialised file on stdout.

URL filename convention:
  <competitor-or-domain-slug>-url-<short-path-slug>-<YYYY-MM-DD>.md

The competitor slug is critical for the `filename_prefix` scoping
strategy (competitive group). Callers who have already resolved the
entity (e.g. Sixfold from a sixfold.ai URL) should pass --competitor
explicitly. Otherwise the script derives a slug from the URL's first
domain label, which matches entity canon stems in most cases but not
all (e.g. `www.sixfold.ai` → `sixfold`, `artificialai.com` → `artificial`).

Exit 0 on success, 1 on structural failure. Stdlib only.
"""

import argparse
import os
import re
import sys
from datetime import date as _date
from pathlib import Path
from urllib.parse import urlparse


def _slugify(text: str, max_len: int = 40) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "untitled"


def _domain_stem(url: str) -> str:
    host = urlparse(url).netloc
    host = host.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    # First label, stripping common suffixes like `ai`, `io`, `com`
    # only if there are 2+ labels. `sixfold.ai` → `sixfold`.
    parts = host.split(".")
    if len(parts) >= 2:
        return parts[0]
    return host or "url"


def _url_path_slug(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return "root"
    # Take the last path segment — usually the post slug.
    return _slugify(path.split("/")[-1], max_len=60)


def _run_dir(run_id: str) -> Path:
    d = Path("/tmp") / "kb-update-raw" / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def cmd_url(args):
    body = sys.stdin.read()
    if not body.strip():
        raise SystemExit("materialise_ephemeral_input: empty stdin for url mode")
    competitor = args.competitor or _domain_stem(args.url)
    competitor_slug = _slugify(competitor, max_len=30)
    path_slug = _url_path_slug(args.url)
    run_date = args.date or _date.today().isoformat()
    filename = f"{competitor_slug}-url-{path_slug}-{run_date}.md"
    out_path = _run_dir(args.run_id) / filename
    out_path.write_text(body, encoding="utf-8")
    print(str(out_path))
    return 0


def cmd_inline(args):
    body = sys.stdin.read()
    if not body.strip():
        raise SystemExit("materialise_ephemeral_input: empty stdin for inline mode")
    run_date = args.date or _date.today().isoformat()
    filename = f"inline-paste-{run_date}.md"
    out_path = _run_dir(args.run_id) / filename
    out_path.write_text(body, encoding="utf-8")
    print(str(out_path))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("url")
    p1.add_argument("--url", required=True)
    p1.add_argument("--run-id", required=True)
    p1.add_argument("--competitor", default=None)
    p1.add_argument("--date", default=None)
    p1.set_defaults(func=cmd_url)

    p2 = sub.add_parser("inline")
    p2.add_argument("--run-id", required=True)
    p2.add_argument("--date", default=None)
    p2.set_defaults(func=cmd_inline)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
