#!/bin/bash
# package-skill.sh — package a Claude Code skill into a .skill file for Claude Desktop
#
# Usage:
#   ./package-skill.sh <skill-name>           # e.g. webinar-promo-card
#   ./package-skill.sh <skill-name> [dest]    # optional output directory
#
# Default output: ~/Developer/skills/<skill-name>.skill
# Previous version is archived to ~/Developer/skills/archive/

set -e

SKILLS_DIR="$HOME/Developer/skills"
ARCHIVE_DIR="$SKILLS_DIR/archive"

if [ -z "$1" ]; then
  echo "Usage: ./package-skill.sh <skill-name> [output-dir]"
  echo "Example: ./package-skill.sh webinar-promo-card"
  echo ""
  echo "Available skills:"
  find .claude/skills -mindepth 1 -maxdepth 1 -type d | sed 's|.claude/skills/||' | sort
  exit 1
fi

SKILL_NAME="$1"
SKILL_PATH=".claude/skills/$SKILL_NAME"
OUTPUT_DIR="${2:-$SKILLS_DIR}"

if [ ! -d "$SKILL_PATH" ]; then
  echo "Error: skill not found at $SKILL_PATH"
  echo ""
  echo "Available skills:"
  find .claude/skills -mindepth 1 -maxdepth 1 -type d | sed 's|.claude/skills/||' | sort
  exit 1
fi

if [ ! -f "$SKILL_PATH/SKILL.md" ]; then
  echo "Error: no SKILL.md found in $SKILL_PATH"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
ABS_OUTPUT="$(cd "$OUTPUT_DIR" && pwd)/$SKILL_NAME.skill"

# Archive previous version if it exists
if [ -f "$ABS_OUTPUT" ]; then
  mkdir -p "$ARCHIVE_DIR"
  TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
  mv "$ABS_OUTPUT" "$ARCHIVE_DIR/${SKILL_NAME}_${TIMESTAMP}.skill"
  echo "→ archived previous version to $ARCHIVE_DIR/${SKILL_NAME}_${TIMESTAMP}.skill"
fi

# Create zip with skill-name as top-level directory (matches Claude Desktop format)
cd "$(dirname "$SKILL_PATH")"
zip -qr "$ABS_OUTPUT" "$SKILL_NAME/"
cd - > /dev/null

echo "✓ $ABS_OUTPUT"
