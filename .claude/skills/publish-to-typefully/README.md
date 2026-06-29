# publish-to-typefully

Stage-2 (Push to Production) publish skill for the Perkins pipeline. Creates LinkedIn drafts in
[Typefully](https://typefully.com) from a card's approved LinkedIn output, so a human reviews and
posts inside Typefully instead of copy-pasting into LinkedIn.

It's the LinkedIn analogue of `publish-to-framer`: an MCP-I/O-only skill that hard-stops if its
connector is missing, reads approved content from the reviewer-edited *Editable draft* (never the
read-only original), creates drafts only, and writes nothing to the card (the orchestrator appends
the draft URLs). See [`SKILL.md`](SKILL.md) for the full procedure.

## Quick facts

- Connector: the Typefully MCP (add via *Settings → Connectors*, like Notion / the Framer MCP).
  Step 0 hard-stops if it isn't connected — no manual-paste fallback.
- Auto-discovery: binds the create-draft / media-upload / accounts tools by name-match; no server id
  or `social_set_id` to hardcode. LinkedIn is assumed already connected inside Typefully (set up on
  typefully.com).
- Copy source: stage-1 copy is pulled from the `linkedin` output's *Editable draft* page via
  `notion-fetch` (never the `Original output (read only)`, never the inline brief snapshot), so a
  reviewer's edits at Step 1 carry into the draft — mirroring `format-for-framer` / `publish-to-framer`.
  Stage-2 in-run-rendered copy is read from the render skill's `TASK_RESULT` instead (no review gap).
- Bundling: one draft per surviving LinkedIn image (same approved copy); text-only → one draft.
  Stage-2 variants emit a `1x` + `@2x` per variant — upload only the `primary: true` `@2x`, never
  the `1x` twin.
- Images: bytes to local disk → Typefully presign → PUT raw bytes → poll-ready → `media_ids`
  (stage-1 images: `download-from-notion` URL mode for bytes; stage-2: local PNG paths from the render
  skill's `TASK_RESULT`).
- Rate limit: the presign call is per-social-set rate-limited (`429 RATE_LIMITED`, no `Retry-After`).
  Upload sequentially (never parallel / background-agent), `sleep 3` paced, with blind exponential
  backoff on 429 (`5 → 15 → 45 → 90`, max 4 retries) and a per-image circuit breaker. See `SKILL.md`
  Step 3.
- Always a draft. Never schedules, never auto-posts, never threadifies (single LinkedIn post).
- API: Typefully v2 (v1 sunsets 2026-06-15).

## Wiring

Add `publish-to-typefully` to a LinkedIn-output playbook's `Skill-2` column (as the last entry,
after any stage-2 render skills), keeping `Content Type-2` / `Guidance Type-2` index counts aligned
(a blank/`N-A` slot is fine for a publish-only skill). No `context.ts` registration needed — the stage-2
publish routine resolves the skill by path.

## Testing

Branch: `feat/publish-to-typefully`. Start with Phase 1 (text-only smoke) on Expert Video Post —
a text draft lands in Typefully and its URL appears under Step 2 on the card. See the full phased test
matrix in the Perkins planning notes.
