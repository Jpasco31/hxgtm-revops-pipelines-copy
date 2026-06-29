"""
Cell Reference Parser

Utilities for parsing and converting Excel cell references:
- A1 notation to row/col indices
- Sheet-qualified references ('Sheet1'!A1)
- Workbook-qualified references ([Workbook.xlsx]Sheet1!A1)
"""

import re


def a1_to_row_col(a1: str):
    """
    Convert A1 notation to (row, col) tuple (0-indexed).
    Returns None if not a valid A1 reference.
    """
    if not a1 or not isinstance(a1, str):
        return None
    cleaned = a1.replace("$", "")
    m = re.match(r"^([A-Z]+)(\d+)$", cleaned, re.IGNORECASE)
    if not m:
        return None
    col_str, row_str = m.group(1).upper(), m.group(2)
    col = 0
    for ch in col_str:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    col -= 1  # 0-indexed
    row = int(row_str) - 1  # 0-indexed
    return row, col


def row_col_to_a1(row: int, col: int) -> str:
    """Convert 0-indexed (row, col) to A1 notation."""
    col_str = ""
    c = col + 1
    while c > 0:
        remainder = (c - 1) % 26
        col_str = chr(ord("A") + remainder) + col_str
        c = (c - 1) // 26
    return f"{col_str}{row + 1}"


def parse_reference(ref: str) -> dict:
    """
    Parse a cell reference that may be sheet-qualified.
    Returns {'sheet': str|None, 'cell': str|None, 'is_qualified': bool}
    """
    if not ref or not isinstance(ref, str):
        return {"sheet": None, "cell": None, "is_qualified": False}
    m = re.match(r"^(?:'([^']+)'|([^!]+))!(.+)$", ref)
    if m:
        sheet = m.group(1) or m.group(2)
        return {"sheet": sheet, "cell": m.group(3), "is_qualified": True}
    return {"sheet": None, "cell": ref, "is_qualified": False}


def parse_full_reference(ref: str) -> dict:
    """
    Parse a reference that may include workbook qualification.
    Returns {'workbook': str|None, 'sheet': str|None, 'cell': str|None}
    """
    if not ref or not isinstance(ref, str):
        return {"workbook": None, "sheet": None, "cell": None}
    m = re.match(r"^\[([^\]]+)\](.+)$", ref)
    if m:
        parsed = parse_reference(m.group(2))
        return {"workbook": m.group(1), "sheet": parsed["sheet"], "cell": parsed["cell"]}
    parsed = parse_reference(ref)
    return {"workbook": None, "sheet": parsed["sheet"], "cell": parsed["cell"]}


def is_cell_reference(s: str) -> bool:
    """Check if string is an A1-style cell reference."""
    if not s or not isinstance(s, str):
        return False
    return bool(re.match(r"^[A-Z$]+\d+$", s, re.IGNORECASE))


def is_range_reference(s: str) -> bool:
    """Check if string is a range reference (A1:B10)."""
    if not s or not isinstance(s, str):
        return False
    return bool(re.match(r"^[A-Z$]+\d+:[A-Z$]+\d+$", s, re.IGNORECASE))


def parse_range(range_str: str):
    """Parse a range reference into start/end tuples. Returns None if invalid."""
    if not is_range_reference(range_str):
        return None
    parts = range_str.split(":")
    start = a1_to_row_col(parts[0])
    end = a1_to_row_col(parts[1])
    if start is None or end is None:
        return None
    return {"start": {"row": start[0], "col": start[1]},
            "end": {"row": end[0], "col": end[1]}}
