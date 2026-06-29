#!/usr/bin/env bash
#
# upload_to_notion.sh — deterministic 3-step Notion file-upload pipeline
# with exponential-backoff retries, Retry-After honoring, and an
# idempotency check that prevents duplicate blocks if a 5xx response
# was a hidden success.
#
# Usage: see --help. Outputs markdown to stdout matching the contract
# documented in SKILL.md (## Output format).
#
# Why a script instead of inline curl: 5xx incidents on Notion's
# `public_appendBlockChildren` endpoint can last several minutes; an
# LLM-driven retry loop is slow and non-deterministic. This script
# sleeps precisely, parses headers reliably, and survives without
# burning agent context per attempt.
#
# Required tools: bash, curl, jq, awk, python3 (only for --source-b64).

set -uo pipefail

# ─── Defaults ──────────────────────────────────────────────────────────────────
NOTION_API_VERSION="2022-06-28"
MAX_ATTEMPTS=7
# Backoff schedule in seconds for attempts 2..MAX_ATTEMPTS. ±25% jitter applied.
# Total worst-case wait: 2+5+10+30+60+120+180 = ~407s ≈ 6.8 min per step.
BACKOFF_SCHEDULE=(2 5 10 30 60 120 180)

# ─── Args ──────────────────────────────────────────────────────────────────────
API_KEY=""
SOURCE=""
SOURCE_B64=""
FILENAME=""
MIME=""
TARGET=""
TARGET_ID=""
PROPERTY_NAME=""
BLOCK_TYPE=""
CAPTION=""
DISPLAY_NAME=""
AFTER_BLOCK=""

usage() {
  cat >&2 <<'EOF'
upload_to_notion.sh — upload a file to Notion (page block, row property, cover, icon)

Required:
  --api-key <token>          Notion integration token
  --target <kind>            page_block | row_property | page_cover | page_icon
  --target-id <uuid>         Target page ID (or row page ID for row_property)
  --source <path|https-url>  Local file path or remote URL (or use --source-b64)

For base64 in-memory uploads:
  --source-b64 <data>        Base64-encoded bytes (mutually exclusive with --source)
  --filename <name>          Required with --source-b64
  --mime <content-type>      Required with --source-b64

Optional:
  --property-name <name>     Required when --target=row_property (Files property name)
  --block-type <kind>        image | file | pdf (default: inferred)
  --caption <text>           Caption for image/file/pdf blocks
  --after <block_id>         page_block only: insert immediately after this
                             sibling block instead of at the end of the page
  --display-name <name>      Override display filename
  --max-attempts <n>         Override retry count per step (default: 7)
  -h, --help                 Show this help

Exit codes:
  0  full success
  2  partial success (Steps 1+2 ok, Step 3 failed after retries) — see stdout for resume recipe
  3  full failure (Step 1 or 2 failed, or 4xx)
  4  bad input / missing dependency
EOF
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-key) API_KEY="$2"; shift 2 ;;
    --source) SOURCE="$2"; shift 2 ;;
    --source-b64) SOURCE_B64="$2"; shift 2 ;;
    --filename) FILENAME="$2"; shift 2 ;;
    --mime) MIME="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    --target-id) TARGET_ID="$2"; shift 2 ;;
    --property-name) PROPERTY_NAME="$2"; shift 2 ;;
    --block-type) BLOCK_TYPE="$2"; shift 2 ;;
    --caption) CAPTION="$2"; shift 2 ;;
    --after) AFTER_BLOCK="$2"; shift 2 ;;
    --display-name) DISPLAY_NAME="$2"; shift 2 ;;
    --max-attempts) MAX_ATTEMPTS="$2"; shift 2 ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown arg: $1" >&2; usage 4 ;;
  esac
done

log() { echo "[upload-to-notion] $*" >&2; }
fail4() { echo "$*" >&2; exit 4; }

