---
name: estimate-model
description: Analyze Excel rating models for migration complexity and effort estimation. Use when triaging new models, estimating project sizing, or generating triage reports for client Excel files.
argument-hint: [path-to-excel-file-or-directory]
allowed-tools: Bash(python *) Read Write Glob Grep
---

# Model Estimation Skill

Analyze Excel rating models at `$ARGUMENTS` to produce triage reports, a comparative analysis, and a summary estimate workbook.

## Step 1: Run Analysis

First, ensure the required Python packages are installed (openpyxl, oletools). Then run the analysis engine:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/run_triage.py" "$ARGUMENTS"
```

This produces `analysis/analysis-data.json` next to the input file(s). If the input is a single file, `analysis/` is created in the same directory. If the input is a directory, `analysis/` is created inside it.

## Step 2: Read Analysis Data

Read the `analysis-data.json` file. It contains an array of objects, each with:
- `filename`: The Excel file name
- `data`: Structured analysis results including sizing, formulas, dependencies, VBA, and more

## Step 3: Write Triage Reports

For each model in the analysis data, write a markdown file to the `analysis/` directory named `{model_stem} - Triage Report.md`.

### Report Structure

Each report must include these sections:

- **Executive Summary**: T-shirt size, key characteristics, one-paragraph overview
- **File Information**: Size, sheet count, formula count, input count
- **Worksheet Structure**: Notable sheets, hidden sheets, sheet-level complexity distribution
- **Complexity Indicators**: Formula count, dependency depth, named ranges, array formulas
- **Modern Functions** (if detected): Which Excel 365 functions are used, compatibility implications
- **Dependency Analysis**: Chain depth, cross-sheet references, circular references if any
- **Risk Indicators**: Volatile functions, error cells, circular references, hard-coded values
- **VBA Analysis** (if present): Complexity, patterns detected, external integrations
- **Sizing Breakdown**: Score, contributing factors, confidence level with reasoning
- **Migration Considerations**: Specific areas of difficulty, recommended approach, things to watch for during detailed review

### Report Quality Guidelines

- Write for experienced practitioners who understand Excel complexity, VBA, and model architecture
- Go beyond template reporting — identify patterns, flag unusual characteristics, provide insights
- Be specific: reference actual numbers from the data ("47,231 formulas across 23 sheets" not "many formulas")
- Only use data provided — do not invent sheet names, formula details, or metrics not in the analysis
- Do not re-evaluate sizing — the scores and sizes are deterministic, use them as-is
- Do not use emojis

## Step 4: Write Comparative Analysis

If there are multiple models, write `analysis/Comparative Analysis.md` with:

- **Portfolio Overview**: Summary table of all models with size, score, key flags
- **Cross-Model Patterns**: Common characteristics, outliers, shared risk factors
- **Suggested Triage Priority**: Which models to review first and why
- **Resource Planning**: High-level guidance on team composition and sequencing
- **Overall Assessment**: One-paragraph summary of the project's complexity profile

For a single model, skip this step.

## Step 5: Write sizing.json

Write `analysis/sizing.json` with the following structure. Extract `size`, `score`, and `confidence` directly from the analysis data (they are already computed). Add your own `summary` (one sentence) and `flags` (array of notable characteristics like "Actuarial model", "ODBC integrations", "Modern Excel functions", "VBA password protected").

```json
{
  "project_name": "<parent directory name>",
  "models": [
    {
      "file_name": "<exact filename>",
      "size": "SMALL|MEDIUM|LARGE|EXTRA_LARGE",
      "score": 0.0,
      "confidence": "HIGH|MEDIUM|LOW",
      "formula_count": 0,
      "sheet_count": 0,
      "max_dependency_depth": 0,
      "has_vba": false,
      "vba_lines": 0,
      "has_integrations": false,
      "integration_count": 0,
      "is_actuarial": false,
      "has_modern_functions": false,
      "file_size_mb": 0.0,
      "summary": "<one-sentence description>",
      "flags": ["<notable characteristic>"]
    }
  ],
  "total_formulas": 0,
  "average_score": 0.0,
  "size_distribution": {
    "SMALL": 0,
    "MEDIUM": 0,
    "LARGE": 0,
    "EXTRA_LARGE": 0
  }
}
```

### Field Mapping from Analysis Data

For each model in the analysis data, map fields as follows:

| sizing.json field | Source in analysis data |
|---|---|
| `file_name` | `filename` (top-level) |
| `size` | `data.sizing.size` |
| `score` | `data.sizing.score` |
| `confidence` | `data.sizing.confidence.level` |
| `formula_count` | `data.size.formulaCells` |
| `sheet_count` | `data.size.sheetCount` |
| `max_dependency_depth` | `data.dependencies.maxDepth` |
| `has_vba` | `data.vba.hasVBA` |
| `vba_lines` | `data.vba.totalLines` |
| `has_integrations` | `data.vba.externalIntegrations.detected` (default false) |
| `integration_count` | `data.vba.externalIntegrations.totalCount` (default 0) |
| `is_actuarial` | `data.modelType.flagged` (default false) |
| `has_modern_functions` | `data.modernFunctions.detected` (default false) |
| `file_size_mb` | `data.metadata.fileSizeMB` |

For aggregate fields:
- `total_formulas`: sum of all models' `formula_count`
- `average_score`: mean of all models' `score`
- `size_distribution`: count of models per size category

## Step 6: Generate Workbook

Run the workbook generator on the analysis directory:

```bash
python -c "
import sys; sys.path.insert(0, '${CLAUDE_SKILL_DIR}/scripts')
from generate_workbook import generate_workbook
from pathlib import Path
import json
output_dir = Path('$ARGUMENTS').resolve()
if output_dir.is_file():
    output_dir = output_dir.parent / 'analysis'
else:
    output_dir = output_dir / 'analysis'
sizing = json.loads((output_dir / 'sizing.json').read_text())
path = generate_workbook(sizing, output_dir)
print(f'Workbook: {path}')
"
```

## Step 7: Summarise

Tell the user what was produced and where the files are located. List each output file with its purpose.

## Sizing Framework Reference

These thresholds are used by the deterministic sizing engine:

- **SMALL** (score < 1.5): Straightforward model, limited complexity
- **MEDIUM** (score 1.5-2.49): Moderate complexity, some areas requiring attention
- **LARGE** (score 2.5-2.74): Significant complexity, multiple risk factors
- **EXTRA_LARGE** (score >= 2.75): Highly complex, requires senior expertise and extended timeline
