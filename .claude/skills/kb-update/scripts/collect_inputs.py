#!/usr/bin/env python3
"""
collect_inputs.py

Raw-dir input discovery and INDEX.md writeback for kb-update. Two
subcommands:

  list-eligible --group <slug> [--repo-root <path>]

    Parse raw/<slug>/INDEX.md and emit a JSON object listing every raw
    .md file under the group's raw directory, classified as:
      - eligible:   Process? == 'yes' AND Last processed is blank
                    (these get unioned into the batch)
      - skipped:    Process? == 'no' (reference-only; ignored)
      - already_processed: Process? == 'yes' AND Last processed has
                    a non-blank value (ignored for this run)
      - missing_from_index: file exists under raw/<slug>/ but no
                    INDEX.md row matches. Treated as eligible but
                    surfaced with a warning so the operator can backfill
                    INDEX.md.

    Paths in the output are absolute.

  stamp-processed --group <slug> --date <YYYY-MM-DD> \
                  --files <rel_path_1,rel_path_2,...>
                  [--repo-root <path>]

    Edit raw/<slug>/INDEX.md in place: for every row whose File cell
    matches one of --files (path relative to raw/<slug>/), set the
    Last processed cell to --date. Atomic via write-to-temp + os.replace.
    Files listed in --files but missing from INDEX.md are appended as
    new rows with Added = <today's date>, Last processed = <date>,
    Process? = yes. Prints a short summary to stdout.

Exit 0 on success, 1 on structural failure (INDEX.md missing, raw dir
missing, group not in config, malformed table). Stdlib only.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import date as _date
from pathlib import Path


CONVERTIBLE_EXTS = {".pdf", ".docx"}
SOURCE_EXTS = {".md"} | CONVERTIBLE_EXTS


# ----- config.yaml helpers (pattern shared with publish_to_notion.py) -----


def _read_yaml_scalar(path, key_path):
    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    path_stack = []
    for raw in lines:
        stripped = raw.rstrip("\n")
        if not stripped.strip() or stripped.strip().startswith("#"):
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        content = stripped.strip()
        if ":" not in content:
            continue
        key, _, value = content.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        while path_stack and path_stack[-1][1] >= indent:
            path_stack.pop()
        path_stack.append((key, indent))
        current_keys = tuple(k for k, _ in path_stack)
        if current_keys == key_path and value:
            return value
    return None


def _resolve_raw_dir(repo_root: Path, group: str) -> Path:
    config_path = repo_root / ".claude" / "skills" / "kb-update" / "config.yaml"
    if not config_path.exists():
        raise SystemExit(f"config.yaml not found at {config_path}")
    raw_rel = _read_yaml_scalar(config_path, ("groups", group, "raw"))
    if not raw_rel:
        raise SystemExit(
            f"group '{group}' has no 'raw' entry in {config_path} — "
            "check config.yaml or pass --group <known slug>"
        )
    return (repo_root / raw_rel).resolve()


# ----- INDEX.md parser -----


def _parse_index_table(index_path: Path):
    """
    Return (header_cells, rows, raw_lines) where rows is a list of dicts
    keyed by header name with 'File', 'Added', 'Last processed', 'Process?'
    cells. raw_lines is the full file content (list of strings incl. '\n')
    used by the writeback path to preserve formatting.

    Tolerant of header variations: matches by lowercased header text.
    Returns (None, [], raw_lines) if no table is detected.
    """
    if not index_path.exists():
        return None, [], []
    with index_path.open("r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    header_cells = None
    sep_line_idx = None
    # INDEX.md can contain a legend table before the data table. Prefer
    # a table whose header includes a "File" column; fall back to the
    # first pipe-row-with-separator if no such match exists.
    first_match = None
    for i, line in enumerate(raw_lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if i + 1 >= len(raw_lines):
            continue
        nxt = raw_lines[i + 1].strip()
        if not (nxt.startswith("|") and set(nxt.replace("|", "").strip()) <= set("-: ")):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        cells_lower = [c.lower() for c in cells]
        if first_match is None:
            first_match = (cells, i + 1)
        if "file" in cells_lower:
            header_cells = cells
            sep_line_idx = i + 1
            break
    if header_cells is None and first_match is not None:
        header_cells, sep_line_idx = first_match
    if header_cells is None:
        return None, [], raw_lines

    header_lower = [h.lower() for h in header_cells]
    rows = []
    for i in range(sep_line_idx + 1, len(raw_lines)):
        line = raw_lines[i]
        stripped = line.strip()
        if not stripped.startswith("|"):
            break  # table ended
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        while len(cells) < len(header_cells):
            cells.append("")
        row = {header_cells[j]: cells[j] for j in range(len(header_cells))}
        row["_line_idx"] = i
        row["_lower"] = {header_lower[j]: cells[j] for j in range(len(header_cells))}
        rows.append(row)
    return header_cells, rows, raw_lines


def _list_source_files_recursive(raw_dir: Path):
    """Return a sorted list of source file paths (.md, .pdf, .docx)
    relative to raw_dir, excluding INDEX.md and any sidecar files
    that look like `<source>.pdf.md` or `<source>.docx.md`. Recurses
    into typed subfolders."""
    if not raw_dir.exists():
        return []
    # Build a set of sidecar filenames to exclude — when foo.pdf and
    # foo.pdf.md both exist, we want only foo.pdf in the listing.
    sidecars = set()
    for p in raw_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() != ".md":
            continue
        # Strip the .md and check whether the remainder is a real source file.
        stem_with_ext = p.with_suffix("")  # /path/foo.pdf
        if stem_with_ext.suffix.lower() in CONVERTIBLE_EXTS and stem_with_ext.exists():
            sidecars.add(p.resolve())

    out = []
    for p in raw_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.name == "INDEX.md":
            continue
        if p.suffix.lower() not in SOURCE_EXTS:
            continue
        if p.resolve() in sidecars:
            continue
        out.append(p.relative_to(raw_dir).as_posix())
    out.sort()
    return out


# Back-compat alias for any external callers.
_list_md_files_recursive = _list_source_files_recursive


def _convert_script_path() -> Path:
    return Path(__file__).resolve().parent / "convert_to_markdown.py"


def _ensure_sidecar(source_abs: Path) -> Path:
    """For a .pdf/.docx source, run convert_to_markdown.py to (re)build
    the sidecar `<source>.md` next to the source. Returns the sidecar
    Path. Raises SystemExit on conversion failure with the converter's
    stderr surfaced."""
    sidecar = source_abs.parent / (source_abs.name + ".md")
    proc = subprocess.run(
        ["python3", str(_convert_script_path()),
         "--input", str(source_abs), "--output", str(sidecar)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(
            f"convert_to_markdown.py failed for {source_abs.name} "
            f"(exit {proc.returncode}):\n{proc.stderr}"
        )
        raise SystemExit(1)
    return sidecar


# ----- list-eligible -----


def _build_record_lite(raw_dir: Path, fname: str, proc: str, last: str, disk_set):
    """Build a record without triggering sidecar conversion. For
    skipped/already-processed rows where we won't read the file."""
    source_abs = (raw_dir / fname).resolve()
    return {
        "file": fname,
        "abs_path": str(source_abs),
        "diff_path": str(source_abs),
        "exists_on_disk": fname in disk_set,
        "process": proc or "yes",
        "last_processed": last,
    }


