---
name: upload-to-notion
description: Upload a local file or remote URL (image, PDF, or generic file) to a specific Notion page block, database row Files property, page cover, or page icon. Used standalone or chained from other skills that produce binary artifacts.
---

# upload-to-notion

## Purpose

Reusable utility skill that uploads a single file or image to a specific Notion target. Designed to be chained from any skill that produces a binary artifact (e.g. `webinar-promo-card`, `clip-podcast`) and also callable directly by you. The Notion integration token is **always passed in by the caller at invocation time** — never read from disk or environment variables.

## When to Use

- A skill produces an image/PDF/file and needs to attach it to a Notion page.
- You want to set a Notion page's cover or icon to a specific image.
- You want to populate a "Files & media" property on a Notion database row.
- You have a remote `https://` URL pointing to a file and want it placed in Notion without downloading it locally first.

## Inputs (required)

| Argument         | Description                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| `notion_api_key` | Notion integration token (secret). Provided by the orchestrator or user per call.                 |
| `source`         | Absolute local file path **or** an `https://` URL. Mutually exclusive with `source_b64`.          |
| `target`         | One of: `page_block`, `row_property`, `page_cover`, `page_icon`.                                  |
| `target_id`      | Notion page ID (UUID, with or without dashes). For `row_property` this is the page ID of the row. |

Exactly one of `source` or `source_b64` must be provided.

| Argument     | Description                                                                                                                                                                                                                                                                           |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `source_b64` | Base64-encoded file bytes. Use when the caller has the file in memory (e.g. routine running in a sandbox with no shared filesystem). When set, `filename` and `mime` are also required. The skill writes the decoded bytes to a temp file and uploads as a single-part `file_upload`. |
| `filename`   | Required with `source_b64`. The basename Notion will display, e.g. `linkedin-card_20260326_topic_wine.png`.                                                                                                                                                                           |
| `mime`       | Required with `source_b64`. The Content-Type, e.g. `image/png`.                                                                                                                                                                                                                       |

## Inputs (optional)

