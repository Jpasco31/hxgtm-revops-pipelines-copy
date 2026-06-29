# Segments New — Framer CMS Reference

Framer CMS structure for segment landing pages using the "Segments New" template: page URLs, collection schema, field IDs, layout zones, and publishing field mapping.

> **These IDs and case names are a cache, not the source of truth.** Collection IDs and field IDs differ between Framer projects and can change over time. `format-for-framer` reconciles this file against the **live** schema via a required `framer.agent.getNodesOfTypes({types:["CollectionNode"]})` preflight (Step 1.5) on every forward run and maps to the live values — surfacing any drift in the bundle's `Schema drift:` section. Update the cached values here opportunistically when you notice drift, but do not treat them as authoritative.

---

## Framer CMS Structure

### Pages

- Detail template: `/segments/<slug-dont-touch>` (driven by the `Slug / don't touch` field — `XwXTH81Ht`)

> **URL pattern to verify.** Based on existing items (`reinsurance`, `us-admitted`, `specialty-and-commercial`, `mga`), the routing slug appears to be the `Slug / don't touch` field. Confirm the live URL with the web team before publishing.

### CMS Collections

Flat single collection — no linked sub-collections.

#### Segments New (id: `iGaJ4omkL`)

One item per published segment landing page.

---

### SEO / Page Identity

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `XwXTH81Ht` | Slug / don't touch | string | **URL routing slug** — drives the page URL path (e.g. `reinsurance`, `mga`). Set once on create; do not change on updates. |
| `PxW6Tsk34` | Page Name | string | Short display name for the segment (e.g. `Reinsurance`, `MGA`) |
| `X75x3WJdp` | Page Title | string | SEO `<title>` tag |
| `D_lRCDn0l` | Meta Description | string | SEO meta description |
| `isJYQq4Ov` | Slug | string | Secondary slug identifier — existing items use a `how-<role>-teams-use-hx` pattern |

---

### Hero Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `l981vHE0Q` | hero-H1-title | string | Page H1 headline |
| `VN0WdzQls` | hero-paragraph | string | Hero subheading / intro paragraph |
| `SJGghq5ST` | hero-pillar-1-title | string | First pillar label |
| `dXYjYS_lb` | hero-pillar-1-description | string | First pillar supporting copy |
| `eAzmKZWJg` | hero-pillar-2-title | string | Second pillar label |
| `n6JUnoVDk` | hero-pillar-2-description | string | Second pillar supporting copy |
| `ZQz3G77Z4` | hero-pillar-3-title | string | Third pillar label |
| `pt9NMzTi5` | hero-pillar-3-description | string | Third pillar supporting copy |

---

### Box Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `acx12sIFU` | box-section-h2-title | string | Section H2 heading |
| `gUolwOhKh` | box-section-paragraph | string | Section intro paragraph |
| | **Box 1** | *divider* | |
| `OXaXeihsw` | box-1-title | string | Box 1 heading |
| `R0ymkoT8g` | box-1-description | string | Box 1 supporting copy |
| `tgDvqpFBa` | box-1-image-option | enum | Selects the pre-built product screenshot to display. Case names: `Triage`, `Pricing & Rating`, `Portfolio Intelligence`, `Decision Engine`, `Governance` |
| `E0R3l35V5` | box-1-image-background | enum | Background style behind the image. Case names: `Plain White`, `Dots_Rectangle Mask`, `Dots_Round Mask`, `Grid` |
| `bIe41TNty` | box-1-image | image | Custom image override (optional — use only when none of the enum options fit) |
| | **Box 2** | *divider* | |
| `BlC4t9a_8` | box-2-title | string | Box 2 heading |
| `XKpTD_Wfp` | box-2-description | string | Box 2 supporting copy |
| `FneqydGYY` | box-2-image-option | enum | Same cases as box-1-image-option: `Triage`, `Pricing & Rating`, `Portfolio Intelligence`, `Decision Engine`, `Governance` |
| `xD0US_bHN` | box-2-image-background | enum | Same cases as box-1-image-background: `Plain White`, `Dots_Rectangle Mask`, `Dots_Round Mask`, `Grid` |
| `Zn_okil0S` | box-2-image | image | Custom image override (optional) |
| | **Box 3** | *divider* | |
| `W4QNGH4IO` | box-3-title | string | Box 3 heading |
| `ihaBVSWUt` | box-3-description | string | Box 3 supporting copy |
| `zZxUrQKHG` | box-3-image-option | enum | Same cases as box-1-image-option |
| `ADvvaOcN3` | box-3-image-background | enum | Same cases as box-1-image-background |
| `nuWCfGq4g` | box-3-image | image | Custom image override (optional) |
| | **Box 4** | *divider* | |
| `XU_VGLO1E` | box-4-title | string | Box 4 heading |
| `c4hWnVa3U` | box-4-description | string | Box 4 supporting copy |
| `rcK8heTDO` | box-4-image-option | enum | Same cases as box-1-image-option |
| `ISr7yn4sg` | box-4-image-background | enum | Same cases as box-1-image-background |
| `pPOgicgSI` | box-4-image | image | Custom image override (optional) |

