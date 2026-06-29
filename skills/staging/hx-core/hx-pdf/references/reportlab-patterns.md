# ReportLab & Plotly Quick Reference for hx Reports

## Document boilerplate

```python
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer

import hx_fonts, hx_layout
from hx_styles import STYLES

hx_fonts.register()   # Must come first

OUTPUT = Path(__file__).parent / "my_report.pdf"

LEFT_MARGIN = RIGHT_MARGIN = 20 * mm
TOP_MARGIN = 22 * mm
BOTTOM_MARGIN = 18 * mm

def main():
    doc = BaseDocTemplate(
        str(OUTPUT), pagesize=A4,
        leftMargin=LEFT_MARGIN, rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,   bottomMargin=BOTTOM_MARGIN,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    on_page = hx_layout.make_on_page_fn(
        header="hyperexponential  ·  My Report Title",
        footer="Confidential — prepared for Client Name",
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
    doc.build(build_story())
```

## Cover page pattern

```python
story += [
    Spacer(1, 52 * mm),
    Paragraph("hyperexponential", STYLES["cover_eyebrow"]),
    Spacer(1, 3 * mm),
    Paragraph("Report Main Title", STYLES["cover_title"]),
    Paragraph("Report Subtitle", STYLES["cover_subtitle"]),
    Spacer(1, 5 * mm),
    Paragraph("Month Year  ·  Prepared for Client", STYLES["cover_date"]),
    Spacer(1, 40 * mm),
    Paragraph("One-paragraph executive abstract for the cover.", STYLES["cover_body"]),
    PageBreak(),
]
```

The dark background and blue accent line are drawn automatically by the cover callback in `hx_layout`.

## Body page pattern

```python
story += [
    hx_layout.heading("Section Title"),          # H1 + rule kept together
    hx_layout.spacer(3),
    hx_layout.body("Body text. Supports <b>bold</b> and <i>italics</i>."),
    hx_layout.heading("Subsection", level=2),    # H2, no rule
    hx_layout.bullet_item("First point"),
    hx_layout.bullet_item("Second point"),
    hx_layout.spacer(4),
    hx_layout.callout_box(
        "Callout title",
        "Callout body text. Use for key findings, caveats, or highlights.",
    ),
    PageBreak(),
]
```

## Charts — Plotly → PNG → PDF

```python
import plotly.graph_objects as go
from io import BytesIO
from hx_styles import CHART_FONT, HX_DARK, HX_N300, HX_N600, HX_BLUE, C_WITHOUT, C_WITH

def chart_my_data(x_values, y_series_a, y_series_b) -> BytesIO:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_values, y=y_series_a,
        name="Series A", mode="lines+markers",
        line=dict(color=C_WITHOUT, width=2),
        marker=dict(size=6, color="white", line=dict(color=C_WITHOUT, width=2)),
    ))
    fig.add_trace(go.Scatter(
        x=x_values, y=y_series_b,
        name="Series B", mode="lines+markers",
        line=dict(color=C_WITH, width=2),
        marker=dict(size=6, color="white", line=dict(color=C_WITH, width=2)),
    ))

    fig.update_layout(
        font=dict(family=CHART_FONT, size=11, color=HX_DARK),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=50, r=20, t=30, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, linecolor=HX_N300, tickfont=dict(color=HX_N600)),
        yaxis=dict(gridcolor=HX_N300, linecolor=HX_N300, tickfont=dict(color=HX_N600)),
        hovermode=False,
    )

    buf = BytesIO()
    buf.write(fig.to_image(format="png", width=800, height=400, scale=2))
    return buf
```

Then embed in the story:
```python
story += [
    hx_layout.chart_image(chart_my_data(x, a, b), width_mm=140, height_mm=72),
    hx_layout.caption("Figure 1: Description of what this chart shows."),
]
```

## Table with custom cell formatting

For simple tables, use `hx_layout.simple_table(headers, rows, col_widths_mm)`.

For tables needing coloured cells (e.g. green for improvements, red for regressions),
build a ReportLab Table manually and use `TableStyle` commands:
```python
from reportlab.platypus import Table, TableStyle
from hx_styles import RL_GREEN_BG, RL_GREEN_TEXT, RL_RED_BG, RL_RED_TEXT, STYLES

def improvement_table(data):
    ...
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), RL_DARK),   # header row
        ...
        ("TEXTCOLOR",  (2, row_idx), (2, row_idx), RL_GREEN_TEXT),
        ("BACKGROUND", (2, row_idx), (2, row_idx), RL_GREEN_BG),
    ]
    t.setStyle(TableStyle(cmds))
    return t
```

## Dependencies — Poetry (preferred)

Always use Poetry. Run once in the report directory:

```bash
poetry add reportlab plotly kaleido
```

This resolves the latest compatible versions. Ensure `pyproject.toml` has `requires-python = ">=3.11,<4"` — reportlab requires a Python upper bound.

Run the report:

```bash
poetry run python generate_report.py
```

## File layout for a new report project

```
my-report/
├── generate_report.py   # main script — run this to produce the PDF
├── charts.py            # Plotly chart functions returning BytesIO
├── data.py              # hardcoded or loaded data
├── hx_styles.py         # copy from skill scripts/
├── hx_fonts.py          # copy from skill scripts/
├── hx_layout.py         # copy from skill scripts/
└── fonts_ttf/           # copy from skill assets/fonts_ttf/
    ├── AcidGrotesk-Book.ttf
    ├── AcidGrotesk-Bold.ttf
    ├── AcidGrotesk-BookItalic.ttf
    ├── AcidGrotesk-Light.ttf
    └── AcidGrotesk-Medium.ttf
```

## Common gotchas

- `hx_fonts.register()` must be called before any `Paragraph` or `ParagraphStyle` that references Acid Grotesk font names — put it at module level in `generate_report.py`.
- `chart_image()` calls `buf.seek(0)` internally — you don't need to seek before passing the buffer.
- `KeepTogether` prevents a heading from splitting from the content below it across page breaks. Use it for heading + first paragraph pairs.
- `repeatRows=1` on Table means the header row repeats if the table flows across pages.
- For full-bleed cover elements (logos, decorative shapes), draw them in the `onPage` callback using the canvas directly — flowables can't escape the frame margins.
