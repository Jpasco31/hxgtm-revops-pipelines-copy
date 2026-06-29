#!/usr/bin/env bash
#
# download_from_notion.sh — pull files attached to a Notion page to local disk.
#
# Two modes:
#   1. URL mode (--url ... --output ...)
#         No auth. Caller passes a pre-signed Notion S3 URL (or any HTTPS URL)
#         and the absolute path to write to. Signed URLs expire ~1 hour after
#         the originating Notion API call — caller is responsible for freshness.
#
#   2. Page-property mode (--api-key ... --page-id ... --property ... --output-dir ...)
#         The script GETs /v1/pages/<id> at invocation time, reads the named
#         Files property, and downloads every file in it. Re-fetching at run
#         time means signed-URL TTL is never an issue.
#
# Outputs (stdout): markdown wrapper with a JSON manifest. One entry per file:
#   { local_path, filename, mime, bytes, source_url, source_property?, source_page_id?, url_expiry? }
#
# Exit codes:
#   0  full success — every requested file downloaded and validated
#   2  partial success — at least one downloaded, at least one failed
#   3  full failure — auth, 404, network exhausted, MIME/size violation
#   4  bad input / missing dependency
#
# Required tools: bash, curl, jq.

set -uo pipefail

NOTION_API_VERSION="2022-06-28"
MAX_ATTEMPTS=7
BACKOFF_SCHEDULE=(2 5 10 30 60 120 180)

API_KEY=""
PAGE_ID=""
PROPERTY_NAME=""
URL=""
OUTPUT=""
OUTPUT_DIR=""
MIME_ALLOW=""
MAX_BYTES=""
OVERWRITE="1"

usage() {
  cat >&2 <<'EOF'
download_from_notion.sh — download files from a Notion page (Files property
or a pre-signed URL) to local disk with deterministic retries.

URL mode (no auth, caller-resolved pre-signed URL):
  --url <signed-url>         Notion S3 signed URL or any HTTPS URL
  --output <abs-path>        Absolute local path to write to

Page-property mode (script re-fetches the page so TTL is never an issue):
  --api-key <token>          Notion integration token
  --page-id <uuid>           Notion page ID (with or without dashes)
  --property <name>          Exact name of the Files property to pull from
  --output-dir <abs-dir>     Absolute directory to write files into

Optional:
  --mime-allow <list>        Comma-separated MIME whitelist (e.g. "image/png,image/jpeg").
                             Files outside the list cause exit 3.
  --max-bytes <n>            Per-file byte ceiling. Aborts and exits 3 if exceeded.
  --max-attempts <n>         Override retry count (default: 7)
  --no-overwrite             Fail if a target file already exists
  -h, --help                 Show this help

Exit codes:
  0  full success
  2  partial success (some downloaded, some failed)
  3  full failure
  4  bad input / missing dependency
EOF
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-key) API_KEY="$2"; shift 2 ;;
    --page-id) PAGE_ID="$2"; shift 2 ;;
    --property) PROPERTY_NAME="$2"; shift 2 ;;
    --url) URL="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --mime-allow) MIME_ALLOW="$2"; shift 2 ;;
    --max-bytes) MAX_BYTES="$2"; shift 2 ;;
    --max-attempts) MAX_ATTEMPTS="$2"; shift 2 ;;
    --no-overwrite) OVERWRITE="0"; shift ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown arg: $1" >&2; usage 4 ;;
  esac
done

log() { echo "[download-from-notion] $*" >&2; }
fail4() { echo "$*" >&2; exit 4; }

command -v curl >/dev/null || fail4 "curl not found"
command -v jq   >/dev/null || fail4 "jq not found"
command -v awk  >/dev/null || fail4 "awk not found"

