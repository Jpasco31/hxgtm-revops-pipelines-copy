"""Register hx brand fonts (Acid Grotesk) with ReportLab.

Copy this file and the fonts_ttf/ folder into your report directory.
Call register() once before building any document.

Font files live in fonts_ttf/ relative to this script file.
"""

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONT_DIR = Path(__file__).parent / "fonts_ttf"

_FONTS = [
    ("AcidGrotesk-Book",       "AcidGrotesk-Book.ttf"),
    ("AcidGrotesk-BookItalic", "AcidGrotesk-BookItalic.ttf"),
    ("AcidGrotesk-Bold",       "AcidGrotesk-Bold.ttf"),
    ("AcidGrotesk-Medium",     "AcidGrotesk-Medium.ttf"),
    ("AcidGrotesk-Light",      "AcidGrotesk-Light.ttf"),
]


def register():
    """Register Acid Grotesk weights with ReportLab. Safe to call multiple times."""
    for name, filename in _FONTS:
        path = _FONT_DIR / filename
        if path.exists():
            pdfmetrics.registerFont(TTFont(name, str(path)))

    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily(
        "AcidGrotesk",
        normal="AcidGrotesk-Book",
        bold="AcidGrotesk-Bold",
        italic="AcidGrotesk-BookItalic",
        boldItalic="AcidGrotesk-Bold",
    )
