# Platform-new — Framer CMS Reference

Framer CMS structure for platform feature landing pages using the "Platform-new" template: page URLs, collection schema, field IDs, layout zones, and publishing field mapping.

> **These IDs and case names are a cache, not the source of truth.** Collection IDs and field IDs differ between Framer projects and can change over time. `format-for-framer` reconciles this file against the **live** schema via a required `framer.agent.getNodesOfTypes({types:["CollectionNode"]})` preflight (Step 1.5) on every forward run and maps to the live values — surfacing any drift in the bundle's `Schema drift:` section. Update the cached values here opportunistically when you notice drift, but do not treat them as authoritative.

---

## Framer CMS Structure

### Pages

- Detail template: `/platform-new/<slug>` (driven by the `Slug` field — `hS5skEtkc`)

Existing items: `hyperoperator`, `workflow-builder`, `calculation-engines`, `portfolio-intelligence`.

### CMS Collections

Flat single collection — no linked sub-collections.

#### Platform-new (id: `hDH7dx9nG`)

One item per published platform feature landing page.

> **"SR" fields** — fields prefixed `SR` (e.g. `Hero-SR-H1-Title`, `Scroll-SR-H2-Title`) are visually hidden screen-reader headings for accessibility. They should be set to a meaningful heading string (often the same as or a condensed version of the visible title). Do not leave them blank.

---

### SEO / Page Identity

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `hS5skEtkc` | Slug | string | URL path segment (e.g. `calculation-engines`) |
| `hfK3YWjSW` | Page-Title | string | SEO `<title>` tag |
| `RoetZqpQQ` | Meta-Description | string | SEO meta description |

---

### Hero Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `KKeSFnJJT` | Background Gradient | enum | Hero background colour theme. Case names: `Deep Forest`, `Blue`, `Burgundy`, `Light Green` |
| `fqo4Nx8rS` | Hero-SR-H1-Title | string | **Screen-reader H1** — visually hidden; sets the page's accessible H1. Required for accessibility. |
| `pO9sP_6ey` | Hero-Section-Title | string | Visual hero headline — displayed prominently on screen |
| `OStKdHSQZ` | Hero-Button-Title | string | CTA button label |
| `qI2tQ9JB3` | Hero-Button-Link | link | CTA button URL |
| `UE46mHrVf` | Featured | boolean | Marks the page as featured (e.g. for listing carousels). **Default `false`.** |
| `O4MCOzh1A` | Hero-Image | image | Hero visual / product screenshot |
| | **Hero Cards (3)** | *divider* | Stat or highlight cards displayed in the hero |
| `bKjx3tXP1` | Hero-Card1-Title | string | Card 1 label / stat |
| `CE_vzSTPL` | Hero-Card1-Paragraph | string | Card 1 supporting copy |
| `Dz1N2NTTl` | Hero-Card2-Title | string | Card 2 label / stat |
| `IctoBb27X` | Hero-Card2-Paragraph | string | Card 2 supporting copy |
| `v8M2GGxeh` | Hero-Card3-Title | string | Card 3 label / stat |
| `PzKjn_ugj` | Hero-Card3-Paragraph | string | Card 3 supporting copy |

---

### Scroll Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `Ema42ZNrl` | Scroll-SR-H2-Title | string | **Screen-reader H2** — visually hidden section heading for accessibility |
| `IfJ8oWw2a` | Scroll-Title | string | Visual section headline |
| `aadiBkwUP` | Scroll-Paragraph | string | Section body copy |
| `XM8ZqxSzF` | Scroll-Image | image | Supporting visual for the scroll section |

---

### Card Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `Nbwm36fYI` | Section-SR-H2-Title | string | **Screen-reader H2** — visually hidden section heading for accessibility |
| | **Card 1** | *divider* | |
| `I6C0UOx2B` | Card1-Image | image | Card 1 screenshot or visual |
| `i7ym4Ao4e` | Card1-ImageGradient | enum | Gradient overlay on Card 1 image. Cases: `Orange 1`, `Orange 4`, `Burgundy 1`, `Burgundy 2`, `Burgundy 6`, `Light Blue 2`, `Light Blue 4`, `Light Blue 5`, `Light Blue 6`, `Blue 4`, `Blue 6`, `Blue 7`, `Mix 3`, `Green 4`, `Flat` |
| `uYLhJcmuA` | Card1-Title | string | Card 1 heading |
| `Fjwxx1TaL` | Card1-Eyebrow | string | Card 1 eyebrow / label above the title |
| `UGQS5f1du` | Card1-Paragraph1 | string | Card 1 first body paragraph |
| `IbiRFUcKy` | Card1-Paragraph2 | string | Card 1 second body paragraph (optional — omit if not provided) |
| `vpUYJerLE` | Card1-Paragraph3 | string | Card 1 third body paragraph (optional — omit if not provided) |
| | **Card 2** | *divider* | |
| `LBF3eRNt7` | Card2-Image | image | Card 2 screenshot or visual |
| `Mtg1aqZVL` | Card2-ImageGradient | enum | Same cases as Card1-ImageGradient |
| `HUceb4Kly` | Card2-Title | string | Card 2 heading |
| `bqGCp6pVR` | Card2-Eyebrow | string | Card 2 eyebrow / label above the title |
| `iNpGjV6Ex` | Card2-Paragraph1 | string | Card 2 first body paragraph |
| `knh8OGUEc` | Card2-Paragraph2 | string | Card 2 second body paragraph (optional) |
| `JIRjwJy5y` | Card2-Paragraph3 | string | Card 2 third body paragraph (optional) |
| | **Card 3** | *divider* | |
| `h57tpmFeU` | Card3-Image | image | Card 3 screenshot or visual |
| `JOP8xO3wn` | Card3-ImageGradient | enum | Same cases as Card1-ImageGradient |
| `nW7p7nw6P` | Card3-Title | string | Card 3 heading |
| `YTYhHGYzv` | Card3-Eyebrow | string | Card 3 eyebrow / label above the title |
| `x7peDaflV` | Card3-Paragraph1 | string | Card 3 first body paragraph |
| `uqp1xU5pq` | Card3-Paragraph2 | string | Card 3 second body paragraph (optional) |
| `iB4br8PwV` | Card3-paragraph3 | string | Card 3 third body paragraph (optional) |

