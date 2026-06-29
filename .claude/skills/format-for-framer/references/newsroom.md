# Newsroom — Framer CMS Reference

Framer CMS structure for newsroom press releases: page URLs, collection schema, field IDs, layout zones, and publishing field mapping. Editorial guidance (release-type playbooks, formatting rules, boilerplate) lives separately in the `press-release` skill (in the `hx-plugins` repo — not migrated here).

> **These IDs and case names are a cache, not the source of truth.** Collection IDs and field IDs differ between Framer projects; **enum case _names_** are what the new Framer Agent CLI accepts (the old `mcp.unframer.co` MCP used opaque case IDs — those no longer apply). `format-for-framer` reconciles this file against the live schema via a required `framer.agent.getNodesOfTypes({types:["CollectionNode"]})` preflight on every forward run.

---

## Framer CMS Structure

### Pages

- Listing page: `/newsroom`
- Detail template: `/newsroom/:slug`

Page nodeIds are not yet captured in this reference. They are not required for publishing — `format-for-framer` only needs collection IDs and field IDs.

### CMS Collections

Primary flat collection plus one linked sub-collection for quotes.

#### 📄 Newsroom (id: `RwO5YeFWg`)

One item per published press release.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `nU9BrfvXv` | Title | string | Headline. Sentence case. |
| `J5xhPZKGd` | Thumbnail | image | Card image used on the `/newsroom` listing and social sharing. Requires manual upload if no URL is available. |
| `zfI0pNVNO` | Date | date | ISO 8601 (e.g. `2026-05-12T00:00:00.000Z`). Drives listing sort and the dateline date shown on the detail page. |
| `h5VRdSPAe` | Category | enum | Case name (one of): `Company`, `Awards`, `Customers`, `Partnerships` |
| `SYbSfqRml` | Description | string | Short listing description / meta description. 140–180 chars. |
| `rjFLl9EVo` | Reading Time | string | Minutes as a number string (e.g. `"3"`). |
| `ebIIpNhGY` | Content | formattedText | Primary rich-text body. HTML preferred — use `<h2>` for section breaks, `<p>` for paragraphs, `<strong>` for emphasis. Wire-style elements that do NOT belong here: dateline, boilerplate, media contact (all template-static — see below). |
| `PvKa97SWC` | Newsroom Quotes | multiCollectionReference | References items in the 💬 Newsroom Quotes collection (`vq6ySagx5`). |

#### 💬 Newsroom Quotes (id: `vq6ySagx5`)

Linked sub-collection. Rendered as pull-quote cards on the detail page.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `gpQlFhDoN` | Name | string | Full name of the speaker. |
| `DqKxaf6jp` | Role | string | Job title + company (e.g. "CEO, hyperexponential"). |
| `l4oAiu_XA` | Content | string | The pull-quote text. |
| `XecdsIuaI` | LinkedIn | link | Speaker's LinkedIn profile URL (optional). |
| `gNoROxpjv` | Video | image | Optional video thumbnail. |
| `jKY0dYa6c` | Department | string | Optional internal label (e.g. "Executive", "Engineering"). Leave blank unless the brief specifies. |

### Page Layout Zones

```
Zone 1 — Hero header
  ├── Eyebrow: "Press release" / Category label (template-static)
  ├── H1 title ← Title field (nU9BrfvXv)
  ├── Date row ← Date field (zfI0pNVNO)
  ├── Category badge ← Category field (h5VRdSPAe)
  └── Hero image ← Thumbnail field (J5xhPZKGd)

Zone 2 — Body
  └── Rich text Content ← Content field (ebIIpNhGY)
        Conventional structure: Lead paragraph → Body sections → Executive quotes inline (or as referenced Newsroom Quotes cards)
        H2 headings break the body into navigable sections

Zone 3 — Quote cards (optional)
  └── Pull-quote cards ← Newsroom Quotes multi-ref (PvKa97SWC)

Zone 4 — Static template footer
  ├── About hyperexponential boilerplate (template-static; sourced from press-release/references/boilerplate.md)
  ├── Media contact block (template-static)
  └── Related releases grid (auto-populated from the same collection, ordered by Date)
```

### CMS Notes

