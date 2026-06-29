#!/usr/bin/env python3
"""
Aggregate the per-account summary objects returned by the dossier-feedback
sweep-mode subagents into:

  dossier-feedback/_routine-summary.md
  dossier-feedback/_routine-state.json
  dossier-feedback/_routine-errors.md  (only when there are errors)

Reads a JSON array of subagent return objects on stdin:

  [
    {"account": "...", "slug": "...", "status": "ok",
     "entries_count": 12, "anchor_failures": 1, "elapsed_ms": 4321,
     "last_dossier_edited_at": "2026-04-28T22:11:00Z", "error": null},
    ...
  ]

State-merge semantics:
  - For status in {ok, no-comments, skipped-unchanged}: write
    last_dossier_edited_at and last_run_at (this run's UTC now).
  - For status == error: PRESERVE the prior last_dossier_edited_at if
    we have one; do NOT advance last_run_at (so the next run retries).
    The aggregator will, however, record last_error and last_error_at
    on the account so operators can see what happened.

Usage:
  python3 aggregate_routine_summary.py \
      --out-dir dossier-feedback \
      --state-file dossier-feedback/_routine-state.json
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VALID_STATUSES = {"ok", "skipped-unchanged", "no-comments", "error"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "accounts": {}}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "accounts": {}}
    if not isinstance(data, dict):
        return {"version": 1, "accounts": {}}
    if "accounts" not in data or not isinstance(data["accounts"], dict):
        data["accounts"] = {}
    data.setdefault("version", 1)
    return data


def merge_state(prior: dict, summaries: list, run_at: str) -> dict:
    accounts = prior.get("accounts") or {}
    for s in summaries:
        slug = s.get("slug")
        if not slug:
            continue
        prev = accounts.get(slug) or {}
        status = s.get("status")
        if status not in VALID_STATUSES:
            status = "error"

        record = dict(prev)
        record["name"] = s.get("account") or prev.get("name") or slug
        record["last_status"] = status

        if status == "error":
            record["last_error"] = (s.get("error") or "")[:500]
            record["last_error_at"] = run_at
        else:
            edited = s.get("last_dossier_edited_at") or ""
            if edited:
                record["last_dossier_edited_at"] = edited
            record["last_run_at"] = run_at
            record.pop("last_error", None)
            record.pop("last_error_at", None)

        accounts[slug] = record

    return {
        "version": prior.get("version", 1),
        "last_sweep_at": run_at,
        "accounts": accounts,
    }


def render_summary(summaries: list, run_at: str) -> str:
    counts = {"ok": 0, "skipped-unchanged": 0, "no-comments": 0, "error": 0}
    for s in summaries:
        status = s.get("status")
        if status not in counts:
            status = "error"
        counts[status] += 1

    total = len(summaries)
    lines = [
        "# Dossier-feedback sweep summary",
        "",
        f"**Run:** {run_at}",
        f"**Accounts processed:** {total}",
        "",
        "## Totals",
        "",
        f"- ok: {counts['ok']}",
        f"- skipped-unchanged: {counts['skipped-unchanged']}",
        f"- no-comments: {counts['no-comments']}",
        f"- error: {counts['error']}",
        "",
        "## Per-account results",
        "",
        "| Account | Slug | Status | Entries | Anchor failures | Elapsed (ms) | Error |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in sorted(summaries, key=lambda r: (r.get("account") or "").lower()):
        err = (s.get("error") or "").replace("|", "\\|")
        if len(err) > 120:
            err = err[:117] + "..."
        lines.append(
            "| {acct} | {slug} | {status} | {entries} | {anch} | {ms} | {err} |".format(
                acct=s.get("account") or "",
                slug=s.get("slug") or "",
                status=s.get("status") or "",
                entries=s.get("entries_count") or 0,
                anch=s.get("anchor_failures") or 0,
                ms=s.get("elapsed_ms") or 0,
                err=err or "—",
            )
        )
    return "\n".join(lines) + "\n"


def render_errors(summaries: list, run_at: str) -> str:
    err_rows = [s for s in summaries if (s.get("status") == "error")]
    if not err_rows:
        return ""
    lines = [
        "# Dossier-feedback sweep errors",
        "",
        f"**Run:** {run_at}",
        f"**Errored accounts:** {len(err_rows)}",
        "",
        "| Account | Slug | Error |",
        "|---|---|---|",
    ]
    for s in sorted(err_rows, key=lambda r: (r.get("account") or "").lower()):
        err = (s.get("error") or "").replace("|", "\\|")
        if len(err) > 500:
            err = err[:497] + "..."
        lines.append(
            f"| {s.get('account') or ''} | {s.get('slug') or ''} | {err or 'unknown'} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="dossier-feedback")
    parser.add_argument(
        "--state-file",
        default="dossier-feedback/_routine-state.json",
    )
    args = parser.parse_args()

    raw = sys.stdin.read().strip()
    if not raw:
        print("no summaries on stdin", file=sys.stderr)
        return 1
    try:
        summaries = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"failed to parse stdin: {e}", file=sys.stderr)
        return 1
    if not isinstance(summaries, list):
        print("stdin JSON must be an array", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state_file)

    run_at = _utc_now_iso()

    prior = load_state(state_path)
    merged = merge_state(prior, summaries, run_at)
    atomic_write(state_path, json.dumps(merged, indent=2) + "\n")

    summary_path = out_dir / "_routine-summary.md"
    atomic_write(summary_path, render_summary(summaries, run_at))

    errors_md = render_errors(summaries, run_at)
    errors_path = out_dir / "_routine-errors.md"
    if errors_md:
        atomic_write(errors_path, errors_md)
    else:
        if errors_path.exists():
            try:
                errors_path.unlink()
            except OSError:
                pass

    print(
        json.dumps(
            {
                "summary": str(summary_path),
                "state": str(state_path),
                "errors": str(errors_path) if errors_md else None,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
