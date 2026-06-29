"""
Formula Parser

Extracts cell references and analyzes Excel formulas.
"""

import re
from .cell_reference_parser import parse_full_reference, is_cell_reference, is_range_reference

# Reference pattern: optional [Workbook], optional sheet (quoted or unquoted), then cell/range
_REF_PATTERN = re.compile(
    r"(?:\[([^\]]+)\])?"           # optional [Workbook]
    r"(?:'([^']+)'|([^!':\s(),]+))?"  # optional sheet (quoted or bare)
    r"!?"                           # optional !
    r"([A-Z\$]+\d+(?::[A-Z\$]+\d+)?)",  # cell or range
    re.IGNORECASE,
)

_VOLATILE_RE = re.compile(r"\b(NOW|TODAY|INDIRECT|OFFSET|RAND|RANDBETWEEN)\s*\(", re.IGNORECASE)

_FUNCTION_RE = re.compile(r"\b([A-Z_][A-Z0-9_\.]*)\s*\(", re.IGNORECASE)

# Modern Excel functions (Excel 365/2021+)
MODERN_DYNAMIC_ARRAY = frozenset({
    "FILTER", "SORT", "SORTBY", "UNIQUE", "SEQUENCE", "RANDARRAY", "XLOOKUP",
})
MODERN_LOGIC = frozenset({
    "LET", "LAMBDA", "MAKEARRAY", "MAP", "REDUCE", "SCAN", "BYCOL", "BYROW",
})

# Pass-1 fast scan: presence check; Pass-2 uses same regex to extract names
_MODERN_PASS1_RE = re.compile(
    r"\b(FILTER|SORT|SORTBY|UNIQUE|SEQUENCE|RANDARRAY|XLOOKUP"
    r"|LET|LAMBDA|MAKEARRAY|MAP|REDUCE|SCAN|BYCOL|BYROW)\s*\(",
    re.IGNORECASE,
)

_FORMULA_PATTERNS = {
    "LOOKUP":      re.compile(r"\b(VLOOKUP|HLOOKUP|XLOOKUP|INDEX|MATCH|LOOKUP)\b", re.IGNORECASE),
    "CONDITIONAL": re.compile(r"\b(IF|IFS|SWITCH|CHOOSE)\b", re.IGNORECASE),
    "AGGREGATION": re.compile(r"\b(SUM|SUMIF|SUMIFS|AVERAGE|AVERAGEIF|AVERAGEIFS|COUNT|COUNTA|COUNTIF|COUNTIFS|COUNTBLANK)\b", re.IGNORECASE),
    "ARRAY":       re.compile(r"\b(SUMPRODUCT|MMULT|TRANSPOSE|FILTER|SORT|UNIQUE)\b", re.IGNORECASE),
    "TEXT":        re.compile(r"\b(CONCATENATE|TEXTJOIN|CONCAT|LEFT|RIGHT|MID|FIND|SEARCH|SUBSTITUTE|REPLACE|TEXT|LEN|TRIM)\b", re.IGNORECASE),
    "DATE_TIME":   re.compile(r"\b(DATE|TIME|YEAR|MONTH|DAY|HOUR|MINUTE|SECOND|NOW|TODAY|EOMONTH|EDATE|DATEDIF|NETWORKDAYS|WORKDAY)\b", re.IGNORECASE),
    "FINANCIAL":   re.compile(r"\b(NPV|IRR|XIRR|XNPV|PMT|IPMT|PPMT|FV|PV|RATE|NPER)\b", re.IGNORECASE),
    "STATISTICAL": re.compile(r"\b(STDEV|STDEVP|STDEV\.S|STDEV\.P|VAR|VARP|VAR\.S|VAR\.P|CORREL|COVARIANCE|PERCENTILE|QUARTILE|MEDIAN|MODE)\b", re.IGNORECASE),
    "VOLATILE":    re.compile(r"\b(NOW|TODAY|INDIRECT|OFFSET|RAND|RANDBETWEEN)\b", re.IGNORECASE),
    "DATABASE":    re.compile(r"\b(DSUM|DCOUNT|DAVERAGE|DMAX|DMIN|DGET|DCOUNTA)\b", re.IGNORECASE),
    "LOGICAL":     re.compile(r"\b(AND|OR|NOT|XOR|TRUE|FALSE|IFERROR|IFNA|ISERROR|ISNA|ISBLANK)\b", re.IGNORECASE),
    "MATH":        re.compile(r"\b(ROUND|ROUNDUP|ROUNDDOWN|CEILING|FLOOR|ABS|SQRT|POWER|EXP|LN|LOG|LOG10|MOD|INT|TRUNC)\b", re.IGNORECASE),
}


