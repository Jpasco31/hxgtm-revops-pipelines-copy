---
name: publish-to-typefully
description: Create LinkedIn DRAFTS in Typefully from a Perkins card's approved LinkedIn output via the Typefully MCP, at the Push to Production (stage-2) step. Use when a reviewed card's Step output includes a LinkedIn post and you want it drafted in Typefully for a human to review and post — trigger phrases "draft this to Typefully", "push the LinkedIn post to Typefully", "publish to Typefully". One draft per surviving LinkedIn image (reusing the single approved copy); text-only → one draft. Drafts only — never schedules or auto-posts. NOT for Framer pages (use publish-to-framer), NOT for non-LinkedIn channels (X/Threads/Bluesky/Mastodon — out of scope for v1), NOT for writing or rewriting copy.
---

# Publish to Typefully

## Purpose

Take a Perkins card's approved LinkedIn output — the post copy, plus any image cards that survived
human review — and create draft posts in [Typefully](https://typefully.com) via the Typefully MCP,
so a marketer reviews and hits Post inside Typefully instead of copy-pasting into LinkedIn by hand.

This skill owns Typefully MCP I/O only. It does not write copy, render images, or write to the
Notion card. It is the LinkedIn-publishing analogue of `publish-to-framer`, and is normally the last
skill in a playbook's stage-2 (`Skill-2`) chain.

## When to Use

- As a stage-2 publish skill (listed in a playbook's `Skill-2` column) when a card reaches Push to
  Production and the card's approved output includes a LinkedIn post.
- When a user explicitly says "draft this to Typefully" / "push the LinkedIn post to Typefully" and an
  approved LinkedIn post exists in context.

Do not use if:

- The card has no LinkedIn output to publish — emit `blocked`, reason `no LinkedIn output on card`.
- The request is to publish a Framer page — use `publish-to-framer`.
- The request targets a non-LinkedIn channel (X / Threads / Bluesky / Mastodon) — out of scope for v1.
- The request is to schedule or auto-post — this skill only ever creates drafts.

## Inputs

### Required
- Approved LinkedIn copy — the post text after human review (respects edits). Comes from the
  `linkedin` output's *Editable draft* page (the human-edited working copy, fetched via Notion —
  never the read-only original) for copy produced at stage 1, or the in-run rendered output of an
  earlier `Skill-2` skill for copy rendered at stage 2 — see Step 1.
- Card page ID — to re-fetch the page for fresh image signed-URLs (stage-1 images) and for
  `download-from-notion`.

### Optional (if provided, must be used)
- Surviving LinkedIn image(s) — zero or more images; each → one draft (none → one text-only draft).
  Source depends on the trigger: stage-1 images are embedded image blocks in the card body (page
  body, not a Notion Files property); stage-2 images are local PNG paths reported in-run by an
  earlier `Skill-2` render skill. See Step 3.
- `NOTION_API_KEY` — env var; needed to download stage-1 image bytes via `download-from-notion`.

No-prompt rule: this skill runs in orchestration mode. If a required input is absent, emit `blocked`
with a named reason — never ask the user.

## Step 0 — Pre-flight: Typefully connector check (hard-stop)

Before anything else, confirm the Typefully MCP is connected. Detect it the same way the other
skills detect a connector — by server name OR tool name:

- A Typefully MCP server is present if any connected MCP server name contains `"typefully"` OR any
  available tool name contains `"typefully"`.
- From that server, bind the tools you'll use by name-match:
  - the create-draft tool (a tool whose name contains `create` + `draft`, e.g. `create_draft`),
  - the media-upload (presign) tool — a tool whose name contains `media` + `upload` (e.g.
    `create_media_upload`). It takes a social-set id + a `file_name` and returns a presigned
    upload URL plus a `media_id`; you upload the bytes yourself with a plain PUT to that URL
    (Step 3). There is no "upload from a Notion URL" tool — you always supply the bytes.
  - the media-status tool (name contains `media` + `status`, e.g. `get_media_status`), if exposed —
    to poll until an uploaded asset is processed before drafting.
  - the social-sets list tool (lists connected social accounts / sets), if exposed.

If no Typefully connector is found, STOP. Do not generate any output, do not fall back to manual
copy/paste, do not narrate a workaround. Emit `blocked` and print this actionable message verbatim:

> Typefully MCP not connected. Add it via Settings → Connectors (the same way Notion / the Framer
> MCP are added), then re-run. This skill creates Typefully drafts and cannot run without it.

LinkedIn is assumed already connected inside the Typefully account (set up on the Typefully website).
If the connected Typefully account exposes no LinkedIn social account, STOP and emit `blocked`,
reason `no LinkedIn account connected in Typefully — connect LinkedIn on typefully.com`.

> API version: target Typefully API v2 (v2 is social-set–scoped; the media-upload endpoint is
> per social set). The legacy v1 API sunsets 2026-06-15 — the connector must be on v2.

## Step 1 — Extract the approved LinkedIn copy

Locate the approved LinkedIn post text as it stands after human review (respect edits). Use the
most recent approved copy available at the moment this skill runs — this skill runs last in the
`Skill-2` chain, so any copy produced earlier in the same run is already available to you. If there is no
LinkedIn copy from either source below, emit `blocked`, reason `no LinkedIn output on card`.

- Copy produced at stage 1 (e.g. Expert Video Post; also the Customer Press Release post): source it
  from the *Editable draft* page, **not** from the inline copy in your brief. The inline copy in the
  card's *Step-1 Outputs* is the original AI output, frozen at generation time; a reviewer edits the
  *Editable draft* in place during human review, so that page — not the brief, not the read-only
  original — is the source of truth. Resolve it the same way `format-for-framer` does:
  1. Re-fetch the card page (you already have the *Card page ID*) and find its *Step-1 Outputs*
     section. Locate the **`linkedin` output**: the `linkedin` subheading, or — for single-output
     playbooks whose entire Step-1 output is the post (Expert Video Post, Single Image Ads) — the
     Outputs section itself.
  2. Within it, follow the **`Editable draft`** link (a `mention-page` link, or a bare `notion.so`
     URL) and `notion-fetch` that page. **Never** follow the `Original output (read only)` link, and
     never use the inline brief snapshot.
  3. Use the fetched page's body text as the approved copy (these LinkedIn draft pages are just the
     post text; if a `Page Metadata` block is present, exclude it).
  4. If the `linkedin` output has no `Editable draft` link but inline copy *is* present, use the
     inline copy and note that you fell back. If there is neither an `Editable draft` link nor inline
     copy, emit `blocked`, reason `no LinkedIn editable draft on card`. Never silently substitute the
     read-only original.
