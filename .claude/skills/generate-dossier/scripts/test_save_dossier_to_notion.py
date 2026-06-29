#!/usr/bin/env python3
"""Tests for save-dossier-to-notion.py — in particular the --multi partitioner.

Run with:
    python3 .claude/skills/generate-dossier/scripts/test_save_dossier_to_notion.py
"""

import importlib.util
import json
import sys
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent / "save-dossier-to-notion.py"

_spec = importlib.util.spec_from_file_location("save_dossier_to_notion", SCRIPT_PATH)
sdn = importlib.util.module_from_spec(_spec)
sys.modules["save_dossier_to_notion"] = sdn
_spec.loader.exec_module(sdn)


def _jsize(obj):
    return len(json.dumps(obj, ensure_ascii=False))


def _collect_children(payloads):
    """Reassemble every child block from every payload in order. Used to
    verify the partitioner preserves the original block stream."""
    out = []
    for p in payloads:
        out.extend(p["children"])
    return out


def _make_row(cells):
    return {
        "object": "block",
        "type": "table_row",
        "table_row": {
            "cells": [[{"type": "text", "text": {"content": c}}] for c in cells],
        },
    }


def _make_table(width, header_cells, data_rows):
    rows = [_make_row(header_cells)] + [_make_row(r) for r in data_rows]
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": width,
            "has_column_header": True,
            "has_row_header": False,
            "children": rows,
        },
    }


class SmallDossierFitsInOnePayload(unittest.TestCase):
    def test_single_create_page_payload(self):
        md = "# Acme Corp\n\nA short dossier.\n\n## Section 1\n\nJust a paragraph.\n"
        blocks = sdn.parse_markdown_to_blocks(md)
        payloads = sdn.partition_blocks_into_payloads(blocks, byte_limit=4500)

        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["op"], "create_page")
        self.assertEqual(payloads[0]["children"], blocks)


class MediumDossierNeedsMultipleAppends(unittest.TestCase):
    def test_splits_into_create_plus_appends_preserving_order(self):
        # 40 beefy paragraphs, each ~300 bytes — blows past one payload
        # but no individual block is oversized.
        paragraphs = [f"## Section {i}\n\n" + ("Lorem ipsum dolor sit amet " * 10)
                      for i in range(40)]
        md = "# Big Co\n\n" + "\n\n".join(paragraphs) + "\n"
        blocks = sdn.parse_markdown_to_blocks(md)

        payloads = sdn.partition_blocks_into_payloads(blocks, byte_limit=4500)

        self.assertGreater(len(payloads), 1)
        self.assertEqual(payloads[0]["op"], "create_page")
        for p in payloads[1:]:
            self.assertEqual(p["op"], "append")
            self.assertEqual(p["parent"], "page")

        # Every payload stays under budget (create_page gets a tighter budget).
        self.assertLessEqual(_jsize(payloads[0]["children"]),
                             4500 - sdn.CREATE_PAGE_ENVELOPE)
        for p in payloads[1:]:
            self.assertLessEqual(_jsize(p["children"]), 4500)

        # Reassembled children must equal the original block stream.
        self.assertEqual(_collect_children(payloads), blocks)


