---
name: download-from-notion
description: Download a file attached to a Notion page (in a Files property or via a pre-signed URL) to local disk. Used standalone or chained from producer skills that require local file inputs (e.g. webinar-promo-card needs photo_path).
---

# download-from-notion

## Purpose

Reusable utility skill that downloads one or more files from a Notion source to local disk. Designed to be chained from any skill that requires local file inputs (e.g. `webinar-promo-card` hard-fails without `photo_path` for every speaker) and also callable directly by you. The Notion integration token is **always passed in by the caller at invocation time** — never read from disk or environment variables.

This is the mirror image of [`upload-to-notion`](../upload-to-notion/SKILL.md): producer skills download inputs with this skill, process them locally, then upload outputs with `upload-to-notion`.

## When to Use

- A producer skill needs local file paths but the brief sources files from Notion (e.g. speaker headshots attached to a task page).
- A routine orchestrator (Perkins) has fetched a Notion page and wants to resolve its Files property to disk before dispatching the producer skill.
- You have a single pre-signed Notion S3 URL or any HTTPS URL and want it on disk.
- A press-release-style card has its inputs in an inline body-table block (singletons like `Customer Logo`) or an inline child database (unbounded sets like `Customer Quotes`), rather than as page-level Files properties. Use the new body-table-row or child-DB modes.
- A converted playbook collects its inputs through a **Notion form** backed by a **per-step database placed as a full-page child** of the card. Use Mode 4 with `--database-id` (locate by id, not body scan) and `--explode-groups`/`--latest-only` to read the latest submission's numbered fields; singleton files (e.g. `Customer Logo`) sit as a Files property on the submission row, resolvable with page-property mode pointed at that row's page id.

## Inputs

The skill operates in **one of four modes** — pick one per invocation:

1. **URL mode** — caller already has a signed URL (`download_from_notion.sh --url …`).
2. **Page-property mode** — files are in a Notion page's Files property (`download_from_notion.sh --page-id … --property …`). Best when the page model uses page-level Files properties (e.g. `webinar-promo-card`'s `Speaker headshots`).
3. **Body-table row mode** *(new — `download_table_row.py`)* — a single attachment or LinkedIn URL lives in a labelled row of an inline body-table block. Used by the Customer Press Release playbook for `Customer Logo`.
4. **Inline child-DB mode** *(new — `download_child_db_rows.py`)* — an inline child database on the page holds an unbounded list of rows, each with its own attachment + LinkedIn URL fallback. Used by the Customer Press Release playbook for the `Customer Quotes` child DB.

Modes 3 and 4 exist because press-release-style cards don't expose their per-input files as Notion page-level properties — they're embedded in the page body. Modes 1 and 2 stay the right choice for everything else.

### Mode 1: URL mode (no auth, caller-resolved URL)

| Argument | Description |
| --- | --- |
| `url` | Pre-signed Notion S3 URL (`https://prod-files-secure.s3...` or `https://s3.us-west-2.amazonaws.com/secure.notion-static.com/...`) or any HTTPS URL the script can fetch without authentication. |
| `output` | Absolute local path to write to (filename included). Parent directory will be created if missing. |

Notion-issued signed URLs **expire approximately 1 hour after the originating Notion API call returned them**. The caller is responsible for using fresh URLs — there is no resign mechanism in this mode.

### Mode 2: Page-property mode (script re-fetches the page)

| Argument | Description |
| --- | --- |
| `notion_api_key` | Notion integration token (secret). Provided by the caller — never read from env. |
| `page_id` | Notion page UUID (with or without dashes). |
| `property_name` | Exact name of the Files property to pull from (e.g. `Speaker headshots`). |
| `output_dir` | Absolute local directory to write files into. Created if missing. Filenames preserve the original Notion file names (sanitized for path traversal). |

This mode **calls `GET https://api.notion.com/v1/pages/<page_id>` at invocation time**, so signed-URL TTL is never a concern regardless of how long ago the orchestrator first fetched the page.

### Mode 3: Body-table row mode (`download_table_row.py`)

For Notion pages whose inputs live in an inline **body-table block** (a `table` block inside the page body), not in page-level properties. Press-release cards in the Customer Press Release playbook use this pattern — `Customer Logo` lives in a row of the page's body table, with a sibling `Customer LinkedIn URL` row as the optional fallback.

