# Competitor-file style guide (competitive group)

This is the **authoring contract** for per-competitor canon files
under `guidance/competitive/competitors/<competitor>.md`. Every
finding kb-update proposes against a competitor file must produce a
`proposed_text` that would be valid per this guide if it landed in
canon verbatim.

This prose guide is authoritative. The compact `section_schema:` in
[`../config.yaml`](../config.yaml) is the machine-readable compression
of this doc. **If the two conflict, this guide wins** — surface the
conflict via `style_mismatch_with_schema: true` in stats so the
config can be brought back in sync.

---

## Section-level style rules

Each competitor file should contain these sections only. No net-new
sections without explicit approval.

### Snapshot

- **Length:** 1–2 sentences, max 50 words.
- **Lead with:** what they are (category), not what they're good at.
- **Follow with:** one clause naming the main limit or scope.
  **Exactly one limit** — not a list. If the raw surfaces multiple
  limits, keep the single highest-leverage one in Snapshot and split
  the remainder into separate Weaknesses / watch-outs findings.
- **Pattern:** "An AI-powered submission workbench for commercial
  and specialty insurers. Strong on ingestion and triage but their
  AI is only applicable to part of the underwriting workflow."
- **Do not include:** customer names, quotes, funding, dates, or
  feature lists. No multi-clause limit enumeration.

### Where they show up

- **Length:** 3–6 bullets.
- **Each bullet:** a category of buyer pain or initiative they're
  invited into (not a product feature).
- **Pattern:** "Underwriting productivity and workbench
  modernization" — a domain, not a claim.
- **Do not include:** specific product names, customer accounts,
  or comparative framing.

### Core products

- **Length:** 2–5 products, max. This is the authoritative list of
  the competitor's main platform / module offerings.
- **Format per product:** **bolded product name** — one-sentence
  description of what it does.
    - **Pattern:** **Copilot Hub** — the central submission review
      workspace where underwriters triage incoming submissions, see
      appetite alignment, and take actions (quote, refer, decline).
- **Purpose:** this is the **scope gate** for Strengths, Weaknesses,
  hx positioning, and Talk track. Capabilities that belong to a
  listed Core product can drive changes in those sections.
  Capabilities tied to a feature NOT in the Core products list can
  only update Notes.
- **Do not include:** every minor feature, roadmap items not yet
  shipped, integrations, or UI capabilities (those belong inside a
  Core product's description or in Notes).
- **Update rule:** adding a new Core product requires a Tier 1 or
  Tier 2 source (not a blog post). Removing one requires evidence of
  deprecation. This is the slowest-moving section — changes should
  be rare.

### Strengths

- **Length:** 4–6 bullets, max.
- **Format per bullet:** **bolded lead phrase** — one short sentence
  of supporting evidence or source.
- **Pattern:** **Modern UI that attracts underwriting talent** —
  Bowhead customer has touted this.
- **Lead must be a capability claim** (what they're good at).
  Evidence must be a named customer, named analyst, or documented
  source.
- **Do not include:** niche feature details (belongs in Notes if at
  all), staffing, personality observations, or quotes longer than 15
  words.

### Weaknesses / watch-outs

- **Length:** 4–6 bullets, max.
- **Format per bullet:** **bolded lead weakness** — supporting
  evidence or source that contradicts or limits their claim.
- **Pattern:** **Strong at submission, weaker at pricing.** They can
  incorporate Excel or external rates but don't have a native
  pricing system.
- **Lead with the weakness, then the evidence** — not the other way
  round, not essay form.
- **Do not include:** long explanatory paragraphs, multiple quotes,
  or niche feature gaps (those go in Notes / open questions).
- **Single-deployment anecdotes demote to Notes.** A weakness backed
  by only one named customer deployment is field intel, not a
  categorical Weakness. It belongs in Notes unless corroborated by
  a second independent source.

### hx positioning

- **Length:** 2–3 bullets.
- **Each bullet:** a structural claim about hx that contrasts with
  the competitor's core limit — not a rewrite triggered by a single
  new feature.
- **Pattern:** "hx is the governed decisioning platform: pricing and
  underwriting logic as a controlled, auditable, rapidly-iterable
  system."
- **Do not include:**
    - Reactions to specific competitor feature launches.
    - Consolidation-risk commentary (that goes in a counter-positioning
      / "why we win" section if one exists).
    - **Repeat of Strengths / Weaknesses content.** This is the most
      common drift: a weakness bullet phrased from the hx side
      ("hx covers the gap they can't fill") is still the same claim.
      If the underlying fact already lives in Weaknesses, do NOT
      restate it here.
    - **Coverage-matrix evidence.** Phrasings like "zero Federato
      coverage across N use cases" are comparative scorecards, not
      structural positioning. Demote to Notes or reword as a genuine
      structural contrast about how hx approaches the space.

### Talk track

- **Length:** 1–3 one-line quotes a seller could actually say.
- **Pattern:** "Assistive UX is helpful, but the competitive
  advantage comes from owning the decision logic — transparent,
  auditable, and rapidly improvable."
- **Do not include:** customer names (too risky for external use),
  long explanations, or three-paragraph positioning statements.

### Notes / open questions

- **Length:** 2–5 bullets.
- **Each bullet:** a genuine open question about the competitor's
  capability, pricing, governance, or roadmap.
- **Pattern:** "Depth of integration into existing rating engines
  and policy admin."
- **This is the catch-all** for things that don't fit elsewhere —
  single-source intel, unverified claims, niche feature references,
  customer rumours, and anecdotal single-deployment observations.
  Should be periodically pruned once resolved.
- **Closing an open question.** If a raw source provides confirmed
  evidence that answers an existing Notes bullet, the finding
  should replace that bullet (not append alongside) and set
  `closes_open_question: "<exact canon heading text being closed>"`
  on the finding so reviewers see the resolution signal.

---

## Meta-rules that cross sections

- **No net-new sections without explicit approval.** If a raw source
  surfaces content that doesn't fit any of the eight sections above,
  route to Notes (for single-source / niche) or drop (for off-topic
  chronicle / strategic-direction commentary).
- **One claim per finding.** If your `proposed_text` contains "and
  also", "separately", or two distinct facts, split into two
  findings.
- **Style wins over drift.** Existing canon bullets that don't match
  this guide (e.g. plain bullets in Weaknesses where `**Lead** —
  evidence` is required) are drift, not signal. Emit findings in
  correct schema format and set `style_mismatch_in_section: true` in
  stats — canon cleanup is a separate concern.