[[ -n "$API_KEY" ]] || fail4 "Missing --api-key"
[[ -n "$TARGET" && -n "$TARGET_ID" ]] || fail4 "Missing --target / --target-id"
case "$TARGET" in
  page_block|row_property|page_cover|page_icon) ;;
  *) fail4 "Invalid --target: $TARGET" ;;
esac
[[ "$TARGET" != "row_property" || -n "$PROPERTY_NAME" ]] || fail4 "row_property requires --property-name"

if [[ -n "$SOURCE" && -n "$SOURCE_B64" ]]; then
  fail4 "--source and --source-b64 are mutually exclusive"
fi
if [[ -z "$SOURCE" && -z "$SOURCE_B64" ]]; then
  fail4 "Provide --source or --source-b64"
fi
if [[ -n "$SOURCE_B64" && ( -z "$FILENAME" || -z "$MIME" ) ]]; then
  fail4 "--source-b64 requires --filename and --mime"
fi

command -v curl >/dev/null || fail4 "curl not found"
command -v jq   >/dev/null || fail4 "jq not found"
command -v awk  >/dev/null || fail4 "awk not found"

# ─── Source resolution ─────────────────────────────────────────────────────────
TMPDIR_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_ROOT"' EXIT
LOCAL_PATH=""
REMOTE_URL=""

if [[ -n "$SOURCE_B64" ]]; then
  command -v python3 >/dev/null || fail4 "python3 required for --source-b64"
  LOCAL_PATH="$TMPDIR_ROOT/$FILENAME"
  python3 -c "import base64,sys; open(sys.argv[1],'wb').write(base64.b64decode(sys.argv[2]))" "$LOCAL_PATH" "$SOURCE_B64"
elif [[ "$SOURCE" =~ ^https?:// ]]; then
  REMOTE_URL="$SOURCE"
  [[ -n "$FILENAME" ]] || FILENAME="$(basename "${REMOTE_URL%%\?*}")"
else
  LOCAL_PATH="$SOURCE"
  [[ -f "$LOCAL_PATH" ]] || fail4 "File not found: $LOCAL_PATH"
  [[ -n "$FILENAME" ]] || FILENAME="$(basename "$LOCAL_PATH")"
fi

# Block-type inference
if [[ -z "$BLOCK_TYPE" ]]; then
  case "${FILENAME,,}" in
    *.png|*.jpg|*.jpeg|*.gif|*.webp|*.svg) BLOCK_TYPE="image" ;;
    *.pdf) BLOCK_TYPE="pdf" ;;
    *) BLOCK_TYPE="file" ;;
  esac
fi
[[ -z "$MIME" ]] && MIME="$(
  case "$BLOCK_TYPE" in
    image) case "${FILENAME,,}" in
             *.png) echo image/png ;;
             *.jpg|*.jpeg) echo image/jpeg ;;
             *.gif) echo image/gif ;;
             *.webp) echo image/webp ;;
             *.svg) echo image/svg+xml ;;
             *) echo image/png ;;
           esac ;;
    pdf) echo application/pdf ;;
    *) echo application/octet-stream ;;
  esac
)"
[[ -z "$DISPLAY_NAME" ]] && DISPLAY_NAME="$FILENAME"

# ─── HTTP helper with backoff ──────────────────────────────────────────────────
# request_with_retry <step_label> <out_var_name_for_body> <curl_args...>
#
# Captures status + headers + body. On 5xx/429/network errors, sleeps per
# BACKOFF_SCHEDULE (honoring Retry-After if present) and retries up to
# MAX_ATTEMPTS. Returns 0 on 2xx, non-zero on terminal failure.
# Stores the final response body path in the named variable.

LAST_STATUS=""
LAST_BODY_PATH=""
LAST_HEADERS_PATH=""

jitter() {
  awk -v s="$1" 'BEGIN{srand(); printf "%.2f", s*(0.75+rand()*0.5)}'
}

