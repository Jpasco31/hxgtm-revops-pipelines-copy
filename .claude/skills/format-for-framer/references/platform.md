# Platform — Framer CMS Reference

Framer CMS structure for platform feature landing pages using the "Platform" template (distinct from "Platform-new"): page URLs, collection schema, field IDs, layout zones, and publishing field mapping.

> **These IDs and case names are a cache, not the source of truth.** Collection IDs and field IDs differ between Framer projects and can change over time. `format-for-framer` reconciles this file against the **live** schema via a required `framer.agent.getNodesOfTypes({types:["CollectionNode"]})` preflight (Step 1.5) on every forward run and maps to the live values — surfacing any drift in the bundle's `Schema drift:` section. Update the cached values here opportunistically when you notice drift, but do not treat them as authoritative.
>
> **IDs confirmed via live preflight 2026-06-24 against session 2 (project IsvU1UimOvOCYkmfxCGl).**

---

## Framer CMS Structure

### Pages

- Detail template: `/platform/<slug>` — confirm exact URL pattern with the web team; existing items include `submission-triage`, `decision-engine`, `pricing-and-rating`, `portfolio-intelligence`.

### CMS Collections

Flat single collection — no linked sub-collections.

#### Platform (id: `IKHkQVGhR`)

One item per published platform / use case landing page. Distinct from Platform-new (`hDH7dx9nG`).

Existing items (as of 2026-06-24):

| Slug | Page Name | Item ID |
|---|---|---|
| `decision-engine` | Decision Engine | `gG8amV8TP` |
| `portfolio-intelligence` | Portfolio Intelligence | `R1wangtPh` |
| `pricing-and-rating` | Pricing & Rating | `Vq3w11AgN` |
| `submission-triage` | Submission Triage | `jscamTWq2` |
| `pricing-and-rating-use-case` | Pricing & Rating Copy | `T0CgN9bBb` |
| `submission-triage-use-case` | Submission Triage Copy | `lspJ4reud` |
| `pricing-and-rating-new` | Pricing & Rating Copy | `UzEyNcsuh` |
| `submission-triage-new` | Submission Triage Copy | `FwOEAPjee` |

---

### SEO / Page Identity

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `Dygbimx17` | Slug / don't touch | string | **URL routing slug** — drives the page URL. Set once on create; do not change on updates. |
| `QF8irtwWP` | Page Name | string | Short display name for the page (e.g. `Submission Triage`) |
| `A8lstW2Uv` | Page Title | string | SEO `<title>` tag |
| `RQKgrn1cJ` | Meta Description | string | SEO meta description |

---

### Hero Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `QCS7gDMkx` | hero-H1-title | string | Page H1 headline |
| `yVRCSRund` | hero-paragraph | string | Hero subheading / intro paragraph |
| `aeB1La8j4` | Banner (video) Variant | enum | Selects the hero video/banner asset. Case names: `Submission`, `Pricing & Rating`, `Portfolio`, `Decision` |
| | **Hero Pillars (3)** | *divider* | Three benefit/pillar callouts displayed in the hero |
| `NT_K4geBT` | hero-pillar-1-title | string | Pillar 1 label (short, e.g. `Faster responses`) |
| `PxXo2YZYn` | hero-pillar-1-description | string | Pillar 1 supporting sentence |
| `gi6nK5ao1` | hero-pillar-2-title | string | Pillar 2 label |
| `vjVj9cxrI` | hero-pillar-2-description | string | Pillar 2 supporting sentence |
| `rFvxDwfSd` | hero-pillar-3-title | string | Pillar 3 label |
| `Unt8waFtq` | hero-pillar-3-description | string | Pillar 3 supporting sentence |

---

### Tab Section (Feature Showcase)

