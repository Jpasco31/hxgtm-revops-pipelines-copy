# Blog — Framer CMS Reference

Framer CMS structure for blog posts: page URLs, collection schema, field IDs, layout zones, and publishing field mapping. Editorial guidance (headline conventions, section structure, tone) is loaded separately via the `blog` content-type playbook (not yet authored).

> **These IDs and case names are a cache, not the source of truth.** Collection IDs and field IDs differ between Framer projects; **enum case _names_** are what the Framer Agent CLI accepts (the old `mcp.unframer.co` MCP used opaque case IDs — those no longer apply). `format-for-framer` reconciles this file against the live schema via a required `framer.agent.getNodesOfTypes({types:["CollectionNode"]})` preflight on every forward run.
>
> **✅ IDs confirmed 2026-06-28.** Preflight run against session 1. All field IDs, collection IDs, and enum cases confirmed from live schema. Blog Authors collection also confirmed live.

---

## Framer CMS Structure

### Pages

- Listing page: `/blog`
- Detail template: `/blog/:slug`

Page nodeIds are not yet captured in this reference. They are not required for publishing — `format-for-framer` only needs collection IDs and field IDs.

### CMS Collections

Primary flat collection, one linked sub-collection for authors.

#### 📄 Blog (id: `KrkigxyWx`)

One item per published blog post.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `xewbvojrr` | Title | string | Post headline. Sentence case. |
| `iimuo3lb6` | Abstract | string | Short teaser shown on listing cards and as the opening hook. 1–2 sentences, 30–60 words. |
| `gOsh1ghBb` | Category | enum | Case name (one of): `Underwriting`, `AI`, `Announcements`, `Market trends`, `Pricing`, `Technology`, `Comparisons`, `People & Culture` |
| `MiLQyDyQL` | Date | date | ISO 8601 (e.g. `2026-06-04T00:00:00.000Z`). Drives listing sort and the dateline shown on the detail page. |
| `Z5L_RxEdi` | Cover Thumbnail | image | Card image used on the `/blog` listing. Often the same URL as Social Image. |
| `R0BpOp2re` | Social Image | image | OG/meta image for social sharing previews. Often the same URL as Cover Thumbnail. |
| `IikfM37Li` | Content | richtext | Primary rich-text body. HTML with `<h2>` for section breaks, `<p>` for paragraphs, `<strong>` for emphasis, `<a>` for links. `<h1>` is occupied by the Title — do not use it in Content. |
| `JoVV8raZT` | Author | single | Collection reference — ID of an item in the `📄 Blog Authors` collection (`Cgpo91lJp`). See Author Linking below. |
| `eP0RHwd9w` | Table of Contents | enum | **Default `Show`** — case name (one of): `Show`, `Hide` |
| `GH3DxOq3b` | Featured | boolean | **Default `false`** — flags post for featured placement on the listing page |
| `vNS5mOuUw` | SEO Title | string | SEO override for the page `<title>`. Default: same as Title. |
| `yHVZZZtVV` | SEO Description | string | Meta description. 140–160 chars. |
| `PWZkic1b2` | Slug | string | URL slug — kebab-case (e.g. `why-fragmented-intelligence-is-the-defining-problem`). |
| `PvaXcKnZI` | Story ID | string | Optional internal tracking ID. Leave blank unless the brief specifies one. |

#### 📄 Blog Authors (id: `Cgpo91lJp`)

Author profile records. Referenced from the primary Blog item via the `Author` field.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `uFodNPsBT` | Name | string | Author's full name |
| `m7ppCInOj` | Avatar | image | Headshot. Shown on the post detail page alongside the byline. |
| `GomfUhfXi` | Slug | string | Author slug (e.g. `amrit-santhirasenan`) |

Known live authors (confirmed 2026-06-28):

| Author ID | Name |
|---|---|
| `QE3osai_o` | Tom Chamberlain |
| `baatRMyOT` | Richard Gunn |
| `GKVw0Mgt7` | Kamlesh Walia |
| `PicQx0zlb` | *(check live)* |
| `c7HLuuytt` | *(check live)* |
| `ovywxt1E4` | *(check live)* |

> Run `framer.agent.getNodesOfTypes({types:["CollectionItemNode"]})` filtered by `$parentId === "Cgpo91lJp"` to get the full, current author list with IDs. Always use live IDs — do not use the cached IDs above as final values without verifying.

#### 📄 Blog Categories (id: `Xt_oIFkz6`)

Simple label collection used for filtering and nav. **Not referenced from Blog items** — the Blog `Category` field is a standalone enum, not a link to this collection. This collection powers the listing page's category filter UI only.

| Field ID | Field Name | Type |
|---|---|---|
| `zFtTjcNjt` | Title | string |
| `htPEd1t9_` | Slug | string |

---

### Page Layout Zones

```
Zone 1 — Hero header
  ├── Category badge ← Category field (gOsh1ghBb)
  ├── H1 title ← Title field (xewbvojrr)
  ├── Abstract / teaser ← Abstract field (iimuo3lb6)
  ├── Byline row
  │     ├── Author avatar + name ← Author reference (JoVV8raZT) → Blog Authors
  │     └── Date ← Date field (MiLQyDyQL)
  └── Cover image ← Cover Thumbnail field (Z5L_RxEdi)

Zone 2 — Body (horizontal split when ToC is shown)
  ├── LEFT: Table of contents sidebar (conditional)
  │     └── Auto-generated from H2 headings in Content ← Table of Contents (eP0RHwd9w) = Show
  └── RIGHT: Rich text Content ← Content field (IikfM37Li)
        H2 headings drive the sidebar nav — use meaningful section titles

Zone 3 — Related posts (auto-populated, not CMS-driven)
```