def cmd_list_eligible(args):
    repo_root = Path(args.repo_root).resolve()
    raw_dir = _resolve_raw_dir(repo_root, args.group)

    header_cells, rows, _ = _parse_index_table(raw_dir / "INDEX.md")
    disk_files = _list_source_files_recursive(raw_dir)
    disk_set = set(disk_files)

    # Locate columns case-insensitively.
    col_file = col_last = col_process = None
    if header_cells:
        for h in header_cells:
            hl = h.lower()
            if hl == "file":
                col_file = h
            elif hl == "last processed":
                col_last = h
            elif hl == "process?":
                col_process = h

    def _build_record(fname: str, proc: str, last: str):
        source_abs = (raw_dir / fname).resolve()
        ext = source_abs.suffix.lower()
        rec = {
            "file": fname,
            "abs_path": str(source_abs),
            "diff_path": str(source_abs),
            "exists_on_disk": fname in disk_set,
            "process": proc or "yes",
            "last_processed": last,
        }
        # For .pdf / .docx, materialise a sidecar .md and point diff_path at it.
        if ext in CONVERTIBLE_EXTS and rec["exists_on_disk"]:
            sidecar = _ensure_sidecar(source_abs)
            rec["diff_path"] = str(sidecar)
        return rec

    eligible = []
    skipped_process_no = []
    already_processed = []
    missing_from_index = []
    indexed_set = set()

    for row in rows or []:
        fname = row.get(col_file, "") if col_file else ""
        if not fname:
            continue
        indexed_set.add(fname)
        proc = (row.get(col_process, "") if col_process else "").lower()
        last = row.get(col_last, "").strip() if col_last else ""
        if proc == "no":
            skipped_process_no.append(_build_record_lite(raw_dir, fname, proc, last, disk_set))
        elif last:
            already_processed.append(_build_record_lite(raw_dir, fname, proc, last, disk_set))
        else:
            record = _build_record(fname, proc, last)
            if record["exists_on_disk"]:
                eligible.append(record)

    # Files physically present under raw/<slug>/ that have no INDEX.md row.
    for f in disk_files:
        if f not in indexed_set:
            missing_from_index.append(_build_record(f, "yes", ""))

    # Missing-from-index files are treated as eligible but surfaced
    # with the warning so the operator can backfill INDEX.md.
    output = {
        "group": args.group,
        "raw_dir": str(raw_dir),
        "index_exists": (raw_dir / "INDEX.md").exists(),
        "eligible": eligible + missing_from_index,
        "skipped_process_no": skipped_process_no,
        "already_processed": already_processed,
        "missing_from_index": missing_from_index,
        "counts": {
            "eligible": len(eligible) + len(missing_from_index),
            "skipped_process_no": len(skipped_process_no),
            "already_processed": len(already_processed),
            "missing_from_index": len(missing_from_index),
            "total_on_disk": len(disk_files),
        },
    }
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