def extract_cell_references(formula: str) -> list:
    """
    Extract all cell references from a formula string.
    Handles: A1, Sheet1!A1, 'Sheet Name'!A1, [Workbook.xlsx]Sheet1!A1, A1:B10
    """
    if not formula or not isinstance(formula, str):
        return []
    f = formula[1:] if formula.startswith("=") else formula
    references = []
    for m in _REF_PATTERN.finditer(f):
        workbook = m.group(1) or None
        sheet = m.group(2) or m.group(3) or None
        cell_or_range = m.group(4)
        raw = m.group(0)
        if ":" in cell_or_range:
            parts = cell_or_range.split(":")
            references.append({"workbook": workbook, "sheet": sheet,
                                "cell": parts[0], "raw": raw,
                                "is_range": True, "range_end": parts[1]})
        else:
            references.append({"workbook": workbook, "sheet": sheet,
                                "cell": cell_or_range, "raw": raw, "is_range": False})
    return references


def extract_cross_sheet_references(formula: str, current_sheet: str) -> list:
    """Return only references that point to a different sheet."""
    return [
        {"sheet": r["sheet"], "cell": r["cell"]}
        for r in extract_cell_references(formula)
        if r["sheet"] and r["sheet"] != current_sheet
    ]


def extract_external_references(formula: str) -> list:
    """Return references that include a workbook qualifier."""
    return [r for r in extract_cell_references(formula) if r["workbook"]]


def has_modern_functions(formula: str) -> bool:
    """Pass-1 check: does formula contain any modern Excel 365/2021+ functions?"""
    return bool(_MODERN_PASS1_RE.search(formula)) if formula else False


def detect_modern_functions(formula: str) -> list:
    """Pass-2 detailed: return list of modern function names found (uppercase)."""
    if not formula:
        return []
    return list({m.group(1).upper() for m in _MODERN_PASS1_RE.finditer(formula)})


def has_volatile_function(formula: str) -> bool:
    """Check if formula contains volatile functions."""
    if not formula:
        return False
    return bool(_VOLATILE_RE.search(formula))


def extract_functions(formula: str) -> list:
    """Extract unique function names used in a formula (uppercase)."""
    if not formula or not isinstance(formula, str):
        return []
    return list({m.group(1).upper() for m in _FUNCTION_RE.finditer(formula)})


def categorize_formula(formula: str) -> list:
    """Return list of matching category names for a formula."""
    if not formula:
        return []
    return [cat for cat, pattern in _FORMULA_PATTERNS.items() if pattern.search(formula)]


def is_array_formula(cell) -> bool:
    """
    Check if a cell contains an array formula.
    In openpyxl, array formulas are stored with value starting '{='.
    """
    if cell is None:
        return False
    val = cell.value
    return isinstance(val, str) and val.startswith("{=")


def analyze_complexity(formula: str) -> dict:
    """Rough complexity heuristic based on length, nesting, function count."""
    if not formula:
        return {"length": 0, "nesting_depth": 0, "function_count": 0, "complexity": "SIMPLE"}
    length = len(formula)
    functions = extract_functions(formula)
    function_count = len(functions)
    max_depth = current_depth = 0
    for ch in formula:
        if ch == "(":
            current_depth += 1
            max_depth = max(max_depth, current_depth)
        elif ch == ")":
            current_depth -= 1
    if length > 500 or function_count > 10 or max_depth > 5:
        complexity = "COMPLEX"
    elif length > 200 or function_count > 5 or max_depth > 3:
        complexity = "MEDIUM"
    else:
        complexity = "SIMPLE"
    return {"length": length, "nesting_depth": max_depth,
            "function_count": function_count, "complexity": complexity}


def has_hard_coded_values(formula: str) -> bool:
    """Check if formula contains hard-coded numeric or string literals."""
    if not formula:
        return False
    return bool(re.search(r'\b\d+(?:\.\d+)?\b(?![A-Z])', formula) or
                re.search(r'"[^"]*"', formula))