---

### Compare Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `BzK7JMRZC` | Compare-H2-Title | string | Section H2 heading (e.g. "The old way vs. the hx way") |
| `wKEMu7SNV` | Row 1 → Legacy | richtext | Legacy approach description for row 1 |
| `Z1wN2uZUE` | Row 1 → New | richtext | hx/new approach description for row 1 |
| `jWwbJwOSt` | Row 2 → Legacy | richtext | Legacy approach description for row 2 |
| `vBvvXgQA5` | Row 2 → New | richtext | hx/new approach description for row 2 |
| `cmMdNHrk_` | Row 3 → Legacy | richtext | Legacy approach description for row 3 |
| `wqxhLA49P` | Row 3 → New | richtext | hx/new approach description for row 3 |
| `NIbKBSmYk` | Row 4 → Legacy | richtext | Legacy approach description for row 4 |
| `XtfpxT5h5` | Row 4 → New | richtext | hx/new approach description for row 4 |
| `QI715DnC9` | Row 5 → Legacy | richtext | Legacy approach description for row 5 |
| `Tve_mAIZP` | Row 5 → New | richtext | hx/new approach description for row 5 |

---

### Ecosystem Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `ZsULXWsHX` | ecosystem-title | string | Section heading |
| `JqxWlEsd7` | ecosystem-card-1-icon | icon | Framer icon for card 1 — set via Framer canvas; cannot be set via `applyChanges`. Flag for manual entry. |
| `JLDxKRJZF` | ecosystem-card-1-title | string | Card 1 heading |
| `YhoO3g8Bk` | ecosystem-card-1-paragraph | string | Card 1 supporting copy |
| `Yx2WkFg_T` | ecosystem-card-2-icon | icon | Framer icon for card 2 — flag for manual entry. |
| `sfUUJigex` | ecosystem-card-2-title | string | Card 2 heading |
| `DB6bI2W_f` | ecosystem-card-2-paragraph | string | Card 2 supporting copy |
| `qWLB7cEoj` | ecosystem-card-3-icon | icon | Framer icon for card 3 — flag for manual entry. |
| `QIhgP5_hY` | ecosystem-card-3-title | string | Card 3 heading |
| `km8fmdLIm` | ecosystem-card-3-paragraph | string | Card 3 supporting copy |

---

