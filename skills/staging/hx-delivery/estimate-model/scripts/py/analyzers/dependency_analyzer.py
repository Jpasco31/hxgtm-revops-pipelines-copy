"""
Dependency Analyzer

Analyzes formula dependency chains to determine complexity:
- Maximum dependency depth (longest chain)
- Median dependency depth
- Distribution of depths
- Cross-sheet reference patterns
- Most complex cells (deepest dependencies)
"""

import sys

try:
    from utils.formula_parser import extract_cell_references, extract_cross_sheet_references
except ImportError:
    from ..utils.formula_parser import extract_cell_references, extract_cross_sheet_references


class DependencyAnalyzer:
    def __init__(self, reader):
        self.reader = reader
        self.dependency_map = {}   # 'Sheet!Cell' -> {'formula': str, 'precedents': [str]}
        self.depth_cache = {}      # memoized depth results
        self.circular_refs = set()

    def analyze(self) -> dict:
        print("  Building dependency graph...", file=sys.stderr)
        self._build_dependency_map()

        print("  Calculating dependency depths...", file=sys.stderr)
        depths = self._calculate_all_depths()

        cross_sheet = self._analyze_cross_sheet_references()
        stats = self._calculate_statistics(depths)
        complex_cells = self._find_most_complex_cells(depths, 10)

        return {
            "maxDepth": stats["max"],
            "medianDepth": stats["median"],
            "averageDepth": stats["average"],
            "distribution": stats["distribution"],
            "totalFormulaCells": len(depths),
            "crossSheetReferences": {
                "count": cross_sheet["count"],
                "uniqueSheetPairs": len(cross_sheet["unique_pairs"]),
                "mostReferenced": cross_sheet["most_referenced"][:5],
            },
            "circularReferences": {
                "count": len(self.circular_refs),
                "detected": list(self.circular_refs)[:10],
            },
            "complexCells": complex_cells,
            "hasComplexDependencies": stats["max"] > 10 or cross_sheet["count"] > 1000,
        }

    def _build_dependency_map(self) -> None:
        reader = self.reader
        for ws, sheet_name in reader.iter_sheets():
            for cell, address in reader.iter_cells(ws):
                val = cell.value
                if not (isinstance(val, str) and (val.startswith("=") or val.startswith("{="))):
                    continue
                formula = val[1:] if val.startswith("=") else val[2:]
                cell_key = f"{sheet_name}!{address}"
                refs = extract_cell_references(formula)
                precedents = list({
                    f"{(r['sheet'] or sheet_name)}!{r['cell'].replace('$', '')}"
                    for r in refs if not r.get("workbook")
                })
                self.dependency_map[cell_key] = {
                    "formula": formula,
                    "precedents": precedents,
                }

    def _calculate_all_depths(self) -> list:
        return [
            {"cell": key, "depth": self._calculate_depth(key, set())}
            for key in self.dependency_map
        ]

    def _calculate_depth(self, cell_key: str, visited: set) -> int:
        if cell_key in self.depth_cache:
            return self.depth_cache[cell_key]
        if cell_key in visited:
            self.circular_refs.add(cell_key)
            return 0

        node = self.dependency_map.get(cell_key)
        if not node or not node["precedents"]:
            self.depth_cache[cell_key] = 0
            return 0

        visited = visited | {cell_key}  # immutable copy for each branch
        max_precedent_depth = 0
        for precedent in node["precedents"]:
            d = self._calculate_depth(precedent, visited)
            if d > max_precedent_depth:
                max_precedent_depth = d

        depth = max_precedent_depth + 1
        self.depth_cache[cell_key] = depth
        return depth

    def _analyze_cross_sheet_references(self) -> dict:
        reader = self.reader
        total_count = 0
        unique_pairs = set()
        sheet_ref_counts = {}

        for ws, sheet_name in reader.iter_sheets():
            for cell, address in reader.iter_cells(ws):
                val = cell.value
                if not (isinstance(val, str) and (val.startswith("=") or val.startswith("{="))):
                    continue
                formula = val[1:] if val.startswith("=") else val[2:]
                for ref in extract_cross_sheet_references(formula, sheet_name):
                    total_count += 1
                    unique_pairs.add(f"{sheet_name}->{ref['sheet']}")
                    sheet_ref_counts[ref["sheet"]] = sheet_ref_counts.get(ref["sheet"], 0) + 1

        most_referenced = sorted(
            [{"sheet": s, "referenceCount": c} for s, c in sheet_ref_counts.items()],
            key=lambda x: -x["referenceCount"],
        )
        return {"count": total_count, "unique_pairs": unique_pairs, "most_referenced": most_referenced}

    def _calculate_statistics(self, depths: list) -> dict:
        if not depths:
            return {"max": 0, "median": 0, "average": 0.0, "distribution": {}}

        values = sorted(d["depth"] for d in depths)
        n = len(values)
        max_d = values[-1]
        median_d = values[n // 2]
        avg_d = round(sum(values) / n, 1)

        buckets = {"0-5": 0, "6-10": 0, "11-20": 0, "21-50": 0, "51+": 0}
        for v in values:
            if v <= 5:       buckets["0-5"] += 1
            elif v <= 10:    buckets["6-10"] += 1
            elif v <= 20:    buckets["11-20"] += 1
            elif v <= 50:    buckets["21-50"] += 1
            else:            buckets["51+"] += 1

        distribution = {
            k: {"count": c, "percentage": round(c / n * 100, 1)}
            for k, c in buckets.items()
        }
        return {"max": max_d, "median": median_d, "average": avg_d, "distribution": distribution}

    def _find_most_complex_cells(self, depths: list, limit: int) -> list:
        sorted_depths = sorted(
            (d for d in depths if d["depth"] > 0),
            key=lambda x: -x["depth"],
        )[:limit]

        result = []
        for d in sorted_depths:
            parts = d["cell"].split("!", 1)
            node = self.dependency_map.get(d["cell"])
            result.append({
                "cell": d["cell"],
                "sheet": parts[0],
                "address": parts[1] if len(parts) > 1 else "",
                "depth": d["depth"],
                "formula": (node["formula"][:100] if node else ""),
                "precedentCount": len(node["precedents"]) if node else 0,
            })
        return result
