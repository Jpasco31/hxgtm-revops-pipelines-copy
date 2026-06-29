# kb-update — Load inputs (narrowing + canon discovery)

## Contents
- When this reference is loaded
- Step 3a — Read raw and infer source tier (already in SKILL.md)
- Step 3b — Canon discovery (outputs entity tuples)
- Filename-prefix narrowing (preferred — competitive default)
- Filename-entity narrowing (legacy — opt-in)
- Canon aliases (per-group `canon_aliases`)
- Summary-file slice (replaces old always_include fan-out)
- Foundational canon (per-group `foundational_canon`)
- Zero-match fallback
- Trimmed summary-file input (Change 7)
- Empty canon scope

## When this reference is loaded

SKILL.md Step 3 keeps the tier-inference table inline (used every
run). Read this reference when you need the full narrowing algorithm,
alias fallback behaviour, or the trimmed-input logic for summary files
listed under `always_include`.

## Step 3a — Read raw and infer source tier (already in SKILL.md)

Summarised here for context; the full flow lives in SKILL.md Step 3a
and is not duplicated. Key output fields bound into the orchestrator's
state:

- `raw_file_metadata` — filename + any frontmatter fields
- `raw_file_content` — full body (read via `Read`; truncated to first
  2000 words + section headings if over 2000 words)
- `source_tier` — one of tier_1 / tier_2 / tier_3 / tier_4 / tier_5
  (tier_4 is restricted to `Notes / open questions` and must clear the
  comparator-level significance gate; approval in Notion is the
  explicit-approval gate before canon integration)
- `confidentiality` — `internal-only` (default) or `shareable`

## Step 3b — Canon discovery

Discover every canon file in the group's scope and group them into
**entity tuples** — the orchestrator fans out one subagent per entity
tuple in Step 4 (not per file). Each tuple is:

```
{
  entity_name: "<Title-cased canon filename stem>",   // e.g. "Federato"
  canon_file_paths: [                                 // 1–N writable paths
    "<absolute path to the per-entity profile>",
    "<optional absolute path to a summary-file slice>",
    "<zero or more foundational_canon paths (whole-file, unsliced)>"
  ]
}
```

Three classes of canon paths can land on a tuple. Each has its own
attachment rule and its own comparator routing policy:

1. **Narrowed-entity-match** — the per-entity profile produced by the
   `scoping_strategy` below (filename_prefix / filename_entity /
   unset). Always present.