- Copy rendered at stage 2 (two-trigger, e.g. Customer Case Study's `linkedin` post): an earlier
  `Skill-2` skill in this same run produced it — read it from that skill's in-run rendered output
  (its `TASK_RESULT` / `rendered_output`), not from a card section. The orchestrator writes the
  *Step-2 Outputs* card section only after the whole chain finishes, so it does not exist yet mid-run.
  (No Editable-draft hop here: this copy is freshly rendered in the current run, so there is no
  human-review gap to pick up, and its `save-to-notion` draft is written only at end-of-run.)

If both are present, prefer the stage-2 render (it is the latest). Never rewrite the copy.

## Step 1b — Normalize paragraph spacing (formatting only, never reword)

The approved copy frequently arrives single-newline-separated between paragraphs: Notion stores each
paragraph as its own block, so reading the fetched *Editable draft* page yields paragraphs joined by a single `\n`.
LinkedIn renders a single `\n` as a tight line break with no visible gap, so the paragraphs run
together (observed on the Expert Video Post and Product Announcement drafts — paragraphs with no spacing —
while posts that arrived blank-line-separated rendered correctly). Before drafting, normalize the
whitespace only:

- Separate every paragraph with a blank line — exactly one empty line (`\n\n`) between paragraphs.
- Collapse any run of 3+ consecutive newlines down to a single blank line (`\n\n`). This also keeps you
  well clear of the threadify split threshold (4 consecutive newlines).
- Trim trailing spaces per line and strip leading/trailing blank lines.
- Keep a short attribution line that immediately follows a quote (e.g. `-- Name, Title` under a
  `"…quote…"` line) tight to that quote — a single `\n` between them is fine; put the blank line *before*
  the quote and *after* the attribution.

This is a formatting pass only: do not add, remove, reword, reorder, or re-punctuate any text —
adjust the blank lines between paragraphs and nothing else. The words stay verbatim (see Guardrails).

## Step 2 — Determine the draft set (bundling rule)

Count the surviving LinkedIn image(s) for this card:

- N images (N ≥ 1): create N drafts, each with the same approved copy + one image.
- 0 images (text-only): create 1 text-only draft.

One asset per surviving variant — take the `@2x` primary, never its `1x` twin. A stage-2 render
skill emits two files per variant: a `1x` (1080×1080) and an `@2x` (2160×2160). These are the
same image at two resolutions, not two images. The render skills designate the `@2x` as the
primary deliverable and flag it `primary: true` in their `TASK_RESULT` artifacts (the `1x` is
secondary). So when counting surviving images, select exactly one artifact per variant: the
`primary: true` `@2x`, and ignore every `1x`. Uploading both is the bug that turned 9 images
into 12 attempted uploads on the Customer Case Study (P8) and helped trip the rate limit — do not
reintroduce it. (Stage-1 single images embedded on the card body are already one-per-card; no
`@2x`/`1x` split applies there.)

Never invent images or copy. Preserve image order.

## Step 3 — Resolve + upload each image (only if images present)

Typefully uploads are presign → PUT bytes → poll-ready, all per image. Process images strictly
one at a time, in order: finish the entire presign → PUT → status-ready → create its draft (Step 4)
chain for image *i* before starting image *i+1*.

> Why sequential + paced. The rate limit that broke P8 is a per-social-set limit on the presign
> (`create_media_upload`) call. Bursting many presigns at once — or in parallel — trips it (`429
> RATE_LIMITED`), and the original run then retried ~50 times with no wait. Both faults are now banned:
>
> - Never parallelise uploads, and never spawn a background agent to run them. One synchronous loop.
> - Pace between images: after finishing one image's draft, run a literal `sleep 3` in Bash
>   before starting the next.

3a — Get the bytes to a local path. The source depends on the trigger:

- Stage-1 images (single-trigger, e.g. a partner / webinar promo card already on the card): the image
  is an embedded image block in the card body (*Step-1 Outputs* — not a Files property). Take the
  block's fresh signed URL (re-fetch the page if it may have expired — Notion signed URLs live ~1 hr)
  and run `download-from-notion` URL mode (`--url <signed-url> --output <abs-path>`) to write the
  bytes locally.
- Stage-2 rendered images (two-trigger, e.g. quote / ad / case-study cards): an earlier `Skill-2`
  render skill in this same run already wrote the PNG(s) to local disk under
  `{local_revops_path}/campaigns/<slug>/` and reported the absolute path(s) in its `TASK_RESULT`
  `artifacts`. Use the `primary: true` `@2x` path for the variant (per Step 2) — never the `1x`.

3b — Upload (presign → PUT → poll). For the current image only:

1. Call the media-upload (presign) tool with the LinkedIn social-set id + the file's `file_name`;
   it returns a presigned URL + `media_id`.
2. PUT the raw file bytes to that URL with no extra headers — the presigned signature was
   computed without them, so any added header (`Content-Type`, `Authorization`, …) causes
   `403 SignatureDoesNotMatch`. Use `curl -T`, not `--data-binary`:
   ```bash
   curl -sS -X PUT -T "<abs-file-path>" "<presigned_url>" -w 'HTTP_%{http_code}\n'
   ```
   A successful upload returns `200` or `204`. (`-T` streams the file as a clean PUT body; quote
   the URL — it contains `&`.)
3. If a media-status tool exists, poll it until the asset is `ready` — `sleep 2` between polls, at
   most ~10 polls — before drafting. Keep the `media_id`.

3c — Rate-limit backoff (`429 RATE_LIMITED`). Typefully returns `429 RATE_LIMITED` with NO
`Retry-After` header, and the MCP surfaces only the JSON error body (not the `X-RateLimit-SocialSet-*`
headers) — so back off blind. If any Typefully call (presign, PUT, media-status, or create-draft)
returns `429` / `RATE_LIMITED`:

- Wait, then retry the same call, with exponential backoff — run the literal Bash `sleep`:
  `sleep 5` → `sleep 15` → `sleep 45` → `sleep 90`. Never retry a 429 without a `sleep` first.
- Maximum 4 retries per call. A call may be attempted at most 5 times total. (The P8 failure was
  ~50 instant retries — that must now be impossible.)

3d — Circuit breaker + graceful degrade. If a single image still fails after its 4 backed-off
retries (rate-limit or anything else):

- Stop uploading further images — do not keep hammering the endpoint with the remaining ones.
- Ensure a text-only draft of the approved copy exists (create one if no image draft was made yet).
- Record every un-uploaded image as a manual-action note: "attach `<image label>` in Typefully".
- Return `completed` (partial) with those notes — never block the whole card on image upload,
  and never loop past the retry cap.

Preserve image order; one `media_id` per surviving image; one draft per image.

## Step 4 — Create each draft

Create the draft for the current image immediately after its upload succeeds (this runs inside the
Step 3 per-image loop, not as a separate batch afterwards), then `sleep 3` and move to the next image.
For each item in the draft set, call the create-draft tool with:

- the approved copy as the draft content, with paragraph spacing normalized per Step 1b (paragraphs
  blank-line separated so LinkedIn shows the intended gaps),
- target = the connected LinkedIn social set,
- `media_ids: [<media_id>]` for the one image bundled with this draft (omit for text-only),
- draft mode only — do not set a schedule date and do not publish/share,
- `threadify` OFF — a LinkedIn post is a single post; never split on blank lines / 4 consecutive
  newlines.

Capture the returned draft ID / URL.

## Step 5 — Return the result

Return a `TASK_RESULT` payload listing every draft URL with its label. The skill itself writes nothing
to the card — the orchestrator appends these under *Outputs section of Step 2: Finalize & Publish
Assets*.

```
TASK_RESULT
status: completed
skills:
- skill: publish-to-typefully
  rendered_output: |
    Typefully drafts created (LinkedIn, draft — review & post in Typefully):
    - Draft 1 (text + <image label or "text-only">): https://typefully.com/.../<id1>
    - Draft 2 (text + <image label>): https://typefully.com/.../<id2>
```

## Self-Check

- [ ] Typefully MCP confirmed reachable (Step 0) before any draft call; hard-stopped if not.
- [ ] One asset per surviving variant — the `primary: true` `@2x`; no `1x` twin uploaded (Step 2).
- [ ] Number of drafts == number of surviving images (or exactly 1 if text-only).
- [ ] Uploads ran sequentially (one image fully through before the next) — never parallel, never via a background agent; `sleep 3` paced between images.
- [ ] Every `429` was retried only after a `sleep` backoff, at most 4 retries per call; the circuit breaker stopped cleanly on persistent failure (no loop past the cap).
- [ ] Every draft is a draft — none scheduled or posted live; `threadify` off.
- [ ] Each draft uses the post-review copy (not a pre-review payload).
- [ ] Paragraph spacing normalized (Step 1b) — paragraphs blank-line separated (`\n\n`), none run together; words unchanged.
- [ ] Every draft URL is in `TASK_RESULT`; no card writes performed by this skill.

## Failure & Blocked Handling

- Typefully MCP unavailable → `blocked: Typefully MCP not connected` (Step 0 message). No manual fallback.
- No LinkedIn account in Typefully → `blocked: no LinkedIn account connected in Typefully`.
- No LinkedIn copy on the card → `blocked: no LinkedIn output on card`.
- A single draft call fails → do not silently drop it: report the verbatim MCP error in
  `rendered_output`, keep any drafts already created (list their URLs), and return `completed` only if at
  least the text draft succeeded; otherwise `blocked` with the verbatim error.
- Image resolution fails → degrade to a text draft + manual-action note (do not block the whole card).
- `429 RATE_LIMITED` → blind exponential `sleep` backoff (`5 → 15 → 45 → 90`), max 4 retries per
  call (Step 3c). If an image is still rate-limited after that, the circuit breaker (Step 3d) stops
  further uploads, ensures a text draft exists, and reports the rest as manual-attach notes — return
  `completed (partial)`. Never retry a 429 without a `sleep`, and never exceed the retry cap.

## Guardrails

- Drafts only. Never schedule or auto-post. No schedule date, no publish/share flag. The human posts
  in Typefully.
- Never threadify. Keep `threadify` off so the LinkedIn copy stays one post, even with blank lines.
- Never rewrite copy. Publish the approved text verbatim — words, punctuation, and order unchanged. The
  one permitted transformation is paragraph-spacing normalization (Step 1b): adjusting the blank lines
  between paragraphs so LinkedIn renders the intended breaks. Whitespace only, never the words.
- Never write to the Notion card. The orchestrator owns card writes; this skill returns URLs.
- Playbook-agnostic. No playbook names hard-coded — behavior derives only from the card's approved
  LinkedIn copy + surviving images. New LinkedIn-output playbooks need no change here; just add
  `publish-to-typefully` to that playbook's `Skill-2`.
- LinkedIn only (v1). Ignore other channels even if the Typefully account supports them.
- Respect the rate limit. Never fire uploads in parallel or via a background agent; never
  retry a `429` without a `sleep` backoff first; never exceed 4 retries per call or the per-image
  circuit breaker. One asset per variant (`@2x`), uploaded sequentially with a `sleep 3` pace.

## Skill Chaining

- Upstream: the stage-1 `linkedin` (and any LinkedIn card render skills) produced the copy/images now
  on the card.
- This skill runs last in a playbook's `Skill-2` chain — after any stage-2 image renders — so it
  drafts the final, human-reviewed assets.
- Sub-skill: `download-from-notion` (URL mode) — to fetch stage-1 image bytes before the presign+PUT
  upload.
