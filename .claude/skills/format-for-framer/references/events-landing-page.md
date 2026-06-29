# Events Landing Page — Framer CMS Reference

Framer CMS structure for event landing pages: page URLs, collection schema, field IDs, layout zones, and publishing field mapping. Editorial guidance (section structure, copy conventions, QA checklist) is loaded separately via the `events-landing-page` content-type playbook.

> **These IDs and case names are a cache, not the source of truth.** Collection IDs and field IDs differ between Framer projects and can change over time; **enum case _names_** are what the new Framer Agent CLI accepts as input (the old `mcp.unframer.co` MCP used opaque case IDs — those no longer apply). `format-for-framer` reconciles this file against the **live** schema via a required `framer.agent.getNodesOfTypes({types:["CollectionNode"]})` preflight (Step 1.5) on every forward run and maps to the live values — surfacing any drift in the bundle's `Schema drift:` section. Update the cached values here opportunistically when you notice drift, but do not treat them as authoritative.

---

## Framer CMS Structure

### Pages

- Listing page: `/events` (nodeId `ZfcMpBu36`)
- Detail template: `/events/:slug/` (nodeId `iyJc4jWgt`)

### CMS Collections

Primary flat collection plus one linked sub-collection for speakers.

#### Events (id: `Zn5SeVKoW`)

One item per published event landing page.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `d_vQaMg5K` | Title | string | Event headline |
| `ZzwVnpqbN` | Location | string | City, venue area, or "Online" for virtual events |
| `JbG8YB8Ue` | Venue name | string | Venue or platform name |
| `ywc403vDi` | Date | string | Event date (plain text, not a date field) |
| `zkKbmHdhz` | Time | string | Event time with timezone |
| `jus6hZDTq` | Invite Only | boolean | **Default `false`** — marks the event as invite-only |
| `BdGewt49i` | Show Eyebrow | boolean | **Default `false`** — show the eyebrow label above the title |
| `d10V9zYZv` | Event Type | enum | Case name (one of): `Virtual Event`, `On-Demand`, `Conference`, `User Group`, `Partner Event`, `Hosted` |
| `nn7PZJ7gY` | In-Person or Virtual | enum | Case name (one of): `In-Person`, `Virtual` |
| `jPO5FeEiI` | Button Text | enum | Case name (one of): `Reserve your spot`, `Register now`, `Join the waitlist`, `Book a meeting` |
| `LBRm6tnyM` | Button Colour | enum | **Default `Blue`** — Case name (one of): `Burgundy`, `Forest Green`, `Blue`, `Orange` |
| `g9_HlS7J7` | Thumbnail | image | Card image used on the listing page and social sharing |
| `t2VbuiR_h` | Event detail | formattedText | Rich-text body content — the main descriptive copy for the event. Supports HTML with headings, paragraphs, lists. |
| `d_Qlg46jg` | Event Speakers | multiCollectionReference | Links to items in the `Event Speaker` collection (`zHb_jqjR3`) |
| `jYKylbsyR` | Form Embed | string | HubSpot form UUID (not embed HTML) |
| `mJzf5Njs7` | Outbound Link | link | External registration URL. Use for events hosted on third-party platforms (e.g., Eventbrite, partner sites). |
| `AqZdFNuQ6` | Show Nav Bar | boolean | **Default `false`** — show the navigation bar on the page |
| | **Event Takeaways** | *divider* | |
| `UwowYq2Oh` | Item 1 - Title | string | **Always omit from fieldData. Leave empty in Framer.** |
| `nTzR_1C4J` | Item 1 - Description | string | **Always omit from fieldData. Leave empty in Framer.** |
| `h7cUstFjD` | Item 2 - Title | string | **Always omit from fieldData. Leave empty in Framer.** |
| `FWwSfy6Zj` | Item 2 - Description | string | **Always omit from fieldData. Leave empty in Framer.** |
| `y5kHcGXoC` | Item 3 - Title | string | **Always omit from fieldData. Leave empty in Framer.** |
| `AFqCgLZXr` | Item 3 - Description | string | **Always omit from fieldData. Leave empty in Framer.** |
| `wfD7ql_mE` | Item 4 - Title | string | **Always omit from fieldData. Leave empty in Framer.** |
| `qH_yxmS49` | Item 4 - Description | string | **Always omit from fieldData. Leave empty in Framer.** |