# ----- stamp-processed -----


def _rewrite_row_last_processed(line: str, header_cells, col_name: str, value: str) -> str:
    """Rewrite a single table row's 'Last processed' cell, preserving
    leading/trailing whitespace pattern as closely as practical."""
    if not line.strip().startswith("|"):
        return line
    # Split preserving the outer pipes.
    # Format: `| c1 | c2 | c3 | c4 |\n`
    trailing = ""
    body = line
    if body.endswith("\n"):
        trailing = "\n"
        body = body[:-1]
    # Strip outer pipes for splitting, then re-add.
    inner = body
    leading_pipe = inner.startswith("|")
    trailing_pipe = inner.endswith("|")
    if leading_pipe:
        inner = inner[1:]
    if trailing_pipe:
        inner = inner[:-1]
    cells = inner.split("|")
    if len(cells) < len(header_cells):
        return line  # malformed; skip
    idx = header_cells.index(col_name)
    # Preserve one leading + one trailing space convention used by
    # INDEX.md today (`| text |`). Avoid rewriting cells we aren't
    # targeting.
    cells[idx] = f" {value} "
    new_inner = "|".join(cells)
    rebuilt = (
        ("|" if leading_pipe else "")
        + new_inner
        + ("|" if trailing_pipe else "")
        + trailing
    )
    return rebuilt


