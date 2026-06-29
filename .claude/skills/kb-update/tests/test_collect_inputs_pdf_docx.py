#!/usr/bin/env python3
"""
test_collect_inputs_pdf_docx.py

End-to-end check that collect_inputs.py:
  - lists .pdf / .docx eligible rows alongside .md
  - materialises a sidecar .md next to .pdf / .docx sources
  - returns a `diff_path` that points at the sidecar (not the source)
  - keeps `file` (the INDEX.md key) as the original source name
  - excludes the sidecar from the disk listing (no double-counting)

Run:
  python3 .claude/skills/kb-update/tests/test_collect_inputs_pdf_docx.py
"""

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
COLLECT_SCRIPT = REPO_ROOT / "skills" / "kb-update" / "scripts" / "collect_inputs.py"


PASSED = []
FAILED = []


def case(name):
    def deco(fn):
        try:
            fn()
        except AssertionError as exc:
            FAILED.append((name, str(exc)))
            print(f"[FAIL] {name}: {exc}")
            return fn
        PASSED.append(name)
        print(f"[PASS] {name}")
        return fn
    return deco


def _build_repo_with_group(td: Path, group: str = "competitive") -> Path:
    """Set up a fake repo root with config.yaml + raw/<group>/ dir."""
    repo = td / "repo"
    (repo / "skills" / "kb-update").mkdir(parents=True)
    (repo / f"raw/{group}").mkdir(parents=True)
    (repo / "skills" / "kb-update" / "config.yaml").write_text(textwrap.dedent(f"""\
        groups:
          {group}:
            raw: raw/{group}
        """))
    return repo


def _make_docx(parent: Path, name: str, body: str) -> Path:
    md = parent / "src.md"
    md.write_text(body)
    out = parent / name
    proc = subprocess.run(
        ["pandoc", str(md), "-o", str(out)],
        capture_output=True, text=True,
    )
    md.unlink()
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"pandoc failed building DOCX fixture: {proc.stderr}")
    return out


def _run_list_eligible(repo: Path, group: str):
    proc = subprocess.run(
        ["python3", str(COLLECT_SCRIPT), "list-eligible",
         "--group", group, "--repo-root", str(repo)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"list-eligible failed: {proc.stderr}"
    return json.loads(proc.stdout)


# ---------------------------------------------------------------------------


@case("docx source produces sidecar + diff_path")
def t_docx():
    if shutil.which("pandoc") is None:
        print("    (skipped — pandoc not on PATH)")
        return
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        repo = _build_repo_with_group(td)
        raw = repo / "raw" / "competitive"
        # Create a .docx source.
        body = "# Sample\n\n" + ("Real text content. " * 20)
        docx = _make_docx(raw, "sample-brief.docx", body)
        # INDEX.md with header + one row.
        (raw / "INDEX.md").write_text(textwrap.dedent("""\
            # raw/competitive/

            | File | Added | Last processed | Process? |
            |---|---|---|---|
            | sample-brief.docx | 2026-04-27 |  | yes |
            """))
        result = _run_list_eligible(repo, "competitive")
        eligible = result["eligible"]
        assert len(eligible) == 1, f"expected 1 eligible, got {len(eligible)}: {eligible}"
        rec = eligible[0]
        assert rec["file"] == "sample-brief.docx", \
            f"file should be source name; got {rec['file']!r}"
        assert rec["diff_path"].endswith("sample-brief.docx.md"), \
            f"diff_path should be sidecar; got {rec['diff_path']!r}"
        assert rec["abs_path"].endswith("sample-brief.docx"), \
            f"abs_path should be source; got {rec['abs_path']!r}"
        # Sidecar exists.
        sidecar = raw / "sample-brief.docx.md"
        assert sidecar.exists(), "sidecar .md was not written"
        # Sidecar has the provenance comment.
        text = sidecar.read_text()
        assert text.startswith("<!-- kb-update conversion"), \
            f"sidecar missing provenance: {text[:200]!r}"


@case("sidecar excluded from disk listing (no double-count)")
def t_no_double_count():
    if shutil.which("pandoc") is None:
        return
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        repo = _build_repo_with_group(td)
        raw = repo / "raw" / "competitive"
        body = "# Sample\n\n" + ("Body text. " * 20)
        _make_docx(raw, "x.docx", body)
        # Pre-create the sidecar (simulating a previous run).
        (raw / "x.docx.md").write_text("<!-- old sidecar -->\n")
        # INDEX.md with row for x.docx only.
        (raw / "INDEX.md").write_text(textwrap.dedent("""\
            | File | Added | Last processed | Process? |
            |---|---|---|---|
            | x.docx | 2026-04-27 |  | yes |
            """))
        result = _run_list_eligible(repo, "competitive")
        # Total on disk should be 1 (the .docx; the .md sidecar excluded).
        assert result["counts"]["total_on_disk"] == 1, \
            f"expected total_on_disk=1, got {result['counts']['total_on_disk']}; " \
            f"missing_from_index: {result['missing_from_index']}"
        assert len(result["missing_from_index"]) == 0, \
            f"sidecar should not appear as missing_from_index: " \
            f"{result['missing_from_index']}"


@case("plain .md file gets diff_path == abs_path")
def t_md_passthrough():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        repo = _build_repo_with_group(td)
        raw = repo / "raw" / "competitive"
        (raw / "note.md").write_text("# note\n\nbody\n")
        (raw / "INDEX.md").write_text(textwrap.dedent("""\
            | File | Added | Last processed | Process? |
            |---|---|---|---|
            | note.md | 2026-04-27 |  | yes |
            """))
        result = _run_list_eligible(repo, "competitive")
        eligible = result["eligible"]
        assert len(eligible) == 1
        rec = eligible[0]
        assert rec["file"] == "note.md"
        assert rec["abs_path"] == rec["diff_path"], \
            f"md should pass through: abs={rec['abs_path']} diff={rec['diff_path']}"


# ---------------------------------------------------------------------------


def main():
    print()
    print(f"Summary: {len(PASSED)} passed, {len(FAILED)} failed (of "
          f"{len(PASSED) + len(FAILED)})")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
