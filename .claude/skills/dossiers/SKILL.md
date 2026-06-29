---
name: dossiers
description: >
  TEST-ONLY placeholder skill used to exercise the PR-capture dedup guard. Not for
  production use — for real account research and dossier generation use the
  generate-dossier skill instead. Intentionally minimal — no scripts, no external
  services.
---

# Dossiers (test-only stub)

## What this skill does

Nothing of substance. This is a deliberately minimal placeholder skill created to
test the GTM-OS PR-capture **dedup/naming guard**: when a merged PR's `## Brain`
block names `project: dossiers`, the guard should near-match the existing
`account_dossiers` project and route the entry there instead of creating a twin.

## When NOT to use

- Real account research, dossier generation, or batch dossier runs → use
  `generate-dossier`.
- Capturing human feedback on dossiers → use `dossier-feedback`.

## Out of scope / guardrails

- No web research, no Notion publishing, no file generation.
- No scripts and no subdirectories — a single SKILL.md by design.
- Safe to delete once the dedup-guard test has been verified.