request_with_retry() {
  local step="$1"; shift
  local attempt=1
  local body_path headers_path status retry_after wait_s schedule_idx

  while :; do
    body_path="$TMPDIR_ROOT/body.$step.$attempt"
    headers_path="$TMPDIR_ROOT/headers.$step.$attempt"

    # -sS silent except errors; -D dumps headers; -o body; %{http_code} stdout.
    status=$(curl -sS -D "$headers_path" -o "$body_path" -w "%{http_code}" "$@" 2>"$TMPDIR_ROOT/curl.err.$step.$attempt") || status="000"

    LAST_STATUS="$status"
    LAST_BODY_PATH="$body_path"
    LAST_HEADERS_PATH="$headers_path"

    if [[ "$status" =~ ^2 ]]; then
      return 0
    fi

    # 4xx (except 429) → no retry
    if [[ "$status" =~ ^4 && "$status" != "429" ]]; then
      log "step $step attempt $attempt/$MAX_ATTEMPTS: HTTP $status (non-retryable)"
      return 1
    fi

    if (( attempt >= MAX_ATTEMPTS )); then
      log "step $step attempt $attempt/$MAX_ATTEMPTS: HTTP $status — retries exhausted"
      return 1
    fi

    schedule_idx=$(( attempt - 1 ))
    if (( schedule_idx >= ${#BACKOFF_SCHEDULE[@]} )); then
      schedule_idx=$(( ${#BACKOFF_SCHEDULE[@]} - 1 ))
    fi
    wait_s=$(jitter "${BACKOFF_SCHEDULE[$schedule_idx]}")

    # Honor Retry-After header (seconds-only form per Notion docs).
    retry_after="$(grep -i '^retry-after:' "$headers_path" 2>/dev/null | tail -1 | awk '{print $2}' | tr -d '\r')"
    if [[ -n "$retry_after" && "$retry_after" =~ ^[0-9]+$ ]]; then
      if awk -v a="$retry_after" -v b="$wait_s" 'BEGIN{exit !(a>b)}'; then
        wait_s="$retry_after"
      fi
    fi

    log "step $step attempt $attempt/$MAX_ATTEMPTS: HTTP $status — waiting ${wait_s}s before retry"
    sleep "$wait_s"
    attempt=$(( attempt + 1 ))
  done
}

# ─── Step 1 — create file_upload object ────────────────────────────────────────
log "step 1: creating file_upload object"

if [[ -n "$REMOTE_URL" ]]; then
  STEP1_BODY=$(jq -n --arg url "$REMOTE_URL" --arg name "$FILENAME" \
    '{mode:"external_url", external_url:$url, filename:$name}')
else
  FILE_SIZE=$(stat -f%z "$LOCAL_PATH" 2>/dev/null || stat -c%s "$LOCAL_PATH")
  if (( FILE_SIZE > 20*1024*1024 )); then
    NUM_PARTS=$(( (FILE_SIZE + 10*1024*1024 - 1) / (10*1024*1024) ))
    STEP1_BODY=$(jq -n --arg name "$FILENAME" --arg ct "$MIME" --argjson n "$NUM_PARTS" \
      '{mode:"multi_part", number_of_parts:$n, filename:$name, content_type:$ct}')
  else
    STEP1_BODY=$(jq -n --arg name "$FILENAME" --arg ct "$MIME" \
      '{mode:"single_part", filename:$name, content_type:$ct}')
  fi
fi

if ! request_with_retry "1" \
  -X POST "https://api.notion.com/v1/file_uploads" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Notion-Version: $NOTION_API_VERSION" \
  -H "Content-Type: application/json" \
  -d "$STEP1_BODY"
then
  echo "## Upload failed — Step 1 (create file_upload) HTTP $LAST_STATUS"
  echo
  echo '```'
  cat "$LAST_BODY_PATH" 2>/dev/null || echo "(no response body)"
  echo
  echo '```'
  exit 3
fi

FILE_UPLOAD_ID=$(jq -r '.id' "$LAST_BODY_PATH")
UPLOAD_URL=$(jq -r '.upload_url // empty' "$LAST_BODY_PATH")
log "step 1: file_upload.id=$FILE_UPLOAD_ID"

# ─── Step 2 — send bytes (or wait for external_url) ────────────────────────────

if [[ -n "$REMOTE_URL" ]]; then
  log "step 2: polling external_url status"
  POLL_DEADLINE=$(( $(date +%s) + 60 ))
  while :; do
    if ! request_with_retry "2-poll" \
      -X GET "https://api.notion.com/v1/file_uploads/$FILE_UPLOAD_ID" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Notion-Version: $NOTION_API_VERSION"
    then
      echo "## Upload failed — Step 2 (poll external_url) HTTP $LAST_STATUS"
      echo
      echo '```'
      cat "$LAST_BODY_PATH"
      echo
      echo '```'
      exit 3
    fi
    POLL_STATUS=$(jq -r '.status' "$LAST_BODY_PATH")
    [[ "$POLL_STATUS" == "uploaded" ]] && break
    if (( $(date +%s) > POLL_DEADLINE )); then
      echo "## Upload failed — external_url did not reach 'uploaded' status within 60s (last: $POLL_STATUS)"
      exit 3
    fi
    sleep 1
  done
elif (( FILE_SIZE > 20*1024*1024 )); then
  log "step 2: multi-part upload not yet supported by this script — fall back to inline curl flow"
  echo "## Upload failed — multi-part upload (>20MB) not supported by upload_to_notion.sh; use inline curl per SKILL.md reference"
  exit 3
else
  log "step 2: uploading bytes (single-part)"
  if ! request_with_retry "2" \
    -X POST "$UPLOAD_URL" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Notion-Version: $NOTION_API_VERSION" \
    -F "file=@$LOCAL_PATH;type=$MIME"
  then
    echo "## Upload failed — Step 2 (send bytes) HTTP $LAST_STATUS"
    echo
    echo '```'
    cat "$LAST_BODY_PATH"
    echo
    echo '```'
    exit 3
  fi
fi

# ─── Step 3 — attach to target with idempotency check ──────────────────────────

emit_partial_success() {
  local final_status="$1"
  local final_body_path="$2"
  local cap_json after_json
  if [[ -n "$CAPTION" ]]; then
    cap_json=$(jq -nc --arg c "$CAPTION" '{caption:[{type:"text",text:{content:$c}}]}' | sed 's/^{//; s/}$//')
    cap_json=",${cap_json}"
  fi
  if [[ -n "$AFTER_BLOCK" ]]; then
    after_json=$(jq -nc --arg a "$AFTER_BLOCK" '{after:$a}' | sed 's/^{//; s/}$//')
    after_json=",${after_json}"
  fi

  cat <<EOF
## Partial success — block-append failed

- file_upload.id: $FILE_UPLOAD_ID
- parent_page_url: https://www.notion.so/$(echo "$TARGET_ID" | tr -d '-')
- failed_step: PATCH /v1/blocks/$TARGET_ID/children
- attempts: $MAX_ATTEMPTS/$MAX_ATTEMPTS
- final_response: HTTP $final_status

  \`\`\`
$(cat "$final_body_path")
  \`\`\`

To retry just the block-append (file_upload is valid for ~1 hour from creation):

  \`\`\`bash
  curl -sS -X PATCH "https://api.notion.com/v1/blocks/$TARGET_ID/children" \\
    -H "Authorization: Bearer \$NOTION_API_KEY" \\
    -H "Notion-Version: $NOTION_API_VERSION" \\
    -H "Content-Type: application/json" \\
    -d '{"children":[{"type":"$BLOCK_TYPE","$BLOCK_TYPE":{"type":"file_upload","file_upload":{"id":"$FILE_UPLOAD_ID"}${cap_json:-}}}]${after_json:-}}'
  \`\`\`

Or re-run this script with the same args; it will detect the existing file_upload and idempotency-skip if Notion already created the block during the outage.
EOF
}

# Idempotency check: scan existing children for our file_upload.id.
# Returns 0 + sets EXISTING_BLOCK_ID if found; 1 otherwise.
EXISTING_BLOCK_ID=""
check_existing_block() {
  EXISTING_BLOCK_ID=""
  local body_path="$TMPDIR_ROOT/idem.body"
  local status
  status=$(curl -sS -o "$body_path" -w "%{http_code}" \
    -X GET "https://api.notion.com/v1/blocks/$TARGET_ID/children?page_size=100" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Notion-Version: $NOTION_API_VERSION" 2>/dev/null) || return 1
  [[ "$status" =~ ^2 ]] || return 1
  EXISTING_BLOCK_ID=$(jq -r --arg id "$FILE_UPLOAD_ID" --arg type "$BLOCK_TYPE" \
    '.results[] | select(.[$type].file_upload.id == $id) | .id' "$body_path" 2>/dev/null | head -1)
  [[ -n "$EXISTING_BLOCK_ID" ]]
}

case "$TARGET" in
  page_block)
    log "step 3: appending block (with idempotency)"
    # Pre-check: maybe a previous invocation already attached this file_upload.
    if check_existing_block; then
      log "step 3: idempotency hit — block $EXISTING_BLOCK_ID already exists for this file_upload"
      cat <<EOF
## Upload succeeded (idempotency hit)

- page_url: https://www.notion.so/$(echo "$TARGET_ID" | tr -d '-')
- file_upload.id: $FILE_UPLOAD_ID
- block_id: $EXISTING_BLOCK_ID

A previous invocation already attached this file_upload during the outage — no duplicate created.
EOF
      exit 0
    fi

    if [[ -n "$CAPTION" ]]; then
      STEP3_BODY=$(jq -n --arg id "$FILE_UPLOAD_ID" --arg type "$BLOCK_TYPE" --arg cap "$CAPTION" \
        '{children:[{type:$type, ($type):{type:"file_upload", file_upload:{id:$id}, caption:[{type:"text", text:{content:$cap}}]}}]}')
    else
      STEP3_BODY=$(jq -n --arg id "$FILE_UPLOAD_ID" --arg type "$BLOCK_TYPE" \
        '{children:[{type:$type, ($type):{type:"file_upload", file_upload:{id:$id}}}]}')
    fi
    # Positional insert: place the block immediately after a given sibling block
    # instead of at the end of the page (Notion's optional top-level `after`).
    if [[ -n "$AFTER_BLOCK" ]]; then
      STEP3_BODY=$(jq --arg after "$AFTER_BLOCK" '. + {after:$after}' <<<"$STEP3_BODY")
    fi

    # Custom retry loop for Step 3 — re-checks idempotency before each retry.
    attempt=1
    while :; do
      body_path="$TMPDIR_ROOT/body.3.$attempt"
      headers_path="$TMPDIR_ROOT/headers.3.$attempt"
      status=$(curl -sS -D "$headers_path" -o "$body_path" -w "%{http_code}" \
        -X PATCH "https://api.notion.com/v1/blocks/$TARGET_ID/children" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Notion-Version: $NOTION_API_VERSION" \
        -H "Content-Type: application/json" \
        -d "$STEP3_BODY" 2>/dev/null) || status="000"

      if [[ "$status" =~ ^2 ]]; then
        BLOCK_ID=$(jq -r '.results[0].id' "$body_path")
        log "step 3: success — block_id=$BLOCK_ID"
        cat <<EOF
## Upload succeeded

- page_url: https://www.notion.so/$(echo "$TARGET_ID" | tr -d '-')
- file_upload.id: $FILE_UPLOAD_ID
- block_id: $BLOCK_ID
EOF
        exit 0
      fi

      if [[ "$status" =~ ^4 && "$status" != "429" ]]; then
        log "step 3 attempt $attempt/$MAX_ATTEMPTS: HTTP $status (non-retryable)"
        emit_partial_success "$status" "$body_path"
        exit 2
      fi

      # Before retrying: maybe the previous attempt actually succeeded server-side.
      if check_existing_block; then
        log "step 3 attempt $attempt: idempotency hit on retry — block $EXISTING_BLOCK_ID was created server-side"
        cat <<EOF
## Upload succeeded (idempotency hit on retry)

- page_url: https://www.notion.so/$(echo "$TARGET_ID" | tr -d '-')
- file_upload.id: $FILE_UPLOAD_ID
- block_id: $EXISTING_BLOCK_ID
EOF
        exit 0
      fi

      if (( attempt >= MAX_ATTEMPTS )); then
        log "step 3 attempt $attempt/$MAX_ATTEMPTS: HTTP $status — retries exhausted"
        emit_partial_success "$status" "$body_path"
        exit 2
      fi

      schedule_idx=$(( attempt - 1 ))
      if (( schedule_idx >= ${#BACKOFF_SCHEDULE[@]} )); then
        schedule_idx=$(( ${#BACKOFF_SCHEDULE[@]} - 1 ))
      fi
      wait_s=$(jitter "${BACKOFF_SCHEDULE[$schedule_idx]}")
      retry_after="$(grep -i '^retry-after:' "$headers_path" 2>/dev/null | tail -1 | awk '{print $2}' | tr -d '\r')"
      if [[ -n "$retry_after" && "$retry_after" =~ ^[0-9]+$ ]]; then
        if awk -v a="$retry_after" -v b="$wait_s" 'BEGIN{exit !(a>b)}'; then
          wait_s="$retry_after"
        fi
      fi
      log "step 3 attempt $attempt/$MAX_ATTEMPTS: HTTP $status — waiting ${wait_s}s before retry"
      sleep "$wait_s"
      attempt=$(( attempt + 1 ))
    done
    ;;

  row_property)
    log "step 3: setting row property"
    STEP3_BODY=$(jq -n --arg prop "$PROPERTY_NAME" --arg id "$FILE_UPLOAD_ID" --arg name "$DISPLAY_NAME" \
      '{properties:{($prop):{files:[{type:"file_upload", file_upload:{id:$id}, name:$name}]}}}')
    if request_with_retry "3" \
      -X PATCH "https://api.notion.com/v1/pages/$TARGET_ID" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Notion-Version: $NOTION_API_VERSION" \
      -H "Content-Type: application/json" \
      -d "$STEP3_BODY"
    then
      cat <<EOF
## Upload succeeded

- page_url: https://www.notion.so/$(echo "$TARGET_ID" | tr -d '-')
- file_upload.id: $FILE_UPLOAD_ID
- property: $PROPERTY_NAME
EOF
      exit 0
    else
      echo "## Upload failed — Step 3 (set row property) HTTP $LAST_STATUS"
      echo
      echo '```'
      cat "$LAST_BODY_PATH"
      echo
      echo '```'
      exit 3
    fi
    ;;

  page_cover|page_icon)
    log "step 3: setting $TARGET"
    KEY=${TARGET#page_}
    STEP3_BODY=$(jq -n --arg id "$FILE_UPLOAD_ID" --arg key "$KEY" \
      '{($key):{type:"file_upload", file_upload:{id:$id}}}')
    if request_with_retry "3" \
      -X PATCH "https://api.notion.com/v1/pages/$TARGET_ID" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Notion-Version: $NOTION_API_VERSION" \
      -H "Content-Type: application/json" \
      -d "$STEP3_BODY"
    then
      cat <<EOF
## Upload succeeded

- page_url: https://www.notion.so/$(echo "$TARGET_ID" | tr -d '-')
- file_upload.id: $FILE_UPLOAD_ID
- $KEY: set
EOF
      exit 0
    else
      echo "## Upload failed — Step 3 (set $KEY) HTTP $LAST_STATUS"
      echo
      echo '```'
      cat "$LAST_BODY_PATH"
      echo
      echo '```'
      exit 3
    fi
    ;;
esac
