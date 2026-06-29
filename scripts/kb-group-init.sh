#!/usr/bin/env bash
#
# kb-group-init.sh — configure git sparse-checkout so this clone only
# materializes one kb-update group's raw/ folder on disk.
#
# Usage:
#   scripts/kb-group-init.sh <group-slug>
#   scripts/kb-group-init.sh              # prints usage + valid groups
#
# See raw/README.md and .claude/skills/kb-update/README.md for the full
# workflow. (raw/ sources are processed by /kb-update; kb-lint audits
# canon only and does not read raw/.)
# Undo with: git sparse-checkout disable

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: not inside a git repo" >&2
  exit 1
}
cd "$REPO_ROOT"

# kb-update owns the per-group `raw:` staging paths, so it is the source
# of truth for sparse-checkout. (kb-lint's config has no raw fields.)
CONFIG=".claude/skills/kb-update/config.yaml"

if [[ ! -f "$CONFIG" ]]; then
  echo "Error: $CONFIG not found — are you at the repo root?" >&2
  exit 1
fi

list_groups() {
  grep -E '^  [a-z-]+:$' "$CONFIG" | sed 's/^  /  - /;s/:$//'
}

SLUG="${1:-}"

if [[ -z "$SLUG" ]]; then
  cat <<EOF
Usage: scripts/kb-group-init.sh <group-slug>

Configures git sparse-checkout so this clone only materializes one
kb-update group's raw/ folder on disk. All other groups are hidden from
the working tree but remain in git history.

Available groups:
EOF
  list_groups
  echo ""
  echo "Undo: git sparse-checkout disable"
  exit 1
fi

if ! grep -qE "^  ${SLUG}:$" "$CONFIG"; then
  echo "Error: unknown group '$SLUG'" >&2
  echo "" >&2
  echo "Valid groups:" >&2
  list_groups >&2
  exit 1
fi

if [[ -f .git/info/sparse-checkout ]] && [[ "$(git config --get core.sparseCheckout 2>/dev/null || echo false)" == "true" ]]; then
  echo "⚠ sparse-checkout is already configured:"
  git sparse-checkout list 2>/dev/null | sed 's/^/  /' || true
  echo ""
  read -r -p "Overwrite with group '$SLUG'? [y/N] " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
  fi
fi

git sparse-checkout init --cone
git sparse-checkout set skills .claude outputs scratch scripts "raw/$SLUG"

LABEL=$(awk "/^  ${SLUG}:\$/,/raw:/" "$CONFIG" | grep 'label:' | head -1 | sed 's/.*"\(.*\)"/\1/')
CODEOWNER=$(awk "/^  ${SLUG}:\$/,/raw:/" "$CONFIG" | grep 'codeowner:' | head -1 | sed 's/.*"\(.*\)"/\1/')

echo ""
echo "✓ Sparse-checkout configured for group: $SLUG"
echo "  Label:     $LABEL"
echo "  Codeowner: $CODEOWNER"
echo ""
echo "Visible under raw/:"
ls raw/ | sed 's/^/  /'
echo ""
echo "To switch groups:  scripts/kb-group-init.sh <other-slug>"
echo "To undo entirely:  git sparse-checkout disable"
echo "To process raw:    /kb-update --group $SLUG"
