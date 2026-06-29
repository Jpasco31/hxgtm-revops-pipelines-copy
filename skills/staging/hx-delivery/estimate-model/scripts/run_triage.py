#!/usr/bin/env python3
"""
Run Triage Analysis

Analyzes Excel rating models using the bundled analysis engine and writes
structured analysis data to an analysis/ directory next to the input.

Usage:
    python run_triage.py <path>

Where <path> is a single Excel file (.xlsx, .xlsm) or a directory
containing Excel files. Outputs are written to <parent>/analysis/.
"""

import copy
import json
import sys
from pathlib import Path

# Set up sys.path for bundled py/ package
_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR / "py"))

from core.triage_engine import TriageEngine

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}
_MAX_SHEETS_IN_PROMPT = 20


def discover_excel_files(path: Path) -> list:
    """
    Find Excel files from a path (single file or directory).
    Filters out ~$ temp files. Returns sorted list of Paths.
    """
    if path.is_file():
        if path.suffix.lower() in SUPPORTED_EXTENSIONS and not path.name.startswith("~$"):
            return [path]
        return []

    return sorted(
        [
            f for f in path.iterdir()
            if f.is_file()
            and not f.name.startswith("~$")
            and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ],
        key=lambda f: f.name,
    )


def analyze_file(file_path: Path) -> dict | None:
    """Run TriageEngine on a single file. Returns analysis dict or None on error."""
    try:
        engine = TriageEngine(str(file_path))
        return engine.analyze()
    except Exception as e:
        print(f"  Error analyzing {file_path.name}: {e}", file=sys.stderr)
        return None


def prepare_for_prompt(analysis: dict) -> dict:
    """Curate analysis dict for prompt inclusion."""
    data = copy.deepcopy(analysis)
    data.pop("analysis", None)

    if "sheets" in data and len(data["sheets"]) > _MAX_SHEETS_IN_PROMPT:
        total = len(data["sheets"])
        data["sheets"] = data["sheets"][:_MAX_SHEETS_IN_PROMPT]
        data["_sheets_truncated"] = f"Showing {_MAX_SHEETS_IN_PROMPT} of {total} sheets"

    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_triage.py <path-to-file-or-directory>", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1]).resolve()

    if not input_path.exists():
        print(f"Error: Path not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Determine output directory: analysis/ next to the input
    if input_path.is_file():
        output_dir = input_path.parent / "analysis"
    else:
        output_dir = input_path / "analysis"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Discover files
    files = discover_excel_files(input_path)
    if not files:
        print(f"Error: No supported Excel files found at {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing {len(files)} Excel file(s)", file=sys.stderr)

    # Analyze each file
    analyses = []
    for file in files:
        print(f"  {file.name}...", file=sys.stderr)
        result = analyze_file(file)
        if result is not None:
            size = result["sizing"]["size"]
            score = result["sizing"]["score"]
            print(f"    {size} (score: {score:.2f})", file=sys.stderr)
            analyses.append({
                "filename": file.name,
                "data": prepare_for_prompt(result),
            })

    if not analyses:
        print("Error: All files failed analysis.", file=sys.stderr)
        sys.exit(1)

    # Write analysis data
    output_file = output_dir / "analysis-data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analyses, f, indent=2, default=str)

    print(f"\nAnalysis complete:", file=sys.stderr)
    print(f"  Models analyzed: {len(analyses)}/{len(files)}", file=sys.stderr)
    print(f"  Output: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
