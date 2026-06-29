"""
Sizing Engine

Calculates t-shirt size (SMALL/MEDIUM/LARGE/EXTRA_LARGE) with confidence levels
based on analysis results and the configurable sizing-heuristics.json.
"""

import json
import os
from pathlib import Path

_DEFAULT_HEURISTICS_PATH = Path(__file__).parent.parent.parent / "sizing-heuristics.json"

_DEFAULT_HEURISTICS = {
    "factors": {
        "formulaCount":    {"weight": 0.30, "thresholds": {"small": 2000,  "medium": 10000, "large": 50000}},
        "worksheetCount":  {"weight": 0.15, "thresholds": {"small": 5,     "medium": 15,    "large": 30}},
        "fileSize":        {"weight": 0.10, "thresholds": {"small": 2,     "medium": 10,    "large": 50}},
        "namedRanges":     {"weight": 0.10, "thresholds": {"small": 50,    "medium": 500,   "large": 2000}},
        "volatileFunctions": {"weight": 0.10, "thresholds": {"small": 10,  "medium": 100,   "large": 500}},
    },
    "confidenceFactors": {"errorCellThreshold": 100, "maxUncertainties": 2},
}


class SizingEngine:
    def __init__(self, heuristics_path=None):
        path = heuristics_path or _DEFAULT_HEURISTICS_PATH
        try:
            with open(path, encoding="utf-8") as f:
                self.heuristics = json.load(f)
        except Exception:
            self.heuristics = _DEFAULT_HEURISTICS

    def _score_value(self, value: float, thresholds: dict) -> float:
        if value <= thresholds["small"]:  return 0.5
        if value <= thresholds["medium"]: return 1.5
        if value <= thresholds["large"]:  return 2.5
        return 3.0

    def calculate_size(self, analysis_results: dict) -> dict:
        factors = self.heuristics["factors"]
        scores = {}
        total_score = 0.0

        def _score(factor_name, value):
            cfg = factors.get(factor_name)
            if cfg is None:
                return
            s = self._score_value(value, cfg["thresholds"])
            scores[factor_name] = s
            nonlocal total_score
            total_score += s * cfg["weight"]

        _score("formulaCount",     analysis_results.get("size", {}).get("formulaCells", 0))
        _score("worksheetCount",   analysis_results.get("size", {}).get("sheetCount", 0))
        _score("fileSize",         analysis_results.get("metadata", {}).get("fileSizeMB", 0))
        _score("namedRanges",      analysis_results.get("namedRanges", {}).get("count", 0))
        _score("volatileFunctions",analysis_results.get("formulas", {}).get("volatileFunctions", {}).get("count", 0))
        _score("vbaComplexity",    analysis_results.get("vba", {}).get("complexity", {}).get("score", 0))
        _score("dependencyDepth",  analysis_results.get("dependencies", {}).get("maxDepth", 0))

        # Modern functions: categorical scoring (only contributes when present)
        mf_score_val = analysis_results.get("modernFunctions", {}).get("complexityScore", 0)
        if mf_score_val > 0:
            mf_weight = 0.08
            scores["modernFunctions"] = float(mf_score_val)
            total_score += mf_score_val * mf_weight

        if total_score >= 2.75:   size = "EXTRA_LARGE"
        elif total_score >= 2.5:  size = "LARGE"
        elif total_score >= 1.5:  size = "MEDIUM"
        else:                     size = "SMALL"

        confidence = self._calculate_confidence(analysis_results)
        key_factors = self._extract_key_factors(analysis_results, scores)

        return {
            "size": size,
            "confidence": confidence,
            "score": round(total_score, 2),
            "factors": key_factors,
            "scores": scores,
        }

    def _calculate_confidence(self, results: dict) -> dict:
        uncertainties = []
        vba = results.get("vba", {})
        if results.get("macro", {}).get("isMacroEnabled") and not vba.get("accessible"):
            uncertainties.append("Macro-enabled file - VBA complexity not yet analyzed")
        if results.get("metadata", {}).get("samplingUsed"):
            mb = results.get("metadata", {}).get("fileSizeMB", "?")
            uncertainties.append(f"Large file (>{mb} MB) - analysis based on sampling")

        max_u = self.heuristics["confidenceFactors"]["maxUncertainties"]
        if len(uncertainties) > max_u:    level = "LOW"
        elif len(uncertainties) > 0:      level = "MEDIUM"
        else:                             level = "HIGH"

        return {"level": level, "reasons": uncertainties}

    def _extract_key_factors(self, results: dict, scores: dict) -> list:
        factors = []

        formula_count = results.get("size", {}).get("formulaCells", 0)
        if formula_count > 5000:
            factors.append({
                "factor": "Formula Count", "value": f"{formula_count:,}",
                "contribution": "Very High" if formula_count > 50000 else "High" if formula_count > 10000 else "Moderate",
            })

        sheet_count = results.get("size", {}).get("sheetCount", 0)
        if sheet_count > 10:
            factors.append({
                "factor": "Worksheet Count", "value": sheet_count,
                "contribution": "Very High" if sheet_count > 30 else "High" if sheet_count > 15 else "Moderate",
            })

        file_size = results.get("metadata", {}).get("fileSizeMB", 0)
        if file_size > 5:
            factors.append({
                "factor": "File Size", "value": f"{file_size} MB",
                "contribution": "Very High" if file_size > 50 else "High" if file_size > 10 else "Moderate",
            })

        named_count = results.get("namedRanges", {}).get("count", 0)
        if named_count > 200:
            factors.append({
                "factor": "Named Ranges", "value": f"{named_count:,}",
                "contribution": "Very High" if named_count > 2000 else "High" if named_count > 500 else "Moderate",
            })

        volatile_count = results.get("formulas", {}).get("volatileFunctions", {}).get("count", 0)
        if volatile_count > 50:
            factors.append({"factor": "Volatile Functions", "value": f"{volatile_count:,}", "contribution": "Performance concern"})

        if results.get("formulas", {}).get("hasArrayFormulas"):
            factors.append({"factor": "Array Formulas", "value": "Present", "contribution": "Advanced formula techniques"})

        max_depth = results.get("dependencies", {}).get("maxDepth", 0)
        if max_depth > 10:
            factors.append({
                "factor": "Dependency Depth", "value": f"{max_depth} levels",
                "contribution": "Very complex dependencies" if max_depth > 30 else "Complex formula chains" if max_depth > 15 else "Moderate dependencies",
            })

        vba = results.get("vba", {})
        if vba.get("hasVBA") and vba.get("accessible"):
            vba_lines = vba.get("totalLines", 0)
            vba_level = vba.get("complexity", {}).get("level", "UNKNOWN")
            if vba_lines > 0:
                factors.append({
                    "factor": "VBA Code", "value": f"{vba_lines:,} lines ({vba_level})",
                    "contribution": "Complex automation" if vba_level == "HIGH" else "Moderate automation" if vba_level == "MEDIUM" else "Basic automation",
                })
        elif vba.get("passwordProtected"):
            factors.append({"factor": "VBA Code", "value": "Password protected", "contribution": "Unknown complexity"})

        error_count = results.get("risks", {}).get("errorCells", {}).get("count", 0)
        if error_count > 100:
            factors.append({"factor": "Error Cells", "value": f"{error_count:,}", "contribution": "Informational only"})

        mf = results.get("modernFunctions", {})
        if mf.get("detected"):
            fn_names = ", ".join(sorted(mf.get("functions", {}).keys()))
            level = mf.get("complexityLevel", "UNKNOWN")
            level_str = level.lower().replace("_", " ")
            factors.append({
                "factor": "Modern Excel Functions",
                "value": fn_names or "Present",
                "contribution": f"Requires Excel 365/2021+, {level_str} complexity",
            })

        intg = results.get("vba", {}).get("externalIntegrations", {})
        if intg.get("detected"):
            count = intg.get("totalCount", 0)
            overall = intg.get("overallComplexityImpact", "UNKNOWN")
            labels = "; ".join(i["label"] for i in intg.get("integrations", []))
            factors.append({
                "factor": "External Integrations",
                "value": f"{count} integration(s): {labels}",
                "contribution": f"{overall} complexity — each integration requires replication in target environment",
            })

        return factors