### FAQ & Tab Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `wQpOMojhq` | FAQ-Section ? | boolean | Toggle to show/hide the FAQ section on the page |
| `Ly8uwJPZ7` | Tab Section H 2 Title | string | H2 heading above the tab component |
| | **Tab 1** | *divider* | |
| `ZuHn3BQ_q` | Tab 1 Image | image | Screenshot or visual for tab 1 |
| `VoIfJcL9b` | Tab 1 Image Gradient | enum | Gradient overlay on tab 1 image. Cases: `Orange 1`, `Orange 4`, `Burgundy 1`, `Burgundy 2`, `Burgundy 6`, `Light Blue 2`, `Light Blue 4`, `Light Blue 5`, `Light Blue 6`, `Blue 4`, `Blue 6`, `Blue 7`, `Mix 3`, `Green 4`, `Flat` |
| `TACHRYKGG` | Tab 1 Title | string | Tab 1 label / heading |
| `BZDl9qU9I` | Tab 1 Description | richtext | Tab 1 body copy |
| | **Tab 2** | *divider* | |
| `O4geivOyi` | Tab 2 Image | image | Screenshot or visual for tab 2 |
| `Trf3dSdYP` | Tab 2 Image Gradient | enum | Same cases as Tab 1 Image Gradient |
| `lZoJgPidm` | Tab 2 Title | string | Tab 2 label / heading |
| `Dde6T0nb8` | Tab 2 Description | richtext | Tab 2 body copy |
| | **Tab 3** | *divider* | |
| `aH557jtwX` | Tab 3 Image | image | Screenshot or visual for tab 3 |
| `PGoIHv1UI` | Tab 3 Image Gradient | enum | Same cases as Tab 1 Image Gradient |
| `P8gaZ5Q9X` | Tab 3 Title | string | Tab 3 label / heading |
| `J23GROIsT` | Tab 3 Description | richtext | Tab 3 body copy |
| | **Tab 4** | *divider* | |
| `qbzVGZSlA` | Tab 4 Image | image | Screenshot or visual for tab 4 |
| `o6sSKWXew` | Tab 4 Image Gradient | enum | Same cases as Tab 1 Image Gradient |
| `VQBXWyZEV` | Tab 4 Title | string | Tab 4 label / heading |
| `fyGF3TNzm` | Tab 4 Description | richtext | Tab 4 body copy |
| | **Tab 5** | *divider* | |
| `WBVRUBIuK` | Tab 5 Image | image | Screenshot or visual for tab 5 |
| `QBHF4M8vU` | Tab 5 Image Gradient | enum | Same cases as Tab 1 Image Gradient |
| `KHJvTZQhu` | Tab 5 Title | string | Tab 5 label / heading |
| `yGQQhVBLE` | Tab 5 Description | richtext | Tab 5 body copy |
| | **Tab 6** | *divider* | |
| `NvQb2kjOj` | Tab 6 Image | image | Screenshot or visual for tab 6 |
| `ih8iAmkcC` | Tab 6 Image Gradient | enum | Same cases as Tab 1 Image Gradient |
| `FzirYPx1Q` | Tab 6 Title | string | Tab 6 label / heading |
| `ZWua6kUfo` | Tab 6 Description | richtext | Tab 6 body copy |
| | **Tab 7** | *divider* | |
| `yqup241FE` | Tab 7 Image | image | Screenshot or visual for tab 7 |
| `eQDhBc0vb` | Tab 7 Image Gradient | enum | Same cases as Tab 1 Image Gradient |
| `V6RKF3ELU` | Tab 7 Title | string | Tab 7 label / heading |
| `Q6SjOfK43` | Tab 7 Description | richtext | Tab 7 body copy |
| | **Tab 8** | *divider* | |
| `DY3t1T_ii` | Tab 8 Image | image | Screenshot or visual for tab 8 |
| `l1vL51UOU` | Tab 8 Image Gradient | enum | Same cases as Tab 1 Image Gradient |
| `DO2vrRZl3` | Tab 8 Title | string | Tab 8 label / heading |
| `DzxAJaEsm` | Tab 8 Description | richtext | Tab 8 body copy |

---

### Page Layout Zones

```
Zone 1 — SEO / Page Identity (not visible on page)
  ├── Slug / don't touch ← routing slug (XwXTH81Ht)
  ├── Page Name ← short segment name (PxW6Tsk34)
  ├── Page Title ← SEO title (X75x3WJdp)
  ├── Meta Description ← SEO description (D_lRCDn0l)
  └── Slug ← secondary identifier (isJYQq4Ov)

Zone 2 — Hero
  ├── H1 Title ← hero-H1-title (l981vHE0Q)
  ├── Paragraph ← hero-paragraph (VN0WdzQls)
  └── Pillars (3)
        ├── Pillar 1: Title (SJGghq5ST) + Description (dXYjYS_lb)
        ├── Pillar 2: Title (eAzmKZWJg) + Description (n6JUnoVDk)
        └── Pillar 3: Title (ZQz3G77Z4) + Description (pt9NMzTi5)

Zone 3 — Box Section
  ├── H2 Title ← box-section-h2-title (acx12sIFU)
  ├── Paragraph ← box-section-paragraph (gUolwOhKh)
  └── Boxes (4)
        Each box: Title + Description + Image Option enum + Image Background enum + (optional) Image

Zone 4 — Compare Section
  ├── H2 Title ← Compare-H2-Title (BzK7JMRZC)
  └── Rows (up to 5)
        Each row: Legacy richtext + New richtext

Zone 5 — Ecosystem Section
  ├── Title ← ecosystem-title (ZsULXWsHX)
  └── Cards (3)
        Each card: Icon (manual) + Title + Paragraph

Zone 6 — FAQ (conditional)
  └── FAQ-Section toggle ← (wQpOMojhq) — shows/hides the FAQ section

Zone 7 — Tab Section
  ├── H2 Title ← Tab Section H 2 Title (Ly8uwJPZ7)
  └── Tabs (up to 8)
        Each tab: Image + Image Gradient enum + Title + Description richtext
```

