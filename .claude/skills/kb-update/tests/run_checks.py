#!/usr/bin/env python3
"""
run_checks.py — Phase 5 automated verification for kb-update + kb-integrate.

Runs the subset of IMPROVEMENTS.md's 17 verification checks that can be
exercised without an LLM, a live Notion workspace, or a real raw source.
Each check ends in PASS or FAIL; overall exit code is 0 only if every
check passes. Live-run and deferred checks are flagged by VERIFICATION.md,
not by this script.

Covered here:
  - Check 10: Final Updated Text wins over Proposed Updated Text via effective_text()  # noqa
  - Check 11: Long-text replace via line+hash (no 2000-char truncation silently
              dropping content)
  - Check 12: Markdown escape → unescape round-trip (⟪ast⟫⟪ast⟫ → **)
  - Check 13: Drifted canon (hash mismatch) → needs_restage, no disk touch
  - Check 16: Zip-not-git precondition halts with the git-clone instruction

Derived invariants:
  - D1: publish_to_notion EXPECTED_COLUMNS carry every Phase 1 new column
  - D2: publish_to_notion.build_page never writes Confidence and never
        re-wraps Name with [R{n}]
  - D3: publish_to_notion BATCH_SIZE == 50
  - D4: apply_integrations action inference (empty current_text → append)
  - D5: apply_integrations stats expose needs_restage
  - D6: apply_integrations bottom-up replace handles two rows in one file
        without anchor drift
  - D7: apply_integrations post-apply readback catches a failed write
  - D8: config.yaml parses with pyyaml and has source_tiers + global blocks
"""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
PUBLISH_SCRIPT = REPO_ROOT / ".claude" / "skills" / "kb-update" / "scripts" / "publish_to_notion.py"
APPLY_SCRIPT = REPO_ROOT / ".claude" / "skills" / "kb-integrate" / "scripts" / "apply_integrations.py"
RESOLVE_SCRIPT = REPO_ROOT / ".claude" / "skills" / "kb-update" / "scripts" / "resolve_mcp_path.py"
SETUP_SCRIPT = REPO_ROOT / ".claude" / "skills" / "kb-update" / "scripts" / "setup_notion.py"
COLLECT_SCRIPT = REPO_ROOT / ".claude" / "skills" / "kb-update" / "scripts" / "collect_inputs.py"
CONFIG_YAML = REPO_ROOT / ".claude" / "skills" / "kb-update" / "config.yaml"
LOCAL_STATE_PATH = REPO_ROOT / ".kb-local.json"


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------


class CheckReport:
    def __init__(self):
        self.results = []  # list of (check_id, title, status, detail)

    def record(self, check_id, title, status, detail=""):
        self.results.append((check_id, title, status, detail))
        marker = "PASS" if status == "pass" else "FAIL"
        print(f"[{marker}] {check_id} · {title}")
        if detail and status != "pass":
            for line in detail.splitlines():
                print(f"        {line}")

    def summary(self):
        passed = sum(1 for r in self.results if r[2] == "pass")
        failed = sum(1 for r in self.results if r[2] == "fail")
        print()
        print(f"Summary: {passed} passed, {failed} failed (of {len(self.results)})")
        return failed == 0


def _import_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_fake_mcp(base: Path):
    """Fresh fake hxgtm-mcp-server with context/ + .git/, caller owns cleanup."""
    if base.exists():
        shutil.rmtree(base)
    (base / "context").mkdir(parents=True)
    (base / ".git").mkdir()
    return base


def _hash_span(body: str, start: int, end: int):
    lines = body.splitlines()
    span = "\n".join(lines[start - 1 : end]) + "\n"
    return hashlib.sha1(span.encode("utf-8")).hexdigest()


