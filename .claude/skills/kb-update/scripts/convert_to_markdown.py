#!/usr/bin/env python3
"""
convert_to_markdown.py

Convert a PDF or DOCX file to markdown so the kb-update comparator
pipeline (which only knows .md) can consume it. Backends:

  - PDF  → pymupdf (fitz). Pandoc cannot read PDFs.
  - DOCX → pandoc on PATH if present (better fidelity), else mammoth.

Usage:
  python3 convert_to_markdown.py --input <path> --output <path>

Always re-converts (no caching). Prints the output path on stdout.

Exit codes:
  0  success
  2  unsupported extension
  3  required Python lib missing (pymupdf for .pdf; mammoth for .docx
     when pandoc isn't on PATH)
  4  input file too large (> MAX_INPUT_BYTES)
  5  scanned/image-only PDF (avg < SCANNED_PDF_MIN_CHARS_PER_PAGE)
  6  converted output too large (> MAX_OUTPUT_BYTES)
  1  any other structural failure
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


SUPPORTED_EXTS = {".pdf", ".docx"}
MAX_INPUT_BYTES = 25 * 1024 * 1024   # 25 MB
MAX_OUTPUT_BYTES = 2 * 1024 * 1024   # 2 MB
SCANNED_PDF_MIN_CHARS_PER_PAGE = 50


def _provenance_comment(source_name: str, converter: str) -> str:
    return f"<!-- kb-update conversion · source: {source_name} · converter: {converter} -->\n\n"


def _pandoc_available() -> bool:
    return shutil.which("pandoc") is not None


def _convert_with_pandoc(input_path: Path, output_path: Path) -> str:
    """Returns the markdown body (without provenance prefix)."""
    proc = subprocess.run(
        ["pandoc", str(input_path), "-t", "markdown", "--wrap=none"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pandoc failed (exit {proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout


def _try_pip_install(packages):
    """One-shot, best-effort pip install. Tries --user first; falls
    back to --break-system-packages on PEP 668 / externally-managed
    environments. Silent on success, returns False on failure."""
    base = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"]
    for extra in (["--user"], ["--user", "--break-system-packages"]):
        proc = subprocess.run(
            base + extra + list(packages),
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            return True
    return False


def _import_or_install(module_name, pip_name):
    """Optimistic import; on ImportError, try to pip install once and retry.
    Returns the imported module or None."""
    try:
        return __import__(module_name)
    except ImportError:
        pass
    sys.stderr.write(
        f"[convert_to_markdown] {module_name} not installed — "
        f"attempting one-shot `pip install {pip_name}`...\n"
    )
    if not _try_pip_install([pip_name]):
        return None
    # User-site dirs may not be on sys.path yet for the running interpreter.
    import site, importlib
    site.main()
    importlib.invalidate_caches()
    try:
        return __import__(module_name)
    except ImportError:
        return None


def _convert_pdf_pymupdf(input_path: Path):
    """Returns (markdown_body, page_count)."""
    fitz = _import_or_install("fitz", "pymupdf")
    if fitz is None:
        sys.stderr.write(
            "ERROR: pymupdf not installed and auto-install failed.\n"
            "  Install manually: `pip install pymupdf` "
            "(or `pip install --user --break-system-packages pymupdf`).\n"
        )
        sys.exit(3)

    doc = fitz.open(str(input_path))
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    body = "\n\n---\n\n".join(p.rstrip() for p in pages)
    return body, len(pages)


def _convert_docx_mammoth(input_path: Path) -> str:
    mammoth = _import_or_install("mammoth", "mammoth")
    if mammoth is None:
        sys.stderr.write(
            "ERROR: mammoth not installed and auto-install failed.\n"
            "  Install pandoc (preferred) OR `pip install mammoth` "
            "(or `pip install --user --break-system-packages mammoth`).\n"
        )
        sys.exit(3)

    with input_path.open("rb") as f:
        result = mammoth.convert_to_markdown(f)
    return result.value


def convert(input_path: Path, output_path: Path) -> int:
    ext = input_path.suffix.lower()
    if ext not in SUPPORTED_EXTS:
        sys.stderr.write(
            f"ERROR: unsupported extension {ext!r}. "
            f"convert_to_markdown.py handles: {sorted(SUPPORTED_EXTS)}.\n"
        )
        return 2

    if not input_path.exists():
        sys.stderr.write(f"ERROR: input not found: {input_path}\n")
        return 1

    size = input_path.stat().st_size
    if size > MAX_INPUT_BYTES:
        sys.stderr.write(
            f"ERROR: {input_path.name} is {size / 1024 / 1024:.1f} MB "
            f"(cap: {MAX_INPUT_BYTES // 1024 // 1024} MB). "
            "Excerpt the relevant pages and paste inline instead.\n"
        )
        return 4

    output_path.parent.mkdir(parents=True, exist_ok=True)

    page_count = None
    if ext == ".pdf":
        body, page_count = _convert_pdf_pymupdf(input_path)
        converter = "pymupdf"
    elif _pandoc_available():
        try:
            body = _convert_with_pandoc(input_path, output_path)
        except RuntimeError as exc:
            sys.stderr.write(f"ERROR: {exc}\n")
            return 1
        converter = "pandoc"
    else:
        body = _convert_docx_mammoth(input_path)
        converter = "mammoth"

    # Scanned-PDF detection — pymupdf path (always for .pdf).
    if ext == ".pdf":
        body_chars = len(body.strip())
        if page_count and page_count > 0:
            avg_chars = body_chars / page_count
            if avg_chars < SCANNED_PDF_MIN_CHARS_PER_PAGE:
                sys.stderr.write(
                    f"ERROR: {input_path.name} looks like a scanned/image PDF "
                    f"(avg {avg_chars:.0f} chars/page, threshold "
                    f"{SCANNED_PDF_MIN_CHARS_PER_PAGE}). OCR required — kb-update "
                    "doesn't run OCR. Try `ocrmypdf <in> <out>` and re-attach.\n"
                )
                return 5

    full_output = _provenance_comment(input_path.name, converter) + body
    output_bytes = full_output.encode("utf-8")
    if len(output_bytes) > MAX_OUTPUT_BYTES:
        sys.stderr.write(
            f"ERROR: converted markdown is "
            f"{len(output_bytes) / 1024 / 1024:.1f} MB "
            f"(cap: {MAX_OUTPUT_BYTES // 1024 // 1024} MB). "
            "Excerpt the relevant section and re-attach.\n"
        )
        return 6

    with output_path.open("w", encoding="utf-8") as f:
        f.write(full_output)

    sys.stdout.write(str(output_path) + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Convert a PDF or DOCX file to markdown for kb-update."
    )
    parser.add_argument("--input", required=True, help="Path to .pdf or .docx file")
    parser.add_argument("--output", required=True, help="Destination .md path")
    args = parser.parse_args()

    return convert(Path(args.input).resolve(), Path(args.output).resolve())


if __name__ == "__main__":
    sys.exit(main())