#### Event Speaker (id: `zHb_jqjR3`)

Linked sub-collection for speaker profiles. Referenced by the Event Speakers field.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `UQtvBIio3` | Speaker Name | string | **Required.** Full name |
| `rpqzgxIDu` | Company name | string | Speaker's company |
| `pACcHP4jx` | Detail | string | Brief bio or credential line. **Optional — omit from fieldData if not provided in the brief. Do not ask.** |
| `kpbfo3mIH` | Job Title | string | Speaker's role |
| `qVU37w2bj` | Image | image | Headshot |
| `cC3cJ4Z7h` | LinkedIn URL | link | Speaker's LinkedIn profile |

### Page Layout Zones

```
Zone 1 — Navigation (conditional)
  └── Navigation component ← controlled by Show Nav Bar toggle (AqZdFNuQ6)

Zone 2 — Hero / Header
  ├── Eyebrow (conditional) ← controlled by Show Eyebrow toggle (BdGewt49i)
  ├── Title (H1) ← Title field (d_vQaMg5K)
  ├── Event metadata row
  │     ├── Date ← Date field (ywc403vDi)
  │     ├── Time ← Time field (zkKbmHdhz)
  │     ├── Location ← Location field (ZzwVnpqbN)
  │     └── Venue name ← Venue name field (JbG8YB8Ue)
  ├── CTA button ← Button Text enum (jPO5FeEiI) + Button Colour enum (LBRm6tnyM)
  │     └── Links to Form Embed (jYKylbsyR) or Outbound Link (mJzf5Njs7)
  └── Invite Only badge (conditional) ← Invite Only toggle (jus6hZDTq)

Zone 3 — Event Detail / Body
  └── Rich text content ← Event detail field (t2VbuiR_h)
      Supports: H3 headings, paragraphs, bullet lists, bold text

Zone 4 — Speakers
  └── Speaker cards ← Event Speakers reference (d_Qlg46jg)
        Each card pulls: Speaker Name, Job Title, Company name, Image, Detail

Zone 5 — Event Takeaways
  ├── Item 1 ← Item 1 - Title (UwowYq2Oh) + Item 1 - Description (nTzR_1C4J)
  ├── Item 2 ← Item 2 - Title (h7cUstFjD) + Item 2 - Description (FWwSfy6Zj)
  ├── Item 3 ← Item 3 - Title (y5kHcGXoC) + Item 3 - Description (AFqCgLZXr)
  └── Item 4 ← Item 4 - Title (wfD7ql_mE) + Item 4 - Description (qH_yxmS49)
```

### Default Field Values

These fields must be set to their default values on every new event item unless the brief explicitly requests otherwise:

| Field | Field ID | Default |
|---|---|---|
| Invite Only | `jus6hZDTq` | `false` |
| Show Eyebrow | `BdGewt49i` | `false` |
| Button Colour | `LBRm6tnyM` | `Blue` |
| Show Nav Bar | `AqZdFNuQ6` | `false` |

### CMS Notes

- **Flat primary structure with one linked sub-collection** — the primary Events collection holds all content fields inline. The only linked collection is Event Speaker (multiple speakers per event via `multiCollectionReference`).
- **Event detail is `formattedText`** — accepts HTML with `<h3>`, `<p>`, `<ul>/<li>`, and `<strong>` tags. Use `<h3>` for section headings within the detail, not `<h2>` (the page title occupies the H1 slot).
- **Form Embed is a plain string** — pass only the HubSpot form UUID, not an embed snippet or full URL.
- **Outbound Link vs Form Embed** — use Form Embed for events with an embedded HubSpot registration form. Use Outbound Link for events hosted on third-party platforms (Eventbrite, partner sites, etc.). Only one should be populated per event.
- **Event Type is an enum** — pass the case **name** as it appears on the live collection's `variables[].cases`: `Virtual Event`, `On-Demand`, `Conference`, `User Group`, `Partner Event`, `Hosted`. The old MCP's opaque case IDs (`Czt3LlbcI`, `acFXkAH5n`, etc.) are no longer accepted.
- **In-Person or Virtual is an enum** — pass the case name: `In-Person` or `Virtual`. Drives venue / online presentation toggles on the detail template.
- **Button Text is an enum** — pass the case name: `Reserve your spot`, `Register now`, `Join the waitlist`, `Book a meeting`.
- **Button Colour is an enum** — pass the case name: `Burgundy`, `Forest Green`, `Blue`, `Orange`. Default to `Blue`.
- **Date and Time are plain strings** — not date/time fields. Format as human-readable text (e.g., "June 12, 2026", "6:30 PM - 9:00 PM ET").
- **Event Takeaways (Item 1-4) are always omitted** — do not populate Item 1 through Item 4 Title/Description fields for any event type. These fields exist in the CMS schema but are intentionally left empty.
- **Thumbnail** — used on the `/events` listing page cards. Requires manual upload if no URL is available.
- **Event Speakers** — requires creating speaker items in the Event Speaker collection first, then linking their IDs. See Multi-Collection Publishing below.

