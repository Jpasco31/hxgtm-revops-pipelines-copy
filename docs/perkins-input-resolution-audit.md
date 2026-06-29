# Perkins playbooks — card-input resolution audit

**Date:** 2026-06-25
**Scope:** every wired playbook in **Playbook Wiring (Admin View)**
(`collection://d5159cc6-2fc9-83fe-a852-87de9cbaf21b`), checked for whether the
routine auto-resolves the card's file/scalar inputs (vs. silent manual sourcing).
Companion to the routine-level resolver change in this branch.

**Method:** read each playbook's `Generate Assets Skill` / `Finalize & Publish
Assets Skill` wiring, then for every skill that consumes a binary/file input
(headshot, logo, avatar) checked whether the skill documents an
orchestrator-resolved local path (the correct contract) and whether the routine
has a mode that fires for that input shape.

## Summary

| # | Playbook | Type | File/scalar card inputs | Consuming skill(s) | Resolution status |
|---|----------|------|-------------------------|--------------------|-------------------|
| 1 | Virtual Event Promo Pack | Webinar | Speaker 1–4 headshots + `HubSpot Form ID` (`Step 1 Inputs` form DB) | `webinar-promo-card` (S1); `format-for-framer`→`publish-to-framer` (S2) | ✅ **Fixed this PR** — numbered per-entity resolver: S1 local `photo_path`, S2 fresh `source_url` + Form ID |
| 2 | Customer Press Release | Press Release | Customer Logo; Customer Quote 1..N avatars | `linkedin-partnership-card` (logo); `linkedin-customer-quote-card` (avatars) | Avatars ✅ covered (Mode 4 `--explode-groups`, documented in skill). Logo ⚠️ **flag F1** |
| 3 | Partner Press Release | Press Release | Partner Logo | `linkedin-partnership-card` | ⚠️ **flag F1** |
| 4 | Customer Case Study | Case Study | Customer Quote avatars; Customer Logo | `linkedin-customer-quote-card` (avatars); `linkedin-case-study-promo` (logo) | Avatars ✅ covered. Logo ⚠️ **flag F2** |
| 5 | LI - Product Use Case Post | Social | none (text) | `linkedin` | ✅ n/a |
| 6 | Expert Video Post | Social | none (transcript text) | `linkedin` | ✅ n/a |
| 7 | Exec Dinner/Roundtable Invite | Email | none (text) | `email` | ✅ n/a |
| 8 | Event Invite, Hubspot | Email | none (text) | `email` | ✅ n/a |
| 9 | Product Announcement, No PR | Blog | none (text) | `blog`, `linkedin`, `email` | ✅ n/a |
| 10 | Single Image Ads, Text Only | Paid | none (text-only ad by design) | `ads`, `linkedin-image-ad-text-only` | ✅ n/a |

**Tally:** 1 fixed here · 6 with no file inputs · 1 already covered
(`linkedin-customer-quote-card` avatars) · 2 flagged (singleton logo).

## Flags (per card item 6 — "fix same-pattern / flag bespoke")

### F1 — partner/customer logo for `linkedin-partnership-card`
*(Partner Press Release, Customer Press Release)*

`linkedin-partnership-card` requires a local **`Partner logo path`** (SKILL.md
§1 "Collect inputs") but — unlike `webinar-promo-card` and
`linkedin-customer-quote-card` — does **not** document orchestrator /
`download-from-notion` resolution. The routine's general "Notion file inputs"
instruction plus singleton **page-property / body-table** mode *can* resolve a
single logo from a `Step-N Inputs` DB column or a body-table row, so the
**mechanism already exists** — but it is not explicitly wired/verified for these
playbooks and the skill doesn't state the contract, so a run can silently fall
back to manual sourcing (the same failure class as the webinar incident).

**Shape:** singleton file — **not** the numbered `Speaker N` pattern, so no new
resolver is needed. **What it needs (follow-up):**
1. Confirm the live card exposes the partner/customer logo in a resolvable
   surface (a `Logo` / `Customer Logo` column in the Step 1/2 Inputs DB, or a
   labelled body-table row).
2. Add a one-line orchestrator-resolves note to
   `linkedin-partnership-card/SKILL.md` §1 (mirroring `webinar-promo-card`): the
   routine resolves the logo via `download-from-notion` and passes a local path;
   the skill never reads Notion itself — keeps terminal runs safe.

### F2 — customer logo for `linkedin-case-study-promo`
*(Customer Case Study)*

Identical to F1: requires a local **`Customer logo path`** (SKILL.md §1), no
documented orchestrator resolution. Same singleton-file shape, same two-step
follow-up (confirm input surface + add the orchestrator-resolves note).

## No action needed

- `linkedin-customer-quote-card` — already documents orchestrator-resolved
  `avatar_local_path` via `download-from-notion` Mode 4 (legacy `Customer Quotes`
  child DB **or** converted-playbook `--explode-groups` form DB). Correctly wired.
- The 6 text/scalar-only playbooks have no binary inputs.

## Stopgap-cleanup confirmation (card item 4)

Verified on this branch: neither `format-for-framer/SKILL.md` nor
`webinar-promo-card/SKILL.md` contains an in-skill `Step 1 Inputs` / Notion-REST
lookup. The F1.5 stopgap (commit `582446f`) lives only on the unmerged branch
`claude/tender-ride-mbprtc`; the 65c008b overhaul already superseded it. No
revert was required — discovery stays in the routine.
