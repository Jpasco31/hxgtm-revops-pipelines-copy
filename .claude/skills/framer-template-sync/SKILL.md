# Framer Template Sync

Audit all format-for-framer CMS reference files against the live Framer schema in one pass. Optionally rewrite cached IDs and enum case names when drift is unambiguous. Use when the cached references have aged, before a bulk publishing run, or when you want to stamp fresh "✅ IDs confirmed" dates across the reference set. Sibling maintenance skill to `format-for-framer` — that skill handles per-publish drift for one page type; this skill audits and optionally corrects the entire cache.

## Slash Command

`/framer-template-sync [--apply]`

- No arguments → audit mode. Produces a drift report at `outputs/framer-template-sync-YYYY-MM-DD.md`.
- `--apply` → audit + rewrite mode. Updates `references/*.md` for unambiguous drift and TBD placeholders, stamps confirmation lines, and still emits the report.

## Prerequisites

- A live Framer Agent CLI session (run `npx @framer/agent@latest setup` and `session new` if needed). The skill reuses the existing session via `-s <id>`; if none exists, it stops and directs the user to the `framer` skill bootstrap.
- Read access to `company-shared/hxgtm/hxgtm-revops-pipelines/.claude/skills/format-for-framer/references/*.md` (10 files today).

The skill never writes to Framer (no `applyChanges`, no `publish`). It is read-only against the live schema and write-only against the local reference cache.

## Workflow — Audit Mode (`/framer-template-sync`)

1. **Session preflight.** Confirm a Framer Agent session exists. If not, stop and point at `npx @framer/agent@latest setup` + `session new`. Reuse the session ID on every CLI call.
2. **One live schema read.** Execute the same preflight script documented in `format-for-framer` Step 1.5:

   ```js
   // /tmp/framer-template-sync-preflight.js
   state.collections = await framer.agent.getNodesOfTypes({ types: ["CollectionNode"] });
   state.preflight = state.collections.map((c) => ({
     id: c.id,
     name: c.name,
     fields: c.variables.map((v) => ({
       id: v.id,
       name: v.name,
       type: v.type,
       key: v.key,
       cases: v.cases ?? null,
     })),
   }));
   console.log(JSON.stringify(state.preflight, null, 2));
   ```

   Run with `npx @framer/agent@latest exec -s <sessionId> -f /tmp/framer-template-sync-preflight.js`. Capture the full live schema once — this is the source of truth for the entire run.
3. **Walk the reference cache.** Glob `references/*.md`. For each file, parse:
   - Primary collection ID (e.g. `RwO5YeFWg` on newsroom).
   - Linked sub-collection IDs (e.g. `vq6ySagx5` for Newsroom Quotes).
   - Field ID / name / type rows.
   - Enum case-name bullets.
   - Any `TBD` placeholders.
4. **Classify drift per reference.** For each collection / field / case in the reference, compare against the live preflight:
   - `OK` — present and unchanged.
   - `UNAMBIGUOUS` — same role / same name, new ID or new case name (auto-fixable).
   - `AMBIGUOUS` — vanished field or case with no clear live equivalent (needs human).
   - `TBD` — literal `TBD` in the reference (e.g. `faqs.md` lines 36-38) — backfill from live.
   - `ORPHAN_REF` — collection ID in reference no longer exists live.
5. **Detect orphan live collections.** Any live `CollectionNode` whose ID is not claimed by any reference — surface for awareness only (no scaffolding in v1).
6. **Emit report.** Write `outputs/framer-template-sync-YYYY-MM-DD.md` with one section per reference file, severity-ranked (Ambiguous → Orphan Ref → TBD → Unambiguous → OK). Cite each finding by reference path + line range. Include a summary table at the top.

## Workflow — Apply Mode (`/framer-template-sync --apply`)

Runs steps 1-5 above, then:

7. **Rewrite reference files in place** for `UNAMBIGUOUS` + `TBD` drift only. Never edit `AMBIGUOUS` or `ORPHAN_REF` findings — those require human review. Use exact string replacement on:
   - Field ID columns in markdown tables.
   - Enum case-name bullets.
   - `TBD` placeholders (replace the entire row or bullet with the live value).
8. **Stamp a confirmation line** on each rewritten file, matching the convention already used in `faqs.md` line 7:

   > `> **✅ IDs confirmed YYYY-MM-DD.** Preflight run against session <id>. <one-line summary of changes>`

   Insert or replace immediately after the opening `>` block that declares the file is a cache.
9. **Leave changes unstaged.** Do not commit. The human reviews `git diff` and commits manually — same contract as `kb-integrate`.
10. **Report still emitted** with an additional "Apply Summary" block listing what was rewritten and what was deferred.

## Drift Classification Rules (lifted from format-for-framer Step 1.5)

- Match on **live `variables[].cases` strings** for enums — preserve cosmetic quirks verbatim (e.g. `irtual Event` vs `Virtual Event`).
- On any `AMBIGUOUS` drift, stop the apply for that reference and surface the finding in the report.
- If the preflight script fails (no session, CLI error), stop — do not edit references against unverified data.
- `multiCollectionReference` fields are validated by ID presence only; do not attempt to resolve natural keys during sync.
- Image / link / file fields with `TBD` URLs are treated as `TBD` and backfilled only if a live field of the same name exists — otherwise they remain `TBD` and are reported.

## Guardrails

- **Read-only against Framer.** Never call `framer.agent.applyChanges`, `framer.agent.publish`, or any write method. The skill's only write surface is the local reference `.md` files.
- **Never invent field IDs or case names.** Every substitution must come from the live preflight output.
- **Never touch ambiguous drift.** If a field or case vanished with no clear live equivalent, leave the reference as-is and surface the finding for human resolution.
- **No automatic invocation.** This skill is manual-only. `format-for-framer` continues to handle per-publish drift for the page type being published right now.
- **No Notion publishing.** Findings stay in `outputs/`. Unlike `kb-update`, this skill does not create Notion rows.

## Output — Audit Report

See `references/output-format.md` for the exact structure. The report is a single markdown file with:
- Header with run metadata (date, session ID, counts).
- Summary table (per reference: OK / Unambiguous / TBD / Ambiguous / Orphan Ref).
- One section per reference file, each containing a findings table.
- Footer with "Next steps" guidance (run with `--apply` for unambiguous fixes, or review ambiguous findings manually).

## Relationship to format-for-framer

`format-for-framer` Step 1.5 already runs the live preflight and reconciles drift for the single page type being published. It emits a `Schema drift:` block in the publish bundle and prefers live values for unambiguous cases — but it **never writes back** to the cached reference. This skill is the missing "opportunistic update" pass that keeps the entire cache fresh between publishes. Run it periodically or before a bulk publishing wave; continue using `format-for-framer` for the inner per-publish loop.

## Non-Goals (v1)

- No scaffolding of new reference files for live collections that have no reference yet (orphan live collections are reported only).
- No integration with Cursor Automations or scheduled runs.
- No cross-repo sync for mirrored references (e.g. the `framer-format` skill in `.cursor/skills/`).
