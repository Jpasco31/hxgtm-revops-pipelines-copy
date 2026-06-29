#!/bin/bash
# Installs Puppeteer (npm package only) for all card-rendering skills.
# Idempotent — short-circuits per skill when node_modules/puppeteer is already present.
#
# SCOPE: this script installs the npm package only. On Linux, headless Chromium
# also needs OS-level shared libraries (libnss3, libgbm1, libasound2t64, libxss1,
# and ~30 others) that this script does NOT install. Those come from the cloud
# routine's environment Setup Script — see webinar-promo-card's ROUTINE_INTEGRATION.md
# (Option A) for the apt-get list. macOS users can ignore this; Chromium on macOS
# bundles the libs it needs.
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SKILLS=(
  webinar-promo-card
  linkedin-case-study-promo
  linkedin-image-ad-text-only
  linkedin-customer-quote-card
  linkedin-partnership-card
)

for skill in "${SKILLS[@]}"; do
  SCRIPTS_DIR="$REPO_ROOT/.claude/skills/$skill/scripts"

  if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "[install_card_skill_deps] $skill: scripts dir missing at $SCRIPTS_DIR — skipping"
    continue
  fi

  if [ -d "$SCRIPTS_DIR/node_modules/puppeteer" ]; then
    echo "[install_card_skill_deps] $skill: puppeteer already present at $SCRIPTS_DIR/node_modules/puppeteer"
    continue
  fi

  echo "[install_card_skill_deps] $skill: installing puppeteer in $SCRIPTS_DIR"
  (cd "$SCRIPTS_DIR" && npm install)
  echo "[install_card_skill_deps] $skill: puppeteer ready at $SCRIPTS_DIR/node_modules/puppeteer"
done