| Argument | Description |
| --- | --- |
| `--api-key` | Notion integration token. |
| `--page-id` | Notion page UUID (with or without dashes). |
| `--row-label` | Exact left-cell label of the target row, e.g. `"Customer Logo"`. |
| `--output-dir` | Absolute local directory for the resolved file. Created if missing. |

Resolution order:

1. The value cell's first attached file (mention or child image/file block) → downloaded directly.
2. Otherwise, a sibling row labelled `"<row-label> LinkedIn URL"` containing a LinkedIn URL → handed off to `fetch-linkedin-image` (chained automatically; the script must exist at `.claude/skills/fetch-linkedin-image/scripts/fetch_linkedin_image.sh`).
3. Otherwise, if the value cell itself contains a LinkedIn URL → same hand-off.
4. If none of the above resolve, exit 3 with `attach <row-label> as file`.

Manifest (stdout, single-line JSON):

```json
{
  "row_label": "Customer Logo",
  "source": "file" | "linkedin_url",
  "local_path": "/abs/path",
  "bytes": 12345,
  "mime": "image/png"
}
```

### Mode 4: Customer-quotes DB mode (`download_child_db_rows.py`)

Reads customer-quote rows from a Notion database and resolves each quote's photo (file → LinkedIn URL → skipped). The database can be located **two** ways, and the rows can be read in **two** shapes — pick one of each per invocation:

**Locating the database:**
- *Inline child DB (legacy):* `--page-id` + `--child-db-name` — an embedded `child_database` block on the page body. Used by the Customer Press Release playbook's `Customer Quotes` child DB.
- *By id (`--database-id`):* query a database directly, skipping the page-body scan. **Required for a per-step form-inputs database placed as a full-page child of the card** — the body scan cannot see full-page children. Resolve the database id from the card's `<database inline="false">` child block (via MCP `notion-fetch`).

**Reading the rows:**
- *One row per quote (legacy):* each row is one quote.
- *Form-input model (`--explode-groups`):* a single submission row carries N numbered groups — `Customer Quote 1: Text`, `Customer Quote 1: Customer Name`, `Customer Quote 1: Photo`, `Customer Quote 2: Text [Optional]`, … . Each non-blank group becomes one manifest entry; the group number is the order. Combine with `--latest-only` to take the newest submission. Property-name matching ignores a trailing `[Optional]` label.

| Argument | Description |
| --- | --- |
| `--api-key` | Notion integration token. |
| `--database-id` | Query this DB directly (full-page-child form DB). Mutually exclusive with the `--page-id` locator. |
| `--page-id` | Notion page UUID hosting an inline child DB (legacy locator). |
| `--child-db-name` | Title of the inline child DB (legacy locator; default: `"Customer Quotes"`). |
| `--latest-only` | Keep only the most recent row by `created_time` (the latest form submission). |
| `--explode-groups` | Read N numbered quote groups from each row instead of one quote per row. |
| `--group-prefix` | Group-name prefix for `--explode-groups` (default: `"Customer Quote"`). |
| `--max-groups` | Number of numbered groups to read (default: `4`). |
| `--output-dir` | Absolute local directory for the per-row photo files. Created if missing. |

The script resolves each quote's photo via the same file → LinkedIn URL → skipped chain as Mode 3. In legacy mode, rows are sorted by `Order` ascending then `created_time`; a row with both attachment and LinkedIn URL blank is marked `status: skipped` with a reason (it does **not** fail the run — the orchestrator decides whether a skipped row should block the card). In `--explode-groups` mode, a group whose `Text` is blank is treated as not-filled-in and skipped silently (the marketer used fewer than N quotes).

Manifest (stdout, single-line JSON, one entry per row):

```json
{
  "child_db_id": "...",
  "rows": [
    {
      "row_id": "...",
      "order": 1,
      "quote_text": "...",
      "customer_name": "...",
      "customer_title": "...",
      "company_name": "...",
      "avatar_local_path": "/abs/path",
      "avatar_source": "file" | "linkedin_url" | "missing",
      "status": "ok" | "skipped",
      "reason": "..."
    }
  ]
}
```

**Property-name caveat.** The production `Customer Quotes` DB on the press-release template was created with trailing tab characters in every property name (`Customer name\t`, `Customer Photo\t`, etc.). `download_child_db_rows.py` compares property names with trailing whitespace stripped, so the helper works whether or not future schemas have the same quirk.

### Optional (Modes 1 and 2 only)

