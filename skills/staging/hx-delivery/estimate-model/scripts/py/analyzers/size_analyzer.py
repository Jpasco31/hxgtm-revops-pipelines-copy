"""
Size Analyzer

Analyzes basic size metrics of an Excel workbook:
- File size, sheet counts, cell counts
- Formula vs input cells
- Named ranges
- Array formulas, volatile functions, errors
- Actuarial/stochastic model detection
"""

try:
    from utils.formula_parser import (
        has_volatile_function, is_array_formula,
        has_modern_functions, detect_modern_functions,
        MODERN_DYNAMIC_ARRAY, MODERN_LOGIC,
    )
except ImportError:
    from ..utils.formula_parser import (
        has_volatile_function, is_array_formula,
        has_modern_functions, detect_modern_functions,
        MODERN_DYNAMIC_ARRAY, MODERN_LOGIC,
    )

ACTUARIAL_KEYWORDS = ["triangle", "simulation", "stochastic", "monte carlo", "montecarlo"]


def _analyze_modern_functions(hits: list) -> dict:
    """Pass-2: detailed analysis of cells that passed the modern-function Pass-1 check."""
    _EMPTY = {
        "detected": False, "requiresExcel365": False, "functions": {},
        "lambdaCells": [], "letCells": [], "complexityLevel": "NONE", "complexityScore": 0,
    }
    if not hits:
        return _EMPTY

    func_counts = {}
    lambda_cells = []
    let_cells = []

    for sheet_name, address, formula in hits:
        fns = detect_modern_functions(formula)
        for fn in fns:
            func_counts[fn] = func_counts.get(fn, 0) + 1
        if "LAMBDA" in fns and len(lambda_cells) < 20:
            lambda_cells.append({"sheet": sheet_name, "cell": address, "formula": formula[:100]})
        if "LET" in fns and len(let_cells) < 20:
            let_cells.append({"sheet": sheet_name, "cell": address, "formula": formula[:100]})

    if not func_counts:
        return _EMPTY

    has_lambda = "LAMBDA" in func_counts
    has_let = "LET" in func_counts
    has_other_logic = any(fn in MODERN_LOGIC for fn in func_counts if fn not in {"LET", "LAMBDA"})
    has_dynamic = any(fn in MODERN_DYNAMIC_ARRAY for fn in func_counts)

    # Complexity level per CLAUDE.md heuristics
    if has_lambda:
        lambda_count = func_counts.get("LAMBDA", 0)
        nested = lambda_count > 5 or (has_let and lambda_count > 1)
        level = "EXTREME" if nested else "VERY_HIGH"
    elif has_let or has_other_logic:
        level = "HIGH"
    elif has_dynamic:
        level = "MODERATE"
    else:
        level = "MODERATE"

    score_map = {"MODERATE": 1, "HIGH": 2, "VERY_HIGH": 3, "EXTREME": 3}

    functions_with_category = {
        fn: {"count": cnt, "category": "LOGIC" if fn in MODERN_LOGIC else "DYNAMIC_ARRAY"}
        for fn, cnt in func_counts.items()
    }

    return {
        "detected": True,
        "requiresExcel365": True,
        "functions": functions_with_category,
        "lambdaCells": lambda_cells[:10],
        "letCells": let_cells[:10],
        "complexityLevel": level,
        "complexityScore": score_map[level],
    }


class SizeAnalyzer:
    def __init__(self, reader):
        self.reader = reader

    def analyze(self) -> dict:
        reader = self.reader
        metadata = reader.get_metadata()

        has_array_formulas = False
        volatile_functions = []
        modern_hits = []   # (sheet_name, address, formula) for pass-2 modern function analysis
        sheet_analysis = []

        for ws, sheet_name in reader.iter_sheets():
            sheet_formulas = 0
            sheet_inputs = 0
            sheet_cells = 0

            for cell, address in reader.iter_cells(ws):
                sheet_cells += 1
                val = cell.value

                if isinstance(val, str) and (val.startswith("=") or val.startswith("{=")):
                    sheet_formulas += 1
                    formula = val[1:] if val.startswith("=") else val[2:]

                    if is_array_formula(cell):
                        has_array_formulas = True

                    if has_volatile_function(formula):
                        volatile_functions.append({
                            "sheet": sheet_name,
                            "cell": address,
                            "formula": formula[:200],  # truncate long formulas
                        })

                    # Pass 1: fast check for modern functions
                    if has_modern_functions(formula):
                        modern_hits.append((sheet_name, address, formula))

                elif val is not None:
                    sheet_inputs += 1

            # Dimensions of used range
            try:
                range_str = ws.dimensions or "Empty"
            except Exception:
                range_str = "Unknown"

            sheet_analysis.append({
                "name": sheet_name,
                "cells": sheet_cells,
                "formulas": sheet_formulas,
                "inputs": sheet_inputs,
                "range": range_str,
            })

        # Pass 2: detailed modern function analysis (only runs if Pass 1 found hits)
        modern_functions_result = _analyze_modern_functions(modern_hits)

        named_ranges = reader.get_named_ranges()
        sheet_counts = reader.count_sheets_by_visibility()

        # Use XML-based counts for totals (accurate across all files)
        formula_cells = reader._get_total_formula_cells()
        error_cells_count = reader._get_total_error_cells()
        total_cells = sum(s["cells"] for s in sheet_analysis)
        input_cells = max(0, total_cells - formula_cells)

        # Macro detection
        is_macro_enabled = metadata["fileName"].lower().endswith(".xlsm")

        # Actuarial/stochastic model detection
        all_text = " ".join([
            *[s["name"] for s in sheet_analysis],
            *[n.get("name", "") for n in named_ranges],
            metadata["fileName"],
        ]).lower()

        is_actuarial = any(kw in all_text for kw in ACTUARIAL_KEYWORDS)
        detected_keywords = [kw for kw in ACTUARIAL_KEYWORDS if kw in all_text]

        return {
            "metadata": {
                "fileName": metadata["fileName"],
                "fileSizeMB": metadata["fileSizeMB"],
                "samplingUsed": metadata["samplingUsed"],
                "samplingMethod": metadata["samplingMethod"],
            },
            "size": {
                "sheetCount": sheet_counts["total"],
                "visibleSheets": sheet_counts["visible"],
                "hiddenSheets": sheet_counts["hidden"],
                "veryHiddenSheets": sheet_counts["veryHidden"],
                "totalCells": total_cells,
                "inputCells": input_cells,
                "formulaCells": formula_cells,
                "uniqueFormulas": 0,   # expensive to compute; left for future
                "emptyCells": 0,
            },
            "formulas": {
                "hasArrayFormulas": has_array_formulas,
                "volatileFunctions": {
                    "count": len(volatile_functions),
                    "samples": volatile_functions[:10],
                },
            },
            "risks": {
                "errorCells": {
                    "count": error_cells_count,
                    "samples": [],  # sample collection requires extra pass; omitted for speed
                },
            },
            "namedRanges": {
                "count": len(named_ranges),
                "samples": named_ranges[:10],
            },
            "macro": {
                "isMacroEnabled": is_macro_enabled,
            },
            "modelType": {
                "isActuarialModel": is_actuarial,
                "detectedKeywords": detected_keywords,
                "flagged": is_actuarial,
            },
            "modernFunctions": modern_functions_result,
            "sheets": sheet_analysis,
        }
