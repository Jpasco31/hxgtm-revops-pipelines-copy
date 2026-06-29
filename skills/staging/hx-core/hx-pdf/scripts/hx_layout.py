"""Generic hx-branded ReportLab layout helpers.

Copy this file into your report directory. Import from hx_styles.

Usage in generate_report.py:
    import hx_fonts, hx_layout
    hx_fonts.register()
    on_page = hx_layout.make_on_page_fn(
        header="hyperexponential  ·  My Report Title",
        footer="Confidential",
    )
    # Then use layout helpers to build the story list.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.flowables import HRFlowable

from hx_styles import (
    F_BOOK, F_BOLD, F_MEDIUM, F_ITALIC, F_LIGHT,
    HX_BLUE, HX_DARK, HX_DARK_COVER, HX_N300, HX_N600,
    RL_BLUE, RL_BLUE_LIGHT, RL_BLUE_MID,
    RL_DARK, RL_DARK_COVER, RL_GRAY_LIGHT, RL_GRAY_MID, RL_GRAY_DARK,
    RL_GREEN_BG, RL_GREEN_TEXT, RL_N100, RL_N300, RL_N400, RL_N600, RL_WHITE,
    STYLES,
)

_PAGE_W_MM = 210
_PAGE_H_MM = 297


# ---------------------------------------------------------------------------
# Page callbacks
# ---------------------------------------------------------------------------

def _draw_cover(canvas, doc):
    """Full-page dark background for the cover (page 1)."""
    w, h = doc.pagesize
    canvas.saveState()
    canvas.setFillColor(RL_DARK_COVER)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    # Thin blue accent line — marks the lower section of the cover
    canvas.setStrokeColor(RL_BLUE)
    canvas.setLineWidth(1.0)
    canvas.line(doc.leftMargin, 68 * mm, w - doc.rightMargin, 68 * mm)
    canvas.restoreState()


def make_on_page_fn(header: str, footer: str):
    """Return a ReportLab onPage callback with custom header and footer text.

    Args:
        header: Text shown in the running header on body pages, e.g.
                "hyperexponential  ·  Q1 2026 Analysis"
        footer: Text shown centred in the running footer, e.g.
                "Confidential — prepared for Acme Corp"
    """
    def _draw_body(canvas, doc):
        w, h = doc.pagesize
        canvas.saveState()

        # Header rule
        canvas.setStrokeColor(colors.HexColor(HX_N300))
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, h - 14 * mm, w - doc.rightMargin, h - 14 * mm)

        canvas.setFont(F_BOOK, 8)
        canvas.setFillColor(colors.HexColor(HX_N600))
        canvas.drawString(doc.leftMargin, h - 10.5 * mm, header)
        canvas.drawRightString(w - doc.rightMargin, h - 10.5 * mm, f"Page {doc.page}")

        # Footer rule + text
        canvas.line(doc.leftMargin, 14 * mm, w - doc.rightMargin, 14 * mm)
        canvas.setFont(F_BOOK, 7.5)
        canvas.drawCentredString(w / 2, 9.5 * mm, footer)
        canvas.restoreState()

    def _on_page(canvas, doc):
        if doc.page == 1:
            _draw_cover(canvas, doc)
        else:
            _draw_body(canvas, doc)

    return _on_page


# ---------------------------------------------------------------------------
# Generic flowable helpers — use these to build your story list
# ---------------------------------------------------------------------------

def spacer(h_mm: float = 4) -> Spacer:
    return Spacer(1, h_mm * mm)


def rule(color=None, thickness: float = 0.5) -> HRFlowable:
    c = color or colors.HexColor(HX_N300)
    return HRFlowable(width="100%", thickness=thickness, color=c, spaceAfter=4)


def heading(text: str, level: int = 1):
    """H1 (level=1): heading + rule kept together. H2 (level=2): plain paragraph."""
    if level == 1:
        return KeepTogether([
            Paragraph(text, STYLES["h1"]),
            rule(),
        ])
    return Paragraph(text, STYLES["h2"])


def body(text: str) -> Paragraph:
    """Body paragraph. Supports basic HTML tags: <b>, <i>, <br/>."""
    return Paragraph(text, STYLES["body"])


def bullet_item(text: str) -> Paragraph:
    return Paragraph(f"&#8226;&nbsp; {text}", STYLES["bullet"])


def caption(text: str) -> Paragraph:
    return Paragraph(text, STYLES["caption"])


def chart_image(buf: BytesIO, width_mm: float = 140, height_mm: float = 72) -> Table:
    """Wrap a Plotly PNG BytesIO buffer in a centred Table flowable."""
    buf.seek(0)
    img = Image(buf, width=width_mm * mm, height=height_mm * mm)
    t = Table([[img]])
    t.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def callout_box(title: str, body_text: str,
                bg=None, border=None) -> Table:
    """Info/callout box with coloured left border.

    Defaults to blue-50 background with blue accent border.
    Use RL_GREEN_BG/RL_GREEN_TEXT for positive callouts,
    RL_AMBER_BG/RL_AMBER for warnings.
    """
    bg     = bg     or RL_BLUE_LIGHT
    border = border or RL_BLUE

    title_para = Paragraph(title, STYLES["callout_bold"])
    body_para  = Paragraph(body_text, STYLES["callout"])
    inner = Table([[title_para], [body_para]], colWidths=["100%"])
    inner.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    outer = Table([[inner]], colWidths=["100%"])
    outer.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("LINEBEFORE",    (0, 0), (0, -1),  3, border),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return outer


def simple_table(headers: list[str], rows: list[list], col_widths_mm: list[float] = None) -> Table:
    """Generic branded table: dark header row, alternating body rows.

    Args:
        headers: Column header strings.
        rows: List of rows; each row is a list of strings or Paragraphs.
        col_widths_mm: Optional column widths in mm. Omit to let ReportLab auto-size.
    """
    S = STYLES
    header_row = [Paragraph(h, S["table_header"]) for h in headers]
    body_rows = []
    for row in rows:
        body_rows.append([
            Paragraph(str(cell), S["table_cell"]) if isinstance(cell, (str, int, float)) else cell
            for cell in row
        ])

    data = [header_row] + body_rows
    col_w = [w * mm for w in col_widths_mm] if col_widths_mm else None
    t = Table(data, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  RL_DARK),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),  RL_WHITE),
        ("ALIGN",         (0, 0),  (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
        ("GRID",          (0, 0),  (-1, -1), 0.4, RL_GRAY_MID),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -1), [RL_WHITE, RL_GRAY_LIGHT]),
        ("TOPPADDING",    (0, 0),  (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 5),
        ("LEFTPADDING",   (0, 0),  (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0),  (-1, -1), 7),
    ]))
    return t
