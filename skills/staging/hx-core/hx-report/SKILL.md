---
name: hx-pdf
description: >
  Generate professional hx-branded PDF reports using ReportLab and Plotly. Use this skill
  whenever the user wants to build, generate, or produce a PDF report, one-pager, or
  findings document using the hyperexponential brand. Trigger when the user says things like "generate a PDF" or "write up our findings
  as a PDF". The skill bundles the complete hx brand system (Acid Grotesk fonts, brand
  colours, layout helpers, chart styling) as reusable Python modules so every report starts
  from the same professional baseline.
---

# hx Report Builder

This skill generates professional A4 PDF reports in the hx brand using ReportLab (layout) and
Plotly (charts). It bundles three reusable Python modules plus the Acid Grotesk font files.

## What gets bundled

Read these files from the skill before starting work — they contain the complete reusable foundation:

- `scripts/hx_styles.py` — Brand colours, font name constants, all paragraph styles
- `scripts/hx_fonts.py` — Acid Grotesk font registration for ReportLab
- `scripts/hx_layout.py` — Generic flowable helpers (spacer, rule, heading, body, bullet, callout, chart, table)
- `assets/fonts_ttf/` — The five Acid Grotesk TTF font files (Book, Bold, Medium, Light, BookItalic)

See `references/reportlab-patterns.md` for copy-pasteable code patterns, dependencies, and common gotchas.

## Workflow for a new report

### 1. Understand what the user needs

Ask or infer:
- **What is this report about?** (The content drives which sections and charts to build)
- **Where should the PDF land?** (Output path)
- **What data is being visualised?** (Hardcoded values? CSV? Python dict?)
- **How many pages / sections?** (Use judgement — concise is better)
- **Header and footer text?** (`"hyperexponential  ·  Report Title"` / `"Confidential — prepared for X"`)

### 2. Set up the project files

In the report directory (or a `report/` subdirectory of the project):

1. Copy `scripts/hx_styles.py`, `scripts/hx_fonts.py`, `scripts/hx_layout.py` into the directory
2. Copy `assets/fonts_ttf/` folder into the directory (so fonts sit at `fonts_ttf/` next to `hx_fonts.py`)
3. Initialise a Poetry project and add the required dependencies
4. Create the report-specific files: `data.py`, `charts.py`, `generate_report.py`

The source paths for the skill files are:
- `~/.claude/skills/hx-report/scripts/hx_styles.py`
- `~/.claude/skills/hx-report/scripts/hx_fonts.py`
- `~/.claude/skills/hx-report/scripts/hx_layout.py`
- `~/.claude/skills/hx-report/assets/fonts_ttf/` (copy the whole directory)

Use bash to copy: `cp ~/.claude/skills/hx-report/scripts/hx_*.py <target>/ && cp -r ~/.claude/skills/hx-report/assets/fonts_ttf <target>/`

**Poetry setup** — run these in the report directory:

```bash
# Initialise (if no pyproject.toml exists yet)
poetry init --name "my-report" --python ">=3.11,<4" --no-interaction

# Add dependencies (use poetry add — not pip — to get latest resolved versions)
poetry add reportlab plotly kaleido

# Run the report generator
poetry run python generate_report.py
```

If `poetry init` fails because a `pyproject.toml` already exists, just run `poetry add` directly. Note: `requires-python` must be `">=3.11,<4"` (not open-ended) to satisfy reportlab's Python upper bound.

### 3. Write data.py

Put all report data here — hardcoded dicts, lists, or loaded from files. Keep it separate from
presentation logic so charts and tables can import from a single source of truth.

### 4. Write charts.py

Each chart is a function returning a `BytesIO` PNG buffer. Use Plotly with `hx_styles.CHART_FONT`
and brand colours. Render at 2× scale for crispness: `fig.to_image(format="png", width=800, height=400, scale=2)`.

