# Ads Landing Page — Framer CMS Reference

Framer CMS structure for ads landing pages: page URLs, collection schema, field IDs, layout zones, and publishing field mapping. Editorial guidance (section structure, copy conventions, QA checklist) is loaded separately via the `ads-landing-page` content-type playbook.

> **These IDs are a cache, not the source of truth.** Collection IDs and field IDs differ between Framer projects. This collection has no enums today (only booleans and string/formattedText/image/file/link). `format-for-framer` reconciles this file against the live schema via a required `framer.agent.getNodesOfTypes({types:["CollectionNode"]})` preflight on every forward run.

---

## Framer CMS Structure

### Pages

- Detail template: `/explore/:slug` (nodeId `z5OMfhumY`)
- Draft preview: `/explore/:slug/draft` (nodeId `MdkY5LuUP`)
- No listing page — ads landing pages are reached only via paid search links

### CMS Collection

Single flat collection. All fields live on the primary record — no sub-collections.

#### Ads Landing Pages (id: `EkLmddPnz`)

One item per published ads landing page.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `CDknWsX4l` | Eyebrow | string | SEO category label matching the page's target keyword cluster |
| `mt36tmacq` | Title | string | Benefit headline, 8–12 words |
| `rllKUshjf` | Subtitle | formattedText | 1–2 paragraphs, max 80 words |
| `JXQuZShYO` | HubSpot Form Embed | string | Default: `69d534f3-87ce-4f71-802e-4753c7b03a38`. Use this form ID unless a page-specific override is provided. |
| | **Hero Bullet Points** | *divider* | |
| `LusFodCqe` | Bullet 1 | formattedText | One sentence, ~15–25 words. Bold leading metric if metric-led |
| `NK0xfJCKC` | Bullet 2 | formattedText | One sentence, ~15–25 words |
| `Zgjz5IRdr` | Bullet 3 | formattedText | One sentence, ~15–25 words |
| `D0jodvqxd` | Bullet 4 | formattedText | Optional — only when a fourth distinct proof point exists |
| | **Media Section** | *divider* | |
| `hnqLG_Jd_` | Media Section Title | string | Always leave blank |
| `P9mTBuReW` | Youtube Video URL | string | YouTube nocookie embed URL (`youtube-nocookie.com/embed/...`), or blank — leave blank by default |
| `uWmQ2c9W0` | Image | image | Always leave blank — hero image not used on ads landing pages |
| | **Additional Content** | *divider* | |
| `btptWj83e` | Section Title | string | Descriptive or contrastive style heading for the feature-items block |
| `IpUxy9sWD` | Item 1 - Title | string | Colon format: `Short label: lowercase elaboration` |
| `Z8YQuT3r1` | Item 1 - Subtitle | formattedText | 2–3 short paragraphs, 30–60 words |
| `OVeEEGOrh` | Item 1 - Image | image | Product screenshot for this feature |
| `E0VWSqwkX` | Item 2 - Title | string | Colon format |
| `kVXWfuP82` | Item 2 - Subtitle | formattedText | 2–3 short paragraphs, 30–60 words |
| `fS2tkkfX8` | Item 2 - Image | image | Product screenshot |
| `NhyReuBj9` | Item 3 - Title | string | Colon format |
| `EVs_xhF5r` | Item 3 - Subtitle | formattedText | 2–3 short paragraphs, 30–60 words |
| `QGoHErpzs` | Item 3 - Image | image | Product screenshot |
| `C8Z8gKiDs` | Item 4 - Title | string | Optional — colon format |
| `qMrlFEp9F` | Item 4 - Subtitle | formattedText | Optional — 2–3 short paragraphs, 30–60 words |
| `cT6rAsug_` | Item 4 - Image | image | Optional — product screenshot |
| | **Bottom Sections** | *divider* | |
| `V2_hZES2t` | Show Benefits / USPs Section | boolean | Default `false`; set to `true` only if explicitly specified in the brief |
| `I0KCjXgyJ` | Case Study Headline | string | Short bold statement of the customer result |
| `mhNMnt2i5` | Case Study Subtitle | string | Customer name + segment + one-line outcome |
| | **FAQs** | *divider* | |
| `V8s9fKIW6` | Question 1 | string | Long-tail SEO query, or blank if no genuine search intent |
| `FE95_9Xdq` | Answer 1 | string | 2–4 sentences, direct and factual |
| `cfhH6k5_n` | Question 2 | string | |
| `pwVleSXpE` | Answer 2 | string | |
| `Fgm7NPUMA` | Question 3 | string | |
| `aCFQGimeV` | Answer 3 | string | |
| | **CTA** | *divider* | |
| `nrUIYDd9l` | CTA Title | string | Fixed: always `See hx in action` |
| `VohRc33_1` | CTA Subtitle | string | Fixed: always `Your workflows, not a canned demo` |

### Page Layout Zones