Up to 6 tabs. Each tab has an image, image gradient enum, title, and richtext description. Omit tab fields (image, gradient, title, description) for any slot beyond the content provided — do not send empty strings.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `hKZNHxRBO` | tab-section-h2-title | string | H2 heading above the tab component |
| | **Tab 1** | *divider* | |
| `fiWndVhax` | tab-1-image | image | Screenshot or visual for tab 1 |
| `yaQMMyi_I` | tab-1-image-gradient | enum | Gradient overlay. Cases: `Orange 1`, `Orange 4`, `Burgundy 1`, `Burgundy 2`, `Burgundy 6`, `Light Blue 1`, `Light Blue 2`, `Light Blue 4`, `Light Blue 5`, `Light Blue 6`, `Blue 4`, `Blue 6`, `Blue 7`, `Mix 1`, `Mix 3`, `Mix 4`, `Mix 5`, `Green 4`, `Deep Forest 2`, `Deep Forest 4`, `Flat` |
| `z1gf2aJUp` | tab-1-title | string | Tab 1 label / heading |
| `ky2Z5JgxM` | tab-1-description | richtext | Tab 1 body copy (`<p>`, `<strong>`, `<ul>/<li>`) |
| | **Tab 2** | *divider* | |
| `M4kYwcmB1` | tab-2-image | image | |
| `msVdWa5LI` | tab-2-image-gradient | enum | Same cases as tab-1-image-gradient |
| `Iv1y8LBZw` | tab-2-title | string | |
| `MwX7N1Xsy` | tab-2-description | richtext | |
| | **Tab 3** | *divider* | |
| `t4WZWYPFc` | tab-3-image | image | |
| `y9ryERGRD` | tab-3-image-gradient | enum | Same cases as tab-1-image-gradient |
| `no604Oi7Q` | tab-3-title | string | |
| `OFfR27B9P` | tab-3-description | richtext | |
| | **Tab 4** | *divider* | |
| `ohr27MVoZ` | tab-4-image | image | |
| `fkS1X1PQA` | tab-4-image-gradient | enum | Same cases as tab-1-image-gradient |
| `OGIlqy7wA` | tab-4-title | string | |
| `rKZDn5W4o` | tab-4-description | richtext | |
| | **Tab 5** | *divider* | |
| `gYFLMEyCT` | tab-5-image | image | |
| `jZJ15FlME` | tab-5-image-gradient | enum | Same cases as tab-1-image-gradient |
| `BVX_RXwOM` | tab-5-title | string | |
| `WnIKRG1i3` | tab-5-description | richtext | |
| | **Tab 6** | *divider* | |
| `dgaOmHLCZ` | tab-6-image | image | |
| `rbcdhrXv5` | tab-6-image-gradient | enum | Same cases as tab-1-image-gradient |
| `xK1uWIRP4` | tab-6-title | string | |
| `F4Cx1LGNA` | tab-6-description | richtext | |

---

### Ecosystem Section (Trust / Security Bar)

Three fixed cards. Icon fields require manual entry — cannot be set via `applyChanges`.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `cdI25UdwT` | ecosystem-title | string | Section heading above the cards — omit if no heading provided |
| | **Card 1** | *divider* | |
| `wKC8amjcD` | ecosystem-card-1-icon | icon | **Manual entry only** — cannot be set via applyChanges DSL |
| `b4eNosVbY` | ecosystem-card-1-title | string | Card 1 heading |
| `wcyFoJjOl` | ecosystem-card-1-paragraph | string | Card 1 supporting copy |
| | **Card 2** | *divider* | |
| `F8mCXQCOO` | ecosystem-card-2-icon | icon | **Manual entry only** |
| `tHnbjFEXq` | ecosystem-card-2-title | string | Card 2 heading |
| `sXc3WPvvM` | ecosystem-card-2-paragraph | string | Card 2 supporting copy |
| | **Card 3** | *divider* | |
| `q5hoxfAZm` | ecosystem-card-3-icon | icon | **Manual entry only** |
| `s4AQruSW8` | ecosystem-card-3-title | string | Card 3 heading |
| `x6kaCXEx5` | ecosystem-card-3-paragraph | string | Card 3 supporting copy |