---

## Multi-Collection Publishing (Speakers)

Event pages use a linked Event Speaker sub-collection. Full automated publishing requires:

1. Check if the speaker already exists in collection `zHb_jqjR3` (read items via `framer.agent.getNodesOfTypes({types:["CollectionItemNode"]})` filtered by `$parentId === "zHb_jqjR3"` and matched on `$control__UQtvBIio3` — the Speaker Name attribute)
2. If not found, create the speaker item in `zHb_jqjR3` via `framer.agent.applyChanges` with a `+CollectionItemNode … parent="zHb_jqjR3"` + `SET … $control__UQtvBIio3="<name>" …` command. Use the `renamedIds` returned by `applyChanges` to get the canonical item id.
3. Collect all speaker item IDs
4. Create or update the primary event in `Zn5SeVKoW`, passing the speaker IDs in the Event Speakers field (`d_Qlg46jg`) per the live `multiCollectionReference` encoding

If speaker creation is not feasible (e.g., missing headshot images), flag the speakers for manual entry:

> Speaker linking requires creating items in the Event Speaker collection first. The following speakers need to be added manually in Framer: [list names].

---

## Framer Publishing Field Mapping

When producing output that will be published to Framer, structure the deliverable with clear labels for each CMS field so the publisher can copy directly:

- **Title** (`d_vQaMg5K`) — the event headline
- **Location** (`ZzwVnpqbN`) — city/area or "Online"
- **Venue name** (`JbG8YB8Ue`) — venue or platform name
- **Date** (`ywc403vDi`) — event date as readable text
- **Time** (`zkKbmHdhz`) — event time with timezone
- **Invite Only** (`jus6hZDTq`) — `false` (default)
- **Show Eyebrow** (`BdGewt49i`) — `false` (default)
- **Event Type** (`d10V9zYZv`) — enum case **name**: `Virtual Event` / `On-Demand` / `Conference` / `User Group` / `Partner Event` / `Hosted`
- **In-Person or Virtual** (`nn7PZJ7gY`) — enum case **name**: `In-Person` / `Virtual`
- **Button Text** (`jPO5FeEiI`) — enum case **name**: `Reserve your spot` / `Register now` / `Join the waitlist` / `Book a meeting`
- **Button Colour** (`LBRm6tnyM`) — `Blue` (default)
- **Thumbnail** (`g9_HlS7J7`) — card image URL (flag for manual upload if unavailable)
- **Event detail** (`t2VbuiR_h`) — rich text (HTML)
- **Form Embed** (`jYKylbsyR`) — HubSpot form UUID (if applicable)
- **Outbound Link** (`mJzf5Njs7`) — external registration URL (if applicable; omit for embedded forms)
- **Show Nav Bar** (`AqZdFNuQ6`) — `false` (default)
- **Event Speakers** (`d_Qlg46jg`) — array of Event Speaker item IDs (see Multi-Collection Publishing)

> **Item 1-4 Title/Description fields** (`UwowYq2Oh`, `nTzR_1C4J`, `h7cUstFjD`, `FWwSfy6Zj`, `y5kHcGXoC`, `AFqCgLZXr`, `wfD7ql_mE`, `qH_yxmS49`) — always omit from fieldData for all event types.
