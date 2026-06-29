# Resources Landing Page — Framer CMS Reference

Framer CMS structure for resources landing pages: page URLs, collection schema, field IDs, layout zones, and publishing field mapping. Editorial guidance (section structure, copy conventions, QA checklist) is loaded separately via the `resources-landing-page` content-type playbook.

> **These IDs and case names are a cache, not the source of truth.** Collection IDs and field IDs differ between Framer projects; **enum case _names_** are what the new Framer Agent CLI accepts (the old `mcp.unframer.co` MCP used opaque case IDs — those no longer apply). `format-for-framer` reconciles this file against the live schema via a required `framer.agent.getNodesOfTypes({types:["CollectionNode"]})` preflight on every forward run.

---

## Framer CMS Structure

### Pages

- Listing page: `/resources` (nodeId `PUaVzgiap`)
- Detail template: `/resources/:slug` (nodeId `x4a5pD9n5`)

### CMS Collections

Primary flat collection plus one linked sub-collection for quotes.

#### Resources (id: `EiVuI6iES`)

One item per published resources landing page.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `gz9BuCdza` | Title | string | Resource headline |
| `OKb3OSH9s` | Thumbnail | image | Card image used on the listing page and social sharing |
| `KfW0k8P9C` | Resource Type | enum | Case name (one of): `Whitepaper`, `Podcast`, `Report`, `Blog` |
| `ppiTFrsPh` | Description | string | Short description used on listing cards and meta description |
| | **Visibility Toggles** | *divider* | |
| `DCF14RCx7` | Header? | boolean | **Default `false`** — show the navigation header on the page |
| `QU3vJG_KQ` | Featured? | boolean | **Default `false`** — feature this resource on the listing page |
| `EWst3Rwu1` | Show Eyebrow | boolean | **Default `false`** — show the eyebrow label above the title |
| `YelV36kxi` | Show Nav Links | boolean | **Default `false`** — show jump/nav links on the page |
| `hO8_TRimi` | Show Featured Resources | boolean | **Default `false`** — show the featured resources grid at the bottom |
| `Sxwkt2G63` | Show CTA | boolean | **Default `false`** — show the bottom CTA section |
| | **Gated Content** | *divider* | |
| `xlbCDKf1x` | Synopsis | formattedText | Rich-text body content — the main sell copy for the resource. Supports HTML with headings, paragraphs, lists. |
| `Wcm7X75lh` | Form Embed | string | HubSpot form UUID (not embed HTML). Each resource uses a form tuned to its topic. |
| | **Links** | *divider* | |
| `Kzi__WdnH` | File Upload | file | Direct PDF upload (allowed: `.pdf`). Use for downloadable assets. |
| `yqfpQWcos` | Article Link | link | External or internal link. Use for blog posts or external resources instead of a file upload. |
| `m7jrqh50L` | Resources Quote | collectionReference | Links to one item in the `Resources Quotes` collection (`ih86b13lM`) |
| `yzyfu4tzS` | Customer Stories | multiCollectionReference | Links to items in the `Customer Stories` collection (`IdUYGAXJB`). Used for the featured resources grid. |

#### Resources Quotes (id: `ih86b13lM`)

Optional linked quote displayed alongside the synopsis.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `fD4vdhe4H` | Name | string | Speaker name |
| `pAUVpgxFd` | Role | string | Speaker role / title |
| `zcWM1z2hx` | Content | string | Quote text |
| `a6qgDB7Ix` | Theme | enum | Case name (one of): `Red`, `Forest`, `Lilac` |

### Page Layout Zones