---

### Discover Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `kLJGGT1vz` | Discover-SR-H2-Title | string | **Screen-reader H2** — visually hidden section heading for accessibility |
| `rYsqqHo6Y` | Discover-Submission Triage | boolean | Show the Submission Triage product tile in the Discover section |
| `qtETa1M8J` | Discover-Pricing Rating | boolean | Show the Pricing & Rating product tile |
| `Bcy6kMmsY` | Discover-Portfolio Intelligence | boolean | Show the Portfolio Intelligence product tile |
| `CjtIWtPPs` | Discover-Decision Engine | boolean | Show the Decision Engine product tile |

---

### Testimonial Section

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `F82sxxz0d` | Testimonial-SR-H2-Title | string | **Screen-reader H2** — visually hidden section heading for accessibility |
| `COhdClfLJ` | Testimonial-Image | image | Headshot of the person being quoted |
| `GrqEx8VM7` | Testimonial-Text | string | Pull quote / testimonial body |
| `ScFtEErXR` | Testimonial-Name | string | Full name of the person quoted |
| `ZV4Nvi0tw` | Testimonial-Distinction | string | Role and company (e.g. "Head of Pricing, Acme Re") |

---

### Page Layout Zones

```
Zone 1 — SEO / Page Identity (not visible on page)
  ├── Slug ← URL path (hS5skEtkc)
  ├── Page-Title ← SEO title tag (hfK3YWjSW)
  └── Meta-Description ← SEO meta (RoetZqpQQ)

Zone 2 — Hero
  ├── Background Gradient ← colour theme enum (KKeSFnJJT)
  ├── Hero-SR-H1-Title ← screen-reader H1 (fqo4Nx8rS)
  ├── Hero-Section-Title ← visual headline (pO9sP_6ey)
  ├── Hero-Button: Title (OStKdHSQZ) + Link (qI2tQ9JB3)
  ├── Featured toggle ← (UE46mHrVf)
  ├── Hero-Image ← (O4MCOzh1A)
  └── Hero Cards (3)
        ├── Card 1: Title (bKjx3tXP1) + Paragraph (CE_vzSTPL)
        ├── Card 2: Title (Dz1N2NTTl) + Paragraph (IctoBb27X)
        └── Card 3: Title (v8M2GGxeh) + Paragraph (PzKjn_ugj)

Zone 3 — Scroll Section
  ├── Scroll-SR-H2-Title ← screen-reader H2 (Ema42ZNrl)
  ├── Scroll-Title ← visual heading (IfJ8oWw2a)
  ├── Scroll-Paragraph ← (aadiBkwUP)
  └── Scroll-Image ← (XM8ZqxSzF)

Zone 4 — Card Section
  ├── Section-SR-H2-Title ← screen-reader H2 (Nbwm36fYI)
  └── Cards (3)
        Each card: Image + ImageGradient enum + Title + Eyebrow + Paragraph1 + (optional) Paragraph2 + Paragraph3

Zone 5 — Discover Section
  ├── Discover-SR-H2-Title ← screen-reader H2 (kLJGGT1vz)
  └── Product tile toggles (4 booleans)
        ├── Submission Triage (rYsqqHo6Y)
        ├── Pricing Rating (qtETa1M8J)
        ├── Portfolio Intelligence (Bcy6kMmsY)
        └── Decision Engine (CjtIWtPPs)

Zone 6 — Testimonial Section
  ├── Testimonial-SR-H2-Title ← screen-reader H2 (F82sxxz0d)
  ├── Testimonial-Image ← headshot (COhdClfLJ)
  ├── Testimonial-Text ← pull quote (GrqEx8VM7)
  ├── Testimonial-Name ← (ScFtEErXR)
  └── Testimonial-Distinction ← role + company (ZV4Nvi0tw)
```

