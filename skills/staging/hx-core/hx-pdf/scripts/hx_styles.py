"""hx brand colours and ReportLab paragraph styles.

Copy this file into your report/ directory alongside hx_fonts.py and hx_layout.py.
Call hx_fonts.register() before constructing any document.
"""

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle

# ---------------------------------------------------------------------------
# hx brand colour palette (from hx brand guidelines 2026)
# ---------------------------------------------------------------------------
# Neutrals
HX_WHITE      = "#FFFFFF"
HX_N100       = "#F5F5F5"
HX_N200       = "#F0F0F0"
HX_N300       = "#E0E0E0"
HX_N400       = "#C6C7C8"
HX_N600       = "#848D9A"
HX_DARK       = "#111827"   # primary text
HX_DARK_COVER = "#0F172A"   # cover page background (deep navy-slate)

# Blue accent group — primary accent for most reports
HX_BLUE       = "#2563EB"
HX_BLUE_LIGHT = "#EFF6FF"   # callout backgrounds
HX_BLUE_MID   = "#DBEAFE"   # table header tint

# ReportLab colour objects
RL_WHITE      = colors.HexColor(HX_WHITE)
RL_N100       = colors.HexColor(HX_N100)
RL_N200       = colors.HexColor(HX_N200)
RL_N300       = colors.HexColor(HX_N300)
RL_N400       = colors.HexColor(HX_N400)
RL_N600       = colors.HexColor(HX_N600)
RL_DARK       = colors.HexColor(HX_DARK)
RL_DARK_COVER = colors.HexColor(HX_DARK_COVER)
RL_BLUE       = colors.HexColor(HX_BLUE)
RL_BLUE_LIGHT = colors.HexColor(HX_BLUE_LIGHT)
RL_BLUE_MID   = colors.HexColor(HX_BLUE_MID)

# Aliases used in layout helpers
RL_GRAY_LIGHT = RL_N100
RL_GRAY_MID   = RL_N300
RL_GRAY_DARK  = RL_N600

# Semantic status colours — useful for table cells, callouts
RL_GREEN_TEXT = colors.HexColor("#065F46")
RL_GREEN_BG   = colors.HexColor("#ECFDF5")
RL_RED_TEXT   = colors.HexColor("#991B1B")
RL_RED_BG     = colors.HexColor("#FEF2F2")
RL_AMBER      = colors.HexColor("#D97706")
RL_AMBER_BG   = colors.HexColor("#FFFBEB")

# ---------------------------------------------------------------------------
# Font name constants — Acid Grotesk (primary hx brand typeface)
# ---------------------------------------------------------------------------
F_BOOK    = "AcidGrotesk-Book"
F_BOLD    = "AcidGrotesk-Bold"
F_MEDIUM  = "AcidGrotesk-Medium"
F_LIGHT   = "AcidGrotesk-Light"
F_ITALIC  = "AcidGrotesk-BookItalic"

# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------
STYLES = {
    # --- Cover page (white/muted text on dark background) ---
    "cover_eyebrow": ParagraphStyle(
        "cover_eyebrow",
        fontName=F_BOOK, fontSize=11, leading=16,
        textColor=RL_N400, alignment=TA_LEFT, spaceAfter=4,
    ),
    "cover_title": ParagraphStyle(
        "cover_title",
        fontName=F_LIGHT, fontSize=36, leading=42,
        textColor=RL_WHITE, alignment=TA_LEFT, spaceAfter=4,
    ),
    "cover_subtitle": ParagraphStyle(
        "cover_subtitle",
        fontName=F_BOOK, fontSize=15, leading=22,
        textColor=RL_N400, alignment=TA_LEFT, spaceAfter=4,
    ),
    "cover_date": ParagraphStyle(
        "cover_date",
        fontName=F_BOOK, fontSize=11, leading=16,
        textColor=RL_N600, alignment=TA_LEFT,
    ),
    "cover_body": ParagraphStyle(
        "cover_body",
        fontName=F_BOOK, fontSize=10, leading=15,
        textColor=RL_N400, alignment=TA_LEFT, spaceAfter=6,
    ),

    # --- Body page headings ---
    "h1": ParagraphStyle(
        "h1",
        fontName=F_BOOK, fontSize=20, leading=26,
        textColor=RL_DARK, spaceBefore=0, spaceAfter=4,
    ),
    "h2": ParagraphStyle(
        "h2",
        fontName=F_MEDIUM, fontSize=12, leading=17,
        textColor=RL_DARK, spaceBefore=10, spaceAfter=3,
    ),

    # --- Body text ---
    "body": ParagraphStyle(
        "body",
        fontName=F_BOOK, fontSize=10, leading=15,
        textColor=RL_DARK, alignment=TA_LEFT, spaceAfter=6,
    ),
    "body_left": ParagraphStyle(
        "body_left",
        fontName=F_BOOK, fontSize=10, leading=15,
        textColor=RL_DARK, alignment=TA_LEFT, spaceAfter=4,
    ),
    "bullet": ParagraphStyle(
        "bullet",
        fontName=F_BOOK, fontSize=10, leading=15,
        textColor=RL_DARK, leftIndent=14, spaceAfter=4,
    ),
    "caption": ParagraphStyle(
        "caption",
        fontName=F_ITALIC, fontSize=8.5, leading=13,
        textColor=RL_N600, alignment=TA_CENTER, spaceAfter=10, spaceBefore=2,
    ),

    # --- Callout boxes ---
    "callout": ParagraphStyle(
        "callout",
        fontName=F_BOOK, fontSize=9.5, leading=14,
        textColor=RL_DARK, alignment=TA_LEFT,
    ),
    "callout_bold": ParagraphStyle(
        "callout_bold",
        fontName=F_BOLD, fontSize=9.5, leading=14,
        textColor=RL_DARK, alignment=TA_LEFT, spaceAfter=2,
    ),

    # --- Tables ---
    "table_header": ParagraphStyle(
        "table_header",
        fontName=F_MEDIUM, fontSize=9, leading=12,
        textColor=RL_WHITE, alignment=TA_CENTER,
    ),
    "table_cell": ParagraphStyle(
        "table_cell",
        fontName=F_BOOK, fontSize=9, leading=12,
        textColor=RL_DARK, alignment=TA_CENTER,
    ),
    "table_cell_left": ParagraphStyle(
        "table_cell_left",
        fontName=F_BOOK, fontSize=9, leading=12,
        textColor=RL_DARK, alignment=TA_LEFT,
    ),
    "table_num": ParagraphStyle(
        "table_num",
        fontName="Courier",   # JetBrains Mono fallback — closest available without install
        fontSize=8.5, leading=12,
        textColor=RL_DARK, alignment=TA_CENTER,
    ),
    "table_muted": ParagraphStyle(
        "table_muted",
        fontName=F_ITALIC, fontSize=8.5, leading=11,
        textColor=RL_N600, alignment=TA_CENTER,
    ),

    # --- Page chrome ---
    "footer": ParagraphStyle(
        "footer",
        fontName=F_BOOK, fontSize=8, leading=10,
        textColor=RL_N600, alignment=TA_CENTER,
    ),
}

# ---------------------------------------------------------------------------
# Plotly chart font stack
# ---------------------------------------------------------------------------
CHART_FONT = "Acid Grotesk, Inter, Helvetica Neue, sans-serif"