```
Zone 1 — Hero
  ├── Eyebrow + colored dot ← Eyebrow field (CDknWsX4l)
  ├── Title (H1) ← Title field (mt36tmacq)
  ├── Subtitle (rich text) ← Subtitle field (rllKUshjf)
  ├── Bullet Points (icon + text × 3–4)
  │     ├── Bullet 1 ← (LusFodCqe)
  │     ├── Bullet 2 ← (NK0xfJCKC)
  │     ├── Bullet 3 ← (Zgjz5IRdr)
  │     └── Bullet 4 ← (D0jodvqxd) — optional
  ├── Logo strip (static component, not CMS-driven)
  └── HubSpot form (dark card, right column) ← HubSpot Form Embed (JXQuZShYO)

Zone 2 — Media (grey background)
  ├── Media Section Title ← (hnqLG_Jd_) — always blank
  └── YouTube embed OR product image
        ├── Youtube Video URL ← (P9mTBuReW)
        └── Image ← (uWmQ2c9W0)

Zone 3 — Additional Content (Feature Items)
  ├── Section Title (H2) ← Section Title (btptWj83e)
  └── Slide cards × 3–4 (each: title + subtitle + image, alternating layout)
        ├── Item 1 ← Title (IpUxy9sWD), Subtitle (Z8YQuT3r1), Image (OVeEEGOrh)
        ├── Item 2 ← Title (E0VWSqwkX), Subtitle (kVXWfuP82), Image (fS2tkkfX8)
        ├── Item 3 ← Title (NhyReuBj9), Subtitle (EVs_xhF5r), Image (QGoHErpzs)
        └── Item 4 ← Title (C8Z8gKiDs), Subtitle (qMrlFEp9F), Image (cT6rAsug_) — optional

Zone 4 — Bottom Sections
  ├── Case Study callout card
  │     ├── Headline (H5) ← Case Study Headline (I0KCjXgyJ)
  │     └── Subtitle ← Case Study Subtitle (mhNMnt2i5)
  └── Benefits/USPs grid (static security & compliance badges, toggled by V2_hZES2t)

Zone 5 — FAQs (accordion component)
  └── Q&A pairs 1–3 (leave blank when no genuine search intent)
        ├── Q1/A1 ← (V8s9fKIW6) / (FE95_9Xdq)
        ├── Q2/A2 ← (cfhH6k5_n) / (pwVleSXpE)
        └── Q3/A3 ← (Fgm7NPUMA) / (aCFQGimeV)

Zone 6 — CTA (dark background)
  ├── CTA Title (H3) ← CTA Title (nrUIYDd9l)
  ├── CTA Subtitle ← CTA Subtitle (VohRc33_1)
  └── "Book a demo" button (static component, not CMS-driven)
```

### CMS Notes

- **Flat structure** — unlike Customer Stories, there are no sub-collections. All fields (bullets, feature items, FAQs) are inline on the primary record.
- **Feature items are fixed slots, not repeaters** — the collection has exactly 4 item slots (Title + Subtitle + Image each). Item 4 is optional; leave all three fields blank to hide it.
- **FAQ fields are plain strings, not rich text** — answers cannot contain inline formatting. Keep them factual and short.
- **Subtitle and bullet fields are `formattedText`** — plain text or HTML with paragraph tags is accepted; no inline bold required.
- **Feature item subtitles are `formattedText`** — same HTML convention as the hero subtitle.
- **Hero media** — Leave both `Youtube Video URL` and `Image` blank. Hero image is not used on ads landing pages.
- **Benefits/USPs content is static** — the CMS toggle (`Show Benefits / USPs Section`) controls visibility, but the security badges and copy within the section are baked into the template, not editable via CMS.
- **HubSpot Form Embed** — defaults to `69d534f3-87ce-4f71-802e-4753c7b03a38` for all ads landing pages. Use a page-specific override only when explicitly provided.

---

## Framer Publishing Field Mapping

When producing output that will be published to Framer, structure the deliverable with clear labels for each CMS field so the publisher can copy directly:

- **Eyebrow** (`CDknWsX4l`) — the SEO category label
- **Title** (`mt36tmacq`) — the benefit headline
- **Subtitle** (`rllKUshjf`) — rich text
- **Bullet 1** (`LusFodCqe`) — first hero bullet, rich text
- **Bullet 2** (`NK0xfJCKC`) — second hero bullet, rich text
- **Bullet 3** (`Zgjz5IRdr`) — third hero bullet, rich text
- **Bullet 4** (`D0jodvqxd`) — fourth hero bullet (omit if only 3)
- **Media Section Title** (`hnqLG_Jd_`) — leave blank
- **Youtube Video URL** (`P9mTBuReW`) — nocookie embed URL, or blank
- **Section Title** (`btptWj83e`) — the additional-content heading
- **Item 1–4** — for each item, list Title, Subtitle (HTML), and note that Image requires a screenshot upload
- **Show Benefits / USPs Section** (`V2_hZES2t`) — `false` (default; set to `true` only if explicitly specified)
- **Case Study Headline** (`I0KCjXgyJ`) — customer result statement
- **Case Study Subtitle** (`mhNMnt2i5`) — customer name + segment + outcome
- **Question 1–3 / Answer 1–3** — list each pair, or note "leave blank" when no FAQ content
- **CTA Title** (`nrUIYDd9l`) — fixed: `See hx in action`
- **CTA Subtitle** (`VohRc33_1`) — fixed: `Your workflows, not a canned demo`
