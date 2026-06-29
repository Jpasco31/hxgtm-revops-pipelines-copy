---
name: model-code-review
description: Review hx platform model code (Python and JavaScript files) for complexity, efficiency, and anti-patterns. This skill should be used when someone wants to analyse a model's codebase for code quality issues, performance concerns, or deviations from best practices in hx platform modelling.
argument-hint: "[path to model file or folder]"
user-invocable: true
---

# Model Code Review

Analyse hx platform model files (Python and JavaScript) to assess code complexity, identify inefficiencies, and flag anti-patterns. Produce an actionable summary that highlights areas for improvement.

## Step 1: Locate and Read Model Files

Accept a path to a single file or a directory. If a directory is provided, recursively find all `.py` and `.js` files within it.

Read each file into context. If the total file count exceeds 30 or the combined size is very large, prioritise files that appear to contain core model logic (e.g. files with calculation functions, rating engines, or transformation pipelines) and note any files that were skipped.

If platform documentation exists in `references/`, load it to inform the review:

```
${CLAUDE_SKILL_DIR}/references/
```

## Step 2: Analyse Complexity

For each file, assess:

- **Cyclomatic complexity** — deeply nested conditionals, long chains of if/elif/else, complex boolean expressions
- **Function length** — functions exceeding ~50 lines that could be decomposed
- **File length** — files exceeding ~500 lines that may benefit from modularisation
- **Parameter counts** — functions accepting many parameters, suggesting missing abstractions
- **Variable scope** — overuse of global state or excessively broad variable scoping

## Step 3: Identify Inefficiencies

Look for code patterns that are likely to cause performance or maintainability problems in a model context:

- **Redundant computation** — the same calculation performed multiple times when it could be cached or extracted
- **Unnecessary loops** — iterating over data sets when vectorised operations or lookups would suffice
- **Copy-paste duplication** — repeated blocks of near-identical logic that should be refactored into shared functions
- **Hardcoded values** — magic numbers or string literals embedded in logic rather than defined as named constants or configuration
- **Inefficient data structures** — using lists for frequent lookups instead of dictionaries/sets, or rebuilding structures unnecessarily
- **Unused code** — dead imports, unreachable branches, or commented-out blocks left in the codebase

## Step 4: Flag Anti-Patterns

Identify patterns that are specifically problematic in hx platform model code:

- **Overly complex single-expression calculations** — long formulas crammed into one line that are difficult to audit or debug
- **Poor separation of concerns** — mixing data loading, transformation, and calculation logic in the same function
- **Lack of intermediate variables** — chaining many operations without naming intermediate results, making the logic opaque
- **Inconsistent naming** — variable names that do not clearly convey what they represent, especially in actuarial or financial calculations
- **Missing or misleading comments** — complex business logic with no explanation, or comments that contradict the code
- **Brittle assumptions** — code that assumes specific data shapes, column orders, or input ranges without validation

## Step 5: Produce the Review Summary

Structure the output as follows:

### Overview

A 2-3 sentence high-level assessment of the model's code quality, noting whether it is broadly well-structured or has systemic issues.

### File-by-File Findings

For each file reviewed (or grouped by logical module if there are many files), list:

- **File**: path and brief description of what the file does
- **Complexity**: Low / Medium / High — with specific evidence
- **Key issues**: Bulleted list of the most impactful findings, each with:
  - What the issue is
  - Where it occurs (line numbers or function names)
  - Why it matters (impact on performance, readability, or correctness)
  - A suggested improvement

### Priority Recommendations

A ranked list of the top 3-5 changes that would most improve the model's code quality. Focus on changes with the highest impact-to-effort ratio.

### Metrics Summary

A table summarising key metrics across the model:

| Metric | Value |
|---|---|
| Total files reviewed | |
| Total lines of code | |
| Files with high complexity | |
| Duplicated code blocks found | |
| Hardcoded values found | |
| Unused imports/code found | |

## Step 6: Offer Follow-ups

After delivering the review, offer relevant next steps:

- "Want me to refactor a specific file or function based on these findings?"
- "Should I generate a detailed breakdown for any particular area?"
- "Want me to check this model against a different version to see what changed?"