```
Zone 1 — Navigation (conditional)
  └── Navigation component ← controlled by Header? toggle (DCF14RCx7)

Zone 2 — Header
  ├── Back link ("All resources" → /resources)
  └── Container (two-column layout)
        ├── Content (left column)
        │     ├── Eyebrow (dot + label) ← controlled by Show Eyebrow toggle (EWst3Rwu1)
        │     ├── Title (H1) ← Title field (gz9BuCdza)
        │     └── Quote block ← Resources Quote reference (m7jrqh50L)
        │           └── QuoteCards component (Name, Role, Content from linked quote)
        └── Form (right column)
              ├── "Register now" label (H3)
              └── HubSpot form ← Form Embed field (Wcm7X75lh)

Zone 3 — Body / Synopsis
  └── Rich text content ← Synopsis field (xlbCDKf1x)
      Supports: H3 headings, paragraphs, bullet lists, bold text

Zone 4 — Featured Resources (conditional)
  ├── "Featured resources" heading
  └── 3-column grid of ResourceCard components
      └── Controlled by Show Featured Resources toggle (hO8_TRimi)
          Cards pull from Customer Stories reference (yzyfu4tzS) and related resources

Zone 5 — CTA (conditional)
  ├── CTA heading ("Accelerate your journey from submission to decision")
  ├── "Book a demo" button → /company/contact
  └── Controlled by Show CTA toggle (Sxwkt2G63)
```

### Default Toggle Values

These toggles must be set to `false` on every new resource item unless the brief explicitly requests otherwise:

| Toggle | Field ID | Default |
|---|---|---|
| Header? | `DCF14RCx7` | `false` |
| Featured? | `QU3vJG_KQ` | `false` |
| Show Eyebrow | `EWst3Rwu1` | `false` |
| Show Nav Links | `YelV36kxi` | `false` |
| Show Featured Resources | `hO8_TRimi` | `false` |
| Show CTA | `Sxwkt2G63` | `false` |

### CMS Notes

- **Flat primary structure with one linked sub-collection** — the primary Resources collection holds all content fields inline. The only linked collection is Resources Quotes (one optional quote per resource).
- **Synopsis is `formattedText`** — accepts HTML with `<h3>`, `<p>`, `<ul>/<li>`, and `<strong>` tags. Use `<h3>` for the synopsis lead-in heading, not `<h2>` (the page title occupies the H1 slot).
- **Form Embed is a plain string** — pass only the HubSpot form UUID, not an embed snippet or full URL.
- **Resource Type is an enum** — pass the case **name** as it appears on the live collection's `variables[].cases`: `Whitepaper`, `Podcast`, `Report`, `Blog`. (The old MCP's opaque case IDs no longer apply.)
- **File Upload vs Article Link** — use File Upload for gated PDFs (whitepapers, reports). Use Article Link for blog posts, podcast episodes, or external URLs. Only one should be populated per resource.
- **Customer Stories reference** — used to populate the featured resources grid when Show Featured Resources is enabled. Pass an array of Customer Stories item slugs.
- **Thumbnail** — used on the `/resources` listing page cards. Requires manual upload if no URL is available.

---

## Framer Publishing Field Mapping

When producing output that will be published to Framer, structure the deliverable with clear labels for each CMS field so the publisher can copy directly:

- **Title** (`gz9BuCdza`) — the resource headline
- **Thumbnail** (`OKb3OSH9s`) — card image URL (flag for manual upload if unavailable)
- **Resource Type** (`KfW0k8P9C`) — enum case **name**: `Whitepaper` / `Podcast` / `Report` / `Blog`
- **Description** (`ppiTFrsPh`) — short listing description
- **Header?** (`DCF14RCx7`) — `false` (default)
- **Featured?** (`QU3vJG_KQ`) — `false` (default)
- **Show Eyebrow** (`EWst3Rwu1`) — `false` (default)
- **Show Nav Links** (`YelV36kxi`) — `false` (default)
- **Show Featured Resources** (`hO8_TRimi`) — `false` (default)
- **Show CTA** (`Sxwkt2G63`) — `false` (default)
- **Synopsis** (`xlbCDKf1x`) — rich text (HTML)
- **Form Embed** (`Wcm7X75lh`) — HubSpot form UUID
- **File Upload** (`Kzi__WdnH`) — PDF URL (if applicable; flag for manual upload)
- **Article Link** (`yqfpQWcos`) — external URL (if applicable; omit for gated PDFs)
- **Resources Quote** (`m7jrqh50L`) — ID of a Resources Quotes item (if applicable)
- **Customer Stories** (`yzyfu4tzS`) — array of Customer Stories item slugs (if Show Featured Resources is enabled)
