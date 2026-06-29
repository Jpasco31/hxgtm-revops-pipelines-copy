---
name: format-for-framer
description: Map polished copy to Framer CMS fields by page type, producing a publish-ready bundle for publish-to-framer. Use after a content skill (web-copy, press-release, edit-impact-story) AND after human review of the final copy, so the mapping reflects the current copy — not a stale draft. Also use in reverse to pull an existing Framer page into the conversation as editable copy. Targets the official Framer Agent CLI (`npx @framer/agent@latest`); enums encode as case NAMES (live from the collection's variables), not opaque case IDs.
---

# Format for Framer

## Purpose

Translate between polished human-readable copy and the Framer CMS field schema for a given page type. This skill is the seam between editorial and publishing: it owns page-type routing, CMS reference loading, field-ID labeling, **enum case-name resolution**, HTML formatting for rich-text fields, and content-aware validation.

It never writes to Framer — that is `publish-to-framer`'s job. This separation exists so the mapping step can run *after* human review of the final copy, eliminating drift between what a human approved and what gets staged.

## API context

This skill targets the **official Framer Agent CLI** (`npx @framer/agent@latest`) — not the deprecated `mcp.unframer.co` MCP. Concretely:

- Collections, items, and fields are read via `framer.agent.getNodesOfTypes({ types: ["CollectionNode"] })` and `framer.agent.serialize`, not `getCMSCollections` / `getCMSItems` MCP tools.
- **Enum values encode as case _names_** (the strings on the live collection's `variables[].cases`), not opaque case IDs.
- CMS field values are addressed by `$control__<fieldId>` attributes on `CollectionItemNode`s; field IDs themselves still survive as opaque strings on the live `CollectionNode.variables[].id`.
- Items are written by the downstream `publish-to-framer` skill via `framer.agent.applyChanges(dsl)` using the `+CollectionItemNode` / `SET` DSL.
- The skill assumes a Framer Agent session is already wired up (see the `framer` skill at `~/.claude/skills/framer/SKILL.md` for setup); reuse its session id with `-s <id>` on every CLI call.

## When to Use

- After a content skill has produced Final Copy AND the human has reviewed (and possibly edited) it — to derive the Framer mapping from the *current* copy in the conversation
- When run inside the **Push to Production** routine — the copy is not in the conversation; follow the web-copy → Editable draft → Final Copy path on the card (see F1, "Card-grounded sourcing")
- When publishing externally-drafted copy (paste from Notion, Google Docs, email) — input is the page type plus the pasted copy
- When pulling an existing Framer page into the conversation for editing — see Reverse Mode
- When updating one or two fields on an existing page — emit a **thin** update bundle. With the new Framer Agent API, a `SET` on an existing `CollectionItemNode` only touches the keys you mention, so partial updates are safe and re-sending unchanged enums/references is **no longer required**. (Old MCP needed that workaround due to a label/slug round-trip bug; it's gone now.)

**Do not use if:**

- The user wants to draft new copy — use `web-copy`, `press-release`, or the relevant content skill first
- The user wants to push to Framer with no human review — that's a `web-copy` → `publish-to-framer` direct chain, which is intentionally not offered; human review is the contract

## Step 0 — Confirm the page type

Determine the page type before doing anything else. Detection order (first match wins):

1. **Page Metadata block on the linked working-copy page.** In a card-grounded run (see F1), once you have followed the Editable draft link, the linked page carries a `Page Metadata` block (`page-type` / `sub-type` / `slug`). This is authoritative — it exists in practice and reflects the human-reviewed working copy.
2. **Explicit Page Metadata header in the conversation.** If the conversation contains a `Page Metadata` block emitted by a content skill (`web-copy`, `press-release`, `edit-impact-story`), use its `page-type` value.
3. **Parent card's `Content Type-2` property.** In a card-grounded run, the Perkins card's `Content Type-2` wiring (e.g. `events-landing-page`) names the page type.
4. **Linked page's `Page Type` / `Sub Type` properties**, if present on the working-copy page.
5. **Skill context.** If a content skill produced the output, infer page type from the loaded playbook (`ads-landing-page`, `customer-impact-story` → `customer-story`, `events-landing-page`, `resources-landing-page`, press release → `newsroom`).
6. **Ask once if ambiguous:** *"Which page type is this? (ads-landing-page / resources-landing-page / events-landing-page / customer-story / newsroom / platform-new)"*

> **Team to validate.** The precedence between the linked page's Page Metadata block, the card's `Content Type-2` property, and the linked page's `Page Type` / `Sub Type` properties (sources 1, 3, 4) is provisional. They should agree in practice; if they disagree, the Page Metadata block wins and the discrepancy is worth surfacing to the team.

If the user names a page type not in the routing table below, tell them no CMS reference exists for that type and list the available options. Do not invent a mapping.

## Page Type Routing

Each page type maps to a CMS reference file containing collection IDs, field schemas, layout zones, and any enum case-name mappings.

| Page Type                | CMS Reference                                                           | Collection Structure                                                                           |
| ------------------------ | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `ads-landing-page`       | `.claude/skills/format-for-framer/references/ads-landing-page.md`       | Flat — single collection `EkLmddPnz`                                                           |
| `resources-landing-page` | `.claude/skills/format-for-framer/references/resources-landing-page.md` | Primary `EiVuI6iES` + optional linked Quotes `ih86b13lM`                                       |
| `events-landing-page`    | `.claude/skills/format-for-framer/references/events-landing-page.md`    | Primary `Zn5SeVKoW` + linked Speakers `zHb_jqjR3`                                              |
| `customer-story`         | `.claude/skills/format-for-framer/references/customer-story.md`         | Primary `IdUYGAXJB` + Quotes `vWjx7C_pn` + Stats `R6bUNUEd4` (Phase 2 for full linked publish) |
| `newsroom`               | `.claude/skills/format-for-framer/references/newsroom.md`               | Primary `RwO5YeFWg` + linked Quotes `vq6ySagx5`                                                |
| `platform-new`           | `.claude/skills/format-for-framer/references/platform-new.md`           | Flat — single collection `hDH7dx9nG` (no linked sub-collections)                               |
| `home-v2`                | `.claude/skills/format-for-framer/references/home-v2.md`                | **Static page** — no CMS collection. Nine zones; edits target node IDs via `SET` operations, not `+CollectionItemNode`. |
| `segments-new`           | `.claude/skills/format-for-framer/references/segments-new.md`           | Flat — single collection `iGaJ4omkL`. Hero + box section + compare table + ecosystem cards + tab section. Icon fields require manual entry. |
| `faqs`                   | `.claude/skills/format-for-framer/references/faqs.md`                   | Repeating FAQ-item collection (one item = one Q/A pair). **⚠ Bootstrap: field IDs are TBD — run live preflight before first publish.** Category enum groups items on the page; cases must be confirmed from live schema. |
| `platform`               | `.claude/skills/format-for-framer/references/platform.md`               | Flat — single collection `IKHkQVGhR` (distinct from Platform-new `hDH7dx9nG`). Hero + 3 pillars + 6-tab feature section + 3 ecosystem cards + testimonial toggle + FAQ toggle. |
| `blog`                   | `.claude/skills/format-for-framer/references/blog.md`                   | Primary `KrkigxyWx` + linked Author `Cgpo91lJp`. Category is a standalone enum (not a reference to Blog Categories collection). |

As new page types gain CMS references, add them here and to the Preview URL Construction table below.

## Step 1 — Load the CMS reference

Read the CMS reference file for the resolved page type. Treat the reference as a **cache/hint**, not the source of truth — it carries:

- Collection ID(s)
- Field IDs, names, types, and per-field notes (default values, required fields, formatted-text conventions, enum case-name mappings)
- Page URL pattern (used to construct preview links downstream)
- Multi-collection structure (for events, newsroom, customer-story)

The reference is a static file and **drifts**: Framer's internal IDs and enum case names differ between projects and can change over time. The **live Framer schema is authoritative** — Step 1.5 reconciles the two on every forward run.

If the reference file does not exist, stop and tell the user the page type has no CMS reference yet — it needs to be authored before publishing is possible.

## Step 1.5 — Live-schema preflight (forward mode; required)

Before mapping any copy, run a Framer Agent script that reads the live collection metadata and reconciles the reference against it. This is a **standard preflight on every forward run**, not a "suspected stale" fallback. (Reverse mode pulls live data directly via `framer.agent.serialize`, so it does not need this step.)

Example preflight script:

```js
// /var/folders/9r/6bc9bw3d48z3clhmgmnwry2w0000gn/T/framer/<session>-preflight-<page-type>.js
state.collections = await framer.agent.getNodesOfTypes({ types: ["CollectionNode"] });
state.preflight = state.collections.map((c) => ({
  id: c.id,
  name: c.name,
  fields: c.variables.map((v) => ({
    id: v.id,
    name: v.name,
    type: v.type,
    key: v.key, // the $control__... key used in applyChanges SET statements
    cases: v.cases ?? null, // for enums: array of case-name strings
  })),
}));
console.log(JSON.stringify(state.preflight, null, 2));
```

Run with `npx @framer/agent@latest exec -s <sessionId> -f <path>`.

See `framer-template-sync` (sibling maintenance skill) to audit and optionally rewrite the entire cached reference set in one pass.

For the resolved page type, cross-check against the live output:

1. **Collection IDs** — the primary collection and every linked sub-collection ID in the reference exist live, under the same names.
2. **Field IDs** — every field ID the mapping will use exists on the live collection, with a matching type.
3. **Enum case names** — for each enum field (e.g. Event Type, Button Text, Button Colour), every case **name** the mapping will emit exists in the live field's `cases` array. (Match on the literal `cases[]` string; live names may have cosmetic quirks — preserve them verbatim and do not "fix" them.)

**On any mismatch:** stop. Do **not** map against an ID or name that is absent live. Surface a drift table so the human sees exactly what moved:

```
Schema drift — <page type> (reference vs live)
- <kind>: reference `<ref-value>` → live `<live-value>` (<field/collection/enum name>)
- <kind>: reference `<ref-value>` → MISSING live (no equivalent found — needs human resolution)
```

For drift where the live equivalent is unambiguous (same name/role, new ID or new case name), **prefer the live value** for the emitted bundle and record the substitution in the bundle's `Schema drift:` section (see Output). For drift with no clear live equivalent (a field/enum that vanished), stop and ask the human how to proceed — never silently drop or guess. The bundle must map only to IDs and case names confirmed present in the live schema.

If the preflight script fails (Framer Agent CLI not connected, no session, etc.), stop and tell the user to connect the Framer Agent (`npx @framer/agent@latest setup` then `session new`) before mapping — do not emit a bundle mapped against the unverified reference.

## Step 2 — Choose direction

Ask the user which direction unless the conversation makes it obvious:

*"Are we mapping copy → Framer (forward) or pulling an existing page → editable copy (reverse)?"*

- **Forward** — Final Copy is present in the conversation; the user wants to publish or update.
- **Reverse** — The user has a slug for an existing Framer page and wants to bring it into the conversation for editing.

---

## Forward Mode — Copy → Framer Publish Bundle

### F1. Locate the current copy

Find the most recent **Final Copy** / **Final Release** / **Final Story** block in the conversation. If the human edited the copy after the content skill ran, use the edited version — that's the whole point of this skill running post-review.

If multiple candidate copy blocks exist (e.g., the content skill produced one and the human pasted a revised version), ask the user which to use. Never silently pick.

**Card-grounded sourcing (Push to Production).** If no Final Copy block is present in the conversation but the context contains a Perkins card body (the Push to Production routine passes the full card page body, including its `## Agent Outputs` / Step 1: Generate Assets Outputs section), the copy is one hop away — follow this path with the Notion MCP (`notion-fetch`):

1. In the card body, locate the **most recent `web-copy` subheading** under the Agent Outputs / Step 1: Generate Assets Outputs section. Ignore the other output subheadings (`linkedin`, `email`, `webinar-promo-card`) and anything that is not the page copy.
2. Within that web-copy section, find the **`Editable draft`** mention-page link — the human-editable working copy created by `save-to-notion`. Do **not** use the `Original output (read only)` link. `notion-fetch` the Editable draft page.
3. On the linked page, find the **Final Copy** section (a heading containing `Final Copy`, e.g. `## Web Copy — Final Copy`). Use its **current, human-edited** state — reviewers edit the draft in place, so the live page is the source of truth. That page's body — its `Page Metadata` block plus the copy — becomes the Final Copy for the rest of forward mode.

If any hop fails (no `web-copy` subheading, no `Editable draft` link, or no `Final Copy` section on the linked page), stop and report exactly which hop failed — do not silently fall back to another section or skill output. If both a conversation Final Copy **and** a card-grounded Editable draft are present, ask the user which to use (never silently pick).

If no Final Copy block is identifiable by any of the above, stop and ask the user to paste the copy explicitly.

### F2. Parse the Page Metadata header

Content skills emit a small `Page Metadata` header at the top of Final Copy:

```
Page Metadata
- page-type: <type>
- sub-type: <e.g. release-type, event-type — optional>
- slug: <if known; otherwise blank>
- additional-defaults: <only when the content skill set non-default toggles>
```

Read this block to pick up the sub-type (which drives enum case-name resolution — see Enum Case Resolution below) and any slug hint. If the block is missing, fall back to asking the user.

In a **card-grounded run** (F1), the `Page Metadata` block is read from the **linked working-copy page** rather than the conversation — parse it the same way. If the linked page has no `Page Metadata` block, fall back to the card-grounded page-type sources from Step 0 (the card's `Content Type-2` property, then the linked page's `Page Type` / `Sub Type` properties).

**`events-landing-page` slug fallback.** If `page-type` is `events-landing-page` and `slug` is blank, derive it by kebab-casing the Event Title (lowercase; non-alphanumerics replaced with `-`; runs of `-` collapsed; leading/trailing `-` stripped). This supports unattended runs from the Perkins Job Board where the user is not prompted for a slug. For every other page type, a blank slug still requires explicit input — do not infer.

### F3. Map each copy element to its field ID and type

Walk the copy section by section. For each piece of content, find the matching field in the CMS reference and encode it per the **Field Encoding Rules** table below.

Skip:

- Divider rows in the CMS reference (`*divider*` marker)
- Sections that are template-static and not CMS-driven (these are explicitly noted in each CMS reference — e.g., the company boilerplate and media contact on a newsroom page live on the page template, not the CMS)
- Optional fields with no value — omit from the bundle entirely. Do not send empty strings.

**`events-landing-page` — audience callout.** The Final Copy may include a labelled **audience callout** block (the target roles / segments for the event). The events CMS has **no audience field** (see `references/events-landing-page.md`), so do not invent one and do not silently drop it — **append the callout into the Event detail (`t2VbuiR_h`) rich-text body** as a trailing paragraph so it stays on-page. *Team to validate:* whether the audience callout belongs in the body copy or should be handled some other way is still open.

### F4. Resolve sub-type to enum case names

If the page type has an enum field driven by the sub-type, look it up in **Enum Case Resolution** below and encode it as the case **name** (the string from the live `variables[].cases` array). The downstream skill will write it as `$control__<fieldId>="<case-name>"` in `applyChanges` DSL.

> If the live preflight surfaced a different case name than what the reference lists (cosmetic differences, renames), prefer the **live** case name and record the substitution in the bundle's `Schema drift:` section.

### F5. Apply field defaults

For booleans and enums with documented defaults (see each CMS reference's "Default Field Values" section), set them to their defaults unless the brief explicitly overrode them on a `create`. **On update**, only include defaults if the brief says to change them — partial updates are safe (see "Update mode" below).

### F6. Plan linked sub-collection items

For page types with linked sub-collections (events Speakers, newsroom Quotes, customer-story Quotes/Stats):

- For each linked item in the source copy, build a field-by-field plan using the sub-collection's schema from the CMS reference.
- Mark each linked item with a "natural key" the publisher can use to detect duplicates (speaker name, quote author name + first 40 chars of content, etc.).
- Do not pre-populate the primary record's `multiCollectionReference` field with item IDs — the publisher fills this after creating the sub-items and collecting their canonical IDs via `applyChanges`' `renamedIds`.

### F7. Validate

Run the **Validation Checklist** in the section below. If any check fails, stop and either fix the mapping with the user or surface the issue clearly. Never silently emit a payload that fails validation.

### F8. Emit the Framer Publish Bundle

Produce the standard output block described under **Output — Framer Publish Bundle**. This is the exact structure `publish-to-framer` consumes.

### F9. Hand off to publish-to-framer

After emitting the bundle, tell the user:

*"Mapping ready. Run publish-to-framer to stage this in Framer, or edit any field above and re-run me to re-map. publish-to-framer will leave the item on the canvas — review and go live yourself in Framer."*

If the chain was invoked by a Post-Copy Options prompt that selected "Publish to Framer" or "Both", invoke `../publish-to-framer/SKILL.md` next, passing the bundle.

### Update mode (thin bundles allowed)

On `Action: update`, emit only the fields the human actually wants to change (plus `Slug` if it's changing). With the new Framer Agent API, `applyChanges`' `SET` on an existing `CollectionItemNode` leaves unmentioned `$control__` keys untouched server-side, so partial updates are safe and no enum/reference re-send is required. If you're unsure which fields changed (e.g. the human pasted a wholesale revision), emit a full bundle — the cost is the same, and it's still correct.

---

## Reverse Mode — Framer → Editable Copy

### R1. Confirm slug

Ask the user for the slug if they did not provide one. Do not infer.

### R2. Retrieve

Read the primary item via a Framer Agent script. Example:

```js
// /var/folders/9r/6bc9bw3d48z3clhmgmnwry2w0000gn/T/framer/<session>-pull-<page-type>-<slug>.js
const collectionId = "<primary-collection-id>";
const slug = "<slug>";

const items = await framer.agent.getNodesOfTypes({ types: ["CollectionItemNode"] });
const primary = items.find(
  (i) => i.$parentId === collectionId && i.attributes?.$control__slug === slug,
);
if (!primary) {
  console.log({ error: `No item with slug "${slug}" in ${collectionId}` });
} else {
  state.primary = primary;
  console.log(JSON.stringify(primary, null, 2));
}
```

For linked sub-collection items referenced from the primary record's `multiCollectionReference` fields, resolve each referenced item id via `framer.agent.getNode({ id: "<itemId>" })` (or another `getNodesOfTypes` filter) and gather the full attributes for each linked item.

If no primary item is found, report the error and stop.

### R3. Map field IDs to labels

Using the CMS reference plus the live preflight from Step 1.5 (you'll need to run it here too, since reverse mode needs current `cases[]` to map case names back to human labels), convert the returned attributes into a human-readable structure:

- For each populated `$control__<field-id>` attribute, output: ``**<Field Name>** (`<field-id>`): <value or HTML or current image URL or "(no image)">``.
- For `formattedText` fields, output the raw HTML value as-is so the human can edit it directly.
- For `enum` fields, show the case name as stored: `"Conference"`.
- For `multiCollectionReference` fields, output a nested list of the linked items with their own labeled fields.
- Skip divider markers.
- For image fields, note the current image URL (likely a `framerusercontent.com` URL) or "(no image)".

### R4. Emit the editable view

Output two parallel blocks:

1. **Current Final Copy** — a human-readable view assembled from the field values. Use the CMS reference's Layout Zones diagram as the structural template. The human reads and edits this block.
2. **Current Framer CMS Fields** — the same data, labeled by field ID, in the Framer Publish Bundle format. The publisher would consume this if the user wanted to push without further editing.

Then include:

```
Pulled from Framer.

Page type: <page type>
Slug: <slug>
Item ID: <primary itemId>
Linked item IDs: <list per sub-collection>
Preview: <full draft preview URL — built from `framer.agent.publish({action: "preview"})` staging/production URL + URL pattern>

Fields retrieved: <count>
```

Use a one-shot `framer.agent.publish({ action: "preview" })` call to fetch the site's staging/production URL — this does **not** publish, it just returns readiness diagnostics and URLs (discard the `confirmationHash`).

### R5. Hand back

Tell the user:

*"Edit any fields in 'Current Final Copy' above and run me again in forward mode (or run web-copy / press-release / edit-impact-story on a section) to re-map. Then run publish-to-framer to push the changes back as staged canvas changes. The primary item ID and any linked item IDs above will be reused for the update."*

---

## Field Encoding Rules

The bundle describes each field by ID, type, and value. `publish-to-framer` converts the bundle into `applyChanges` DSL of the shape:

```
+CollectionItemNode <tempId> parent="<collectionId>";
SET <tempId> $control__<fieldId>=<encoded-value> $control__<fieldId>=<encoded-value> …;
```

So the bundle's "encoded value" must match the DSL conventions below.

| CMS Field Type             | Bundle encoding (verbatim)                                                | Notes                                                                                                                                                                                                                                                                |
| -------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `string`                   | `"…"` (double-quoted; escape inner `"` as `\"`)                          | Plain text. No HTML.                                                                                                                                                                                                                                                  |
| `formattedText`            | `"<html>"` (double-quoted; escape inner `"` as `\"`)                     | HTML with `<p>`, `<h2>`/`<h3>`, `<ul>/<li>`, `<strong>`. If the value is single-paragraph plain text, pass the raw string in quotes the same way — Framer renders accordingly.                                                                                       |
| `boolean`                  | `"true"` / `"false"`                                                      | Always set both true/false explicitly when the field is in the reference's Default Field Values table — do not rely on server defaults.                                                                                                                                |
| `date`                     | `"YYYY-MM-DDTHH:mm:ss.sssZ"`                                              | ISO 8601 string. For date-only inputs, use `T00:00:00.000Z`.                                                                                                                                                                                                          |
| `enum`                     | `"<case-name>"`                                                           | **Live case name from `variables[].cases`, not a case ID.** This is the biggest delta from the old MCP path. Run the Step 1.5 preflight to get the authoritative case-name list per enum field.                                                                       |
| `number`                   | `<n>` (unquoted)                                                          | Numeric.                                                                                                                                                                                                                                                              |
| `image`                    | `"https://…"`                                                              | Durable URL. Framer asset URLs (`framerusercontent.com`) are ideal. For an expiring/source URL that must be re-hosted (e.g. a Notion presigned S3 headshot), annotate the bullet `(re-host via publisher)` — publish-to-framer re-hosts via `framer.uploadImage` before writing. If no URL is available at all, **do not include the field**, and add a manual-upload flag (see below). |
| `link`                     | `"https://…"`                                                              | Full URL.                                                                                                                                                                                                                                                             |
| `file`                     | `"https://…"`                                                              | URL to PDF or other allowed type. Same manual-upload flagging as image when missing.                                                                                                                                                                                  |
| `multiCollectionReference` | bundle holds linked-item natural keys; **publish-to-framer fills the IDs** | Do not populate at the mapping step.                                                                                                                                                                                                                                  |
| `collectionReference`      | `"<itemId>"`                                                               | Single item ID from the referenced collection (must be a live id).                                                                                                                                                                                                    |

### Manual upload flags

When a field needs content that cannot be encoded (e.g., an image with no URL, a PDF that hasn't been uploaded yet), do not include it in the bundle's primary or linked-item entries. Instead add it to the bundle's `Manual actions` list as:

```
- Manual upload required: <field name> (<field-id>) — <short reason>
```

The publisher surfaces this list in its confirmation so the human knows what to fix in Framer directly.

**Card-grounded runs.** Images on the Perkins card (speaker headshots, promo-card assets) are **expiring presigned S3 URLs** — they will 404 if stored as-is. Do **not** put the raw S3 URL in the bundle as the durable value. Handle by image role:

- **Speaker headshots** (each speaker's Image — events `qVU37w2bj`): encode the Image field with the card's source S3 URL as the value and annotate the bullet `(re-host via publisher)`. publish-to-framer downloads the bytes at publish time via `framer.uploadImage` so Framer stores a durable asset URL — **not** the S3 link. This is the default; do **not** emit a manual-upload flag for speaker headshots when a card image block exists. (See publish-to-framer Step 3.5 for the re-host mechanism. The new path uses `framer.uploadImage` and no longer needs the uguu.se/precheck dance the old MCP required.)
- **Event Thumbnail** (`g9_HlS7J7`) and other non-headshot assets: there is usually no durable thumbnail source on the card, so keep the **manual-upload flag** default — emit `Manual upload required: Thumbnail (g9_HlS7J7)`. Only switch a thumbnail to the `(re-host via publisher)` path when the card genuinely carries a dedicated thumbnail image block.

If the card has no image block for a speaker at all, fall back to the manual-upload flag for that speaker's Image.

## Enum Case Resolution

Page-type-specific tables for mapping content-skill sub-types to CMS enum case names. If a sub-type does not appear here, fall back to the per-page-type enum table in the CMS reference and ask the user when ambiguous. **Always reconcile against the live `cases[]` list from the Step 1.5 preflight** — case names below are the cache, not the source of truth.

### `newsroom` — Category

Press-release release type → newsroom Category case name:

| Press release release-type | Newsroom Category case name |
| -------------------------- | --------------------------- |
| `customer-partnership`     | Customers                   |
| `product-launch`           | Company                     |
| `alliance-partnership`     | Partnerships                |
| `company-momentum`         | Company                     |
| `executive-appointment`    | Company                     |
| `award-recognition`        | Awards                      |
| `research-data-release`    | Company                     |
| `event-conference`         | Company                     |

### `events-landing-page` — Event Type

Web-copy event sub-type → Event Type case name:

| Sub-type              | Case name        |
| --------------------- | ---------------- |
| Conference            | Conference       |
| Customer / User Group | Customer         |
| Hosted                | Hosted           |
| Virtual Event         | Virtual Event    |
| On-Demand             | On-Demand        |
| Partner               | Partner          |

### `resources-landing-page` — Resource Type

Per the CMS reference: `Whitepaper` / `Podcast` / `Report` / `Blog`. Ask the user when not stated in the brief.

### Themes (`Red` / `Forest` / `Lilac` / `Ink`)

Theme enums vary per collection — always look up the case names in the specific CMS reference (customer-story Quotes / customer-story Stats / resources-landing-page Quotes), not from a shared table.

## Validation Checklist

Run all applicable checks before emitting the bundle. Stop and surface failures.

**Universal**

- No field ID appears more than once in the primary entries.
- Every value matches its declared field type from the CMS reference (no strings in number fields, no opaque IDs in enum fields, etc.).
- Every enum value resolves to a known case **name** present in the live preflight's `cases[]` — case IDs are an error in the new API.
- `formattedText` HTML is well-formed (balanced tags). When unsure, fall back to plain-text encoding.
- Linked sub-collection items have all required fields (e.g., `Speaker Name` on the Event Speaker collection).

**`ads-landing-page` specific**

- Duplicate FAQ Question fields — if any two of `V8s9fKIW6`/`cfhH6k5_n`/`Fgm7NPUMA` share a value, stop and re-map the Q/A pairs.
- `HubSpot Form Embed` (`JXQuZShYO`) is populated — default to `69d534f3-87ce-4f71-802e-4753c7b03a38` if not specified.
- `Media Section Title` (`hnqLG_Jd_`), `Image` (`uWmQ2c9W0`), and `Youtube Video URL` (`P9mTBuReW`) all blank unless explicitly required.
- `CTA Title` (`nrUIYDd9l`) is `See hx in action`. `CTA Subtitle` (`VohRc33_1`) is `Your workflows, not a canned demo`.

**`resources-landing-page` specific**

- All six visibility toggles (`DCF14RCx7`, `QU3vJG_KQ`, `EWst3Rwu1`, `YelV36kxi`, `hO8_TRimi`, `Sxwkt2G63`) explicitly set to `false` unless the brief states otherwise.
- Exactly one of `File Upload` (`Kzi__WdnH`) or `Article Link` (`yqfpQWcos`) populated, not both.

**`events-landing-page` specific**

- `Event Type` (`d10V9zYZv`) enum resolved to a live case **name** from the sub-type.
- `Button Colour` (`LBRm6tnyM`) defaults to `Blue` (case name).
- At most one of `Form Embed` (`jYKylbsyR`) or `Outbound Link` (`mJzf5Njs7`) populated — never both. Both blank is **allowed but not silent**: the page publishes without a registration form or external CTA target, so the CTA button has nowhere to go. When both are blank, add a manual-actions warning: `CTA button has no destination — neither Form Embed nor Outbound Link is set; the Register button will not link anywhere until one is supplied.`
- Every Speaker has a `Speaker Name` (`UQtvBIio3`).
- `Slug` is present in the bundle — either user-supplied or auto-derived from the Event Title per the F2 fallback rule.

**`customer-story` specific**

- If `Show Summary?` (`dBt_NcJmd`) is true, all six summary fields populated.
- `Content` (`b0TURoa3D`) uses `<h2>` headings for body sections (these drive the sticky jump-link sidebar). Do not use `<h2>` for the page title — that's the `Title` field.
- Quote `Theme` and Stat `Theme` are case names, not IDs.

**`blog` specific**

- `Title` (`xewbvojrr`) present.
- `Date` (`MiLQyDyQL`) present and ISO 8601.
- `Category` (`gOsh1ghBb`) resolved to a live case name. Do not pass a Blog Categories item ID — `Category` is a standalone enum, not a collection reference.
- `Author` (`JoVV8raZT`) is a resolved Blog Authors item ID (not a name string). Look up or create the author before emitting the bundle.
- `Content` (`IikfM37Li`) uses `<h2>` headings for body sections (these drive the sticky table-of-contents sidebar). Do not use `<h1>`.
- `Slug` (`PWZkic1b2`) present and kebab-case.
- `Table of Contents` (`eP0RHwd9w`) defaults to `Show` unless the brief says otherwise.

**`newsroom` specific**

- `Title` (`nU9BrfvXv`) present.
- `Date` (`zfI0pNVNO`) present and ISO 8601.
- `Category` (`h5VRdSPAe`) resolved to a live case **name** from press-release sub-type, not blank.
- `Content` (`ebIIpNhGY`) does not include the boilerplate (About hyperexponential) or the media contact block — both are template-static.
- Embargo markers from the press release draft are NOT in `Content` — the publisher will leave the staged change un-published until the embargo lifts; no CMS field for embargo metadata exists today.

## Output — Framer Publish Bundle

Emit a fenced block that `publish-to-framer` reads verbatim. Keep the exact label format below.

```
Framer Publish Bundle

Page type: <type>
Collection ID: <primary collection id>
Slug: <user-supplied or from metadata; blank if not yet supplied>
Action: <create | update | unspecified>
Item ID: <only for update; from prior pull or user input>
Preview URL pattern: <e.g. /newsroom/<slug>>

Primary fields:
- <field-id> (<Field Name>, <type>): <encoded value>
- ...

Linked sub-collection items:
- Collection: <sub-collection-id> (<sub-collection name>)
  Reference field on primary: <primary field id> (<primary field name>)
  Items:
    - Natural key: <e.g. Speaker Name = "Jane Doe">
      Fields:
      - <field-id> (<Field Name>, <type>): <encoded value>
      - ...
    - ...

Manual actions:
- <one bullet per manual upload or external step>

Schema drift:
- <none | one bullet per reference→live substitution applied during Step 1.5, e.g. "Event Type case: reference `Virtual Event` → live `irtual Event` (matched by position)" or "Field id: reference `acFXkAH5n` (no longer used in new API)">

Validation: passed
```

The `Collection ID` line, every `<field-id>`, and every `enum` case **name** in the bundle must be **live values confirmed by the Step 1.5 preflight**, not raw reference values. List every substitution under `Schema drift:` (or `none`) so the publisher and the human can see what moved. If validation fails, replace the final line with `Validation: FAILED` and list the failures above it.

## Preview URL Construction

The publisher builds preview URLs from the site URL (resolved via `framer.agent.publish({ action: "preview" })`) + the URL pattern below.

| Page Type                | URL Pattern                          |
| ------------------------ | ------------------------------------ |
| `ads-landing-page`       | `<site-url>/explore/<slug>/draft`    |
| `resources-landing-page` | `<site-url>/resources/<slug>`        |
| `events-landing-page`    | `<site-url>/events/<slug>`           |
| `customer-story`         | `<site-url>/customer-stories/<slug>` |
| `newsroom`               | `<site-url>/newsroom/<slug>`         |
| `platform-new`           | `<site-url>/platform-new/<slug>`     |
| `home-v2`                | `<site-url>/home-v2`                 |
| `segments-new`           | `<site-url>/segments/<slug-dont-touch>` |
| `faqs`                   | `<site-url>/faqs` |
| `platform`               | `<site-url>/platform/<slug>` |
| `blog`                   | `<site-url>/blog/<slug>` |

If the page type uses a different preview URL convention (e.g., explicit `/draft` suffix for ads), it is in the per-page-type CMS reference too.

## Framer Agent Reference

This skill **reads** from Framer in both modes via the Framer Agent CLI. It never writes to Framer (no `applyChanges`, no `publish`) — that's strictly `publish-to-framer`'s responsibility.

| Method                                              | Use                                                                                                          |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `framer.agent.getNodesOfTypes({types:["CollectionNode"]})`     | **Forward mode — required Step 1.5 preflight** (live collection/field/enum schema); also Reverse-mode cross-checks |
| `framer.agent.getNodesOfTypes({types:["CollectionItemNode"]})` | Reverse Mode — fetch primary + linked items by slug                                                          |
| `framer.agent.serialize({id, depth: 1})`            | Reverse Mode — read a collection plus its direct items when paginating                                       |
| `framer.agent.publish({action: "preview"})`         | Reverse Mode (and forward F8 if asked) — fetch staging/production URLs for preview links. **`preview` only — never `confirm_publish`.** |

In **card-grounded forward runs** (F1, Push to Production) it also **reads Notion** via the Notion MCP `notion-fetch` tool — once to follow the card's web-copy `Editable draft` link, and once to read the linked working-copy page's Final Copy. It still never writes to Notion or Framer.

Always reuse the existing Framer Agent session: `npx @framer/agent@latest exec -s <sessionId> -f <script-path>`. If no session exists, stop and direct the user to the `framer` skill (`~/.claude/skills/framer/SKILL.md`) for bootstrap.

## Guardrails

- Never modify, rewrite, or summarize copy during mapping. Translate verbatim.
- Always read the CMS reference fresh — do not memoize schemas across runs.
- If a copy element cannot be mapped to a CMS field, surface it in the bundle's Manual Actions list. Never silently drop content.
- If the human-readable copy is ambiguous (e.g., two candidates for "headline"), ask rather than guessing.
- Never publish. Hand off to `publish-to-framer` and let it own the write path; even `publish-to-framer` is forbidden from calling `confirm_publish` — the human goes live manually in Framer.
- Enums encode as case **names** (live from `variables[].cases`). Case IDs from the old MCP era are not accepted by the new API and must be reconciled away in Step 1.5.
- When run in reverse, preserve the primary `Item ID` and all linked item IDs in the output — the next forward run reuses them for partial updates.
