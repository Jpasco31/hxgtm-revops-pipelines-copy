#!/usr/bin/env python3
"""
Render the dossier-feedback per-account output: two files written
atomically together for every run.

  comment-logs/<slug>.md   — full audit trail (raw comments + interpreted
                              truths + provenance). Human-facing.
  known-truths/<slug>.md   — section-grouped one-line truths only.
                              LLM-consumer-facing (Phase 2 generate-dossier).

Both files share the same frontmatter (account, slug, source_dossier_url,
generated_at, entry_count) and are regenerated from scratch on every run.
History lives in git. The file shapes are documented at
.claude/skills/dossier-feedback/references/output-format.md.

Input shape (stdin, one JSON array):

  [
    {"title": "HQ moved to Schaumburg in 2023",
     "anchor_text": "Headquartered in Zurich, Switzerland …" | null,
     "comment_text": "Wrong — US HQ moved to Schaumburg IL in 2023.",
     "interpreted_truth": "Zurich's US HQ relocated to Schaumburg, IL in 2023.",
     "section_tag": "overview",
     "author": "Sarah Chen",
     "created_time": "2026-04-22T14:11:00Z",
     "resolved": false,
     "discussion_id": "abc..."}
  ]

Required CLI args:
  --account "<display name>"
  --slug   "<kebab-case slug>"
  --source-url "<notion url>"
  --comment-log-out      "<absolute or repo-relative path>"
  --truths-summary-out   "<absolute or repo-relative path>"

On success: prints both resolved output paths (newline-separated) to
stdout, exits 0.
On failure: writes a one-line error to stderr, exits non-zero.
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SECTION_ORDER = (
    "overview",
    "vision-mission",
    "power-players",
    "past-opps",
    "sentiment",
    "discovery",
    "why-anything",
    "untagged",
)
ALLOWED_TAGS = set(SECTION_ORDER)

NO_ANCHOR = "(page-level comment, no anchor)"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _date_only(iso: str) -> str:
    if not iso:
        return ""
    try:
        return iso.split("T", 1)[0]
    except Exception:
        return iso


def _sanitise_oneline(s: str) -> str:
    if not s:
        return ""
    return " ".join(str(s).split()).strip()


def _normalise_tag(tag: str) -> str:
    if tag in ALLOWED_TAGS:
        return tag
    return "untagged"


def _frontmatter(account: str, slug: str, source_url: str, entry_count: int) -> list:
    return [
        "---",
        f'account: "{account}"',
        f"slug: {slug}",
        f"source_dossier_url: {source_url}",
        f"generated_at: {_utc_now_iso()}",
        f"entry_count: {entry_count}",
        "---",
        "",
    ]


def _render_comment_log_entry(entry: dict) -> str:
    title = _sanitise_oneline(entry.get("title")) or "Untitled"
    section_tag = _normalise_tag(entry.get("section_tag") or "untagged")
    anchor_text = entry.get("anchor_text")
    anchor_str = _sanitise_oneline(anchor_text) if anchor_text else NO_ANCHOR
    if not anchor_str:
        anchor_str = NO_ANCHOR
    comment_text = _sanitise_oneline(entry.get("comment_text"))
    interpreted = _sanitise_oneline(entry.get("interpreted_truth"))
    author = _sanitise_oneline(entry.get("author")) or "Unknown"
    date = _date_only(entry.get("created_time") or "")
    resolved = bool(entry.get("resolved"))
    discussion_id = _sanitise_oneline(entry.get("discussion_id"))

    return (
        f"### {title}\n"
        f"- **Section:** {section_tag}\n"
        f"- **Original passage:** {anchor_str}\n"
        f"- **Reviewer comment:** {comment_text}\n"
        f"- **Interpreted truth:** {interpreted}\n"
        f"- **Author / date:** {author} · {date}\n"
        f"- **Resolved:** {'true' if resolved else 'false'}\n"
        f"- **Discussion ID:** {discussion_id}\n"
    )


def render_comment_log(account: str, slug: str, source_url: str, entries: list) -> str:
    parts = _frontmatter(account, slug, source_url, len(entries))
    parts += [
        f"# Known Truths — {account}",
        "",
        "> Full reviewer-comment log derived from human comments on the latest Account Dossier in Notion.",
        f"> Companion to `../known-truths/{slug}.md` (consumer summary). Phase 1: regenerated from scratch on every run; do not hand-edit.",
        "",
        "## Entries",
        "",
    ]
    if entries:
        body = "\n".join(_render_comment_log_entry(e) for e in entries)
        parts.append(body)
    else:
        parts.append("_No entries — this file is a placeholder._")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


# Backwards-compatible alias for callers / tests that imported the
# original function name. The comment log is the direct successor of the
# pre-split single-file output, so its render function keeps the legacy
# name working.
render = render_comment_log


def render_truths_summary(account: str, slug: str, source_url: str, entries: list) -> str:
    parts = _frontmatter(account, slug, source_url, len(entries))
    parts += [
        f"# Known Truths — {account}",
        "",
        "> Synthesised one-line truths from human comments on the latest Account Dossier in Notion.",
        f"> See `../comment-logs/{slug}.md` for the source comments and full provenance.",
        "> Phase 1: regenerated from scratch on every run; do not hand-edit.",
        "",
    ]

    if not entries:
        parts.append("_No entries — this file is a placeholder._")
        parts.append("")
        return "\n".join(parts).rstrip() + "\n"

    grouped = {tag: [] for tag in SECTION_ORDER}
    for entry in entries:
        tag = _normalise_tag(entry.get("section_tag") or "untagged")
        title = _sanitise_oneline(entry.get("title")) or "Untitled"
        truth = _sanitise_oneline(entry.get("interpreted_truth"))
        if not truth:
            continue
        grouped[tag].append(f"- {truth} _(see: {title})_")

    section_blocks = []
    for tag in SECTION_ORDER:
        bullets = grouped[tag]
        if not bullets:
            continue
        section_blocks.append(f"## {tag}")
        section_blocks.append("\n".join(bullets))
        section_blocks.append("")  # blank line between sections

    if not section_blocks:
        parts.append("_No interpreted truths to summarise._")
        parts.append("")
    else:
        parts += section_blocks

    return "\n".join(parts).rstrip() + "\n"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--comment-log-out", required=True,
                        help="Path for the comment-log file (full audit trail).")
    parser.add_argument("--truths-summary-out", required=True,
                        help="Path for the truths-summary file (section-grouped bullets).")
    args = parser.parse_args()

    raw = sys.stdin.read().strip()
    if not raw:
        entries = []
    else:
        try:
            entries = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"failed to parse stdin as JSON array: {e}", file=sys.stderr)
            return 1
        if not isinstance(entries, list):
            print("stdin JSON must be a list of entries", file=sys.stderr)
            return 1

    try:
        comment_log = render_comment_log(args.account, args.slug, args.source_url, entries)
        truths_summary = render_truths_summary(args.account, args.slug, args.source_url, entries)
    except Exception as e:
        print(f"render failed: {e}", file=sys.stderr)
        return 1

    comment_log_path = Path(args.comment_log_out)
    truths_summary_path = Path(args.truths_summary_out)
    try:
        atomic_write(comment_log_path, comment_log)
        atomic_write(truths_summary_path, truths_summary)
    except OSError as e:
        print(f"atomic write failed: {e}", file=sys.stderr)
        return 1

    print(str(comment_log_path))
    print(str(truths_summary_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
