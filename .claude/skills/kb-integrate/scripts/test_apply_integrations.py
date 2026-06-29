#!/usr/bin/env python3
"""Tests for apply_integrations.py.

Run with:
    python3 .claude/skills/kb-integrate/scripts/test_apply_integrations.py
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import apply_integrations as ai  # noqa: E402


# Lines (1-indexed):
#   1  # Federato
#   2  (blank)
#   3  ## Snapshot
#   4  Federato is an AI-driven underwriting decision platform.
#   5  (blank)
#   6  ## Where they show up
#   7  - Underwriting decision platforms / "control tower" initiatives
#   8  - Submission triage + underwriting prioritization
#   9  - Portfolio steering and underwriting performance programs
#  10  ## Strengths
#  11  - Clear narrative around AI-assisted ...
#  12  - Often resonates with buyers ...
#  13  ## Weaknesses / watch-outs
#  14  - Risk of being perceived as a point solution ...
#  15  - Long-term defensibility ...
#  16  ## hx positioning
#  17  - hx is the governed underwriting and pricing decision platform: ...
#  18  - Reframe: "Federato helps prioritize and steer work; ..."
#  19  ## Talk track
#  20  - "The sustainable edge is owning the decision logic ..."
#  21  ## Notes / open questions
#  22  - Depth of native rating/pricing vs orchestration and intelligence
FEDERATO_ORIGINAL = """# Federato

## Snapshot
Federato is an AI-driven underwriting decision platform.