### CMS Notes

- **Author is a `single` collection reference** — the field stores the Blog Authors item ID. The author must exist in the `Cgpo91lJp` collection before the blog post can link to them. See Author Linking below.
- **Category is a standalone enum** — do NOT confuse with the Blog Categories collection (`Xt_oIFkz6`). The Category field on Blog items uses the enum case names directly (`Underwriting`, `AI`, etc.).
- **Table of Contents defaults to `Show`** — the sidebar auto-generates from H2 headings in the Content field. Set to `Hide` only when explicitly requested or when the post is very short.
- **H2 headings in Content drive the jump-links sidebar** — every `<h2>` becomes a nav item. Use clear, meaningful section titles. Avoid generic headings like "Overview."
- **Cover Thumbnail and Social Image** are often the same asset in practice — when only one image is provided in the brief, use it for both fields.
- **SEO Title** often mirrors Title — default to the same string unless the brief provides an SEO-optimised variant.
- **Story ID** is optional and appears unused on most posts. Leave blank unless specified.
- **Featured** is `false` by default; only set to `true` when explicitly requested.

---

### Author Linking

Blog posts reference one author via `Author` (`JoVV8raZT`) — a `single` collection reference that stores the author's item ID.

**To link an author:**

1. Run `framer.agent.getNodesOfTypes({types:["CollectionItemNode"]})` filtered by `$parentId === "Cgpo91lJp"` and match on `$control__uFodNPsBT` (Name).
2. If the author exists, use their item ID directly.
3. If the author does not exist, create them in `Cgpo91lJp` via `framer.agent.applyChanges` with a `+CollectionItemNode … parent="Cgpo91lJp"` + `SET … $control__uFodNPsBT="<name>" …` command. Use the `renamedIds` from `applyChanges` to get the canonical item ID.
4. Pass the resolved author item ID as the value for the `Author` field on the primary Blog item.

If the author's headshot (`Avatar`) is not available as a durable URL, flag it for manual upload.

---

### Default Field Values

| Field | Field ID | Default |
|---|---|---|
| Table of Contents | `eP0RHwd9w` | `Show` |
| Featured | `GH3DxOq3b` | `false` |
| SEO Title | `vNS5mOuUw` | same as Title |
| Story ID | `PvaXcKnZI` | blank |

---

## Framer Publishing Field Mapping

Used by `format-for-framer` (Forward mode) to encode the blog post into a Framer Publish Bundle.

### Primary (📄 Blog — `KrkigxyWx`)

- **Title** (`xewbvojrr`) — the post headline. Sentence case.
- **Abstract** (`iimuo3lb6`) — the listing-card teaser. 1–2 sentences, 30–60 words.
- **Category** (`gOsh1ghBb`) — enum case name from the table below.
- **Date** (`MiLQyDyQL`) — ISO 8601 from the post's publish date (e.g. `2026-06-28T00:00:00.000Z`).
- **Cover Thumbnail** (`Z5L_RxEdi`) — image URL if durable; otherwise flag for manual upload.
- **Social Image** (`R0BpOp2re`) — image URL (usually same as Cover Thumbnail); otherwise flag for manual upload.
- **Content** (`IikfM37Li`) — HTML assembled from the body sections, with `<h2>` for section headings. Do not include `<h1>` (the Title field occupies that slot).
- **Author** (`JoVV8raZT`) — resolved author item ID from the Blog Authors collection (see Author Linking).
- **Table of Contents** (`eP0RHwd9w`) — `Show` (default) or `Hide`.
- **Featured** (`GH3DxOq3b`) — `false` (default) or `true` if explicitly requested.
- **SEO Title** (`vNS5mOuUw`) — SEO override; default to same as Title.
- **SEO Description** (`yHVZZZtVV`) — meta description, 140–160 chars.
- **Slug** (`PWZkic1b2`) — kebab-case URL slug.

### Category Enum Cases

| Category | Use when |
|---|---|
| `Underwriting` | Posts about underwriting practice, workflows, decision-making |
| `AI` | Posts about AI, agents, machine learning in insurance |
| `Announcements` | Product launches, company news, press-adjacent posts |
| `Market trends` | Industry analysis, market conditions, macro trends |
| `Pricing` | Actuarial, pricing models, rate adequacy |
| `Technology` | Engineering, platform, tech stack, integrations |
| `Comparisons` | Versus posts, competitive positioning, vendor analysis |
| `People & Culture` | Team spotlights, company culture, hiring |

### Linked items (📄 Blog Authors — `Cgpo91lJp`)

Only needed when creating a **new** author not already in the collection:

- **Name** (`uFodNPsBT`) — Author's full name.
- **Avatar** (`m7ppCInOj`) — Headshot URL. Flag for manual upload if unavailable.
- **Slug** (`GomfUhfXi`) — Kebab-case author slug (e.g. `amrit-santhirasenan`).