def cmd_stamp_processed(args):
    repo_root = Path(args.repo_root).resolve()
    raw_dir = _resolve_raw_dir(repo_root, args.group)
    index_path = raw_dir / "INDEX.md"

    targets = [f.strip() for f in args.files.split(",") if f.strip()]
    if not targets:
        print(json.dumps({"updated": 0, "appended": 0, "reason": "no files"}))
        return 0

    header_cells, rows, raw_lines = _parse_index_table(index_path)
    if header_cells is None:
        raise SystemExit(
            f"INDEX.md has no parseable table at {index_path} — "
            "cannot stamp. Add a header row with at least "
            "`File | Added | Last processed | Process?`."
        )

    col_file = col_last = col_added = col_process = None
    for h in header_cells:
        hl = h.lower()
        if hl == "file":
            col_file = h
        elif hl == "last processed":
            col_last = h
        elif hl == "added":
            col_added = h
        elif hl == "process?":
            col_process = h
    if not col_file or not col_last:
        raise SystemExit(
            f"INDEX.md at {index_path} is missing required columns "
            "'File' and 'Last processed'. Refusing to stamp."
        )

    existing_by_file = {row[col_file]: row for row in rows}

    updated = []
    for target in targets:
        row = existing_by_file.get(target)
        if row is None:
            continue
        i = row["_line_idx"]
        raw_lines[i] = _rewrite_row_last_processed(
            raw_lines[i], header_cells, col_last, args.date
        )
        updated.append(target)

    # Append missing rows at the end of the existing table block.
    appended = []
    missing = [t for t in targets if t not in existing_by_file]
    if missing and rows:
        last_table_line_idx = max(r["_line_idx"] for r in rows)
        insertion_point = last_table_line_idx + 1
        new_rows_text = []
        today_iso = _date.today().isoformat()
        for target in missing:
            cells = []
            for h in header_cells:
                hl = h.lower()
                if hl == "file":
                    cells.append(f" {target} ")
                elif hl == "added":
                    cells.append(f" {today_iso} ")
                elif hl == "last processed":
                    cells.append(f" {args.date} ")
                elif hl == "process?":
                    cells.append(" yes ")
                else:
                    cells.append("  ")
            new_rows_text.append("|" + "|".join(cells) + "|\n")
            appended.append(target)
        raw_lines = raw_lines[:insertion_point] + new_rows_text + raw_lines[insertion_point:]
    elif missing:
        # Table exists but has zero data rows — append after separator.
        # Rare enough that we just print a warning and skip.
        print(
            f"warning: {len(missing)} files missing from INDEX.md with no "
            "existing data rows to anchor insertion; not appended.",
            file=sys.stderr,
        )

    # Atomic write.
    fd, tmp_path = tempfile.mkstemp(dir=str(index_path.parent), prefix="INDEX.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(raw_lines)
        os.replace(tmp_path, index_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    summary = {
        "updated": len(updated),
        "appended": len(appended),
        "updated_files": updated,
        "appended_files": appended,
        "requested_but_missing": [t for t in missing if t not in appended],
    }
    print(json.dumps(summary, indent=2))
    return 0


def _default_repo_root():
    # The script lives at <repo>/.claude/skills/kb-update/scripts/<file>.
    return str(Path(__file__).resolve().parents[4])


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("list-eligible")
    p1.add_argument("--group", required=True)
    p1.add_argument("--repo-root", default=_default_repo_root())
    p1.set_defaults(func=cmd_list_eligible)

    p2 = sub.add_parser("stamp-processed")
    p2.add_argument("--group", required=True)
    p2.add_argument("--date", required=True, help="YYYY-MM-DD")
    p2.add_argument(
        "--files",
        required=True,
        help="Comma-separated list of file paths relative to raw/<slug>/",
    )
    p2.add_argument("--repo-root", default=_default_repo_root())
    p2.set_defaults(func=cmd_stamp_processed)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
