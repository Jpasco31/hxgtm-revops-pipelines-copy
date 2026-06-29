#!/usr/bin/env bash
#
# fetch_linkedin_image.sh — resolve a LinkedIn profile/company URL to a local
# image by scraping the page's og:image meta tag.
#
# Fails closed when LinkedIn returns a login wall or omits og:image. Callers
# must surface the verbatim error to the user with an "attach the file
# directly" prompt.
#
# Outputs (stdout): single-line JSON manifest:
#   { source_url, og_image_url, local_path, bytes, mime }
#
# Exit codes:
#   0  success
#   3  full failure (login wall, no og:image, network, invalid image)
#   4  bad input
#
# Required tools: bash, curl, file (or python3 fallback for MIME sniff).

set -uo pipefail

URL=""
OUTPUT=""
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

usage() {
  cat >&2 <<'EOF'
fetch_linkedin_image.sh — pull a LinkedIn profile / company page's og:image to
a local file.

Required:
  --url <linkedin_url>      LinkedIn profile (/in/<slug>) or company (/company/<slug>) URL.
  --output <abs_path>       Absolute local path to write the image to. Parent dir must exist.

Optional:
  -h, --help                Show this help.

Exit codes:
  0  success
  3  full failure (login wall, no og:image, network, invalid image)
  4  bad input
EOF
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) URL="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    -h|--help) usage 0 ;;
    *) echo "fetch_linkedin_image: unknown flag $1" >&2; usage 4 ;;
  esac
done

# ---- pre-flight ------------------------------------------------------------

if [[ -z "$URL" || -z "$OUTPUT" ]]; then
  echo "fetch_linkedin_image: --url and --output are required" >&2
  exit 4
fi