2. **Summary-file slice** — per-entity slice of a `always_include`
   summary file. See [Summary-file slice](#summary-file-slice).
3. **Foundational canon** — whole-file attachments that apply to
   every entity tuple regardless of narrowing. See
   [Foundational canon](#foundational-canon-per-group-foundational_canon).

Use `Glob` against each entry in `groups.<slug>.canon` under
`<mcp_root>/context/`. `mcp_root` was resolved in Step 2a and is the
single source of truth — do NOT hardcode `../hxgtm-mcp-server/` here.
Canon always lives on the local filesystem (kb-integrate writes
there); there is no MCP-mode fallback.

Collect the resulting list as `group_canon_files` (paths only at this
point — we defer reading bodies until after narrowing).

## Filename-prefix narrowing (preferred — competitive group default)

Applies when `groups.<slug>.scoping_strategy == "filename_prefix"`.
This is the default for the `competitive` group as of 2026-04. Other
groups can opt in by setting the key.

The raw filename is the authoritative signal. Content analysis of the
raw body is NOT performed — routing is determined entirely by the
filename, which keeps fan-out predictable and avoids firing a subagent
per mentioned competitor in a multi-entity file.

Algorithm (pure Python, no LLM call):

1. Strip directories from the raw filename → `<basename>.md`.
2. Split the basename on the first `-` or `_` →
   `competitor_stem = re.split(r'[-_]', basename, maxsplit=1)[0].lower()`.
3. Enumerate canon file stems from `groups.<slug>.canon` globs
   (filename with `.md` stripped, lowercased).
4. **Exact match** on `competitor_stem` → produce ONE entity tuple:
   `{entity_name: <Title-cased stem>, canon_file_paths:
   [<matched_canon_file>, <summary_slice_if_any>,
   <foundational_canon_paths>]}`. See
   [Summary-file slice](#summary-file-slice) for how the summary slice
   is attached and
   [Foundational canon](#foundational-canon-per-group-foundational_canon)
   for the whole-file attachments. Log:

   ```
   [scope_narrowing] strategy=filename_prefix matched=<stem> (1 entity)
     summary_slice=<path or none> duration_ms=<ms>
   ```

5. **No match** → halt with the rename banner (do NOT fall through to
   load-all; it's better to make the author rename than silently fan
   out against every canon file):

   ```
   Filename prefix '<competitor_stem>' (from '<filename>') does not
   match any canon file stem in group '<slug>'. Rename to
   '<competitor>-<description>.md' where <competitor> matches a canon
   filename (see the group's canon globs). To process a multi-entity
   scan without splitting, temporarily flip scoping_strategy to
   filename_entity in .claude/skills/kb-update/config.yaml.
   ```

Aliases in `canon_aliases` are consulted the same way as in
`filename_entity`: if `competitor_stem` matches any alias string for a
canon file, the canon file counts as a match.

## Filename-entity narrowing (legacy — opt-in)

Applies when `groups.<slug>.scoping_strategy == "filename_entity"`.
Kept for multi-entity scans (Teams roundups, market-insights dumps)
where splitting into one file per competitor would be wasteful.
Content-scans the raw body for every canon stem.

Algorithm (pure Python / regex — no extra LLM call):

1. For each file in `group_canon_files`, compute `stem` = filename
   with `.md` removed (`akur8.md` → `akur8`).
2. For each `stem`, run
   `re.search(rf"\b{re.escape(stem)}\b", raw_body, re.IGNORECASE)`
   against the raw file body. If it matches, produce an entity tuple
   for that stem.
3. For each entry in `groups.<slug>.canon_aliases[<filename>]`, run
   the same search with the alias string. Any alias hit counts as a
   match for that entity.
4. For each matched entity, attach its summary-file slice (if
   configured) to the tuple's `canon_file_paths`. See
   [Summary-file slice](#summary-file-slice) below.

Output: a list of entity tuples — one per matched stem — each with 1–2
`canon_file_paths` entries. The orchestrator fans out one subagent
per tuple in Step 4.

Log one line with the result:

```
[scope_narrowing] matched=<comma-separated stems> (<K> entities) strategy=filename_entity duration_ms=<ms>
```

Where `K` = matched entity count. Name the actual matched stems so
reviewers can eyeball whether scoping picked the right entities.

## Canon aliases (per-group `canon_aliases`)

Format in `config.yaml`:

```yaml
groups:
  competitive:
    canon_aliases:
      federato.md: ["federato.ai"]
      akur8.md: ["Akur8 Pricing", "Akur8 Solutions"]
```

Populate aliases only when the scope-narrowing fallback log surfaces a
real miss — the default empty map is intentional. Aliases match with
the same `\b<alias>\b` case-insensitive regex as filename stems.

## Summary-file slice (replaces the old `always_include` fan-out)

Files listed under `groups.<slug>.always_include` are **no longer**
fanned out to their own subagent. Instead, each matched entity's slice
of the summary file is attached to that entity's tuple as a second
writable canon path. The subagent then decides per finding whether to
target the profile or the summary slice.

Today only the competitive group uses this
(`truth/market/competitors.md` is the catalog file).

For each entity in the narrowing output:

1. Extract the entity's section from the summary file (see
   [Trimmed summary-file input](#trimmed-summary-file-input-change-7)
   below for the extraction algorithm — unchanged).
2. If a section was found, append the summary-file absolute path to
   that entity's `canon_file_paths`. The subagent treats it as
   writable alongside the per-entity profile.
3. If no section was found, the tuple has only the per-entity profile.

Both files in `canon_file_paths` are valid targets. The subagent picks
per-finding. The orchestrator's Step 4.5 dedup pass collapses any
cross-target duplicates.

## Foundational canon (per-group `foundational_canon`)

Files listed under `groups.<slug>.foundational_canon` are attached
**whole, unsliced** to every entity tuple produced by narrowing.

Schema:

```yaml
groups:
  competitive:
    foundational_canon:
      - guidance/competitive/README.md
      - guidance/competitive/positioning.md
      - truth/market/competitors.md
```

Paths are relative to `<mcp_root>/context/` (same as `canon` globs).
Empty / unset means no foundational attachments (the default for every
group except `competitive` as of 2026-04).

### Attachment algorithm

After the narrowing step has produced its entity tuples (and after any
summary-file slice has been attached), for each tuple:

1. For each path in `groups.<slug>.foundational_canon`, resolve it
   against `<mcp_root>/context/` and verify the file exists on disk.
2. If it exists, append the absolute path to the tuple's
   `canon_file_paths`. Order: per-entity profile first, summary slice
   second (if any), foundational paths last.
3. If the file does not exist, log a WARN line and skip it — treat as
   config drift rather than a halt:

   ```
   [scope_narrowing] WARN foundational_canon missing path=<path>
     (config drift; skipping for this run)
   ```

4. Log one summary line per entity tuple:

   ```
   [scope_narrowing] foundational_canon attached=<N>
     files=[<basename1>, <basename2>, ...]
   ```

No slicing. No per-entity extraction. The comparator subagent reads
each foundational file in full at its own Step 0.

### Interaction with other narrowing outcomes

- **Zero-match fallback** (see below): if narrowing fell through to
  loading every `group_canon_files` entry, foundational_canon still
  attaches to every resulting tuple. Foundational paths are additive,
  never replacement.
- **Filename-prefix halt** (no stem match → rename banner): no tuples
  are produced, so there are no foundational attachments to make. The
  banner is unchanged.
- **Summary-file slice**: independent of foundational_canon. A group
  may configure both; the slice attaches per-entity via
  `always_include`, the whole file attaches via `foundational_canon`.
  (The competitive group as of 2026-04 does not — it moved
  `truth/market/competitors.md` entirely to foundational_canon so the
  full catalog is writable.)

### Why a separate key (not extend `always_include`)

`always_include` is wired to slice extraction (see previous section).
Attaching whole files through it would silently change behaviour for
any group expecting per-entity slicing. `foundational_canon` keeps the
two concepts independent and makes the config self-documenting: slice
vs. whole is declared, not inferred.

### Comparator routing policy

Foundational canon files are writable targets but the subagent must
NOT treat them like per-entity profiles. Two rules that the
group-specific comparator prompt must encode (see
[comparators/competitive.md](comparators/competitive.md) §
"Foundational-file routing policy"):

- **Prefer UPDATES over ADDITIONS.** The reason we attach foundational
  files is to catch contradictions, refinements, and corrections, not
  to grow them. Prefer findings that replace existing canon text; treat
  net-new additions as the exception.
- **Drop, don't demote, for weak additions.** If a finding's natural
  home is a foundational file but it is neither an update nor a
  critical, group-wide, high-value addition, **drop it**. Do not
  redirect group-wide content into the per-entity profile — that would
  bloat the profile. Per-entity content continues to flow to the
  profile as today.

Group-wide source-tier rules (min tier, `render_prefix` on tier_3 /
tier_5) still apply. Per-section gates (`eligible_tiers`,
`scope_gated_by`, per-section `style`) from `section_schema` are
profile-only — they do not transfer onto foundational-file headings.

## Zero-match fallback

If no files matched after steps 1–4:

1. Fall back to loading every file in `group_canon_files` — safe
   default, never silently-zero.
2. Log:

   ```
   [scope_narrowing] FALLBACK: no matches (0/<M>) — consider adding aliases
   ```

A regressed run should not just look slow; it should leave a trail.

## Read file bodies

Subagents Read each canon file themselves in their own Step 0
(cheaper than shipping bodies through orchestrator context). The
orchestrator only needs to know the paths, which it passes through
`{{canon_file_paths}}`.

The orchestrator DOES pre-read the summary file once (to extract
per-entity slices and write them to disk adjacent to the summary) when
the group configures a summary-file slice. See the trimmed-input
section below.

Foundational canon files (per
[Foundational canon](#foundational-canon-per-group-foundational_canon))
are NOT pre-read by the orchestrator — the subagent reads them in full
at its own Step 0, same as the per-entity profile. No trimming.

## Trimmed summary-file input (Change 7)

For files listed in `groups.<slug>.always_include` (summary /
catalog files like `truth/market/competitors.md`), the orchestrator
trims the body to only the section matching the entity it's attaching
to. This keeps the subagent's context small (~60 lines instead of
~280) without losing coverage.

Algorithm:

1. Build the set of entity names from the filename-stem matches
   produced by the narrowing step above (Title-cased form, e.g.
   `Federato`, `Kalepa`).
2. For each entity, find the section in the summary file whose
   heading matches `**<Entity>** ` at the start of a bullet/paragraph
   (per the `competitors.md` convention:
   `**Federato** - AI-native underwriting platform…`).
3. Extract each matched section — the bolded-heading line plus every
   subsequent line up to the next `**<SomethingElse>** ` bold-heading
   (or end-of-file).
4. Concatenate with a 3-line preamble:

   ```
   # Summary catalog — entity sections only
   _Full catalog: {{canon_file_path}}. This view shows only the entity sections matched by the raw file's entity narrowing._
   _Line numbers below preserve the original canon_file line numbering._
   ```

   **Preserve the original 1-indexed line numbers** — the subagent
   still anchors `target_line_start` / `target_line_end` against the
   real canon file, not the trimmed view. When reading the trimmed
   body via `Read`, the numbers visible to the subagent must match
   the numbers in `{{canon_file_path}}`.

5. Pass the trimmed body as `{{canon_file_content}}` to the subagent,
   and pass `{{canon_file_path}}` unchanged (so the subagent Reads the
   real canon at Step 0 — the trimmed body is advisory, the real file
   is the anchor).

This applies **only** to files in `always_include`. Per-entity canon
files (e.g. `federato.md`, `kalepa.md`) pass their full body
unchanged.

**Why preserve line numbers**: `target_content_hash` in the synthesis
step is computed against the real canon file on disk. If the subagent
sees synthetic line numbers from the trimmed view, its anchors won't
match — integrate time would reject every row as `Needs Restage`.

## Empty canon scope

If the group's canon scope is empty (e.g. the `rfp` group with
`canon: []`) or every file was filtered out, skip Step 4 and jump to
Step 7 with:

> No canon in scope for group `<slug>` — kb-update has nothing to
> compare against.

Do NOT publish an empty result set to Notion.
