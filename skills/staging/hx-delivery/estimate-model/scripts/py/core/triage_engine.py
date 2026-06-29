"""
Triage Engine

Orchestrates all analyzers and produces comprehensive analysis results.
"""

import sys
import time
from datetime import datetime, timezone

try:
    from core.excel_reader import ExcelReader
    from analyzers.size_analyzer import SizeAnalyzer
    from analyzers.dependency_analyzer import DependencyAnalyzer
    from analyzers.vba_analyzer import VBAAnalyzer
    from core.sizing_engine import SizingEngine
except ImportError:
    from .excel_reader import ExcelReader
    from ..analyzers.size_analyzer import SizeAnalyzer
    from ..analyzers.dependency_analyzer import DependencyAnalyzer
    from ..analyzers.vba_analyzer import VBAAnalyzer
    from .sizing_engine import SizingEngine

VERSION = "1.0.0-py"


class TriageEngine:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.reader = None

    def analyze(self) -> dict:
        start = time.time()

        # Step 1: Load workbook
        self.reader = ExcelReader(self.file_path)
        self.reader.load()

        # Step 2: Size analysis
        size_results = SizeAnalyzer(self.reader).analyze()

        # Step 3: Dependency analysis
        print("  Analyzing formula dependencies...", file=sys.stderr)
        dep_results = DependencyAnalyzer(self.reader).analyze()
        size_results["dependencies"] = dep_results

        # Step 4: VBA analysis (macro-enabled files only)
        if size_results.get("macro", {}).get("isMacroEnabled"):
            print("  Analyzing VBA macros...", file=sys.stderr)
            vba_results = VBAAnalyzer(self.file_path).analyze()
        else:
            vba_results = {
                "hasVBA": False, "accessible": False,
                "totalLines": 0,
                "complexity": {"level": "NONE", "score": 0},
            }
        size_results["vba"] = vba_results

        # Step 5: Sizing
        sizing = SizingEngine().calculate_size(size_results)

        duration_ms = int((time.time() - start) * 1000)

        return {
            **size_results,
            "sizing": sizing,
            "analysis": {
                "date": datetime.now(timezone.utc).isoformat(),
                "duration": duration_ms,
                "version": VERSION,
            },
        }

    def get_reader(self):
        return self.reader