# Mode resolution
MODE=""
if [[ -n "$URL" ]]; then
  MODE="url"
  [[ -n "$OUTPUT" ]] || fail4 "--url requires --output"
  [[ "$OUTPUT" = /* ]] || fail4 "--output must be an absolute path"
  if [[ -n "$API_KEY$PAGE_ID$PROPERTY_NAME$OUTPUT_DIR" ]]; then
    fail4 "--url is mutually exclusive with page-property mode flags"
  fi
elif [[ -n "$PAGE_ID$PROPERTY_NAME$OUTPUT_DIR$API_KEY" ]]; then
  MODE="property"
  [[ -n "$API_KEY"      ]] || fail4 "page-property mode requires --api-key"
  [[ -n "$PAGE_ID"      ]] || fail4 "page-property mode requires --page-id"
  [[ -n "$PROPERTY_NAME" ]] || fail4 "page-property mode requires --property"
  [[ -n "$OUTPUT_DIR"   ]] || fail4 "page-property mode requires --output-dir"
  [[ "$OUTPUT_DIR" = /* ]] || fail4 "--output-dir must be an absolute path"
else
  fail4 "Provide either (--url + --output) or (--api-key + --page-id + --property + --output-dir)"
fi

# Validate MAX_BYTES if set
if [[ -n "$MAX_BYTES" ]]; then
  [[ "$MAX_BYTES" =~ ^[0-9]+$ ]] || fail4 "--max-bytes must be a positive integer"
fi

TMPDIR_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

LAST_STATUS=""
LAST_BODY_PATH=""
LAST_HEADERS_PATH=""

jitter() {
  awk -v s="$1" 'BEGIN{srand(); printf "%.2f", s*(0.75+rand()*0.5)}'
}

# request_with_retry <step_label> <curl_args...>
# Captures status + headers + body. Retries 5xx / 429 / network errors per
# BACKOFF_SCHEDULE (honoring Retry-After). Returns 0 on 2xx, 1 otherwise.
request_with_retry() {
  local step="$1"; shift
  local attempt=1
  local body_path headers_path status retry_after wait_s schedule_idx

  while :; do
    body_path="$TMPDIR_ROOT/body.$step.$attempt"
    headers_path="$TMPDIR_ROOT/headers.$step.$attempt"

    status=$(curl -sS -D "$headers_path" -o "$body_path" -w "%{http_code}" "$@" 2>"$TMPDIR_ROOT/curl.err.$step.$attempt") || status="000"

    LAST_STATUS="$status"
    LAST_BODY_PATH="$body_path"
    LAST_HEADERS_PATH="$headers_path"

    if [[ "$status" =~ ^2 ]]; then
      return 0
    fi

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

# Strip path traversal and leading dots from filenames pulled from Notion.
sanitize_filename() {
  local name="$1"
  name="${name//\//_}"
  name="${name//$'\\'/_}"
  name="${name//$'\0'/}"
  name="${name#.}"
  name="${name#.}"
  [[ -z "$name" ]] && name="download.bin"
  echo "$name"
}

# Extract extension from a MIME type for fallback naming.
ext_from_mime() {
  case "$1" in
    image/png) echo "png" ;;
    image/jpeg) echo "jpg" ;;
    image/gif) echo "gif" ;;
    image/webp) echo "webp" ;;
    image/svg+xml) echo "svg" ;;
    application/pdf) echo "pdf" ;;
    text/plain) echo "txt" ;;
    *) echo "bin" ;;
  esac
}

# Pull a filename out of a Content-Disposition header (RFC 5987 not supported).
filename_from_disposition() {
  local hpath="$1"
  grep -i '^content-disposition:' "$hpath" 2>/dev/null | tail -1 \
    | sed -E 's/.*filename="?([^";]+)"?.*/\1/' | tr -d '\r' | head -c 200
}

# Pull a Content-Type out of headers.
mime_from_headers() {
  local hpath="$1"
  grep -i '^content-type:' "$hpath" 2>/dev/null | tail -1 \
    | sed -E 's/^[Cc]ontent-[Tt]ype:[[:space:]]*//; s/;.*$//' | tr -d '\r '
}

mime_is_allowed() {
  local mime="$1"
  [[ -z "$MIME_ALLOW" ]] && return 0
  local IFS=','
  for allowed in $MIME_ALLOW; do
    [[ "$mime" == "$allowed" ]] && return 0
  done
  return 1
}

# Stream a URL into a destination path with retries and atomic rename.
# Sets MANIFEST_BYTES, MANIFEST_MIME on success. Echoes verbatim error to
# stderr and returns 1 on failure.
MANIFEST_BYTES=""
MANIFEST_MIME=""
download_one_url() {
  local source_url="$1"
  local dest_path="$2"
  local label="$3"
  local attempt=1
  local tmp_path status retry_after wait_s schedule_idx headers_path

  if [[ "$OVERWRITE" == "0" && -e "$dest_path" ]]; then
    echo "Refusing to overwrite existing file: $dest_path" >&2
    return 1
  fi

  mkdir -p "$(dirname "$dest_path")"

  while :; do
    tmp_path="$TMPDIR_ROOT/dl.$label.$attempt"
    headers_path="$TMPDIR_ROOT/dlheaders.$label.$attempt"

    local curl_args=(-sS -L -D "$headers_path" -o "$tmp_path" -w "%{http_code}")
    if [[ -n "$MAX_BYTES" ]]; then
      curl_args+=(--max-filesize "$MAX_BYTES")
    fi
    curl_args+=("$source_url")

    status=$(curl "${curl_args[@]}" 2>"$TMPDIR_ROOT/dl.err.$label.$attempt") || status="000"

    if [[ "$status" =~ ^2 ]]; then
      MANIFEST_MIME="$(mime_from_headers "$headers_path")"
      [[ -z "$MANIFEST_MIME" ]] && MANIFEST_MIME="application/octet-stream"

      if ! mime_is_allowed "$MANIFEST_MIME"; then
        echo "MIME not allowed for $label: got '$MANIFEST_MIME', allow-list='$MIME_ALLOW'" >&2
        rm -f "$tmp_path"
        return 1
      fi

      MANIFEST_BYTES="$(wc -c <"$tmp_path" | tr -d ' ')"

      if [[ -n "$MAX_BYTES" ]] && (( MANIFEST_BYTES > MAX_BYTES )); then
        echo "Exceeded --max-bytes for $label: ${MANIFEST_BYTES} > ${MAX_BYTES}" >&2
        rm -f "$tmp_path"
        return 1
      fi

      mv -f "$tmp_path" "$dest_path"
      log "downloaded $dest_path (${MANIFEST_BYTES} bytes, $MANIFEST_MIME)"
      return 0
    fi

    if [[ "$status" =~ ^4 && "$status" != "429" ]]; then
      log "$label attempt $attempt/$MAX_ATTEMPTS: HTTP $status (non-retryable)"
      {
        echo "Download failed — HTTP $status from $source_url"
        echo "--- response headers ---"
        cat "$headers_path" 2>/dev/null
        echo "--- response body (first 4 KB) ---"
        head -c 4096 "$tmp_path" 2>/dev/null
        echo
      } >&2
      rm -f "$tmp_path"
      return 1
    fi

    if (( attempt >= MAX_ATTEMPTS )); then
      log "$label attempt $attempt/$MAX_ATTEMPTS: HTTP $status — retries exhausted"
      {
        echo "Download failed — retries exhausted ($MAX_ATTEMPTS attempts) on $source_url"
        echo "Last HTTP status: $status"
        echo "--- response headers ---"
        cat "$headers_path" 2>/dev/null
        echo "--- response body (first 4 KB) ---"
        head -c 4096 "$tmp_path" 2>/dev/null
        echo
      } >&2
      rm -f "$tmp_path"
      return 1
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

    log "$label attempt $attempt/$MAX_ATTEMPTS: HTTP $status — waiting ${wait_s}s before retry"
    rm -f "$tmp_path"
    sleep "$wait_s"
    attempt=$(( attempt + 1 ))
  done
}

# ─── URL mode ─────────────────────────────────────────────────────────────────
if [[ "$MODE" == "url" ]]; then
  if download_one_url "$URL" "$OUTPUT" "url0"; then
    FILENAME="$(basename "$OUTPUT")"
    MANIFEST_JSON=$(jq -n \
      --arg path "$OUTPUT" \
      --arg name "$FILENAME" \
      --arg mime "$MANIFEST_MIME" \
      --argjson bytes "$MANIFEST_BYTES" \
      --arg url "$URL" \
      '{downloads:[{local_path:$path, filename:$name, mime:$mime, bytes:$bytes, source_url:$url}]}')
    cat <<EOF
## Download succeeded

- count: 1
- file: $OUTPUT

\`\`\`json
$MANIFEST_JSON
\`\`\`
EOF
    exit 0
  else
    cat <<EOF
## Download failed

- source: $URL
- target: $OUTPUT

See stderr for the verbatim HTTP response.
EOF
    exit 3
  fi
fi

# ─── Page-property mode ───────────────────────────────────────────────────────
log "fetching page $PAGE_ID"

if ! request_with_retry "page-fetch" \
  -X GET "https://api.notion.com/v1/pages/$PAGE_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Notion-Version: $NOTION_API_VERSION"
then
  cat <<EOF
## Page fetch failed — HTTP $LAST_STATUS

\`\`\`
$(cat "$LAST_BODY_PATH" 2>/dev/null)
\`\`\`
EOF
  exit 3
fi

# Validate that the property exists and is a files type.
PROP_TYPE=$(jq -r --arg p "$PROPERTY_NAME" '.properties[$p].type // "missing"' "$LAST_BODY_PATH")
if [[ "$PROP_TYPE" == "missing" ]]; then
  echo "Property '$PROPERTY_NAME' not found on page $PAGE_ID. Available properties: $(jq -r '.properties | keys | join(", ")' "$LAST_BODY_PATH")" >&2
  exit 3
fi
if [[ "$PROP_TYPE" != "files" ]]; then
  echo "Property '$PROPERTY_NAME' is of type '$PROP_TYPE', not 'files'. download-from-notion only supports Files properties." >&2
  exit 3
fi

FILE_COUNT=$(jq --arg p "$PROPERTY_NAME" '.properties[$p].files | length' "$LAST_BODY_PATH")
if (( FILE_COUNT == 0 )); then
  echo "Property '$PROPERTY_NAME' is empty on page $PAGE_ID — nothing to download." >&2
  exit 3
fi

mkdir -p "$OUTPUT_DIR"

# Build a JSON array of {url, name, type, expiry} for each file.
FILES_JSON=$(jq -c --arg p "$PROPERTY_NAME" '
  .properties[$p].files
  | map({
      url:    (.file.url // .external.url // ""),
      name:   (.name // ""),
      type:   (.type),
      expiry: (.file.expiry_time // null)
    })
' "$LAST_BODY_PATH")

DOWNLOAD_ENTRIES=()
FAILED_ENTRIES=()
INDEX=0

while IFS= read -r FILE_ROW; do
  INDEX=$(( INDEX + 1 ))
  FILE_URL=$(echo "$FILE_ROW" | jq -r '.url')
  FILE_NAME=$(echo "$FILE_ROW" | jq -r '.name')
  FILE_TYPE=$(echo "$FILE_ROW" | jq -r '.type')
  FILE_EXPIRY=$(echo "$FILE_ROW" | jq -r '.expiry // empty')

  if [[ -z "$FILE_URL" || "$FILE_URL" == "null" ]]; then
    log "file $INDEX has no URL — skipping"
    FAILED_ENTRIES+=("$(jq -nc --arg n "$FILE_NAME" '{name:$n, error:"no URL on file object"}')")
    continue
  fi

  if [[ -z "$FILE_NAME" || "$FILE_NAME" == "null" ]]; then
    URL_BASENAME="$(basename "${FILE_URL%%\?*}")"
    FILE_NAME="${URL_BASENAME:-file-$INDEX.bin}"
  fi
  SAFE_NAME="$(sanitize_filename "$FILE_NAME")"
  DEST_PATH="$OUTPUT_DIR/$SAFE_NAME"

  if download_one_url "$FILE_URL" "$DEST_PATH" "file-$INDEX"; then
    DOWNLOAD_ENTRIES+=("$(jq -nc \
      --arg path "$DEST_PATH" \
      --arg name "$SAFE_NAME" \
      --arg mime "$MANIFEST_MIME" \
      --argjson bytes "$MANIFEST_BYTES" \
      --arg url "$FILE_URL" \
      --arg prop "$PROPERTY_NAME" \
      --arg page "$PAGE_ID" \
      --arg expiry "$FILE_EXPIRY" \
      --arg type "$FILE_TYPE" \
      '{
        local_path:$path,
        filename:$name,
        mime:$mime,
        bytes:$bytes,
        source_url:$url,
        source_property:$prop,
        source_page_id:$page,
        source_type:$type,
        url_expiry:(if $expiry=="" then null else $expiry end)
      }')")
  else
    FAILED_ENTRIES+=("$(jq -nc --arg n "$SAFE_NAME" --arg u "$FILE_URL" '{name:$n, url:$u, error:"download failed — see stderr"}')")
  fi
done < <(echo "$FILES_JSON" | jq -c '.[]')

OK_COUNT="${#DOWNLOAD_ENTRIES[@]}"
FAIL_COUNT="${#FAILED_ENTRIES[@]}"

if (( OK_COUNT == 0 )); then
  echo "All $FILE_COUNT downloads failed from property '$PROPERTY_NAME' on page $PAGE_ID." >&2
  exit 3
fi

MANIFEST_DOWNLOADS=$(printf '%s\n' "${DOWNLOAD_ENTRIES[@]}" | jq -s '.')
if (( FAIL_COUNT > 0 )); then
  MANIFEST_FAILURES=$(printf '%s\n' "${FAILED_ENTRIES[@]}" | jq -s '.')
  MANIFEST_JSON=$(jq -n --argjson d "$MANIFEST_DOWNLOADS" --argjson f "$MANIFEST_FAILURES" '{downloads:$d, failures:$f}')
else
  MANIFEST_JSON=$(jq -n --argjson d "$MANIFEST_DOWNLOADS" '{downloads:$d}')
fi

if (( FAIL_COUNT == 0 )); then
  cat <<EOF
## Download succeeded

- count: $OK_COUNT
- directory: $OUTPUT_DIR
- property: $PROPERTY_NAME
- page: $PAGE_ID

\`\`\`json
$MANIFEST_JSON
\`\`\`
EOF
  exit 0
else
  cat <<EOF
## Partial success — $OK_COUNT/$FILE_COUNT downloads ok, $FAIL_COUNT failed

- directory: $OUTPUT_DIR
- property: $PROPERTY_NAME
- page: $PAGE_ID

Verbatim per-file errors are on stderr. Re-run after fixing the upstream cause; existing files will be overwritten unless --no-overwrite is set.

\`\`\`json
$MANIFEST_JSON
\`\`\`
EOF
  exit 2
fi
