#!/usr/bin/env bash
#
# fire.sh — fire the Account Dossier batch cloud routine (the n8n replacement).
#
# Builds the exact payload the old n8n workflow sent and POSTs it to the routine's
# /fire endpoint. Account names may be passed as separate quoted args and/or a single
# comma-separated string; both normalize to {"accounts": "A,B,C", "waves": N}.
#
# Usage:
#   fire.sh "Account A" "Account B" [--waves N]
#   fire.sh "Account A, Account B, Account C"
#
# Env (required):
#   DOSSIER_ROUTINE_TOKEN   routine API token, sk-ant-oat01-...   (secret)
#   DOSSIER_ROUTINE_ID      routine trigger id, trig_...
#
set -euo pipefail

waves=3
accounts=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --waves)   waves="${2:?--waves needs a number}"; shift 2 ;;
    --waves=*) waves="${1#*=}"; shift ;;
    --)        shift; while [[ $# -gt 0 ]]; do accounts+=("$1"); shift; done ;;
    -*)        echo "Error: unknown flag: $1" >&2; exit 2 ;;
    *)         accounts+=("$1"); shift ;;
  esac
done

if [[ ${#accounts[@]} -eq 0 ]]; then
  echo "Error: no account names given." >&2
  echo "Usage: fire.sh \"Account A\" \"Account B\" [--waves N]" >&2
  exit 2
fi
if ! [[ "$waves" =~ ^[0-9]+$ ]]; then
  echo "Error: --waves must be a positive integer (got: $waves)." >&2
  exit 2
fi

# Normalize accounts (split any comma-joined args, trim, drop empties) and build the
# nested payload with python3's json so escaping is always correct.
payload="$(
  ACCS="$(printf '%s\n' "${accounts[@]}")" WAVES="$waves" python3 - <<'PY'
import json, os
# One line per CLI positional arg (verbatim — may contain commas).
lines = [x for x in os.environ["ACCS"].split("\n") if x.strip()]
if len(lines) == 1:
    # Single arg: treat it as a convenience comma-separated list.
    parts = [a.strip() for a in lines[0].split(",") if a.strip()]
else:
    # Multiple args: each arg is exactly one account (internal commas preserved).
    parts = [a.strip() for a in lines]
inner = json.dumps({"accounts": ",".join(parts), "waves": int(os.environ["WAVES"])})
print(json.dumps({"text": inner}))
PY
)"

url_base="https://api.anthropic.com/v1/claude_code/routines"

: "${DOSSIER_ROUTINE_TOKEN:?DOSSIER_ROUTINE_TOKEN is not set — export the routine API token (sk-ant-oat01-...) before firing}"
: "${DOSSIER_ROUTINE_ID:?DOSSIER_ROUTINE_ID is not set — export the routine trigger id (trig_...) before firing}"

echo "Firing routine ${DOSSIER_ROUTINE_ID} with: ${payload}" >&2
curl -sS -X POST "${url_base}/${DOSSIER_ROUTINE_ID}/fire" \
  -H "Authorization: Bearer ${DOSSIER_ROUTINE_TOKEN}" \
  -H "anthropic-beta: experimental-cc-routine-2026-04-01" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d "${payload}"
echo