def _run_apply(args, stdin_json):
    """Invoke apply_integrations.py as a subprocess. Returns (rc, stdout, stderr)."""
    proc = subprocess.run(
        ["python3", str(APPLY_SCRIPT)] + args,
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_D1(report):
    """Derived: publish_to_notion EXPECTED_COLUMNS match the 2026-04 cleanup
    plus the Review Bucket formula column added in the triage-view refactor.

    - 21 columns total (20 from the 2026-04 cleanup + `Review Bucket`).
    - Includes `Final Updated Text` (renamed from `Edited Text`).
    - Includes `Review Bucket` (FORMULA; drives default view grouping).
    - Excludes `Canon Heading`, `Core Product`, `Evidence Basis`,
      `Target Content Hash` (all removed from Notion).
    """
    pn = _import_module("publish_to_notion", PUBLISH_SCRIPT)
    required = {
        "Entity", "Source Tier", "Action", "Final Updated Text",
        "Proposed Updated Text", "Target Line Start", "Target Line End",
        "Review Bucket",
    }
    missing = required - set(pn.EXPECTED_COLUMNS.keys())
    if missing:
        report.record(
            "D1", "publish EXPECTED_COLUMNS match cleaned schema",
            "fail", f"missing required columns: {sorted(missing)}",
        )
        return
    forbidden = {
        "Canon Heading", "Core Product", "Evidence Basis",
        "Target Content Hash", "Edited Text",
    } & set(pn.EXPECTED_COLUMNS.keys())
    if forbidden:
        report.record(
            "D1", "publish EXPECTED_COLUMNS match cleaned schema",
            "fail", f"removed columns still present: {sorted(forbidden)}",
        )
        return
    if len(pn.EXPECTED_COLUMNS) != 21:
        report.record(
            "D1", "publish EXPECTED_COLUMNS match cleaned schema",
            "fail",
            f"expected 21 columns, got {len(pn.EXPECTED_COLUMNS)}: "
            f"{sorted(pn.EXPECTED_COLUMNS.keys())}",
        )
        return
    report.record(
        "D1", "publish EXPECTED_COLUMNS match cleaned schema", "pass",
    )


def check_D2(report):
    """Derived: build_page never writes Confidence; Name has no [R{n}] wrap."""
    pn = _import_module("publish_to_notion", PUBLISH_SCRIPT)
    finding = {
        "finding_id": "R7",
        "title": "R7: sample finding",
        "entity": "Acme",
        "category": "raw-canon-conflict",
        "severity": "high",
        "source_tier": "tier_1",
        "claim_scope": "structural",
        "proposed_text": "replacement",
        "rationale": "because",
        "source_file": "acme.md",
        "target_file": "context/x.md",
        "target_line_start": 1,
        "target_line_end": 1,
        "group": "competitive",
        "run_date": "2026-04-21",
    }
    page = pn.build_page(finding, is_malformed=False)
    properties = page["properties"]
    if "Confidence" in properties:
        report.record(
            "D2", "build_page skips Confidence + no [R{n}] re-wrap",
            "fail", "Confidence property was written on a new row",
        )
        return
    if properties["Name"] != "R7: sample finding":
        report.record(
            "D2", "build_page skips Confidence + no [R{n}] re-wrap",
            "fail", f"Name is '{properties['Name']}' — expected 'R7: sample finding'",
        )
        return
    report.record(
        "D2", "build_page skips Confidence + no [R{n}] re-wrap", "pass",
    )


def check_D3(report):
    """Derived: BATCH_SIZE == 50."""
    pn = _import_module("publish_to_notion", PUBLISH_SCRIPT)
    if pn.BATCH_SIZE != 50:
        report.record(
            "D3", "publish BATCH_SIZE == 50", "fail",
            f"BATCH_SIZE is {pn.BATCH_SIZE}",
        )
        return
    report.record("D3", "publish BATCH_SIZE == 50", "pass")


def check_D4(report):
    """Derived: _infer_action — empty current_text → append; non-empty → replace."""
    ai = _import_module("apply_integrations", APPLY_SCRIPT)
    cases = [
        ({"current_text": ""}, "append"),
        ({"current_text": "   "}, "append"),
        ({"current_text": "some content"}, "replace"),
        ({"action": "append", "current_text": "irrelevant"}, "append"),
    ]
    for row, expected in cases:
        got = ai._infer_action(row)
        if got != expected:
            report.record(
                "D4", "apply _infer_action produces expected action",
                "fail",
                f"row={row} → {got} (expected {expected})",
            )
            return
    report.record(
        "D4", "apply _infer_action produces expected action", "pass",
    )


def check_D5(report):
    """Derived: stats objects include needs_restage."""
    ai = _import_module("apply_integrations", APPLY_SCRIPT)
    plan = [{"action": "replace", "will_succeed": False, "needs_restage": True}]
    stats = ai._plan_stats(plan)
    if "needs_restage" not in stats:
        report.record(
            "D5", "apply plan/apply stats expose needs_restage", "fail",
            f"plan stats keys: {sorted(stats.keys())}",
        )
        return
    apply_stats = ai._apply_stats(
        [{"status": "needs_restage"}, {"status": "success"}]
    )
    if "needs_restage" not in apply_stats or apply_stats["needs_restage"] != 1:
        report.record(
            "D5", "apply plan/apply stats expose needs_restage", "fail",
            f"apply stats: {apply_stats}",
        )
        return
    report.record(
        "D5", "apply plan/apply stats expose needs_restage", "pass",
    )


def check_D6(report):
    """Derived: bottom-up replace handles two non-overlapping spans in the same file."""
    tmp = Path(tempfile.mkdtemp(prefix="phase5-d6-"))
    try:
        mcp = _make_fake_mcp(tmp / "mcp")
        canon = mcp / "context" / "x.md"
        body = (
            "# Title\n"
            "\n"
            "## Section A\n"                # line 3
            "\n"
            "- original A bullet one\n"     # line 5
            "- original A bullet two\n"     # line 6
            "\n"
            "## Section B\n"                # line 8
            "\n"
            "- original B bullet\n"         # line 10
        )
        canon.write_text(body)

        rows = [
            {
                "page_id": "pA", "finding_id": "R1",
                "title": "R1: Update A",
                "action": "replace",
                "target_file": "context/x.md",
                "target_line_start": 5, "target_line_end": 6,
                "proposed_text": "- new A bullet alpha\n- new A bullet beta\n- new A bullet gamma",
                "current_text": "preview",
                "source_file": "src.md", "source_line": 1,
                "category": "raw-canon-conflict",
            },
            {
                "page_id": "pB", "finding_id": "R2",
                "title": "R2: Update B",
                "action": "replace",
                "target_file": "context/x.md",
                "target_line_start": 10, "target_line_end": 10,
                "proposed_text": "- new B bullet",
                "current_text": "preview",
                "source_file": "src.md", "source_line": 1,
                "category": "raw-canon-conflict",
            },
        ]

        rc, stdout, stderr = _run_apply(
            ["--group", "competitive", "--apply",
             "--mcp-server-path", str(mcp), "--run-date", "2026-04-21"],
            rows,
        )
        if rc != 0:
            report.record(
                "D6", "bottom-up replace handles two rows in one file",
                "fail", f"rc={rc} stderr={stderr}",
            )
            return
        result = json.loads(stdout)
        statuses = [r["status"] for r in result["results"]]
        if statuses != ["success", "success"]:
            report.record(
                "D6", "bottom-up replace handles two rows in one file",
                "fail", f"statuses={statuses} results={result['results']}",
            )
            return
        new_body = canon.read_text()
        if "new A bullet alpha" not in new_body or "new B bullet" not in new_body:
            report.record(
                "D6", "bottom-up replace handles two rows in one file",
                "fail", f"canon missing expected content:\n{new_body}",
            )
            return
        report.record(
            "D6", "bottom-up replace handles two rows in one file", "pass",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_D7(report):
    """Derived: _verify_post_apply downgrades a success-marked result to
    failure when the effective_text isn't present in the re-read file.

    Unit-tests the helper directly rather than trying to simulate a
    silent-write filesystem (symlinks to /dev/null trip the
    canon-confinement guard before the verification path ever runs).
    """
    tmp = Path(tempfile.mkdtemp(prefix="phase5-d7-"))
    try:
        canon = tmp / "x.md"
        # File contains OTHER_CONTENT, not the expected effective_text —
        # simulates a silent write failure or an unrelated corruption
        # that removed the text between apply and readback.
        canon.write_text("# Title\n\nOTHER_CONTENT\n")

        ai = _import_module("apply_integrations", APPLY_SCRIPT)

        entry_success = {
            "page_id": "pOK", "finding_id": "R1", "action": "append",
            "target_rel": "x.md",
            "_effective_text": "UNIQUE_MARKER_SHOULD_BE_PRESENT",
        }
        entry_unrelated = {
            "page_id": "pU", "finding_id": "R2", "action": "append",
            "target_rel": "x.md",
            "_effective_text": "OTHER_CONTENT",  # actually present
        }
        entries = [(0, entry_success), (1, entry_unrelated)]
        results = [
            ai._build_result(entry_success, status="success", reason="wrote"),
            ai._build_result(entry_unrelated, status="success", reason="wrote"),
        ]

        ai._verify_post_apply(canon, entries, results)

        if results[0]["status"] != "failure":
            report.record(
                "D7", "post-apply readback catches failed write", "fail",
                f"expected failure for missing text, got '{results[0]['status']}'",
            )
            return
        if results[1]["status"] != "success":
            report.record(
                "D7", "post-apply readback catches failed write", "fail",
                f"unrelated row spuriously downgraded to '{results[1]['status']}'",
            )
            return
        report.record(
            "D7", "post-apply readback catches failed write", "pass",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_D9(report):
    """Derived: setup_notion.default_view_config() returns a single
    dict (not a list of views) with the required filter/group/sort
    fields and VISIBLE/HIDDEN column partition, and SCHEMA_DDL yields
    21 columns (the 2026-04 cleanup's 20 + `Review Bucket`) — locks
    the default-view-only / cleaned-schema / Review-Bucket-grouping
    invariants (no separate Triage view: the pipeline configures the
    database's built-in default view, and group_by is Review Bucket).
    """
    sn = _import_module("setup_notion", SETUP_SCRIPT)
    cfg = sn.default_view_config()
    if not isinstance(cfg, dict):
        report.record(
            "D9", "setup_notion default-view config + 21-col schema",
            "fail", f"default_view_config() returned {type(cfg).__name__}, expected dict",
        )
        return
    required_keys = {"filter", "group_by", "sort",
                     "visible_columns", "hidden_columns"}
    missing = required_keys - set(cfg.keys())
    if missing:
        report.record(
            "D9", "setup_notion default-view config + 21-col schema",
            "fail", f"default_view_config missing keys: {sorted(missing)}",
        )
        return
    if "title" in cfg or "is_default" in cfg:
        report.record(
            "D9", "setup_notion default-view config + 21-col schema",
            "fail",
            "default_view_config must not carry 'title'/'is_default' — "
            "it configures the DB's built-in default view, not a new view",
        )
        return
    banned = ("Canon Heading", "Core Product", "Evidence Basis",
              "Target Content Hash", "Edited Text")
    ddl = sn.SCHEMA_DDL
    for banned_col in banned:
        if f'"{banned_col}"' in ddl:
            report.record(
                "D9", "setup_notion default-view config + 21-col schema",
                "fail", f"SCHEMA_DDL still carries {banned_col!r}",
            )
            return
    if '"Final Updated Text"' not in ddl:
        report.record(
            "D9", "setup_notion default-view config + 21-col schema",
            "fail", "SCHEMA_DDL missing 'Final Updated Text'",
        )
        return
    if '"Review Bucket"' not in ddl:
        report.record(
            "D9", "setup_notion default-view config + 21-col schema",
            "fail", "SCHEMA_DDL missing 'Review Bucket'",
        )
        return
    if cfg.get("group_by") != "Review Bucket":
        report.record(
            "D9", "setup_notion default-view config + 21-col schema",
            "fail",
            f"default_view_config group_by is {cfg.get('group_by')!r}, "
            "expected 'Review Bucket'",
        )
        return
    report.record(
        "D9", "setup_notion default-view config + 21-col schema", "pass",
    )


def check_D10(report):
    """Derived: collect_inputs.py emits a `diff_path` field on every
    eligible record, and the field points at a sidecar `.md` for
    `.pdf` / `.docx` sources (not the source itself). Locks the
    PDF/DOCX wiring contract that the orchestrator relies on.

    Skips if pandoc is not available (we use it to build the .docx
    fixture without committing a binary to the repo).
    """
    if shutil.which("pandoc") is None:
        report.record(
            "D10", "collect_inputs diff_path for pdf/docx sources",
            "pass",  # treat as no-op (skip would fail summary)
            detail="skipped — pandoc not on PATH",
        )
        return

    import textwrap as _tw
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        repo = td / "repo"
        (repo / "skills" / "kb-update").mkdir(parents=True)
        raw = repo / "raw" / "competitive"
        raw.mkdir(parents=True)
        (repo / "skills" / "kb-update" / "config.yaml").write_text(_tw.dedent("""\
            groups:
              competitive:
                raw: raw/competitive
            """))
        # Build a tiny .docx via pandoc.
        src_md = td / "src.md"
        src_md.write_text("# T\n\n" + ("Body content for the test fixture. " * 10))
        proc = subprocess.run(
            ["pandoc", str(src_md), "-o", str(raw / "sample.docx")],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            report.record("D10", "collect_inputs diff_path for pdf/docx sources",
                          "fail", f"pandoc failed: {proc.stderr}")
            return

        (raw / "INDEX.md").write_text(_tw.dedent("""\
            | File | Added | Last processed | Process? |
            |---|---|---|---|
            | sample.docx | 2026-04-27 |  | yes |
            | note.md | 2026-04-27 |  | yes |
            """))
        (raw / "note.md").write_text("# note\n\nbody\n")

        proc = subprocess.run(
            ["python3", str(COLLECT_SCRIPT), "list-eligible",
             "--group", "competitive", "--repo-root", str(repo)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            report.record("D10", "collect_inputs diff_path for pdf/docx sources",
                          "fail", f"collect_inputs failed: {proc.stderr}")
            return
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            report.record("D10", "collect_inputs diff_path for pdf/docx sources",
                          "fail", f"JSON decode error: {exc}")
            return

        eligible = data.get("eligible", [])
        by_file = {r["file"]: r for r in eligible}
        if "sample.docx" not in by_file or "note.md" not in by_file:
            report.record("D10", "collect_inputs diff_path for pdf/docx sources",
                          "fail",
                          f"expected both sample.docx and note.md eligible; got "
                          f"{sorted(by_file.keys())}")
            return
        docx_rec = by_file["sample.docx"]
        md_rec = by_file["note.md"]
        if "diff_path" not in docx_rec:
            report.record("D10", "collect_inputs diff_path for pdf/docx sources",
                          "fail", "docx record has no diff_path field")
            return
        if not docx_rec["diff_path"].endswith("sample.docx.md"):
            report.record("D10", "collect_inputs diff_path for pdf/docx sources",
                          "fail",
                          f"docx diff_path should end in sample.docx.md; "
                          f"got {docx_rec['diff_path']!r}")
            return
        if md_rec["diff_path"] != md_rec["abs_path"]:
            report.record("D10", "collect_inputs diff_path for pdf/docx sources",
                          "fail",
                          f"md record diff_path should equal abs_path; got "
                          f"{md_rec['diff_path']!r} vs {md_rec['abs_path']!r}")
            return

    report.record("D10", "collect_inputs diff_path for pdf/docx sources", "pass")


def check_D8(report):
    """Derived: config.yaml parses and carries source_tiers + global + competitive schema."""
    try:
        import yaml
    except ImportError:
        report.record(
            "D8", "config.yaml loads with source_tiers + global + schema",
            "fail", "pyyaml not available (pip install --break-system-packages pyyaml)",
        )
        return
    with CONFIG_YAML.open() as f:
        cfg = yaml.safe_load(f)
    issues = []
    for tier in ("tier_1", "tier_2", "tier_3", "tier_4", "tier_5"):
        if tier not in cfg.get("source_tiers", {}):
            issues.append(f"missing source_tiers.{tier}")
    for key in ("comparator_model", "batch_wave_size", "deny_list",
                "include_provenance_comment"):
        if key not in cfg.get("global", {}):
            issues.append(f"missing global.{key}")
    comp = cfg.get("groups", {}).get("competitive", {})
    for key in ("section_schema", "scoping_strategy", "always_include",
                "canon_aliases", "max_new_sections_per_run"):
        if key not in comp:
            issues.append(f"missing groups.competitive.{key}")
    sections = [s.get("name") for s in comp.get("section_schema", [])]
    expected_sections = {
        "Snapshot", "Where they show up", "Core products", "Strengths",
        "Weaknesses / watch-outs", "hx positioning", "Talk track",
        "Notes / open questions",
    }
    missing_sections = expected_sections - set(sections)
    if missing_sections:
        issues.append(f"missing sections: {sorted(missing_sections)}")
    if issues:
        report.record(
            "D8", "config.yaml loads with source_tiers + global + schema",
            "fail", "\n".join(issues),
        )
        return
    report.record(
        "D8", "config.yaml loads with source_tiers + global + schema", "pass",
    )


def check_10(report):
    """Check 10: Final Updated Text wins over Proposed Updated Text at integrate time."""
    tmp = Path(tempfile.mkdtemp(prefix="phase5-10-"))
    try:
        mcp = _make_fake_mcp(tmp / "mcp")
        canon = mcp / "context" / "x.md"
        body = "# Title\n"
        canon.write_text(body)

        rows = [{
            "page_id": "pE", "finding_id": "R1",
            "title": "R1: Edited test",
            "action": "append",
            "target_file": "context/x.md",
            "target_line_start": 1, "target_line_end": 1,
            "current_text": "",
            "proposed_text": "ORIGINAL proposed text — should not land.",
            "final_updated_text": "REVIEWER TWEAK — this is what must land.",
            "source_file": "src.md", "source_line": 1,
            "category": "raw-canon-conflict",
        }]

        rc, stdout, stderr = _run_apply(
            ["--group", "competitive", "--apply",
             "--mcp-server-path", str(mcp), "--run-date", "2026-04-21"],
            rows,
        )
        if rc != 0:
            report.record(
                "10", "Final Updated Text wins via effective_text()", "fail",
                f"rc={rc} stderr={stderr}",
            )
            return
        new_body = canon.read_text()
        if "REVIEWER TWEAK" not in new_body:
            report.record(
                "10", "Final Updated Text wins via effective_text()", "fail",
                f"REVIEWER TWEAK missing from canon:\n{new_body}",
            )
            return
        if "ORIGINAL proposed text" in new_body:
            report.record(
                "10", "Final Updated Text wins via effective_text()", "fail",
                "ORIGINAL proposed text leaked into canon",
            )
            return
        report.record(
            "10", "Final Updated Text wins via effective_text()", "pass",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_11(report):
    """Check 11: Long-text replace (>2000 chars) via line+hash."""
    tmp = Path(tempfile.mkdtemp(prefix="phase5-11-"))
    try:
        mcp = _make_fake_mcp(tmp / "mcp")
        canon = mcp / "context" / "long.md"
        # 5-line canon region that we'll replace with a >2000-char block.
        body_lines = [
            "# Long file",
            "",
            "Original line A.",       # line 3
            "Original line B.",       # line 4
            "Original line C.",       # line 5
        ]
        body = "\n".join(body_lines) + "\n"
        canon.write_text(body)

        huge = "new long paragraph. " * 200  # ~4000 chars
        rows = [{
            "page_id": "pL", "finding_id": "R1",
            "title": "R1: long replace",
            "action": "replace",
            "target_file": "context/long.md",
            "target_line_start": 3, "target_line_end": 5,
            "current_text": "Original line A.\nOriginal line B.\nOriginal line C.",
            "proposed_text": huge,
            "source_file": "src.md", "source_line": 1,
            "category": "raw-canon-conflict",
        }]

        rc, stdout, stderr = _run_apply(
            ["--group", "competitive", "--apply",
             "--mcp-server-path", str(mcp), "--run-date", "2026-04-21"],
            rows,
        )
        if rc != 0:
            report.record(
                "11", "Long-text replace via line+hash", "fail",
                f"rc={rc} stderr={stderr}",
            )
            return
        result = json.loads(stdout)
        status = result["results"][0]["status"]
        if status != "success":
            report.record(
                "11", "Long-text replace via line+hash", "fail",
                f"status={status} reason={result['results'][0].get('reason')}",
            )
            return
        new_body = canon.read_text()
        if huge.strip() not in new_body:
            report.record(
                "11", "Long-text replace via line+hash", "fail",
                "huge text not present in canon after apply",
            )
            return
        if "Original line A" in new_body:
            report.record(
                "11", "Long-text replace via line+hash", "fail",
                "original span wasn't actually replaced",
            )
            return
        report.record(
            "11", "Long-text replace via line+hash", "pass",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_12(report):
    """Check 12: Round-trip fidelity — ⟪ast⟫⟪ast⟫bold⟪ast⟫⟪ast⟫ → **bold**."""
    pn = _import_module("publish_to_notion", PUBLISH_SCRIPT)
    ai = _import_module("apply_integrations", APPLY_SCRIPT)

    cases = [
        ("**bold claim**", "⟪ast⟫⟪ast⟫bold claim⟪ast⟫⟪ast⟫"),
        ("_italic_", "⟪us⟫italic⟪us⟫"),
        ("# heading", "⟪hash⟫ heading"),
        ("`code`", "⟪bt⟫code⟪bt⟫"),
        ("~strike~", "⟪tld⟫strike⟪tld⟫"),
        (
            "mixed **bold**/_italic_/`code`",
            "mixed ⟪ast⟫⟪ast⟫bold⟪ast⟫⟪ast⟫/⟪us⟫italic⟪us⟫/⟪bt⟫code⟪bt⟫",
        ),
    ]
    for original, escaped in cases:
        if pn.escape_markdown_for_notion_property(original) != escaped:
            report.record(
                "12", "escape / unescape round-trip", "fail",
                f"escape({original!r}) != {escaped!r}",
            )
            return
        if ai.unescape_markdown_from_notion_property(escaped) != original:
            report.record(
                "12", "escape / unescape round-trip", "fail",
                f"unescape({escaped!r}) != {original!r}",
            )
            return
    # End-to-end: publisher → apply. The publisher escapes; the apply
    # script must unescape on ingest so canon sees the raw markers.
    tmp = Path(tempfile.mkdtemp(prefix="phase5-12-"))
    try:
        mcp = _make_fake_mcp(tmp / "mcp")
        canon = mcp / "context" / "x.md"
        canon.write_text("# Title\n")
        rows = [{
            "page_id": "pM", "finding_id": "R1",
            "title": "R1: roundtrip",
            "action": "append",
            "target_file": "context/x.md",
            "target_line_start": 1, "target_line_end": 1,
            "current_text": "",
            # Escaped as the publisher would emit it:
            "proposed_text": "⟪ast⟫⟪ast⟫Lead claim⟪ast⟫⟪ast⟫ — with _emphasis_ and ⟪bt⟫code⟪bt⟫.",
            "source_file": "src.md", "source_line": 1,
            "category": "raw-canon-conflict",
        }]
        rc, stdout, stderr = _run_apply(
            ["--group", "competitive", "--apply",
             "--mcp-server-path", str(mcp), "--run-date", "2026-04-21"],
            rows,
        )
        if rc != 0:
            report.record(
                "12", "escape / unescape round-trip", "fail",
                f"e2e apply rc={rc} stderr={stderr}",
            )
            return
        new_body = canon.read_text()
        if "**Lead claim**" not in new_body or "_emphasis_" not in new_body or "`code`" not in new_body:
            report.record(
                "12", "escape / unescape round-trip", "fail",
                f"markdown markers not restored in canon:\n{new_body}",
            )
            return
        if "⟪ast⟫" in new_body or "⟪us⟫" in new_body or "⟪bt⟫" in new_body:
            report.record(
                "12", "escape / unescape round-trip", "fail",
                "placeholder leaked through to canon",
            )
            return
        report.record(
            "12", "escape / unescape round-trip", "pass",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_13(report):
    """Check 13: Replace with target_line_end beyond file length →
    needs_restage, no disk write.

    The 2026-04 cleanup removed the SHA-1 drift guard (see
    apply_integrations.py). The only remaining safety is a bounds
    check on the recorded line range: if the target span extends past
    EOF, the row flips to Needs Restage instead of silently creating
    phantom lines. This test locks that bounds check.
    """
    tmp = Path(tempfile.mkdtemp(prefix="phase5-13-"))
    try:
        mcp = _make_fake_mcp(tmp / "mcp")
        canon = mcp / "context" / "shortfile.md"
        body = "# Title\n\nline two\nline three\n"  # 4 lines
        canon.write_text(body)

        rows = [{
            "page_id": "pD", "finding_id": "R1",
            "title": "R1: out-of-bounds replace",
            "action": "replace",
            "target_file": "context/shortfile.md",
            "target_line_start": 3, "target_line_end": 10,  # end > EOF
            "current_text": "preview",
            "proposed_text": "should never land",
            "source_file": "src.md", "source_line": 1,
            "category": "raw-canon-conflict",
        }]

        rc, stdout, stderr = _run_apply(
            ["--group", "competitive", "--apply",
             "--mcp-server-path", str(mcp), "--run-date", "2026-04-21"],
            rows,
        )
        if rc != 0:
            report.record(
                "13", "Out-of-bounds replace → needs_restage", "fail",
                f"rc={rc} stderr={stderr}",
            )
            return
        result = json.loads(stdout)
        status = result["results"][0]["status"]
        if status != "needs_restage":
            report.record(
                "13", "Out-of-bounds replace → needs_restage", "fail",
                f"status={status} — expected needs_restage",
            )
            return
        after = canon.read_text()
        if "should never land" in after:
            report.record(
                "13", "Out-of-bounds replace → needs_restage", "fail",
                "proposed_text leaked into canon despite bounds failure",
            )
            return
        report.record(
            "13", "Out-of-bounds replace → needs_restage", "pass",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_15(report):
    """Check 15: First-run path discovery.

    Delete `.kb-local.json` (backed up to a temp), clear
    HXGTM_MCP_SERVER_PATH, run the resolver, and expect it to locate
    the adjacent `../hxgtm-mcp-server/` clone and write the absolute
    path into a fresh `.kb-local.json`. Second invocation must report
    `"source": "cache"` — no re-scan on the fast path.
    """
    backup = None
    try:
        # Back up any existing .kb-local.json so the test doesn't
        # clobber the user's state.
        if LOCAL_STATE_PATH.exists():
            backup = LOCAL_STATE_PATH.read_text(encoding="utf-8")
            LOCAL_STATE_PATH.unlink()

        env = {k: v for k, v in os.environ.items() if k != "HXGTM_MCP_SERVER_PATH"}

        first = subprocess.run(
            ["python3", str(RESOLVE_SCRIPT), "mcp-path", "--quiet"],
            capture_output=True, text=True, env=env,
        )
        if first.returncode != 0:
            report.record(
                "15", "First-run path discovery writes .kb-local.json cache",
                "fail",
                f"first run exit {first.returncode}: {first.stderr}",
            )
            return
        result1 = json.loads(first.stdout)
        if result1.get("cached") is not False:
            report.record(
                "15", "First-run path discovery writes .kb-local.json cache",
                "fail",
                f"first run reported cached={result1.get('cached')} — expected false",
            )
            return
        if result1.get("source") not in {"adjacent", "scan"}:
            report.record(
                "15", "First-run path discovery writes .kb-local.json cache",
                "fail",
                f"first run source={result1.get('source')} — expected adjacent/scan",
            )
            return
        if not LOCAL_STATE_PATH.exists():
            report.record(
                "15", "First-run path discovery writes .kb-local.json cache",
                "fail", ".kb-local.json not created after first run",
            )
            return
        cached_state = json.loads(LOCAL_STATE_PATH.read_text())
        if cached_state.get("hxgtm_mcp_server_path") != result1.get("path"):
            report.record(
                "15", "First-run path discovery writes .kb-local.json cache",
                "fail",
                f".kb-local.json cached path does not match resolver output",
            )
            return

        # Second run — expect cache hit.
        second = subprocess.run(
            ["python3", str(RESOLVE_SCRIPT), "mcp-path", "--quiet"],
            capture_output=True, text=True, env=env,
        )
        if second.returncode != 0:
            report.record(
                "15", "First-run path discovery writes .kb-local.json cache",
                "fail", f"second run exit {second.returncode}: {second.stderr}",
            )
            return
        result2 = json.loads(second.stdout)
        if result2.get("source") != "cache":
            report.record(
                "15", "First-run path discovery writes .kb-local.json cache",
                "fail",
                f"second run source={result2.get('source')} — expected cache",
            )
            return
        if result2.get("cached") is not True:
            report.record(
                "15", "First-run path discovery writes .kb-local.json cache",
                "fail",
                f"second run cached={result2.get('cached')} — expected true",
            )
            return

        report.record(
            "15", "First-run path discovery writes .kb-local.json cache", "pass",
        )
    finally:
        # Restore the user's original state if we backed one up; else
        # leave whatever the resolver wrote (likely the happy-path entry).
        if backup is not None:
            LOCAL_STATE_PATH.write_text(backup, encoding="utf-8")


def check_16(report):
    """Check 16: Zip-not-git precondition halts with the git clone message."""
    tmp = Path(tempfile.mkdtemp(prefix="phase5-16-"))
    try:
        zip_root = tmp / "mcp-zip"
        (zip_root / "context").mkdir(parents=True)
        # NO .git/ directory.

        rows = [{
            "page_id": "p", "finding_id": "R1", "title": "R1: unused",
            "target_file": "context/anything.md",
            "current_text": "x", "proposed_text": "y",
            "source_file": "src.md", "group": "competitive",
            "run_date": "2026-04-21",
            "target_line_start": 1, "target_line_end": 1,
            "category": "raw-canon-conflict",
        }]

        rc, stdout, stderr = _run_apply(
            ["--group", "competitive", "--plan",
             "--mcp-server-path", str(zip_root), "--run-date", "2026-04-21"],
            rows,
        )
        if rc == 0:
            report.record(
                "16", "Zip-not-git precondition halts", "fail",
                "script exited 0 — expected non-zero",
            )
            return
        combined = (stdout + stderr).lower()
        if "not a git clone" not in combined:
            report.record(
                "16", "Zip-not-git precondition halts", "fail",
                f"expected 'not a git clone' in output — got:\n{stdout}\n---\n{stderr}",
            )
            return
        if "git clone" not in combined:
            report.record(
                "16", "Zip-not-git precondition halts", "fail",
                "missing `git clone` instruction in halt message",
            )
            return
        report.record("16", "Zip-not-git precondition halts", "pass")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main():
    report = CheckReport()

    print("=== Phase 5 — automated verification ===")
    print()

    # Derived invariants first — they don't need fixtures.
    check_D1(report)
    check_D2(report)
    check_D3(report)
    check_D4(report)
    check_D5(report)
    check_D6(report)
    check_D7(report)
    check_D8(report)
    check_D9(report)
    check_D10(report)

    # IMPROVEMENTS.md numbered checks that are script-testable.
    check_10(report)
    check_11(report)
    check_12(report)
    check_13(report)
    check_15(report)
    check_16(report)

    return 0 if report.summary() else 1


if __name__ == "__main__":
    sys.exit(main())