---

### Testimonial Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `CMcqbPNZS` | Testimonial-Section? | boolean | `true` to show; `false` to hide. **Default `false`.** |
| `XY1DL6TV0` | Testimonial-Variant | enum | Visual style. Case names: `Primary`, `Green`, `Red`, `Primary Extended`. Safe default: `Primary`. |
| `fqCw7W_So` | Testimonial-text | string | Pull quote — the quote body |
| `db6K5rqzi` | Testimonial-name | string | Full name of the person quoted |
| `Yp3HoYOrp` | Testimonial-role | string | Role and company (e.g. `Chief Underwriting Officer, Aviva`) |

---

### FAQ Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `y_PKKFOFn` | FAQ-Section? | boolean | `true` to show; `false` to hide. **Default `false`.** The FAQ content itself is managed via the separate `FAQ` collection (`kCI7wbxLr`), not inline on this item. |

---

### Page Layout Zones

```
Zone 1 — SEO / Page Identity (not visible on page)
  ├── Slug / don't touch ← routing slug (Dygbimx17)
  ├── Page Name ← short display name (QF8irtwWP)
  ├── Page Title ← SEO title tag (A8lstW2Uv)
  └── Meta Description ← SEO meta (RQKgrn1cJ)

Zone 2 — Hero
  ├── hero-H1-title ← H1 (QCS7gDMkx)
  ├── hero-paragraph ← subheadline (yVRCSRund)
  ├── Banner (video) Variant ← enum (aeB1La8j4): Submission / Pricing & Rating / Portfolio / Decision
  └── Hero Pillars (3)
        ├── Pillar 1: Title (NT_K4geBT) + Description (PxXo2YZYn)
        ├── Pillar 2: Title (gi6nK5ao1) + Description (vjVj9cxrI)
        └── Pillar 3: Title (rFvxDwfSd) + Description (Unt8waFtq)

Zone 3 — Tab Section (Feature Showcase)
  ├── tab-section-h2-title ← section H2 (hKZNHxRBO)
  └── Tabs (up to 6)
        Each tab: Image (image) + Image Gradient (enum) + Title (string) + Description (richtext)
        Tab 1: fiWndVhax / yaQMMyi_I / z1gf2aJUp / ky2Z5JgxM
        Tab 2: M4kYwcmB1 / msVdWa5LI / Iv1y8LBZw / MwX7N1Xsy
        Tab 3: t4WZWYPFc / y9ryERGRD / no604Oi7Q / OFfR27B9P
        Tab 4: ohr27MVoZ / fkS1X1PQA / OGIlqy7wA / rKZDn5W4o
        Tab 5: gYFLMEyCT / jZJ15FlME / BVX_RXwOM / WnIKRG1i3
        Tab 6: dgaOmHLCZ / rbcdhrXv5 / xK1uWIRP4 / F4Cx1LGNA

Zone 4 — Ecosystem Section (Trust / Security Bar)
  ├── ecosystem-title ← section heading (cdI25UdwT) — optional
  └── Cards (3)
        Each card: Icon (manual) + Title (string) + Paragraph (string)
        Card 1: wKC8amjcD / b4eNosVbY / wcyFoJjOl
        Card 2: F8mCXQCOO / tHnbjFEXq / sXc3WPvvM
        Card 3: q5hoxfAZm / s4AQruSW8 / x6kaCXEx5

Zone 5 — Testimonial Section
  ├── Testimonial-Section? ← boolean toggle (CMcqbPNZS)
  ├── Testimonial-Variant ← enum (XY1DL6TV0)
  ├── Testimonial-text ← pull quote (fqCw7W_So)
  ├── Testimonial-name ← (db6K5rqzi)
  └── Testimonial-role ← role + company (Yp3HoYOrp)

Zone 6 — FAQ Section
  └── FAQ-Section? ← boolean toggle (y_PKKFOFn)
      (FAQ content managed via separate FAQ collection kCI7wbxLr)
```