| Argument | Description |
| --- | --- |
| `mime_allow` | Comma-separated MIME whitelist (e.g. `image/png,image/jpeg`). Any file outside the list aborts with exit 3. Use to enforce input constraints — e.g. headshot pipelines should only accept image types. |
| `max_bytes` | Per-file byte ceiling. Exceeded → abort and exit 3. Uses `curl --max-filesize` for early abort plus a post-write check. |
| `max_attempts` | Override retry count (default `7`). Same backoff schedule as `upload-to-notion`: `2s, 5s, 10s, 30s, 60s, 120s, 180s` with ±25% jitter, honouring `Retry-After`. |
| `no_overwrite` | Refuse to write a target path if it already exists. Off by default — re-runs overwrite cleanly. |

## Resolving IDs (when the caller has names, not UUIDs)

If the caller passes a page **name** or URL instead of a UUID, resolve it first via the Notion MCP:

1. Call `mcp__claude_ai_Notion__notion-search` (or `mcp__claude_ai_Notion__notion-fetch` with the URL) to confirm the page and capture its ID.
2. Pass the 32-char hex ID (or hyphenated UUID — both work) as `page_id`.

The skill does **not** accept Notion URLs directly; resolve to an ID first. This keeps the script free of URL-parsing surprises.

## Execution

**Primary path: invoke `scripts/download_from_notion.sh`.** Deterministic Bash script that handles retries, signed-URL streaming, MIME/size validation, atomic writes (temp file → rename so no partial file ever appears at the target path), and JSON manifest output.

Invoke via the Bash tool. Resolve the script path once at the start of the run:

```bash
SCRIPT="$(find "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PROJECT_DIR:-.}" -path '*/download-from-notion/scripts/download_from_notion.sh' -print -quit 2>/dev/null)"
[[ -x "$SCRIPT" ]] || { echo "download_from_notion.sh not found"; exit 1; }
```

**Example — page-property mode, the most common path for routine orchestration:**

```bash
"$SCRIPT" \
  --api-key "$NOTION_API_KEY" \
  --page-id "344802db-20a6-80d6-8ba3-dabe1b6ba6e6" \
  --property "Speaker headshots" \
  --output-dir "/path/to/campaigns/my-event/working/inputs/headshots" \
  --mime-allow "image/png,image/jpeg,image/webp"
```

**Example — URL mode for an ad-hoc resolved URL:**

```bash
"$SCRIPT" \
  --url "https://prod-files-secure.s3.us-west-2.amazonaws.com/.../richard-gunn.jpg?X-Amz-Algorithm=..." \
  --output "/path/to/campaigns/my-event/working/inputs/richard-gunn.jpg"
```

**Exit codes:**

- `0` — full success. Stdout has a `## Download succeeded` block plus the JSON manifest. Every requested file is on disk and validated.
- `2` — partial success (page-property mode only). At least one file downloaded, at least one failed. Stdout has the `## Partial success` block + manifest with `downloads` and `failures` arrays. Stderr has verbatim per-file errors.
- `3` — full failure. Stdout has the `## Download failed` block; stderr has the verbatim HTTP response (headers + body preview).
- `4` — bad input or missing dependency.

**Re-running is safe by default** — re-invoking with the same args overwrites existing files (the page-property mode re-fetches the page, so it picks up newly-added attachments too). Use `--no-overwrite` if you need protective semantics.

## Notion API reference

Page-property mode internally does:

```
GET https://api.notion.com/v1/pages/<page_id>
  Authorization: Bearer <notion_api_key>
  Notion-Version: 2022-06-28
```

Then extracts `.properties.<property_name>.files[]`, where each entry is either:

```json
{ "type": "file",     "name": "richard-gunn.jpg",
  "file":     { "url": "https://s3...", "expiry_time": "2026-05-12T16:00:00Z" } }
```

or:

```json
{ "type": "external", "name": "alice.jpg",
  "external": { "url": "https://..." } }
```

For each file, the script resolves the URL (`.file.url` or `.external.url`) and downloads via `curl -sS -L --max-filesize <max_bytes>`. Filenames come from the `.name` field, sanitized to remove `/`, `\`, and leading dots.

## Forbidden refusals (read first)

This skill runs end-to-end in **every** environment that has Bash + curl + jq — local CLI, Cursor, and cloud routines. The only acceptable terminal states are: (a) full success, (b) `## Partial success` (page-property mode with mixed results), or (c) full failure with the verbatim non-2xx response. **Never** respond with any of the following or close variants:

