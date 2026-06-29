#!/usr/bin/env python3
"""
test_convert_to_markdown.py

Standalone test harness for .claude/skills/kb-update/scripts/convert_to_markdown.py.
Uses pandoc itself to generate tiny .pdf / .docx fixtures at test time
(so the repo carries no committed binary blobs).

Run directly:
  python3 .claude/skills/kb-update/tests/test_convert_to_markdown.py

Exit 0 on green; non-zero on any failure. Prints PASS/FAIL per case.
Skips fixture-dependent cases if pandoc isn't on PATH (logged as SKIP).
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CONVERT_SCRIPT = REPO_ROOT / "skills" / "kb-update" / "scripts" / "convert_to_markdown.py"


def _import(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cv = _import("convert_to_markdown", CONVERT_SCRIPT)


# ---------------------------------------------------------------------------
# Fixture builders (pandoc-driven)
# ---------------------------------------------------------------------------


def _make_pdf(tmpdir: Path, body: str = "# Hello\n\nThis is a test PDF body.\n") -> Path:
    md = tmpdir / "src.md"
    md.write_text(body)
    out = tmpdir / "fixture.pdf"
    proc = subprocess.run(
        ["pandoc", str(md), "-o", str(out)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        # pandoc may need a PDF engine; try the html2pdf-free path
        proc = subprocess.run(
            ["pandoc", str(md), "--pdf-engine=context", "-o", str(out)],
            capture_output=True, text=True,
        )
    if proc.returncode != 0 or not out.exists():
        return None
    return out


def _make_docx(tmpdir: Path, body: str = "# Hello DOCX\n\nDOCX paragraph body.\n") -> Path:
    md = tmpdir / "src.md"
    md.write_text(body)
    out = tmpdir / "fixture.docx"
    proc = subprocess.run(
        ["pandoc", str(md), "-o", str(out)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0 or not out.exists():
        return None
    return out


def _run_convert(in_path: Path, out_path: Path):
    proc = subprocess.run(
        ["python3", str(CONVERT_SCRIPT),
         "--input", str(in_path), "--output", str(out_path)],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


PASSED = []
FAILED = []
SKIPPED = []


def case(name):
    def deco(fn):
        try:
            fn()
        except AssertionError as exc:
            FAILED.append((name, str(exc)))
            print(f"[FAIL] {name}: {exc}")
            return fn
        except _Skip as exc:
            SKIPPED.append((name, str(exc)))
            print(f"[SKIP] {name}: {exc}")
            return fn
        PASSED.append(name)
        print(f"[PASS] {name}")
        return fn
    return deco


class _Skip(Exception):
    pass


def skip(reason):
    raise _Skip(reason)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


@case("docx end-to-end via pandoc")
def t_docx_e2e():
    if shutil.which("pandoc") is None:
        skip("pandoc not on PATH")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        docx = _make_docx(td)
        if docx is None:
            skip("pandoc could not build DOCX fixture")
        out = td / "out.md"
        rc, stdout, stderr = _run_convert(docx, out)
        assert rc == 0, f"rc={rc} stderr={stderr}"
        text = out.read_text()
        assert text.startswith("<!-- kb-update conversion"), "missing provenance comment"
        assert "DOCX paragraph body" in text, f"body missing: {text[:200]!r}"


@case("pdf end-to-end via pymupdf")
def t_pdf_e2e():
    try:
        import fitz  # noqa: F401
    except ImportError:
        skip("pymupdf not installed — PDF path is pymupdf-only")
    if shutil.which("pandoc") is None:
        skip("pandoc not on PATH (used to build PDF fixture)")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        body = (
            "# Test Document\n\n"
            + ("This is a paragraph of test content with enough characters "
               "to clear the scanned-PDF heuristic threshold. " * 5)
        )
        pdf = _make_pdf(td, body=body)
        if pdf is None:
            skip("pandoc could not build PDF fixture (no PDF engine)")
        out = td / "out.md"
        rc, stdout, stderr = _run_convert(pdf, out)
        assert rc == 0, f"rc={rc} stderr={stderr}"
        text = out.read_text()
        assert text.startswith("<!-- kb-update conversion"), "missing provenance comment"
        assert "test content" in text.lower(), \
            f"expected body content: {text[:300]!r}"


@case("unsupported extension exits 2")
def t_bad_ext():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bad = td / "foo.txt"
        bad.write_text("hello")
        out = td / "out.md"
        rc, _, stderr = _run_convert(bad, out)
        assert rc == 2, f"expected 2, got {rc}; stderr={stderr}"
        assert "unsupported extension" in stderr.lower()


@case("oversize input exits 4")
def t_oversize():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        big = td / "huge.pdf"
        # Write 26 MB. Don't bother making it a real PDF; size check
        # happens before any conversion attempt.
        with big.open("wb") as f:
            f.write(b"%PDF-1.4\n")
            f.write(b"\0" * (26 * 1024 * 1024))
        out = td / "out.md"
        rc, _, stderr = _run_convert(big, out)
        assert rc == 4, f"expected 4, got {rc}; stderr={stderr}"
        assert "too large" in stderr.lower() or "cap" in stderr.lower()


@case("scanned-pdf detection exits 5 (pymupdf path)")
def t_scanned_pdf():
    try:
        import fitz  # noqa: F401
    except ImportError:
        skip("pymupdf not installed — PDF path is pymupdf-only")
    if shutil.which("pandoc") is None:
        skip("pandoc not on PATH (used to build PDF fixture)")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        pdf = _make_pdf(td, body="hi\n")
        if pdf is None:
            skip("pandoc could not build PDF fixture")
        out = td / "out.md"
        rc, _, stderr = _run_convert(pdf, out)
        assert rc == 5, f"expected 5, got {rc}; stderr={stderr}"
        assert "scanned" in stderr.lower() or "ocr" in stderr.lower()


@case("missing pymupdf exits 3 for .pdf")
def t_missing_libs():
    try:
        import fitz  # noqa: F401
        skip("pymupdf installed — can't exercise the missing-lib path")
    except ImportError:
        pass
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        fake_pdf = td / "x.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4\nstub\n")
        out = td / "out.md"
        rc, _, stderr = _run_convert(fake_pdf, out)
        assert rc == 3, f"expected 3, got {rc}; stderr={stderr}"
        assert "pymupdf" in stderr.lower()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print()
    print(f"Summary: {len(PASSED)} passed, {len(FAILED)} failed, "
          f"{len(SKIPPED)} skipped (of "
          f"{len(PASSED) + len(FAILED) + len(SKIPPED)})")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