| Argument        | Description                                                                                               |
| --------------- | --------------------------------------------------------------------------------------------------------- |
| `property_name` | Required only when `target = row_property`. The exact name of the Files & media property on the database. |
| `block_type`    | `image` \| `file` \| `pdf`. If omitted, infer from the source's extension or `Content-Type`.              |
| `caption`       | String caption for `image` / `file` / `pdf` blocks.                                                       |
| `after`         | `page_block` only. Block ID of an existing sibling to insert the new block immediately **after**, instead of at the end of the page. Use to land an image under a specific section (e.g. a Perkins card's Step 1/Step 2 Outputs) rather than at page-bottom. Omit for end-of-page append. |
| `display_name`  | Override for the filename shown in Notion. Defaults to the source filename.                               |

## Resolving IDs (when the caller has names, not IDs)

If the caller passes a page or database **name** instead of a UUID, resolve it first using the Notion MCP:

1. Call `mcp__claude_ai_Notion__notion-search` with the name and an appropriate `query_type` (`internal` for a page, `internal` filtered to data sources for a database).
2. If multiple matches return, pick the most recently edited one and confirm the choice in the response. Never proceed on an ambiguous match silently.
3. Use the returned ID as `target_id`.

## Block-type inference

| Extension / MIME                              | `block_type` |
| --------------------------------------------- | ------------ |
| `.png .jpg .jpeg .gif .webp .svg` / `image/*` | `image`      |
| `.pdf` / `application/pdf`                    | `pdf`        |
| anything else                                 | `file`       |

## Execution

**Primary path: invoke `scripts/upload_to_notion.sh`.** This is a deterministic Bash script that runs the full 3-step pipeline (file_upload create → bytes upload → attach to target) with exponential-backoff retries (7 attempts ramping `2s, 5s, 10s, 30s, 60s, 120s, 180s` per step ≈ 6.8 min budget), `Retry-After` honoring, and an **idempotency check** that prevents duplicate blocks if a 5xx response was a hidden success.

Why a script instead of inline curl: the `public_appendBlockChildren` endpoint returns transient `503 / DatastoreInfraError` during routine Notion incidents that can last several minutes. An LLM-driven retry loop is slow and non-deterministic; the script sleeps precisely between attempts, parses headers reliably, and survives without burning agent context per attempt. Notion's own JS SDK explicitly does **not** auto-retry 5xx on PATCH/POST endpoints to avoid duplicate side effects — the script handles this safely via the idempotency pre-check (`GET /v1/blocks/<target_id>/children` matched on `file_upload.id`).

Invoke via the Bash tool. The script discovers itself relative to the SKILL.md location. Resolve the absolute path once at the start of the run:

```bash
SCRIPT="$(find "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PROJECT_DIR:-.}" -path '*/upload-to-notion/scripts/upload_to_notion.sh' -print -quit 2>/dev/null)"
[[ -x "$SCRIPT" ]] || { echo "upload_to_notion.sh not found"; exit 1; }
```

**Example — append a PNG as an image block (the most common path, used by `webinar-promo-card`):**

```bash
"$SCRIPT" \
  --api-key "$NOTION_API_KEY" \
  --source "/path/to/linkedin-card_20260326_topic@2x.png" \
  --target page_block \
  --target-id "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d" \
  --block-type image \
  --caption "LinkedIn promo card — Why AI-cautious carriers create the most underwriting risk"
```

**Example — set a Notion page cover from a remote URL:**

```bash
"$SCRIPT" \
  --api-key "$NOTION_API_KEY" \
  --source "https://example.com/cover.png" \
  --target page_cover \
  --target-id "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
```

**Example — populate a database row's Files & media property:**

```bash
"$SCRIPT" \
  --api-key "$NOTION_API_KEY" \
  --source "/path/to/file.pdf" \
  --target row_property \
  --target-id "<row_page_id>" \
  --property-name "Attachments" \
  --display-name "Q2 Briefing.pdf"
```

**Exit codes:**

- `0` — full success. The script prints a `## Upload succeeded` markdown block.
- `2` — partial success (Steps 1+2 ok, Step 3 exhausted retries). Stdout contains the `## Partial success — block-append failed` block with the manual-retry recipe. Surface it verbatim per the contract in `## Output format`.
- `3` — full failure (Step 1 or 2 failed, or 4xx from any step). Stdout has the verbatim Notion response.
- `4` — bad input or missing dependency.

**Re-running is safe.** If a previous invocation got partway and Notion eventually created the block, re-invoking with the same args will hit the idempotency check and return success without creating a duplicate (works while the `file_upload.id` is still valid — Notion garbage-collects unused uploads after ~1 hour).

**Multi-part uploads (>20 MB):** the script does **not** yet handle multi-part. For files over 20 MB, fall back to the manual HTTP pipeline in `## Reference` below. Most webinar-promo-card PNGs are 1–4 MB and use the single-part path.

## Reference: HTTP pipeline (what the script does internally; manual fallback if the script is unavailable)

The pipeline is three sequential HTTP calls via `curl`. All requests carry these headers:

```
Authorization: Bearer <notion_api_key>
Notion-Version: 2022-06-28
```

### Step 1 — create the `file_upload` object

`POST https://api.notion.com/v1/file_uploads` with `Content-Type: application/json`.

**Base64 in-memory bytes (`source_b64`):** decode and write to a temp path first:

```bash
python3 -c "import base64,sys; open(sys.argv[1],'wb').write(base64.b64decode(sys.argv[2]))" \
  /tmp/<filename> "<source_b64>"
```

Then treat the temp path as a local file and proceed with the single-part flow below using `filename` and `mime` from the caller. Delete the temp file after step 3 completes.

**Local file ≤ 20 MB:**

```json
{ "mode": "single_part", "filename": "<name>", "content_type": "<mime>" }
```

**Local file > 20 MB:**

```json
{ "mode": "multi_part", "number_of_parts": <N>, "filename": "<name>", "content_type": "<mime>" }
```

Where `N = ceil(file_size / 10MB)`.

**Remote URL** (Notion fetches the file itself — no local download needed):

```json
{ "mode": "external_url", "external_url": "<https url>", "filename": "<name>" }
```

Capture the returned `id` (and `upload_url` for single/multi-part modes).

### Step 2 — send the file bytes

**Single-part:**

```bash
curl -X POST "<upload_url>" \
  -H "Authorization: Bearer <notion_api_key>" \
  -H "Notion-Version: 2022-06-28" \
  -F "file=@<local_path>"
```

**Multi-part:** repeat the single-part call once per part with an additional `-F "part_number=<n>"` field, slicing the file into 10 MB chunks. Then call:

```
POST https://api.notion.com/v1/file_uploads/<id>/complete
```

**External URL:** skip the upload call. Poll `GET https://api.notion.com/v1/file_uploads/<id>` until `status == "uploaded"`. Wait 1 s between polls; fail with a clear message if not uploaded within ~30 s.

### Step 3 — attach to the target

Branch on `target`:

**`page_block`** — append a new block to the page:

```
PATCH https://api.notion.com/v1/blocks/<target_id>/children
```

Body:

```json
{
  "children": [
    {
      "type": "<block_type>",
      "<block_type>": {
        "type": "file_upload",
        "file_upload": { "id": "<file_upload_id>" },
        "caption": [{ "type": "text", "text": { "content": "<caption>" } }]
      }
    }
  ]
}
```

Omit the `caption` array when no caption is provided.

By default the block is appended at the **end of the page**. When `after` is
provided, add it as a top-level sibling of `children` so Notion inserts the new
block immediately after that existing block instead:

```json
{ "children": [ /* … */ ], "after": "<after_block_id>" }
```

**`row_property`** — populate a Files & media property on a database row:

```
PATCH https://api.notion.com/v1/pages/<target_id>
```

Body:

```json
{
  "properties": {
    "<property_name>": {
      "files": [
        {
          "type": "file_upload",
          "file_upload": { "id": "<file_upload_id>" },
          "name": "<display_name>"
        }
      ]
    }
  }
}
```

**`page_cover`:**

```
PATCH https://api.notion.com/v1/pages/<target_id>
```

Body:

```json
{
  "cover": {
    "type": "file_upload",
    "file_upload": { "id": "<file_upload_id>" }
  }
}
```

**`page_icon`:** identical to `page_cover` but with the `icon` key.

## Forbidden refusals (read first)

This skill runs end-to-end in **every** environment that has Bash + curl + the Notion MCP token — local CLI, Cursor, and cloud routines. The only acceptable terminal states are: (a) full success, (b) full failure with the verbatim non-2xx response, or (c) the **Partial success** block defined in `## Output format`. **Never** respond with any of the following or close variants:

- "I cannot upload to Notion in this environment"
- "Notion access is not available"
- "I'll skip the upload step"
- "the Notion API is currently unavailable, please retry later" (without the Partial success block)
- any silent success claim when the documented outputs (page URL, file_upload.id, block ID for `target = page_block`) were not actually returned by Notion
- any variant that redirects the user to a different tool, environment, or "later" instead of completing the retry schedule in `## Error handling` and emitting one of the three terminal states above

If retries on Step 3 (block-append) are exhausted while Steps 1–2 already succeeded, the answer is the **Partial success** block — never a generic "failed" message that drops the captured `file_upload.id` and parent page URL.

## Error handling

**The script (`scripts/upload_to_notion.sh`) owns retry behavior.** When invoked via `## Execution`, you do **not** loop curl yourself — the script does it correctly. Your job is to read the script's exit code + stdout and surface the result faithfully.

- **Pre-flight:** if `notion_api_key` is missing or empty, fail immediately and ask the caller to supply it. Do not invoke the script.
- **Exit code 0 (success):** copy the script's `## Upload succeeded` markdown block to your response. Done.
- **Exit code 2 (partial success):** copy the script's `## Partial success — block-append failed` block **verbatim** to your response — no paraphrase, no collapse, no extra prose. The block contains the `file_upload.id`, parent page URL, verbatim final HTTP response, and a copy-paste curl recipe. Re-running the script with identical args is also safe — the idempotency check will skip the upload if Notion eventually created the block.
- **Exit code 3 (full failure):** copy the script's `## Upload failed` block verbatim. A 404 on Step 3 almost always means the integration is not shared with the target page or database — say so explicitly when surfacing the error.
- **Exit code 4 (bad input / missing dep):** fix the input or surface the missing tool to the caller.
- **Never attempt cleanup on a partial failure** (no DELETE on the file_upload, no page deletion). The Partial-success block is the recovery surface; Notion garbage-collects unused file_uploads after ~1 hour anyway.

**What the script does internally** (so you understand the contract): retries 5xx (500/502/503/504), 429, and network errors up to 7 attempts per step with backoff `2s, 5s, 10s, 30s, 60s, 120s, 180s` and ±25% jitter. Honors `Retry-After` (uses `max(Retry-After, schedule_entry)`). Treats 4xx (excluding 429) as terminal, no retry. Before each Step-3 retry, GETs `/v1/blocks/<target_id>/children` to detect a hidden success and short-circuit if found. Logs `[upload-to-notion] step <N> attempt <K>/<max>: HTTP <status> — waiting <Ns> before retry` to stderr per attempt.

### Manual fallback (only if the script cannot run)

If `scripts/upload_to_notion.sh` is genuinely unavailable (e.g., environment without bash) and you must execute the curl pipeline by hand from `## Reference`, follow these rules — they mirror what the script does:

- Surface the HTTP status and response body verbatim on any non-2xx. Use `curl -sS -D -` (or `-i`) so response headers — including `Retry-After` — are captured.
- On 4xx **excluding 429** (auth, validation, page-not-shared), do **not** retry.
- For 5xx, 429, or network errors: retry the failing step up to **7 attempts** with backoff `2s, 5s, 10s, 30s, 60s, 120s, 180s` and ±25% jitter (e.g. `awk -v s=2 'BEGIN{srand(); printf "%.2f", s*(0.75+rand()*0.5)}'`). Honor `Retry-After`.
- Before each Step-3 retry, GET `/v1/blocks/<target_id>/children?page_size=100` and `jq` for any block whose `<block_type>.file_upload.id` matches your `file_upload.id` — if found, you've hit a hidden success; treat as exit code 0 and do **not** PATCH again.
- If Steps 1–2 succeed but Step 3 retries are exhausted, emit the `## Partial success — block-append failed` block from `## Output format` (verbatim — id, URL, final response, curl recipe).

## Output format

### On full success

Return a short markdown response to the caller:

- The Notion URL of the page or row that was modified
- The `file_upload.id` used
- The new block ID (when `target = page_block`)

Plain markdown, no JSON wrapper.

### On partial success (block-append failed after retries)

If Steps 1–2 succeeded but Step 3 (`PATCH /v1/blocks/<target_id>/children`) failed after the full retry budget, return **exactly** this block — no extra prose before or after, no apology, no environment-blame:

```markdown
## Partial success — block-append failed

- file_upload.id: <uuid>
- parent_page_url: <https://www.notion.so/...>
- failed_step: PATCH /v1/blocks/<target_id>/children
- attempts: 5/5
- final_response: HTTP <status>
```

  <verbatim response body>
  ```

To retry just the block-append (file_upload is valid for ~1 hour from creation):

```bash
curl -sS -X PATCH "https://api.notion.com/v1/blocks/<target_id>/children" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{"children":[{"type":"<block_type>","<block_type>":{"type":"file_upload","file_upload":{"id":"<file_upload_id>"},"caption":[{"type":"text","text":{"content":"<caption>"}}]}}]}'
```

```

Substitute `<block_type>` with `image` / `file` / `pdf` to match the original call. Drop the `caption` key if no caption was supplied. Use the actual `target_id` from the original request (not the parent page URL).

### On full failure (Steps 1 or 2 failed after retries, or 4xx)

Return the verbatim non-2xx response body and the failed step number. No Partial-success block — there is nothing to resume.

## Examples

**1. Chained from `webinar-promo-card`** — append the generated PNG as an image block on a Notion page:

```

notion_api_key: <secret>
source: /tmp/webinar-promo-2026-05.png
target: page_block
target_id: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
block_type: image
caption: Promo card for the May 2026 pricing webinar

```

**2. Direct user invocation** — attach a local PDF to a database row's `Attachments` property:

```

notion_api_key: <secret>
source: /Users/me/Desktop/q2-deck.pdf
target: row_property
target_id: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
property_name: Attachments
display_name: Q2 2026 Pricing Deck

```

**3. Remote URL → page cover** — set a page's cover from a public image URL without downloading:

```

notion_api_key: <secret>
source: https://example.com/cover.png
target: page_cover
target_id: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d

```

## Skill Chaining

Producer skills (`webinar-promo-card`, `clip-podcast`, future image generators) should:

1. Run their own pipeline to produce a local file path (or hand off a URL).
2. Confirm the destination page/row ID with the caller (or resolve a name via the Notion MCP).
3. Invoke this skill with the resulting `source`, `target`, `target_id`, and the `notion_api_key` provided by the orchestrator.
4. Pass the returned URL/IDs back to the caller in their final output.
```