---

### Default Field Values

| Field | Field ID | Default |
|---|---|---|
| FAQ-Section ? | `wQpOMojhq` | `false` |

> No other boolean/enum defaults are confirmed from existing items. Omit tabs and compare rows if the brief doesn't supply content for them — do not send empty strings.

---

### CMS Notes

- **Flat single collection** — no linked sub-collections. All content is inline on the primary item.
- **"Slug / don't touch"** (`XwXTH81Ht`) is the URL routing slug. Set it on create using the segment's short identifier (e.g. `reinsurance`, `mga`). Do not change it on updates — changing it breaks the live URL.
- **"Slug"** (`isJYQq4Ov`) appears to use a different convention from existing items (`how-<role>-teams-use-hx`). Confirm the intended pattern with the web team before setting on new pages.
- **icon fields** (`ecosystem-card-1-icon`, `ecosystem-card-2-icon`, `ecosystem-card-3-icon`) — the `icon` type cannot be written via `applyChanges` DSL. Always add these to the `Manual actions` list in the bundle.
- **richtext fields** (Compare rows, Tab descriptions) — use `formattedText` HTML encoding with `<p>`, `<strong>`, `<ul>/<li>`. Omit rows/tabs for which no content is provided; do not send empty strings.
- **Tab Image Gradient enum** — 15 named cases. Always confirm against the live `cases[]` from the Step 1.5 preflight before encoding.
- **Box image-option enum** — selects a pre-built product screenshot (`Triage`, `Pricing & Rating`, `Portfolio Intelligence`, `Decision Engine`, `Governance`). Use the enum rather than a custom image whenever a standard screenshot fits.
- **Box image-background enum** — controls the background style. `Plain White` is the safe default when not specified.
- **Compare rows** — use only the rows needed (1–5). Do not emit empty richtext for unused rows.
- **Tab section** — up to 8 tabs supported. Omit tab fields (image, gradient, title, description) for any tab slot beyond the content provided.

---

## Framer Publishing Field Mapping

When producing output that will be published to Framer, structure the deliverable with clear labels for each CMS field:

### SEO / Page Identity
- **Slug / don't touch** (`XwXTH81Ht`) — URL routing slug (e.g. `reinsurance`)
- **Page Name** (`PxW6Tsk34`) — short segment name
- **Page Title** (`X75x3WJdp`) — SEO title tag
- **Meta Description** (`D_lRCDn0l`) — SEO meta description
- **Slug** (`isJYQq4Ov`) — secondary slug (confirm pattern with web team)

### Hero
- **hero-H1-title** (`l981vHE0Q`)
- **hero-paragraph** (`VN0WdzQls`)
- **hero-pillar-1-title** (`SJGghq5ST`) / **hero-pillar-1-description** (`dXYjYS_lb`)
- **hero-pillar-2-title** (`eAzmKZWJg`) / **hero-pillar-2-description** (`n6JUnoVDk`)
- **hero-pillar-3-title** (`ZQz3G77Z4`) / **hero-pillar-3-description** (`pt9NMzTi5`)

### Box Section
- **box-section-h2-title** (`acx12sIFU`) / **box-section-paragraph** (`gUolwOhKh`)
- Per box (1–4): **title** / **description** / **image-option** (enum) / **image-background** (enum) / **image** (optional URL)

### Compare Section
- **Compare-H2-Title** (`BzK7JMRZC`)
- Per row (1–5): **Row N → Legacy** (richtext) / **Row N → New** (richtext)

### Ecosystem Section
- **ecosystem-title** (`ZsULXWsHX`)
- Per card (1–3): **icon** (manual) / **title** / **paragraph**

### FAQ & Tab Section
- **FAQ-Section ?** (`wQpOMojhq`) — `false` (default)
- **Tab Section H 2 Title** (`Ly8uwJPZ7`)
- Per tab (1–8): **Tab N Image** (image URL) / **Tab N Image Gradient** (enum) / **Tab N Title** / **Tab N Description** (richtext)

> **Icon fields** (`JqxWlEsd7`, `Yx2WkFg_T`, `qWLB7cEoj`) — always emit as Manual actions. Cannot be set via applyChanges.
