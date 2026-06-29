# Customer Story — Framer CMS Reference

Framer CMS structure for customer impact stories: page URLs, collection schema, field IDs, layout zones, and publishing field mapping. Editorial guidance (headline rules, section structure, tone) is loaded separately via the `customer-impact-story` content-type playbook.

> **These IDs and case names are a cache, not the source of truth.** Collection IDs and field IDs differ between Framer projects; **enum case _names_** are what the new Framer Agent CLI accepts (the old `mcp.unframer.co` MCP used opaque case IDs — those no longer apply). `format-for-framer` reconciles this file against the live schema via a required `framer.agent.getNodesOfTypes({types:["CollectionNode"]})` preflight on every forward run. The `Theme` enums below already use case names; verify them against the live `variables[].cases` array.

---

## Framer CMS Structure

### Pages

- Listing page: `/customer-stories` (nodeId `FmxCLC25O`)
- Detail template: `/customer-stories/:slug` (nodeId `J_1VsgBBR`)

### CMS Collections

Three linked collections. The primary record references the other two via multi-collection reference fields.

#### Customer Stories (id: `IdUYGAXJB`)

The primary CMS record. One item per published customer story.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `Va7uLHKjr` | Title | string | Full headline — displayed as H2 on the detail page |
| `RZ6bvZ7Se` | Name | string | Company name only (e.g. "Convex") |
| `aDIqZk5j2` | Thumbnail | image | Hero image on the detail page and card thumbnail |
| `JBdF_Pzw2` | Date | date | ISO 8601 |
| `nKVbnBVff` | Reading Time | string | Minutes as a number string (e.g. "5") |
| `ihbadDjuk` | Description | string | Short description — currently unused in most stories |
| `F9hdomdSL` | Featured? | boolean | Flags story for featured placement |
| `VxiyKGTEI` | Show in Form Reel | boolean | Flags story for reel/carousel |
| `iZiccKVSZ` | Featured Heading | string | Override heading for featured placement |
| `WXPP06lRt` | Featured Subheading | string | Override subheading for featured placement |
| `OdEcVW92K` | Stat | string | Top-line metric shown on the card (e.g. "85%") |
| `aYN_fuUIs` | Body Text | string | Stat caption — explains the metric (e.g. "of business priced on hx") |
| `dBt_NcJmd` | Show Summary? | boolean | Toggles the 3-panel summary block in Zone 1 |
| `qQi8CAmT3` | First Summary Title | string | Heading for summary panel 1 (H5) |
| `a7TOQMhkM` | Second Summary Title | string | Heading for summary panel 2 (H5) |
| `FRz6BSTtG` | Third Summary Title | string | Heading for summary panel 3 (H5) |
| `m41yT2yLj` | First Summary Text | string | Body copy for summary panel 1 |
| `rdRh56Cqo` | Second Summary Text | string | Body copy for summary panel 2 |
| `qdSPcEzL7` | Third Summary Text | string | Body copy for summary panel 3 |
| `b0TURoa3D` | Content | formattedText | Primary rich text body — H2 headings drive the sticky jump-links sidebar |
| `Upd0iYJzV` | Customer Story Quotes | multiCollectionReference | References items in the Customer Story Quotes collection (id: `vWjx7C_pn`) |
| `clM21r1Ee` | Customer Story Stats | multiCollectionReference | References items in the Customer Story Stats collection (id: `R6bUNUEd4`) |

#### Customer Story Quotes (id: `vWjx7C_pn`)

Separate records, referenced from the primary story. Rendered as pull-quote cards inline in the body.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `fFIrQxI64` | Name | string | Person's full name |
| `BUE2LWFDe` | Role | string | Job title + company (e.g. "Head of Aerospace, Convex") |
| `T8F5CGFg6` | Content | string | The pull quote text |
| `gnvuSc173` | Theme | enum | `Red` / `Forest` / `Lilac` |
| `bCjy1Jstx` | Index | number | Sort order within the story |

#### Customer Story Stats (id: `R6bUNUEd4`)

Separate records, referenced from the primary story. Rendered as a 2×2 stat tile grid.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `Ijg7VOnjT` | Amount | string | Stat figure (e.g. "4x", "85%") |
| `RXSFxtpVW` | Caption | string | Stat description |
| `Uev5zN9eG` | Theme | enum | `Red` / `Forest` / `Ink` |

### Page Layout Zones

```
Zone 1 — Hero header
  ├── Eyebrow: "Customer story" (static, not a CMS field)
  ├── H2 title (max 800px) ← Title field (Va7uLHKjr)
  ├── Hero image ← Thumbnail field (aDIqZk5j2)
  └── Summary grid (3 cols) — only shown when Show Summary? = true (dBt_NcJmd)
        └── Summary Title (H5) + Summary Text × 3

Zone 2 — Main body (horizontal split)
  ├── LEFT: Sticky ArticleJumpLinks sidebar
  │     Auto-generated from H2 headings in the Content field (b0TURoa3D)
  │     H2 headings must be meaningful section titles — they become the nav labels
  └── RIGHT column (max 700px)
        ├── Rich text Content (b0TURoa3D)
        │     Conventional structure: Background → Challenge → Solution → Results
        ├── QuoteCards component — from Customer Story Quotes multi-ref (Upd0iYJzV)
        └── StoryStatBlocks grid 2×2 — from Customer Story Stats multi-ref (clM21r1Ee)

Zone 3 — More Stories
  └── 3-col grid of CustomerStoriesCard components (auto-populated, not editable)
```

### CMS notes

- **Stats and Quotes are separate CMS records** — they must be created as standalone items in their respective collections, then linked via the multi-ref fields on the primary story. Label them clearly in any output that includes them.
- **Summary block is optional** — toggle `Show Summary?` on when there are 3 distinct outcome categories worth highlighting above the fold. Leave it off for stories that lead with a single strong narrative.
- **H2 headings in the Content field drive the jump-links sidebar** — every H2 becomes a nav item. Use clear, meaningful section titles. Avoid generic headings like "Overview."
- **Older stories (Convex, Rising Edge) don't use the Stats collection** — `clM21r1Ee` is empty on those records. That's a content gap, not a structural error.

---

## Framer Publishing Field Mapping

When producing output that will be published to Framer, structure the deliverable with clear labels for each CMS field so the publisher can copy directly:

- **Title** (`Va7uLHKjr`) — the canonical headline
- **Content** (`b0TURoa3D`) — the three body sections as HTML with `<h2>` tags for section headings
- **Quotes** — list each quote as a separate block: Name, Role, Content, Theme
- **Stats** — list each stat as a separate block: Amount, Caption, Theme
- **Summary titles and texts** — if three distinct outcomes exist, provide all six fields