---

### Default Field Values

| Field | Field ID | Default |
|---|---|---|
| Featured | `UE46mHrVf` | `false` |
| Discover-Submission Triage | `rYsqqHo6Y` | `false` |
| Discover-Pricing Rating | `qtETa1M8J` | `false` |
| Discover-Portfolio Intelligence | `Bcy6kMmsY` | `false` |
| Discover-Decision Engine | `CjtIWtPPs` | `false` |

> Set all Discover booleans explicitly on `create` unless the brief specifies otherwise. On `update`, only include them if they are changing.

---

### CMS Notes

- **Flat single collection** — no linked sub-collections. All content is inline on the primary item.
- **"SR" fields** (Hero-SR-H1-Title, Scroll-SR-H2-Title, Section-SR-H2-Title, Discover-SR-H2-Title, Testimonial-SR-H2-Title) are visually hidden screen-reader headings. Always set them to a meaningful string — use the same text as the visual title when in doubt. Do not omit.
- **Background Gradient** — sets the hero colour theme. The safe default when not specified by the brief is `Blue`.
- **Hero-Section-Title vs Hero-SR-H1-Title** — the SR field is the accessible H1 (may be identical or abbreviated); the Section Title is the visual display copy. Both should be set.
- **Hero Cards** — 3 fixed slots. If the brief provides fewer than 3, omit the missing slots entirely (do not send empty strings).
- **Card Paragraph2 and Paragraph3** — optional per card. Omit from the bundle if not provided in the brief.
- **Card3-paragraph3** — note the lowercase `p` in the field name. This is the live field name; the key is `$control__card3_paragraph3`.
- **Discover booleans** — each toggle independently shows/hides a pre-built product tile. Set only the tiles relevant to the page's feature focus to `true`.
- **ImageGradient enum** — 15 cases. Always confirm against the live `cases[]` from the Step 1.5 preflight before encoding.
- **Hero-Button-Link** — a `link` type. Pass a full URL. Omit if the brief does not supply a CTA URL.
- **Testimonial-Image** — headshot. Flag for manual upload if no durable URL is available.

---

## Framer Publishing Field Mapping

When producing output that will be published to Framer, structure the deliverable with clear labels for each CMS field:

### SEO / Page Identity
- **Slug** (`hS5skEtkc`) — URL path segment
- **Page-Title** (`hfK3YWjSW`) — SEO title
- **Meta-Description** (`RoetZqpQQ`) — SEO meta description

### Hero
- **Background Gradient** (`KKeSFnJJT`) — enum case name: `Deep Forest` / `Blue` / `Burgundy` / `Light Green`
- **Hero-SR-H1-Title** (`fqo4Nx8rS`) — screen-reader H1
- **Hero-Section-Title** (`pO9sP_6ey`) — visual headline
- **Hero-Button-Title** (`OStKdHSQZ`) / **Hero-Button-Link** (`qI2tQ9JB3`)
- **Featured** (`UE46mHrVf`) — `false` (default)
- **Hero-Image** (`O4MCOzh1A`) — image URL
- **Hero-Card1-Title** (`bKjx3tXP1`) / **Hero-Card1-Paragraph** (`CE_vzSTPL`)
- **Hero-Card2-Title** (`Dz1N2NTTl`) / **Hero-Card2-Paragraph** (`IctoBb27X`)
- **Hero-Card3-Title** (`v8M2GGxeh`) / **Hero-Card3-Paragraph** (`PzKjn_ugj`)

### Scroll Section
- **Scroll-SR-H2-Title** (`Ema42ZNrl`) — screen-reader H2
- **Scroll-Title** (`IfJ8oWw2a`) / **Scroll-Paragraph** (`aadiBkwUP`) / **Scroll-Image** (`XM8ZqxSzF`)

### Card Section
- **Section-SR-H2-Title** (`Nbwm36fYI`) — screen-reader H2
- Per card (1–3): **Image** / **ImageGradient** (enum) / **Title** / **Eyebrow** / **Paragraph1** / (optional) **Paragraph2** / **Paragraph3**

### Discover Section
- **Discover-SR-H2-Title** (`kLJGGT1vz`) — screen-reader H2
- **Discover-Submission Triage** (`rYsqqHo6Y`) — `true` / `false`
- **Discover-Pricing Rating** (`qtETa1M8J`) — `true` / `false`
- **Discover-Portfolio Intelligence** (`Bcy6kMmsY`) — `true` / `false`
- **Discover-Decision Engine** (`CjtIWtPPs`) — `true` / `false`

### Testimonial Section
- **Testimonial-SR-H2-Title** (`F82sxxz0d`) — screen-reader H2
- **Testimonial-Image** (`COhdClfLJ`) — headshot URL (flag for manual upload if unavailable)
- **Testimonial-Text** (`GrqEx8VM7`) — pull quote
- **Testimonial-Name** (`ScFtEErXR`) — person's full name
- **Testimonial-Distinction** (`ZV4Nvi0tw`) — role and company
