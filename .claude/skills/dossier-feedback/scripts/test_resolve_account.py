#!/usr/bin/env python3
"""
Pytest covering scripts/resolve_account.py.

Run with: pytest .claude/skills/dossier-feedback/scripts/test_resolve_account.py
"""

import importlib.util
import json
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("ra", HERE / "resolve_account.py")
ra = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ra)


@pytest.fixture
def state_file():
    state = {
        "version": 1,
        "accounts": {
            "zurich-north-america": {
                "name": "Zurich North America",
                "status": "done",
                "notion_url": "https://www.notion.so/hyperexponential/abc12345abc12345abc12345abc12345",
            },
            "the-hartford": {
                "name": "The Hartford",
                "status": "done",
                "notion_url": "https://www.notion.so/hyperexponential/def67890-def6-7890-def6-7890def67890",
            },
            "axa-xl": {
                "name": "AXA XL",
                "status": "partial",
                "notion_url": None,
            },
        },
    }
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "_batch-state.json"
        p.write_text(json.dumps(state))
        yield p


def test_slugify_basic():
    assert ra.slugify("Zurich North America") == "zurich-north-america"
    assert ra.slugify("AXA XL") == "axa-xl"
    assert ra.slugify("The Hartford!") == "the-hartford"
    assert ra.slugify("  Multiple   Spaces  ") == "multiple-spaces"


def test_page_id_from_url_unhyphenated():
    pid = ra.page_id_from_url(
        "https://www.notion.so/hyperexponential/abc12345abc12345abc12345abc12345"
    )
    assert pid == "abc12345abc12345abc12345abc12345"


def test_page_id_from_url_hyphenated():
    pid = ra.page_id_from_url(
        "https://www.notion.so/hyperexponential/Page-Title-def67890-def6-7890-def6-7890def67890"
    )
    assert pid == "def67890def67890def67890def67890"


def test_page_id_from_url_garbage_returns_none():
    assert ra.page_id_from_url("https://example.com/no-id-here") is None


def test_find_in_state_exact_slug(state_file):
    state = json.loads(state_file.read_text())
    rec = ra.find_in_state(state, "zurich-north-america")
    assert rec is not None
    assert rec["name"] == "Zurich North America"


def test_find_in_state_exact_name(state_file):
    state = json.loads(state_file.read_text())
    rec = ra.find_in_state(state, "The Hartford")
    assert rec is not None
    assert rec["slug"] == "the-hartford"


def test_find_in_state_case_insensitive(state_file):
    state = json.loads(state_file.read_text())
    rec = ra.find_in_state(state, "the hartford")
    assert rec is not None
    assert rec["slug"] == "the-hartford"


def test_find_in_state_miss(state_file):
    state = json.loads(state_file.read_text())
    rec = ra.find_in_state(state, "Allianz")
    assert rec is None


def test_load_state_missing_returns_none():
    assert ra.load_state(Path("/tmp/definitely-not-a-real-file-zzz.json")) is None


def test_load_state_corrupt_returns_none():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "broken.json"
        p.write_text("{not json")
        assert ra.load_state(p) is None
