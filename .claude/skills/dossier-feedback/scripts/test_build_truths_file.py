#!/usr/bin/env python3
"""
Pytest covering build_truths_file render output shape and atomic_write.
Both files (comment log + truths summary) are exercised.

Run with: pytest .claude/skills/dossier-feedback/scripts/test_build_truths_file.py
"""

import importlib.util
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("btf", HERE / "build_truths_file.py")
btf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(btf)


def _entry(**overrides):
    base = {
        "title": "HQ moved to Schaumburg",
        "anchor_text": "Headquartered in Zurich, Switzerland.",
        "comment_text": "Wrong — US HQ moved to Schaumburg IL in 2023.",
        "interpreted_truth": "US HQ relocated to Schaumburg, IL in 2023.",
        "section_tag": "overview",
        "author": "Sarah Chen",
        "created_time": "2026-04-22T14:11:00Z",
        "resolved": False,
        "discussion_id": "abc-123",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Comment-log render
# ---------------------------------------------------------------------------

def test_comment_log_includes_frontmatter_and_entry():
    out = btf.render_comment_log(
        account="Zurich North America",
        slug="zurich-north-america",
        source_url="https://www.notion.so/example",
        entries=[_entry()],
    )
    assert out.startswith("---\n")
    assert 'account: "Zurich North America"' in out
    assert "slug: zurich-north-america" in out
    assert "source_dossier_url: https://www.notion.so/example" in out
    assert "entry_count: 1" in out
    assert "# Known Truths — Zurich North America" in out
    assert "### HQ moved to Schaumburg" in out
    assert "- **Section:** overview" in out
    assert "- **Interpreted truth:** US HQ relocated to Schaumburg, IL in 2023." in out
    assert "- **Resolved:** false" in out
    assert "- **Author / date:** Sarah Chen · 2026-04-22" in out


def test_comment_log_page_level_anchor_uses_no_anchor_literal():
    out = btf.render_comment_log(
        account="X",
        slug="x",
        source_url="https://www.notion.so/x",
        entries=[_entry(anchor_text=None)],
    )
    assert "(page-level comment, no anchor)" in out


def test_comment_log_unknown_section_tag_falls_back_to_untagged():
    out = btf.render_comment_log(
        account="X",
        slug="x",
        source_url="https://www.notion.so/x",
        entries=[_entry(section_tag="not-a-real-tag")],
    )
    assert "- **Section:** untagged" in out


def test_comment_log_resolved_true_renders_lowercase():
    out = btf.render_comment_log(
        account="X",
        slug="x",
        source_url="https://www.notion.so/x",
        entries=[_entry(resolved=True)],
    )
    assert "- **Resolved:** true" in out
    assert "- **Resolved:** True" not in out


def test_comment_log_zero_entries_includes_placeholder_note():
    out = btf.render_comment_log(
        account="X", slug="x", source_url="https://www.notion.so/x", entries=[]
    )
    assert "entry_count: 0" in out
    assert "_No entries — this file is a placeholder._" in out


def test_comment_log_collapses_multiline_comment_to_single_line():
    out = btf.render_comment_log(
        account="X",
        slug="x",
        source_url="https://www.notion.so/x",
        entries=[_entry(comment_text="line1\n\nline2\n   line3")],
    )
    assert "Reviewer comment:** line1 line2 line3" in out


def test_comment_log_entry_order_preserved():
    entries = [
        _entry(title=f"Entry {i}", discussion_id=f"d-{i}") for i in range(5)
    ]
    out = btf.render_comment_log(
        account="X", slug="x", source_url="https://www.notion.so/x", entries=entries
    )
    positions = [out.index(f"### Entry {i}") for i in range(5)]
    assert positions == sorted(positions)


def test_legacy_render_alias_returns_comment_log():
    """The legacy `render` name should still work and produce the comment log."""
    legacy_out = btf.render(
        account="X", slug="x", source_url="https://www.notion.so/x", entries=[_entry()]
    )
    canonical_out = btf.render_comment_log(
        account="X", slug="x", source_url="https://www.notion.so/x", entries=[_entry()]
    )
    # The two should match modulo the `generated_at` line which contains
    # a per-call timestamp.
    legacy_no_ts = "\n".join(
        line for line in legacy_out.splitlines() if not line.startswith("generated_at:")
    )
    canonical_no_ts = "\n".join(
        line for line in canonical_out.splitlines() if not line.startswith("generated_at:")
    )
    assert legacy_no_ts == canonical_no_ts


# ---------------------------------------------------------------------------
# Truths-summary render
# ---------------------------------------------------------------------------

def test_truths_summary_includes_frontmatter_and_grouped_bullets():
    entries = [
        _entry(title="HQ correction", section_tag="overview",
               interpreted_truth="HQ is in Schaumburg, IL since 2023."),
        _entry(title="CUO is buyer", section_tag="power-players",
               interpreted_truth="The CUO owns platform spend."),
    ]
    out = btf.render_truths_summary(
        account="Acme Corp",
        slug="acme-corp",
        source_url="https://www.notion.so/acme",
        entries=entries,
    )
    assert out.startswith("---\n")
    assert 'account: "Acme Corp"' in out
    assert "entry_count: 2" in out
    assert "# Known Truths — Acme Corp" in out
    assert "## overview" in out
    assert "## power-players" in out
    assert "- HQ is in Schaumburg, IL since 2023. _(see: HQ correction)_" in out
    assert "- The CUO owns platform spend. _(see: CUO is buyer)_" in out


def test_truths_summary_omits_empty_section_groups():
    entries = [
        _entry(title="HQ correction", section_tag="overview",
               interpreted_truth="HQ moved."),
    ]
    out = btf.render_truths_summary(
        account="X", slug="x", source_url="https://www.notion.so/x", entries=entries
    )
    assert "## overview" in out
    assert "## power-players" not in out
    assert "## untagged" not in out
    assert "## why-anything" not in out


def test_truths_summary_section_order_matches_section_order_constant():
    entries = [
        _entry(title=f"e-{tag}", section_tag=tag,
               interpreted_truth=f"truth for {tag}.")
        for tag in btf.SECTION_ORDER
    ]
    out = btf.render_truths_summary(
        account="X", slug="x", source_url="https://www.notion.so/x", entries=entries
    )
    positions = [out.index(f"## {tag}") for tag in btf.SECTION_ORDER]
    assert positions == sorted(positions), (
        "Section groups must appear in SECTION_ORDER order"
    )


def test_truths_summary_includes_why_anything_section():
    """Phase-1.5 enum addition: the why-anything tag should render correctly."""
    entries = [
        _entry(title="Cost of inaction is steep", section_tag="why-anything",
               interpreted_truth="Status-quo costs $X/yr in lost premium."),
    ]
    out = btf.render_truths_summary(
        account="X", slug="x", source_url="https://www.notion.so/x", entries=entries
    )
    assert "## why-anything" in out
    assert (
        "- Status-quo costs $X/yr in lost premium. "
        "_(see: Cost of inaction is steep)_"
    ) in out
    # why-anything should appear after discovery and before untagged
    assert btf.SECTION_ORDER.index("why-anything") == 6
    assert btf.SECTION_ORDER.index("untagged") == 7


def test_truths_summary_unknown_tag_falls_back_to_untagged():
    entries = [
        _entry(title="Mystery tag", section_tag="not-a-real-tag",
               interpreted_truth="A mystery."),
    ]
    out = btf.render_truths_summary(
        account="X", slug="x", source_url="https://www.notion.so/x", entries=entries
    )
    assert "## untagged" in out
    assert "- A mystery. _(see: Mystery tag)_" in out


def test_truths_summary_zero_entries_includes_placeholder_note():
    out = btf.render_truths_summary(
        account="X", slug="x", source_url="https://www.notion.so/x", entries=[]
    )
    assert "entry_count: 0" in out
    assert "_No entries — this file is a placeholder._" in out
    assert "## overview" not in out  # no section groups when empty


def test_truths_summary_skips_entries_with_blank_truth():
    entries = [
        _entry(title="Has truth", section_tag="overview",
               interpreted_truth="A real truth."),
        _entry(title="Blank truth", section_tag="overview",
               interpreted_truth=""),
    ]
    out = btf.render_truths_summary(
        account="X", slug="x", source_url="https://www.notion.so/x", entries=entries
    )
    assert "_(see: Has truth)_" in out
    assert "_(see: Blank truth)_" not in out


def test_truths_summary_links_back_to_comment_log_path():
    out = btf.render_truths_summary(
        account="X", slug="my-slug", source_url="https://www.notion.so/x",
        entries=[_entry()],
    )
    assert "../comment-logs/my-slug.md" in out


def test_comment_log_links_back_to_truths_summary_path():
    out = btf.render_comment_log(
        account="X", slug="my-slug", source_url="https://www.notion.so/x",
        entries=[_entry()],
    )
    assert "../known-truths/my-slug.md" in out


# ---------------------------------------------------------------------------
# Atomic dual-write through the CLI surface
# ---------------------------------------------------------------------------

def test_atomic_write_creates_file_and_replaces():
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "subdir" / "out.md"
        btf.atomic_write(target, "first\n")
        assert target.read_text() == "first\n"
        btf.atomic_write(target, "second\n")
        assert target.read_text() == "second\n"


def test_dual_file_write_via_main(monkeypatch, tmp_path, capsys):
    """End-to-end: main() reads JSON from stdin and writes both files."""
    import json as _json
    import sys as _sys
    import io as _io

    entries = [
        _entry(title="A title", section_tag="overview",
               interpreted_truth="An overview truth."),
        _entry(title="B title", section_tag="why-anything",
               interpreted_truth="A why-anything truth."),
    ]
    stdin_content = _json.dumps(entries)
    monkeypatch.setattr(_sys, "stdin", _io.StringIO(stdin_content))

    comment_log_path = tmp_path / "comment-logs" / "x.md"
    truths_summary_path = tmp_path / "known-truths" / "x.md"

    monkeypatch.setattr(_sys, "argv", [
        "build_truths_file.py",
        "--account", "X Corp",
        "--slug", "x",
        "--source-url", "https://www.notion.so/x",
        "--comment-log-out", str(comment_log_path),
        "--truths-summary-out", str(truths_summary_path),
    ])

    rc = btf.main()
    assert rc == 0

    assert comment_log_path.exists()
    assert truths_summary_path.exists()

    comment_log = comment_log_path.read_text()
    truths_summary = truths_summary_path.read_text()

    # Both share frontmatter
    assert "entry_count: 2" in comment_log
    assert "entry_count: 2" in truths_summary
    assert 'account: "X Corp"' in comment_log
    assert 'account: "X Corp"' in truths_summary

    # Comment log has full entry blocks
    assert "### A title" in comment_log
    assert "- **Reviewer comment:**" in comment_log
    assert "- **Discussion ID:**" in comment_log

    # Truths summary has section-grouped bullets without provenance
    assert "## overview" in truths_summary
    assert "## why-anything" in truths_summary
    assert "- An overview truth. _(see: A title)_" in truths_summary
    assert "- A why-anything truth. _(see: B title)_" in truths_summary
    assert "**Reviewer comment:**" not in truths_summary
    assert "**Discussion ID:**" not in truths_summary