class OversizedTableGetsSplit(unittest.TestCase):
    def test_shell_plus_row_groups_under_budget(self):
        # 30 rows, each ~250 bytes — table as a whole is >4500B.
        header = ["Theme", "Sources", "Notes"]
        data_rows = []
        for i in range(30):
            data_rows.append([
                f"Theme {i}",
                f"Source {i} with a reasonably long description that adds bytes",
                f"Notes about theme {i} extending to fill more bytes per row " * 2,
            ])
        big_table = _make_table(3, header, data_rows)
        blocks = [
            {"object": "block", "type": "heading_1",
             "heading_1": {"rich_text": [{"type": "text",
                                          "text": {"content": "Big Co"}}]}},
            big_table,
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [{"type": "text",
                                          "text": {"content": "After the table."}}]}},
        ]

        payloads = sdn.partition_blocks_into_payloads(blocks, byte_limit=4500)

        # Expected shape:
        #   create_page: [H1]
        #   append page (capture=table_1): [shell]
        #   append $table_1: rows...
        #   append $table_1: rows...
        #   (...more row groups as needed)
        #   append page: [paragraph]
        self.assertEqual(payloads[0]["op"], "create_page")
        self.assertEqual([b["type"] for b in payloads[0]["children"]], ["heading_1"])

        shell_idx = 1
        self.assertEqual(payloads[shell_idx]["op"], "append")
        self.assertEqual(payloads[shell_idx]["parent"], "page")
        self.assertEqual(payloads[shell_idx]["capture"], "table_1")
        self.assertEqual(len(payloads[shell_idx]["children"]), 1)
        shell = payloads[shell_idx]["children"][0]
        self.assertEqual(shell["type"], "table")
        # Shell holds header row only.
        self.assertEqual(len(shell["table"]["children"]), 1)

        # All row-group payloads target $table_1 and are under budget.
        row_group_idxs = []
        for i, p in enumerate(payloads[2:], start=2):
            if p.get("parent") == "$table_1":
                row_group_idxs.append(i)
                self.assertEqual(p["op"], "append")
                self.assertNotIn("capture", p)
                for row in p["children"]:
                    self.assertEqual(row["type"], "table_row")
                self.assertLessEqual(_jsize(p["children"]), 4500)
        self.assertGreaterEqual(len(row_group_idxs), 2,
                                "expected multiple row groups for a 30-row table")

        # Row groups collectively contain all 30 data rows.
        total_data_rows = sum(len(payloads[i]["children"]) for i in row_group_idxs)
        self.assertEqual(total_data_rows, 30)

        # Final payload is a page-level append with the trailing paragraph.
        self.assertEqual(payloads[-1]["op"], "append")
        self.assertEqual(payloads[-1]["parent"], "page")
        self.assertEqual([b["type"] for b in payloads[-1]["children"]], ["paragraph"])


class PartitionerPreservesOrderAcrossTableSplit(unittest.TestCase):
    """Reassembling data rows from row-groups in order must equal the table's
    original data rows."""

    def test_data_row_order_preserved(self):
        header = ["A", "B"]
        data_rows = [[f"a{i}", f"b{i}" * 50] for i in range(20)]  # fat col B
        table = _make_table(2, header, data_rows)

        payloads = sdn.partition_blocks_into_payloads([table], byte_limit=4500)

        collected = []
        for p in payloads:
            if p.get("parent", "").startswith("$table_"):
                collected.extend(p["children"])

        self.assertEqual(len(collected), 20)
        for i, row in enumerate(collected):
            self.assertEqual(
                row["table_row"]["cells"][0][0]["text"]["content"], f"a{i}")


class RealAspenDossierRoundTrip(unittest.TestCase):
    """End-to-end against the Aspen dossier file — large doc with two oversize
    tables. Verifies every payload fits under budget and block order is
    preserved outside of table-internal rows."""

    def test_aspen(self):
        repo_root = Path(__file__).resolve().parents[4]
        dossier = (repo_root
                   / "outputs/generate-dossier"
                   / "aspen-insurance-holdings-limited-dossier.md")
        if not dossier.exists():
            self.skipTest(f"dossier not found at {dossier}")

        content = dossier.read_text(encoding="utf-8")
        blocks = sdn.parse_markdown_to_blocks(content)
        payloads = sdn.partition_blocks_into_payloads(blocks, byte_limit=4500)

        # First payload is always create_page.
        self.assertEqual(payloads[0]["op"], "create_page")

        # Every payload under budget.
        for i, p in enumerate(payloads):
            limit = (4500 - sdn.CREATE_PAGE_ENVELOPE
                     if p["op"] == "create_page" else 4500)
            self.assertLessEqual(
                _jsize(p["children"]), limit,
                f"payload {i} ({p['op']}, parent={p.get('parent')}) "
                f"exceeds budget: {_jsize(p['children'])}B")

        # We expect at least 2 table-shell captures (Opportunities + Themes).
        captures = [p["capture"] for p in payloads if "capture" in p]
        self.assertGreaterEqual(len(captures), 2)
        self.assertEqual(captures, sorted(set(captures), key=captures.index))
        # Captures are referenced by at least one subsequent append.
        for key in captures:
            ref = f"${key}"
            self.assertTrue(
                any(p.get("parent") == ref for p in payloads),
                f"capture {key} is never referenced")


if __name__ == "__main__":
    unittest.main(verbosity=2)