## Where they show up
- Underwriting decision platforms / "control tower" initiatives
- Submission triage + underwriting prioritization
- Portfolio steering and underwriting performance programs
## Strengths
- Clear narrative around AI-assisted underwriting decisions and prioritization
- Often resonates with buyers prioritizing speed-to-quote and underwriting productivity
## Weaknesses / watch-outs
- Risk of being perceived as a point solution if pricing/rating and governed decision logic live elsewhere
- Long-term defensibility depends on depth of decision governance, auditability, and integration into the underwriting operating model
## hx positioning
- hx is the governed underwriting and pricing decision platform: model governance, auditability, and rapid iteration on the decision logic.
- Reframe: "Federato helps prioritize and steer work; hx is where the actual decision logic and pricing is built, governed, deployed, and improved."
## Talk track
- "The sustainable edge is owning the decision logic end-to-end—transparent, auditable, and fast to iterate. That's hx's core."
## Notes / open questions
- Depth of native rating/pricing vs orchestration and intelligence
"""


def _make_mcp_tree(tmpdir: Path) -> Path:
    mcp = tmpdir / "hxgtm-mcp-server"
    (mcp / "context" / "guidance" / "competitive" / "competitors").mkdir(
        parents=True, exist_ok=True
    )
    return mcp


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ApplyReplaceLineRangeHelperTests(unittest.TestCase):
    """Unit tests for _apply_replace_line_range (line-range slicing)."""

    def test_replace_single_line(self):
        lines = ["alpha", "beta", "gamma"]
        new = ai._apply_replace_line_range(lines, 2, 2, "BETA")
        self.assertEqual(new, ["alpha", "BETA", "gamma"])

    def test_replace_multi_line_with_multi_line_replacement(self):
        lines = ["a", "b", "c", "d"]
        new = ai._apply_replace_line_range(lines, 2, 3, "X\nY")
        self.assertEqual(new, ["a", "X", "Y", "d"])

    def test_replace_collapses_range_to_single_line(self):
        lines = ["a", "b", "c", "d"]
        new = ai._apply_replace_line_range(lines, 2, 3, "MERGED")
        self.assertEqual(new, ["a", "MERGED", "d"])

    def test_trailing_newline_in_new_text_does_not_insert_blank_line(self):
        # The helper drops the trailing empty element produced by split()
        # when new_text ends with '\n', preserving the line count contract.
        lines = ["a", "b", "c"]
        new = ai._apply_replace_line_range(lines, 2, 2, "BETA\n")
        self.assertEqual(new, ["a", "BETA", "c"])

    def test_replace_full_range(self):
        lines = ["a", "b", "c"]
        new = ai._apply_replace_line_range(lines, 1, 3, "ONE")
        self.assertEqual(new, ["ONE"])


class PlannerRejectsBadLineRanges(unittest.TestCase):
    """Replace rows missing or with malformed line ranges must not
    will_succeed at plan time and must be flagged needs_restage."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kb-integrate-test-"))
        self.mcp = _make_mcp_tree(self.tmp)
        self.target = (
            self.mcp / "context" / "guidance" / "competitive" / "competitors" / "vendor.md"
        )
        _write(self.target, "## Section\nLINE-A\nLINE-B\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _row(self, **overrides):
        row = {
            "page_id": "page-x",
            "finding_id": "X1",
            "title": "Test row",
            "target_file": "context/guidance/competitive/competitors/vendor.md",
            "current_text": "LINE-A",
            "proposed_text": "LINE-A (edited)",
            "category": "raw-canon-conflict",
            "source_file": "scan.md",
        }
        row.update(overrides)
        return row

    def test_missing_line_range_marks_needs_restage(self):
        plan = ai.build_plan([self._row()], self.mcp, "2026-04-16")
        self.assertFalse(plan[0]["will_succeed"])
        self.assertTrue(plan[0]["needs_restage"])
        self.assertIn("missing target_line_start", plan[0]["reason"])

    def test_inverted_line_range_marks_needs_restage(self):
        row = self._row(target_line_start=5, target_line_end=2)
        plan = ai.build_plan([row], self.mcp, "2026-04-16")
        self.assertFalse(plan[0]["will_succeed"])
        self.assertTrue(plan[0]["needs_restage"])
        self.assertIn("invalid line range", plan[0]["reason"])

    def test_zero_line_start_marks_needs_restage(self):
        row = self._row(target_line_start=0, target_line_end=1)
        plan = ai.build_plan([row], self.mcp, "2026-04-16")
        self.assertFalse(plan[0]["will_succeed"])
        self.assertTrue(plan[0]["needs_restage"])
        self.assertIn("invalid line range", plan[0]["reason"])

    def test_out_of_bounds_line_end_marks_needs_restage(self):
        # vendor.md is 3 lines long.
        row = self._row(target_line_start=2, target_line_end=999)
        plan = ai.build_plan([row], self.mcp, "2026-04-16")
        self.assertFalse(plan[0]["will_succeed"])
        self.assertTrue(plan[0]["needs_restage"])
        self.assertIn("beyond file length", plan[0]["reason"])

    def test_apply_skips_rows_that_failed_planning(self):
        plan = ai.build_plan([self._row()], self.mcp, "2026-04-16")
        before = self.target.read_text(encoding="utf-8")
        results = ai.apply_plan(plan, self.mcp)
        after = self.target.read_text(encoding="utf-8")
        self.assertEqual(before, after)
        # Plan-time failures with needs_restage propagate to apply as
        # the "needs_restage" status (not generic "skipped").
        self.assertEqual(results[0]["status"], "needs_restage")


class MultiReplaceSameFileRegressionTest(unittest.TestCase):
    """Two replaces targeting the same file at different line ranges must
    both land correctly. Bottom-up ordering inside apply_plan ensures the
    earlier replace's line numbers don't shift before the later replace
    runs."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kb-integrate-test-"))
        self.mcp = _make_mcp_tree(self.tmp)
        self.target = (
            self.mcp / "context" / "guidance" / "competitive" / "competitors" / "federato.md"
        )
        _write(self.target, FEDERATO_ORIGINAL)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_R11_then_R12_both_land_cleanly(self):
        rows = [
            {
                "page_id": "page-r11",
                "finding_id": "R11",
                "title": "Federato missing billing / PAS expansion",
                "target_file": "context/guidance/competitive/competitors/federato.md",
                # Lines 6-9: "## Where they show up" + 3 bullets
                "target_line_start": 6,
                "target_line_end": 9,
                "current_text": (
                    "## Where they show up\n"
                    "- Underwriting decision platforms / \"control tower\" initiatives\n"
                    "- Submission triage + underwriting prioritization\n"
                    "- Portfolio steering and underwriting performance programs"
                ),
                "proposed_text": (
                    "## Where they show up\n"
                    "- Underwriting decision platforms / \"control tower\" initiatives\n"
                    "- Submission triage + underwriting prioritization\n"
                    "- Portfolio steering and underwriting performance programs\n"
                    "- PAS / billing expansion (April 2026 LinkedIn post)"
                ),
                "category": "raw-canon-conflict",
                "source_file": "scan.md",
            },
            {
                "page_id": "page-r12",
                "finding_id": "R12",
                "title": "Federato workbench talk track",
                "target_file": "context/guidance/competitive/competitors/federato.md",
                # Lines 19-20: "## Talk track" + the existing bullet
                "target_line_start": 19,
                "target_line_end": 20,
                "current_text": (
                    "## Talk track\n"
                    "- \"The sustainable edge is owning the decision logic "
                    "end-to-end—transparent, auditable, and fast to iterate. "
                    "That's hx's core.\""
                ),
                "proposed_text": (
                    "## Talk track\n"
                    "- \"The sustainable edge is owning the decision logic "
                    "end-to-end—transparent, auditable, and fast to iterate. "
                    "That's hx's core.\"\n"
                    "- \"Federato overlaps on workbench + UW agents, but the "
                    "differentiation is data vs decisioning.\""
                ),
                "category": "raw-canon-conflict",
                "source_file": "scan.md",
            },
        ]

        plan = ai.build_plan(rows, self.mcp, "2026-04-16")
        self.assertEqual(len(plan), 2)
        self.assertTrue(plan[0]["will_succeed"], plan[0]["reason"])
        self.assertTrue(plan[1]["will_succeed"], plan[1]["reason"])

        results = ai.apply_plan(plan, self.mcp)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["status"], "success", results[0])
        self.assertEqual(results[1]["status"], "success", results[1])

        final = self.target.read_text(encoding="utf-8")

        # R11's bullet landed in the "Where they show up" section.
        self.assertIn(
            "- PAS / billing expansion (April 2026 LinkedIn post)", final
        )
        # R12's bullet landed in the "Talk track" section.
        self.assertIn(
            '- "Federato overlaps on workbench + UW agents, but the '
            'differentiation is data vs decisioning."',
            final,
        )

        # No corruption: the "Reframe:" line must still be intact.
        self.assertIn(
            '- Reframe: "Federato helps prioritize and steer work; hx is '
            'where the actual decision logic and pricing is built, '
            'governed, deployed, and improved."',
            final,
        )

        # No corruption: there must be exactly one "## Talk track" heading.
        self.assertEqual(
            final.count("## Talk track"),
            1,
            "duplicate or mangled Talk track section",
        )


class MultipleAppendsToSameFile(unittest.TestCase):
    """Multiple coverage-gap appends to the same file must stack
    correctly at EOF and each land under a distinct heading."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kb-integrate-test-"))
        self.mcp = _make_mcp_tree(self.tmp)
        self.target = (
            self.mcp / "context" / "truth" / "market" / "competitors.md"
        )
        _write(self.target, "# Competitors\n\nLandscape notes.\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_three_appends_stack_cleanly(self):
        def row(fid, title, body):
            return {
                "page_id": f"page-{fid}",
                "finding_id": fid,
                "title": title,
                "target_file": "context/truth/market/competitors.md",
                "current_text": "",
                "proposed_text": body,
                "category": "coverage-gap",
                "source_file": "scan.md",
            }

        rows = [
            row("A1", "Alpha net-new", "Alpha is a pricing vendor."),
            row("A2", "Bravo net-new", "Bravo is a workflow vendor."),
            row("A3", "Charlie net-new", "Charlie is OSS."),
        ]
        plan = ai.build_plan(rows, self.mcp, "2026-04-16")
        for entry in plan:
            self.assertTrue(entry["will_succeed"], entry["reason"])

        results = ai.apply_plan(plan, self.mcp)
        for r in results:
            self.assertEqual(r["status"], "success", r)

        final = self.target.read_text(encoding="utf-8")
        self.assertIn("Alpha is a pricing vendor.", final)
        self.assertIn("Bravo is a workflow vendor.", final)
        self.assertIn("Charlie is OSS.", final)
        self.assertIn("## Alpha net-new", final)
        self.assertIn("## Bravo net-new", final)
        self.assertIn("## Charlie net-new", final)
        # Alpha should come before Bravo, Bravo before Charlie.
        self.assertLess(final.index("Alpha"), final.index("Bravo"))
        self.assertLess(final.index("Bravo"), final.index("Charlie"))


if __name__ == "__main__":
    unittest.main()