See `references/reportlab-patterns.md` for the full Plotly chart template including axis styling,
legend placement, and brand colour usage.

### 5. Write generate_report.py

This is the main script. Structure:

```python
import hx_fonts, hx_layout
from hx_styles import STYLES
hx_fonts.register()   # must be first

def build_story():
    story = []

    # Cover page
    story += [ ... cover flowables ... PageBreak() ]

    # Body pages — one PageBreak() per page
    story += [ hx_layout.heading("Section"), hx_layout.body("..."), ... PageBreak() ]

    return story

def main():
    # Set up BaseDocTemplate with A4, margins, frame, on_page callback
    # Build story and call doc.build(story)
    ...
```

See `references/reportlab-patterns.md` for the complete `main()` boilerplate.

## Cover page design

The cover uses a full-page deep navy background (`#0F172A`) drawn by the page callback, with a
thin blue accent line at 68mm from the bottom. Content flows over the top using white/muted
palette styles (`cover_eyebrow`, `cover_title`, `cover_subtitle`, `cover_date`, `cover_body`).

The canonical structure:
1. `Spacer(1, 52mm)` — push content down from top
2. `Paragraph("hyperexponential", cover_eyebrow)` — brand eyebrow
3. `Paragraph(report_title, cover_title)` — main title (Light weight, 36pt)
4. `Paragraph(subtitle, cover_subtitle)` — subtitle
5. `Spacer + Paragraph(date_client, cover_date)` — date and client
6. `Spacer(1, ~40mm)` — gap to description
7. `Paragraph(abstract, cover_body)` — one-paragraph summary
8. `PageBreak()`

## Key layout helpers

| Helper | Purpose |
|--------|---------|
| `heading(text, level=1)` | H1 (with rule, kept together) or H2 |
| `body(text)` | Body paragraph, supports `<b>`, `<i>`, `<br/>` |
| `bullet_item(text)` | Bulleted list item |
| `caption(text)` | Italic centred caption below a chart |
| `chart_image(buf, width_mm, height_mm)` | Embeds a Plotly PNG BytesIO, centred |
| `callout_box(title, body_text, bg, border)` | Info box with coloured left border |
| `simple_table(headers, rows, col_widths_mm)` | Generic branded table |
| `spacer(h_mm)` | Vertical gap |
| `rule()` | Horizontal divider |

## Brand colour quick reference

| Token | Hex | Use |
|-------|-----|-----|
| `HX_DARK` | `#111827` | Primary text, table headers |
| `HX_DARK_COVER` | `#0F172A` | Cover background |
| `HX_BLUE` | `#2563EB` | Accent, callout borders, links |
| `HX_BLUE_LIGHT` | `#EFF6FF` | Callout backgrounds |
| `HX_N300` | `#E0E0E0` | Rules, grid lines |
| `HX_N600` | `#848D9A` | Secondary text, captions |
| `RL_GREEN_BG/TEXT` | `#ECFDF5 / #065F46` | Positive highlights in tables |
| `RL_RED_BG/TEXT` | `#FEF2F2 / #991B1B` | Negative highlights |
| `RL_AMBER_BG/AMBER` | `#FFFBEB / #D97706` | Warning callouts |

## Dependencies

Always use **Poetry** to manage dependencies — not pip directly.

```bash
poetry add reportlab plotly kaleido
poetry run python generate_report.py
```

The `pyproject.toml` must pin `requires-python = ">=3.11,<4"` to satisfy reportlab's upper Python bound. Poetry will resolve to the latest compatible versions automatically.

## Notes on quality

- Render charts at `scale=2` (effectively 2× resolution) for crisp PDF output
- Use `KeepTogether([heading, first_para])` to prevent section headings orphaning at page bottoms
- The `simple_table` helper handles most cases; for coloured cells or spans, build the `TableStyle` manually — see `references/reportlab-patterns.md`
- Always run via `poetry run python generate_report.py` — not bare `python`