- **Boilerplate and media contact are template-static.** They live on the Framer newsroom detail page template, NOT in the CMS. Do not include them in the `Content` field — `format-for-framer` strips them at mapping time so the Framer page renders the canonical version from `press-release/references/boilerplate.md`.
- **Dateline is template-rendered.** The "CITY — Month DD, YYYY —" dateline is composed at render time from the `Date` field plus a hard-coded city on the template (or a future `Dateline City` field if added). The press-release Final Release still includes the wire-style dateline for distribution, but `format-for-framer` strips it from the `Content` field.
- **Embargo is not a CMS field today.** Embargoed releases are pushed via `framer.agent.applyChanges` (which only stages canvas changes — the page does not go live until someone runs publish in Framer). The press-release skill captures `embargoed: true/false` in Page Metadata so the publisher can flag it in the confirmation, but there is no Framer field to populate.
- **Reading Time is editorial.** The press-release skill estimates it; do not auto-calculate from word count at publish time.
- **Content is `formattedText`.** Use HTML with `<h2>` for body section headings, `<p>` for paragraphs, `<strong>` for emphasis, and `<a>` for inline links. Do not include `<h1>` — the page title occupies the H1 slot.
- **Newsroom Quotes** is a `multiCollectionReference`. Each quote is a standalone CMS record in `vq6ySagx5` that must be created before linking. Reuse existing quotes when speaker + content match.
- **Newsroom Quotes do not have a Theme enum** (unlike customer-story Quotes). Cards render in a default style.
- **No formal Index field on Newsroom Quotes** — display order on the detail page follows the order of IDs in the multi-ref array. Order them in the bundle the same way you want them rendered.

### Default Values

| Field | Field ID | Default |
|---|---|---|
| Reading Time | `rjFLl9EVo` | `"3"` if the press-release skill did not estimate one |
| Department (on linked Quotes) | `jKY0dYa6c` | blank |
| LinkedIn (on linked Quotes) | `XecdsIuaI` | omit when not provided |
| Video (on linked Quotes) | `gNoROxpjv` | omit when not provided |

---

## Framer Publishing Field Mapping

Used by `format-for-framer` (Forward mode) to encode the press release into a Framer Publish Bundle. Map the wire-style Final Release sections to the fields below:

### Primary (📄 Newsroom — `RwO5YeFWg`)

- **Title** (`nU9BrfvXv`) — Headline from the Final Release. Sentence case.
- **Description** (`SYbSfqRml`) — Use the Sub-headline if present; otherwise the first sentence of the Lead paragraph, trimmed to ~160 chars.
- **Date** (`zfI0pNVNO`) — ISO 8601, derived from the wire-style dateline date. Convert e.g. `15 April, 2026` → `2026-04-15T00:00:00.000Z`.
- **Category** (`h5VRdSPAe`) — Enum case **name** resolved from the Page Metadata `sub-type` per `format-for-framer`'s Enum Case Resolution table:
  - `customer-partnership` → `Customers`
  - `product-launch` → `Company`
  - `alliance-partnership` → `Partnerships`
  - `company-momentum` → `Company`
  - `executive-appointment` → `Company`
  - `award-recognition` → `Awards`
  - `research-data-release` → `Company`
  - `event-conference` → `Company`

  (The old `mcp.unframer.co` MCP used opaque case IDs like `JU6EGypzh`; the new Framer Agent CLI accepts case names as written on the live collection's `variables[].cases` array.)
- **Reading Time** (`rjFLl9EVo`) — From Page Metadata `reading-time`; default `"3"`.
- **Content** (`ebIIpNhGY`) — HTML assembled from the Lead paragraph and Body sections, with `<h2>` for any internal section breaks. Strip:
  - The wire dateline (template renders from the `Date` field)
  - Inline executive quote blocks if they are also being created as linked Newsroom Quotes (avoid duplication — pick one)
  - The boilerplate (About hyperexponential) and media contact (template-static)
  - The end mark `###`
- **Thumbnail** (`J5xhPZKGd`) — Image URL if provided; otherwise add to the bundle's manual-actions list.
- **Newsroom Quotes** (`PvKa97SWC`) — Populated by `publish-to-framer` after creating linked Quote items.

### Linked items (💬 Newsroom Quotes — `vq6ySagx5`)

For each executive quote block in the Final Release that should render as a pull-quote card (rather than inline prose), emit a linked-item entry with:

- **Name** (`gpQlFhDoN`) — Speaker full name from the attribution line.
- **Role** (`DqKxaf6jp`) — Speaker title + company from the attribution line.
- **Content** (`l4oAiu_XA`) — The quote text only (no surrounding "said X" wrapper).
- **LinkedIn** (`XecdsIuaI`) — Only when explicitly provided.
- **Video** (`gNoROxpjv`) — Only when provided; otherwise omit (image field).
- **Department** (`jKY0dYa6c`) — Only when explicitly provided.

Use Natural key: `Name + first 40 chars of Content` so the publisher can detect duplicate quotes across releases.

If a release contains exec quotes that the editorial intent is to render *inline* in the body rather than as cards, leave them in the `Content` HTML and do not emit them as linked items. The default for press releases is inline (matching wire conventions) — only break a quote out into a card when the brief explicitly asks for it.