---

### Default Field Values

| Field | Field ID | Default |
|---|---|---|
| Testimonial-Section? | `CMcqbPNZS` | `false` |
| FAQ-Section? | `y_PKKFOFn` | `false` |

> Set both explicitly on `create`. On `update`, only include them if the value is intentionally changing.

---

### Enum Case Resolution — Banner (video) Variant

| Page / use-case type | Banner case name |
|---|---|
| Submission Triage | `Submission` |
| Pricing & Rating | `Pricing & Rating` |
| Portfolio Intelligence | `Portfolio` |
| Decision Engine | `Decision` |

---

### CMS Notes

- **Flat single collection** — no linked sub-collections. All content is inline on the primary item.
- **"Slug / don't touch"** (`Dygbimx17`) is the URL routing slug. Set it on create; do not change on updates.
- **Banner (video) Variant** (`aeB1La8j4`) selects the pre-built hero video asset. Only 4 cases exist — use the closest match for any new page type and confirm with the web team.
- **Hero pillars** map to the "Benefits Bar" layout on the page. All three are always visible; do not omit any pillar.
- **Tab section** (Feature Showcase) supports up to 6 tabs. Omit tab fields beyond the number of features provided — do not send empty strings.
- **Tab image-gradient enum** — 21 cases. Always confirm against the live `cases[]` from the Step 1.5 preflight.
- **Ecosystem icon fields** (`wKC8amjcD`, `F8mCXQCOO`, `q5hoxfAZm`) — `icon` type cannot be written via `applyChanges` DSL. Always emit as Manual actions in the bundle.
- **FAQ-Section? toggle** (`y_PKKFOFn`) — shows/hides the FAQ section. FAQ items themselves live in the separate `FAQ` collection (`kCI7wbxLr`), not on this item.
- **Testimonial-Variant** — `Primary` is the safe default when not specified.

---

## Framer Publishing Field Mapping

### SEO / Page Identity
- **Slug / don't touch** (`Dygbimx17`) — URL routing slug
- **Page Name** (`QF8irtwWP`) — short display name
- **Page Title** (`A8lstW2Uv`) — SEO title tag
- **Meta Description** (`RQKgrn1cJ`) — SEO meta description

### Hero
- **hero-H1-title** (`QCS7gDMkx`) — H1 headline
- **hero-paragraph** (`yVRCSRund`) — subheadline
- **Banner (video) Variant** (`aeB1La8j4`) — enum case name
- **hero-pillar-1-title** (`NT_K4geBT`) / **hero-pillar-1-description** (`PxXo2YZYn`)
- **hero-pillar-2-title** (`gi6nK5ao1`) / **hero-pillar-2-description** (`vjVj9cxrI`)
- **hero-pillar-3-title** (`rFvxDwfSd`) / **hero-pillar-3-description** (`Unt8waFtq`)

### Tab Section
- **tab-section-h2-title** (`hKZNHxRBO`)
- Per tab (1–6): **tab-N-image** (image URL or manual) / **tab-N-image-gradient** (enum) / **tab-N-title** / **tab-N-description** (richtext)

### Ecosystem Section
- **ecosystem-title** (`cdI25UdwT`) — omit if no heading provided
- Per card (1–3): **ecosystem-card-N-icon** (manual) / **ecosystem-card-N-title** / **ecosystem-card-N-paragraph**

### Testimonial Section
- **Testimonial-Section?** (`CMcqbPNZS`) — `true` / `false`
- **Testimonial-Variant** (`XY1DL6TV0`) — enum case name
- **Testimonial-text** (`fqCw7W_So`) — pull quote body
- **Testimonial-name** (`db6K5rqzi`) — full name
- **Testimonial-role** (`Yp3HoYOrp`) — role and company

### FAQ Section
- **FAQ-Section?** (`y_PKKFOFn`) — `true` / `false`