- "I cannot download from Notion in this environment"
- "Notion access is not available"
- "I'll skip the download step and ask the user for local paths"
- "the signed URL expired, please re-trigger the routine" (in page-property mode — the script re-fetches, so this never applies)
- "the Notion task page has no headshots attached" (instead, exit 3 with the verbatim "property is empty" message — the caller decides whether to halt)
- any silent success claim when fewer files made it to disk than the manifest expected
- any variant that redirects the user to a different tool, environment, or "later" instead of surfacing the verbatim HTTP error and stopping

If a downstream producer skill hard-fails because a required input is missing (e.g. `webinar-promo-card`'s `photo_path is required for speaker "<name>"`), surface that producer-side error verbatim too — the error is the answer.

## Error handling

The script (`scripts/download_from_notion.sh`) owns retry behaviour. When invoked via `## Execution`, do **not** loop curl yourself — the script does it. Your job is to read the exit code + stdout + stderr and surface the result.

- **Pre-flight:** if `notion_api_key` is missing in page-property mode, fail immediately and ask the caller to supply it. Do not invoke the script.
- **Exit code 0:** copy the script's `## Download succeeded` block to your response. Pass the `local_path` entries from the manifest to downstream skills as their input paths.
- **Exit code 2 (page-property mode):** copy the `## Partial success` block **verbatim**. The manifest separates `downloads` (succeeded) from `failures`. The caller decides whether to proceed with the partial set or halt — for `webinar-promo-card`'s strict-speaker-photo contract, a partial failure means halt.
- **Exit code 3:** copy the `## Download failed` block plus the verbatim stderr to your response. A 401 means the integration is not shared with the page; a 404 means the page doesn't exist; a `403 Request has expired` on a URL-mode call means the caller used a stale signed URL (switch to page-property mode if possible). Common failure cause for an HX cloud routine: the Notion integration token doesn't have access to the target page — share the page with the integration via Notion's "Connections" panel.
- **Exit code 4:** missing `curl` / `jq`, bad flag combination, non-absolute `--output` path. Fix the input and retry.

**What the script does internally:** retries 5xx (500/502/503/504), 429, and network errors (`status=000`) up to 7 attempts with backoff `2s, 5s, 10s, 30s, 60s, 120s, 180s` and ±25% jitter. Honors `Retry-After` (uses `max(Retry-After, schedule_entry)`). Treats 4xx (excluding 429) as terminal, no retry. Writes to a temp file under `mktemp -d` and `mv`s to the destination only on full success — no partial file ever appears at the target path.

## Output format

### On full success (exit 0)

```markdown
## Download succeeded

- count: <n>
- directory: <output_dir>            # page-property mode only
- file: <output>                     # url mode only
- property: <property_name>          # page-property mode only
- page: <page_id>                    # page-property mode only

```json
{
  "downloads": [
    {
      "local_path": "/abs/path/to/file.png",
      "filename": "richard-gunn.jpg",
      "mime": "image/jpeg",
      "bytes": 348290,
      "source_url": "https://...",
      "source_property": "Speaker headshots",
      "source_page_id": "344802db-...",
      "source_type": "file",
      "url_expiry": "2026-05-12T16:00:00.000Z"
    }
  ]
}
```
```

### On partial success (exit 2, page-property mode)

```markdown
## Partial success — <ok>/<total> downloads ok, <fail> failed

- directory: <output_dir>
- property: <property_name>
- page: <page_id>

Verbatim per-file errors are on stderr. Re-run after fixing the upstream cause; existing files will be overwritten unless --no-overwrite is set.

```json
{ "downloads": [...], "failures": [...] }
```
```

### On full failure (exit 3)

```markdown
## Download failed

- source: <url> | source-page: <page_id>
- target: <output> | <output_dir>

See stderr for the verbatim HTTP response.
```

## Examples

**1. Chained from the Perkins orchestrator (most common):** routine subagent dispatched for a webinar task. Task page has speaker headshots in a `Speaker headshots` Files property. Resolve them to disk before invoking `webinar-promo-card`.

```bash
"$SCRIPT" \
  --api-key "$NOTION_API_KEY" \
  --page-id "$TASK_PAGE_ID" \
  --property "Speaker headshots" \
  --output-dir "$CAMPAIGN_DIR/working/inputs/headshots" \
  --mime-allow "image/png,image/jpeg,image/webp"
```

Parse the JSON manifest, map each `local_path` to a speaker (by filename slug, or by index in the property order), then pass each absolute path as `photo_path` to `webinar-promo-card`.

**2. Direct URL mode:** caller already has a fresh signed URL (e.g. plucked from an MCP `notion-fetch` response within the last minute).

```bash
"$SCRIPT" \
  --url "$SIGNED_URL" \
  --output "/abs/path/to/cover.png"
```

**3. Strict MIME enforcement on a headshot pipeline:**

```bash
"$SCRIPT" \
  --api-key "$NOTION_API_KEY" \
  --page-id "$TASK_PAGE_ID" \
  --property "Speaker headshots" \
  --output-dir "$CAMPAIGN_DIR/working/inputs/headshots" \
  --mime-allow "image/png,image/jpeg" \
  --max-bytes 10485760
```

Rejects PDFs, SVGs, anything over 10 MB. The producer skill's hard-fail contract handles the downstream consequence if a speaker has no usable photo.

**4. Body-table singleton (Customer Press Release `Customer Logo`):**

```bash
python3 .claude/skills/download-from-notion/scripts/download_table_row.py \
  --api-key "$NOTION_API_KEY" \
  --page-id "$CARD_PAGE_ID" \
  --row-label "Customer Logo" \
  --output-dir "$CAMPAIGN_DIR/working/inputs"
```

Parses the page body for the first `table` block, finds the row whose left cell reads `Customer Logo`, and downloads the attached file. If the file slot is empty, looks for a sibling row `Customer Logo LinkedIn URL` (or a LinkedIn URL in the value cell) and chains to `fetch-linkedin-image`. Outputs a single-row JSON manifest with `local_path`. Hard-fails (exit 3) with `attach Customer Logo as file` if neither path resolves.

**5. Inline child DB (Customer Press Release `Customer Quotes`):**

```bash
python3 .claude/skills/download-from-notion/scripts/download_child_db_rows.py \
  --api-key "$NOTION_API_KEY" \
  --page-id "$CARD_PAGE_ID" \
  --child-db-name "Customer Quotes" \
  --output-dir "$CAMPAIGN_DIR/working/inputs/quotes"
```

Reads every row of the embedded `Customer Quotes` child DB, sorts by `Order` then `created_time`, resolves each row's photo (file → LinkedIn URL → skipped), and emits one manifest object covering all rows. Pass the `status: ok` rows on to `linkedin-customer-quote-card` as its input list (each row has `quote_text`, `customer_name`, `customer_title`, `company_name`, and `avatar_local_path`).

**6. Form-inputs DB as a full-page child (converted playbook, Step 2 quotes):**

```bash
python3 .claude/skills/download-from-notion/scripts/download_child_db_rows.py \
  --api-key "$NOTION_API_KEY" \
  --database-id "$STEP2_INPUT_DB_ID" \
  --latest-only \
  --explode-groups \
  --group-prefix "Customer Quote" \
  --max-groups 4 \
  --output-dir "$CAMPAIGN_DIR/working/inputs/quotes"
```

Queries the per-step input database directly (no body scan), takes the most recent form submission, and explodes its `Customer Quote 1..4: …` columns into the **same manifest shape** as example 5 — so `linkedin-customer-quote-card` consumes it identically. The submission row's singleton `Customer Logo` Files property is fetched separately with page-property mode (`download_from_notion.sh --page-id "$SUBMISSION_ROW_ID" --property "Customer Logo"`).

## Skill Chaining

Producer skills (`webinar-promo-card`, future content skills that need binary inputs) should:

1. Inspect the brief for Notion-hosted file references (Files property names, signed URLs, or task page IDs).
2. Confirm or resolve the page ID via the Notion MCP if the brief gives a name or URL.
3. Invoke this skill with the resulting page ID + property name (preferred) or URL.
4. Parse the JSON manifest from stdout to recover absolute local paths.
5. Pass those paths into the producer skill's required input fields (e.g. `photo_path`).
6. Fail loudly if a required input has no resolvable Notion source — never substitute placeholders.

## Limitations (v1)

- **Body-block file extraction is not supported.** Image and file blocks embedded directly in a page's body content cannot be discovered by this skill. Only Files properties on the page object are introspected. If you need a file from a block, resolve the signed URL via the Notion MCP first and use URL mode. (A database placed as a full-page child *is* supported — locate it with Mode 4's `--database-id`.)
- **Multi-part / resumable downloads are not supported.** Notion attachments are typically single-digit MB; on transient failure the script re-downloads the whole file rather than resuming.
- **No filename collision resolution within `--output-dir`.** If two files in the property have the same `name`, the second overwrites the first. Notion's UI prevents this in practice, but be aware.
