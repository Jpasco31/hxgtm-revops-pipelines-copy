# kb-update — Input routing edge cases

## Contents
- When this reference is loaded
- Union algorithm (all surfaces)
- INDEX.md filtering (`raw/<slug>/` eligibility)
- Inline paste (markdown typed after the command)
- URL argument — plain HTTP(S)
- URL argument — Teams / Glean-sourced
- PDF / DOCX auto-conversion
- Unsupported attachment types (halt)
- Group resolution prompt when `--group` is omitted
- Batch mode — resolving the file set (mixed-source batches)
- Unsupported attachments in a batch (halt policy)

## When this reference is loaded

SKILL.md Step 1b enumerates the four input surfaces inline. Read this
reference when you need:

- Per-surface extraction details (URL fetch prompts, Teams/Glean
  branch, inline-paste frontmatter synthesis).
- The exact INDEX.md filtering contract for raw-dir eligibility.
- The halt policy for unsupported attachment types.
- The legacy `batch_source` handling for explicit `--batch <path>`.

## Union algorithm (all surfaces)

kb-update does NOT use first-match routing. Every non-empty surface
contributes to the batch. In one invocation any combination of
{attachments, URL, inline, raw/<slug/>} is valid:

1. Enumerate chat attachments (N ≥ 0 `.md` / `.pdf` / `.docx` files;
   PDF/DOCX are auto-converted to markdown, see [PDF / DOCX
   auto-conversion](#pdf--docx-auto-conversion)).
2. Parse the command line for a URL argument (0 or 1). Fetch and
   materialise to a tempfile (see URL sections below).
3. Detect inline-pasted markdown after the command (0 or 1).
   Materialise to a tempfile.
4. Call `collect_inputs.py list-eligible --group <slug>` to discover
   eligible `raw/<slug>/` files.

Union = attachments + URL tempfile (if any) + inline tempfile (if any)
+ eligible raw-dir files. Track the raw-dir subset separately as
`raw_dir_members` so Step 6a can stamp INDEX.md selectively.

- Empty union → halt with the Step 1b empty-union banner.
- Union size == 1 → single-source mode (SKILL.md Step 2).
- Union size ≥ 2 → batch mode (SKILL.md Step 1c).

**Union is non-negotiable.** The orchestrator MUST process every
surface in the resolved union; silently dropping one (e.g. ignoring an
eligible raw-dir file when the operator passed a URL) is a skill
violation. See SKILL.md Step 1b "CRITICAL — union is non-negotiable"
and VERIFICATION.md invariant U1.

## INDEX.md filtering (`raw/<slug>/` eligibility)

`collect_inputs.py list-eligible --group <slug>` returns JSON with
these buckets. Eligibility rules:

| Bucket | Rule | Unioned? |
|--------|------|----------|
| `eligible` | INDEX.md row has `Process? = yes` AND `Last processed` is blank | Yes |
| `missing_from_index` | `.md` / `.pdf` / `.docx` file physically present under `raw/<slug>/` but no INDEX.md row matches | Yes — with a warning log |
| `skipped_process_no` | INDEX.md row has `Process? = no` | No (silent skip) |
| `already_processed` | INDEX.md row has `Process? = yes` but `Last processed` is non-blank | No (silent skip — prevents re-publishing the same findings) |

Missing-from-index files are unioned (kb-update should never silently
drop a file the operator dropped into raw/). Log one line per missing
file:

```
[missing_from_index] file=<relpath> — union anyway; add a row to INDEX.md to stop the warning
```

After a successful publish, Step 6a stamps `Last processed = <today>`
for every raw-dir member — both those originally in `eligible` and
those flagged `missing_from_index`. The stamp-processed subcommand
appends new INDEX.md rows for missing-from-index files so subsequent
runs see them in the `already_processed` bucket.

**INDEX.md format expectations** (competitive group shown; same
columns across all 11 groups):

```
| File | Added | Last processed | Process? |
|---|---|---|---|
| teams-chats/scan-2026-04-09.md | 2026-04-09 | 2026-04-15 | yes |
```

Extra columns are ignored. A missing `Last processed` column halts
`stamp-processed` with a clear error. Case-insensitive matching on
column names.

## Per-surface extraction details

The sections below cover how each individual surface is read and
normalised into a batch-ready tempfile. They apply identically
whether the surface is the sole contributor to the union or one of
several.

## Inline paste (markdown typed after the command)

Invocation: `/kb-update --group competitive` followed by a block of
markdown on subsequent lines. Inline paste may appear alongside any
other surface — all are unioned (Step 1b).

1. Prompt **once** via `AskUserQuestion` for optional `source_title`,
   `source_url`, `source_type` (free text, all optional).
2. Synthesize minimal frontmatter from the answers.
3. Pipe the assembled body (frontmatter + paste) into
   `scripts/materialise_ephemeral_input.py inline --run-id <run-id>`.
   The script writes
   `/tmp/kb-update-raw/<run-id>/inline-paste-<YYYY-MM-DD>.md` and
   prints the absolute path on stdout.
4. The tempfile joins the Step 1b union; cardinality decides
   single-source vs batch mode.

## URL argument — plain HTTP(S)

Invocation: `/kb-update --group competitive https://example.com/brief`.
A URL argument may appear alongside attachments, inline paste, and
eligible `raw/<slug>/` files — all four surfaces are unioned (Step 1b).

1. Fetch silently via `WebFetch` with a prompt asking for "the
   markdown-style extraction of the article body, no summarisation".
2. Infer `source_type` from the URL domain per the Step 3a inference
   table:
   - `gartner.com`, `forrester.com` → `analyst_report` (tier_1)
   - vendor's own domain → `vendor_blog` / `vendor_website` (tier_5)
   - otherwise → `tier_5` conservative default
3. Prepend a minimal YAML frontmatter block to the fetched body with
   `source_type`, `source_url`, `published` (if detected), and
   `confidentiality: shareable` (default for public URLs).
4. Pipe the body into
   `scripts/materialise_ephemeral_input.py url --url <URL> --run-id
   <run-id> [--competitor <stem>]` — the script writes the tempfile
   under `/tmp/kb-update-raw/<run-id>/` with filename
   `<competitor-or-domain>-url-<path-slug>-<YYYY-MM-DD>.md` and prints
   the absolute path on stdout. Pass `--competitor` when the group's
   scoping strategy is `filename_prefix` and you can map the URL to a
   canon entity stem (e.g. `sixfold.ai` → `--competitor sixfold`).
5. No prompting — the URL plus `--group` is unambiguous.

## URL argument — Teams / Glean-sourced

Invocation: `/kb-update --group competitive https://teams.microsoft.com/l/message/...`.

Glean MCP is the authenticated fetcher for Teams content that `WebFetch`
cannot reach. Glean indexes **public Teams channels only** — private
channels and DMs are not indexed, so "no content returned" is a normal
path, not a rare edge case.

### Pre-flight: Glean availability

Detect Glean by scanning available MCP tools for any tool whose name
contains `glean` (e.g. `mcp__glean__read_document`, `mcp__glean__search`).
The exact prefix depends on how the user registered the server; match
conceptually on the tool name, not the prefix.

If no Glean tool is available:

- Use `AskUserQuestion`:
  > "Glean MCP is required to fetch Teams content — it is not connected
  > in this session. You can: (a) paste the thread content inline, or
  > (b) cancel."
- "Paste inline" → inline-paste mode (prompt for optional metadata).
- "Cancel" → halt cleanly.

### Parse the Teams URL

Extract before calling Glean (used for search fallback and filenames):

| Component | Extraction |
|---|---|
| `channel_thread_id` | Path segment after `/l/message/`, before next `/` (e.g. `19:abc@thread.skype`) |
| `message_id` | Next path segment (numeric timestamp, e.g. `1774519510518`) |
| `group_id` | `groupId` query param |
| `created_time` | `createdTime` query param (epoch ms — useful as Glean date filter) |

### Primary: `read_document` by URL

Glean's `read_document` tool accepts a URL directly and returns the
indexed document body.

```json
{
  "documentSpecs": [{ "url": "<full Teams URL>" }]
}
```

If the call succeeds with non-empty content → use it.

### Fallback: `search` with Teams datasource filter

If `read_document` returns empty / not-found, call `search`:

```json
{
  "query": "<channel_thread_id or message_id>",
  "datasourcesFilter": ["microsoft_teams"]
}
```

Note: the exact `app` / `datasourcesFilter` string for Teams is not in
Glean's public docs. `microsoft_teams` is the conventional name but
verify against the tenant by calling `search` with no filter once and
inspecting the `app` facet bucket values. If search returns ranked
results, concatenate matching snippets into the body.

### No content from either call

- Use `AskUserQuestion`:
  > "Glean returned no content for this Teams URL. The thread may be in
  > a private channel (Glean indexes public channels only) or not yet
  > indexed. You can: (a) paste the thread content inline, or (b) cancel."
- "Paste inline" → inline-paste mode.
- "Cancel" → halt cleanly.

### Content returned — set variables directly, skip frontmatter round-trip

Since every field Step 3a would parse is already known from the URL and
the Glean response, skip the "build frontmatter → re-parse in Step 3a"
detour. Set the in-memory variables that Step 3b consumes directly:

| Variable | Value |
|---|---|
| `raw_body` | Glean content as markdown: author + timestamp header (if metadata returned), message text, then replies in order |
| `source_type` | `"teams_chat"` (forced — we know from the URL pattern) |
| `source_tier` | `"tier_4"` (derived from source_type) |
| `source_url` | original Teams URL |
| `source_title` | thread subject from Glean, else `"Teams thread <message_id>"` |
| `source_filename` | `teams-<message_id>-<YYYY-MM-DD>.md` (label for Notion's "Source file" column — never written to disk) |
| `fetched_via` | `"glean"` (for provenance / Step 7 report) |

Jump directly to **Step 3b** (canon discovery). Skip Step 3a entirely —
there's no frontmatter to parse, no tier to infer, no no-frontmatter
warning to emit. The tier_4 Notes-only routing and significance gate
apply at the comparator level, not at Step 3a.

Findings publish to Notion at `Status = Pending Review`; reviewer
approval in Notion is the "explicitly approved" gate before
`/kb-integrate` promotes them into canon.

## PDF / DOCX auto-conversion

PDF and DOCX attachments are first-class inputs. Before the union is
built, every `.pdf` and `.docx` file is converted to markdown via
`scripts/convert_to_markdown.py`:

- **Chat attachment / URL fetch** — the converted markdown is written
  to `/tmp/kb-update-raw/<run-id>/<stem>.md` (ephemeral; cleaned up by
  the run-id directory lifecycle).
- **`raw/<slug>/` source** — the converted markdown is written as a
  sidecar next to the source, e.g. `foo.pdf` → `foo.pdf.md`. The
  sidecar is committed to git so reviewers can read what kb-update
  actually compared against. **Do not hand-edit the sidecar; it is
  regenerated on every run.** INDEX.md stamping targets the source
  filename (`foo.pdf`), not the sidecar.

Converter backends: `pymupdf` for PDF (Pandoc cannot read PDFs);
Pandoc (preferred) or `mammoth` for DOCX. The script halts on:

| Exit | Reason |
|---|---|
| 2 | unsupported extension (only `.pdf` / `.docx` accepted) |
| 3 | required Python lib missing (`pip install pymupdf mammoth`) |
| 4 | input >25 MB (excerpt the relevant pages and paste inline) |
| 5 | scanned/image-only PDF (run `ocrmypdf` first; OCR is out of scope) |
| 6 | converted markdown >2 MB (excerpt and re-attach) |

A converter halt is surfaced verbatim and the kb-update run stops —
no silent skipping.

## Unsupported attachment types (halt)

Any attachment that isn't `.md`, `.pdf`, or `.docx` — image, archive,
other binary — halts the whole run with a single clean refusal:

```
/kb-update only handles markdown (.md), PDF, or DOCX attachments,
inline-pasted markdown, or HTTP(S) URLs. <filename> isn't supported.
Excerpt the relevant content and paste it inline, or attach a
supported format.
```

No follow-up questions.

**If ANY attachment in a multi-file upload is an unsupported type,
halt the whole run** — don't silently batch the supported ones. The
user likely uploaded the unsupported file in error and should see the
refusal before we process the rest.

## Group resolution prompt when `--group` is omitted

Use `AskUserQuestion` with the list of active groups from
`config.yaml`:

> "Which group should this input be compared against? Pick the canon
> slice that best matches the content."

Options: active group slugs + labels (e.g.
`competitive — Competitive Intelligence`). Record the user's choice as
`--group <slug>` for the remaining steps.

## Batch mode — resolving the file set

Batch mode fires whenever the Step 1b union resolves to ≥2 files,
regardless of which surfaces contributed. The file set is a flat list
of absolute paths — there is no per-surface branching in Step 4 /
Step 5. `collect_inputs.py` handles the raw-dir portion;
`materialise_ephemeral_input.py` handles URL / inline tempfiles;
attachments are already files with paths.

### Mixed sources in one batch

A single batch may contain (for example) 1 URL tempfile + 2
attachments + 3 raw-dir files = 6 total. Waves of
`global.batch_wave_size` (default 3) run across the flat list; the
orchestrator does not need to distinguish sources during fan-out. The
only source-dependent bookkeeping is `raw_dir_members` — the subset
whose INDEX.md rows get stamped in Step 6a.

### `--batch <path>` (explicit override)

When `--batch <path>` is passed, kb-update ignores all four auto-
detected surfaces and processes only `<path>` (a directory of `.md`
files, or a single `.md` file). Intended for operator-driven
one-offs where the auto-union behaviour is unwanted.

### `raw/<slug>/` via `collect_inputs.py`

The `list-eligible` subcommand handles recursion into typed
subfolders (`deep-research/`, `transcripts/`, `clippings/`, etc.),
excludes `INDEX.md`, and applies the `Process?` / `Last processed`
filter. Output is a JSON object whose `eligible` array contains
absolute paths the orchestrator can read directly.

### Empty-set halt

If the union resolved to zero files (no attachments, no URL, no
inline, zero eligible in `raw/<slug>/`), halt per the Step 1b
empty-union banner.

For the explicit `--batch <path>` override: if `<path>` is empty or
missing, halt with:

> No `.md` files to process at `<path>`. Drop sources and re-run.

## Unsupported attachments in a batch (halt policy)

If **any** chat attachment is an unsupported type (image, archive,
other binary — i.e. not `.md`/`.pdf`/`.docx`), halt the whole run
with the generic
[unsupported-attachment banner](#unsupported-attachment-types-halt),
regardless of whether other surfaces (URL, inline, raw/) could have
contributed. Do not batch the supported attachments and silently
drop the unsupported one — the user likely uploaded it in error and
should see the refusal before we process anything.

`raw/<slug>/` is a filesystem scan via `collect_inputs.py`, which
lists `.md` / `.pdf` / `.docx` by construction (sidecar `.md` files
adjacent to a `.pdf`/`.docx` are excluded so the source isn't
double-counted). Other file types under `raw/<slug>/` are never in
the union and never cause a halt.

## Parallel execution flow (reminder)

After batch input is resolved, Step 4 handles parallel execution:
waves of `global.batch_wave_size` concurrent files (default **3**).
Inside each wave, each file fires its own parallel-per-file Sonnet
subagents. Total parallelism per wave: up to 3 × N subagents in one
orchestrator message. See SKILL.md Step 4 for the message-construction
rules; this reference only covers the input-collection side.
