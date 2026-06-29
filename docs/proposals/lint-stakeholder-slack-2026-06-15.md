# Slack message — copy/paste

---

✅ *Lint remediation (Bucket A) — done & verified*

Wrapped up the five "do-now" KB/context-lint fixes. All re-linted and **clean, no regressions**:

• Fixed broken canon links (18 files)
• Corrected `positioning_source` paths (7 files)
• Removed the duplicate Hartford dossier stub
• Stopped the `polish` skill-chains double-loading context (7 skills)
• Wired up 16 content types (blog/email/social) that were shipping but unreachable

🟡 *One thing needs your call:* a "battlecard generation" link in `competitors.md` points at a file
that never existed — the capability now lives in the `battle` skill (hx-sales), so there's no canon
file to repoint to. My rec: reword the bullet to name the `battle` skill (alt: just delete it). One-liner
once you decide.

📌 I'll raise the PRs for both repos (`hxgtm-mcp-server` + `hx-plugins`) for review.

🧪 Anyone can re-verify it themselves — there's a step-by-step test plan with a paste-ready quick-check
prompt: `docs/proposals/lint-test-plan/TEST_PLAN.md`

Detail: `outputs/lint-phase6-verification-2026-06-15.md` · `docs/proposals/lint-stakeholder-summary-2026-06-15.md`