if [[ ! "$URL" =~ ^https://(www\.)?linkedin\.com/(in|company)/ ]]; then
  echo "fetch_linkedin_image: URL must match https://(www.)?linkedin.com/(in|company)/... — got: $URL" >&2
  exit 4
fi

case "$OUTPUT" in
  /*) : ;;
  *) echo "fetch_linkedin_image: --output must be an absolute path — got: $OUTPUT" >&2; exit 4 ;;
esac

OUT_DIR="$(dirname "$OUTPUT")"
if [[ ! -d "$OUT_DIR" ]]; then
  echo "fetch_linkedin_image: parent directory does not exist: $OUT_DIR" >&2
  exit 4
fi

for tool in curl; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "fetch_linkedin_image: missing required tool: $tool" >&2
    exit 4
  fi
done

# ---- fetch the LinkedIn HTML ----------------------------------------------

HTML_TMP="$(mktemp -t fetch-li-html.XXXXXX)"
trap 'rm -f "$HTML_TMP"' EXIT

HTTP_STATUS="$(curl -sS -L --max-time 30 \
  -o "$HTML_TMP" \
  -w "%{http_code}" \
  -A "$UA" \
  -H "Accept-Language: en-US,en;q=0.9" \
  "$URL" 2>/tmp/fetch-li-curl-err)"
CURL_EXIT=$?

if [[ "$CURL_EXIT" -ne 0 ]]; then
  echo "fetch_linkedin_image: curl failed fetching LinkedIn URL (exit $CURL_EXIT):" >&2
  cat /tmp/fetch-li-curl-err >&2 || true
  exit 3
fi

# LinkedIn 999 = anti-scrape signal.
if [[ "$HTTP_STATUS" == "999" ]]; then
  echo "fetch_linkedin_image: LinkedIn returned HTTP 999 (anti-scrape); login wall — attach the file directly instead." >&2
  exit 3
fi

if [[ "$HTTP_STATUS" != "200" ]]; then
  echo "fetch_linkedin_image: LinkedIn returned HTTP $HTTP_STATUS for $URL — attach the file directly instead." >&2
  exit 3
fi

# Login-wall heuristic: title contains 'Sign In' or 'LinkedIn Login'.
if grep -qiE '<title>[^<]*(sign[ -]?in|linkedin login)' "$HTML_TMP"; then
  echo "fetch_linkedin_image: LinkedIn returned a login wall page (title heuristic) — attach the file directly instead." >&2
  exit 3
fi

# ---- extract og:image ------------------------------------------------------

# Two attribute orderings — property first, or content first. Quotes can be " or '.
# We match the first occurrence either way.

OG_IMAGE="$(grep -oE '<meta[^>]+property=("|'"'"')og:image\1[^>]+content=("|'"'"')[^"'"'"']+\2' "$HTML_TMP" \
  | head -n1 \
  | sed -E 's/.*content=("|'"'"')([^"'"'"']+)\1.*/\2/')"

if [[ -z "$OG_IMAGE" ]]; then
  # Try the swapped attribute order.
  OG_IMAGE="$(grep -oE '<meta[^>]+content=("|'"'"')[^"'"'"']+\1[^>]+property=("|'"'"')og:image\2' "$HTML_TMP" \
    | head -n1 \
    | sed -E 's/.*content=("|'"'"')([^"'"'"']+)\1.*/\2/')"
fi

if [[ -z "$OG_IMAGE" ]]; then
  echo "fetch_linkedin_image: no <meta property=\"og:image\"> tag in LinkedIn response for $URL — attach the file directly instead." >&2
  exit 3
fi

# Decode HTML entities the OG URL is likely to contain.
OG_IMAGE="${OG_IMAGE//&amp;/&}"
OG_IMAGE="${OG_IMAGE//&#x2F;//}"
OG_IMAGE="${OG_IMAGE//&#47;//}"

# ---- download the image ---------------------------------------------------

IMG_HTTP_STATUS="$(curl -sS -L --max-time 60 \
  -o "$OUTPUT" \
  -w "%{http_code}" \
  "$OG_IMAGE" 2>/tmp/fetch-li-img-err)"
IMG_CURL_EXIT=$?

if [[ "$IMG_CURL_EXIT" -ne 0 ]]; then
  rm -f "$OUTPUT"
  echo "fetch_linkedin_image: curl failed downloading og:image (exit $IMG_CURL_EXIT):" >&2
  cat /tmp/fetch-li-img-err >&2 || true
  exit 3
fi

if [[ "$IMG_HTTP_STATUS" != "200" ]]; then
  rm -f "$OUTPUT"
  echo "fetch_linkedin_image: og:image URL returned HTTP $IMG_HTTP_STATUS — $OG_IMAGE" >&2
  exit 3
fi

# ---- validate the downloaded asset ----------------------------------------

BYTES="$(wc -c < "$OUTPUT" | tr -d ' ')"
if [[ "$BYTES" -lt 1024 ]]; then
  rm -f "$OUTPUT"
  echo "fetch_linkedin_image: downloaded asset is only $BYTES bytes (<1024) — likely an error page, not an image." >&2
  exit 3
fi

# MIME sniff — prefer `file --mime-type`, fall back to python.
MIME=""
if command -v file >/dev/null 2>&1; then
  MIME="$(file --mime-type -b "$OUTPUT" 2>/dev/null || true)"
fi
if [[ -z "$MIME" ]] && command -v python3 >/dev/null 2>&1; then
  MIME="$(python3 -c 'import mimetypes,sys; t,_=mimetypes.guess_type(sys.argv[1]); print(t or "")' "$OUTPUT")"
fi

case "$MIME" in
  image/jpeg|image/png|image/webp|image/gif|image/jpg) : ;;
  "")
    rm -f "$OUTPUT"
    echo "fetch_linkedin_image: could not determine MIME type of downloaded asset." >&2
    exit 3
    ;;
  *)
    rm -f "$OUTPUT"
    echo "fetch_linkedin_image: downloaded asset MIME is $MIME — not an image. og:image URL was: $OG_IMAGE" >&2
    exit 3
    ;;
esac

# ---- emit manifest --------------------------------------------------------

# Escape strings for JSON. We only need to escape backslashes and quotes for
# the URL-like fields and absolute-path-like fields; tabs/newlines aren't
# expected in any of these values.

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

printf '{"source_url":"%s","og_image_url":"%s","local_path":"%s","bytes":%s,"mime":"%s"}\n' \
  "$(json_escape "$URL")" \
  "$(json_escape "$OG_IMAGE")" \
  "$(json_escape "$OUTPUT")" \
  "$BYTES" \
  "$MIME"

exit 0
