# FAQs — Framer CMS Reference

Framer CMS structure for the FAQ content type: page URLs, collection schema, field IDs, layout zones, and publishing field mapping.

> **These IDs and case names are a cache, not the source of truth.** Collection IDs and field IDs differ between Framer projects and can change over time. `format-for-framer` reconciles this file against the **live** schema via a required `framer.agent.getNodesOfTypes({types:["CollectionNode"]})` preflight (Step 1.5) on every forward run and maps to the live values — surfacing any drift in the bundle's `Schema drift:` section. Update the cached values here opportunistically when you notice drift, but do not treat them as authoritative.
>
> **✅ IDs confirmed 2026-06-24.** Preflight run against session 2 (branch: glassy-flare). Two FAQ collections found: `📄 FAQ` (`kCI7wbxLr`) — primary, broader topic coverage including product-specific cases; and `LOB FAQ` (`jLTDNhP9V`) — for LOB-scoped FAQs. Use `📄 FAQ` for platform/use-case FAQs. Note: no `Published` or `Order` fields exist in the live schema — those rows in this reference are schema drift and should be omitted from bundles.

---

## Framer CMS Structure

### Pages

- Detail template: `/faqs` (static page or CMS-driven — confirm URL pattern with the web team)

> **URL pattern to confirm.** The FAQ page may be a single CMS-driven page (one item for the whole page, with inline Q/A pairs) or a listing driven by a repeating FAQ-item collection. Confirm the template type and URL with the web team before the first publish, then update this file.

### CMS Collections

#### 📄 FAQ (id: `kCI7wbxLr`) — primary
#### LOB FAQ (id: `jLTDNhP9V`) — LOB-scoped FAQs

One item per FAQ entry (question/answer pair). Items are rendered on the shared FAQ page, grouped by topic.

> **Collection structure to verify.** If the Framer project uses a single flat page item (all Q/A inline) rather than a repeating FAQ-item collection, the schema below will need to be reauthored to match the inline pattern. Confirm via the live preflight.

---

### SEO / Page Identity

> These fields apply if the FAQ page is CMS-driven with a page-level item. If the FAQ page is a static Framer page (no CMS collection for page-level metadata), omit this section and skip to the FAQ Items section.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `TBD` | Slug | string | URL path segment for the FAQ page (e.g. `faqs`) — set once on create; do not change on updates |
| `TBD` | Page Title | string | SEO `<title>` tag |
| `TBD` | Meta Description | string | SEO meta description |

---

### FAQ Items (📄 FAQ collection)

Each CMS item represents one FAQ entry. Items are grouped on the page by Topic.

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `pWmFF80uS` | Question | string | The FAQ question — plain text, no HTML |
| `iBOTRliBE` | Slug | string | URL-safe identifier for the item |
| `XuuzmIzfJ` | Topic | enum | Groups the FAQ item by topic area. Live cases: Global, AI, Modelling, Submission, Underwriters, Actuaries, US Admitted, Specialty & Commercial, Reinsurance, MGAs, IT, hyperoperator, Workflow Builder, Portfolio intelligence, Calculation Engines |
| `vSWhmdD2R` | Answer | richtext | The FAQ answer. HTML accepted: `<p>`, `<strong>`, `<ul>/<li>`. Keep to 2–5 sentences. |
| `ZzCAnAvFN` | Lob | string | LOB filter — leave blank for platform-level FAQs |
| `ytbgcIOgF` | LOB | string | Duplicate key (`$control__lob`) — likely a rename artifact; omit from bundles |

> **No Published or Order field exists in the live schema.** Those rows in the original template are schema drift — do not include them in bundles.

### FAQ Items (LOB FAQ collection — id: `jLTDNhP9V`)

| Field ID | Field Name | Type | Notes |
|---|---|---|---|
| `UWcJrE4IL` | Question | string | Plain text |
| `cv35R25li` | Slug | string | |
| `nyLiLg5yH` | Topic | enum | Cases: Global, AI, Modelling, Submission, Underwriters, Actuaries, US Admitted, Specialty & Commercial, Reinsurance, MGAs, IT |
| `YQqa4CrKR` | Answer | richtext | HTML or plain text |
| `H4W2yb8RP` | LOB | string | LOB filter |

---

### Page Layout Zones

```
Zone 1 — SEO / Page Identity (not visible on page; skip if FAQ page is static)
  ├── Slug ← URL path (TBD)
  ├── Page Title ← SEO title tag (TBD)
  └── Meta Description ← SEO meta (TBD)

Zone 2 — FAQ Items (repeating, grouped by Category)
  └── Per item:
        ├── Category ← enum (TBD) — controls grouping / section header
        ├── Question ← string (TBD)
        ├── Answer ← formattedText (TBD)
        ├── Order ← number (TBD)
        └── Published ← boolean (TBD)
```

> Update this diagram with confirmed zone names and node IDs after the first live preflight.

---

### Default Field Values

| Field | Field ID | Default |
|---|---|---|
| Published | `TBD` | `false` |

> Always set `Published` explicitly on `create`. On `update`, only include it if the published state is changing.

---

### Enum Case Resolution — Topic

The Topic enum groups FAQ items on the page. Confirmed live case names from 2026-06-24 preflight (📄 FAQ collection):

| Topic | Live case name |
|---|---|
| Global | `Global` |
| AI | `AI` |
| Modelling | `Modelling` |
| Submission (use case) | `Submission` |
| Underwriters | `Underwriters` |
| Actuaries | `Actuaries` |
| US Admitted | `US Admitted` |
| Specialty & Commercial | `Specialty & Commercial` |
| Reinsurance | `Reinsurance` |
| MGAs | `MGAs` |
| IT | `IT` |
| hyperoperator product | `hyperoperator` |
| Workflow Builder product | `Workflow Builder` |
| Portfolio intelligence product | `Portfolio intelligence` |
| Calculation Engines product | `Calculation Engines` |

---

### CMS Notes

- **Collection structure is unconfirmed.** The schema above assumes a repeating FAQ-item collection (one CMS item = one Q/A pair). If the live Framer project uses a different model (e.g. a single page item with inline Q/A slots, or a separate FAQs collection per category), reauthor this reference to match the live schema.
- **Category enum** — always resolve case names from the live preflight. Do not hardcode case names from this file until they have been confirmed.
- **Answer field** — `formattedText` HTML is accepted. For plain-text answers, pass the string without tags; Framer renders it as a paragraph. Do not use `<h2>` or `<h1>` inside answers.
- **Order field** — if the live collection has no numeric sort field, omit this row and note that ordering is managed manually in the Framer CMS UI.
- **Published toggle** — always set explicitly on `create` to avoid silent-publish. On `update`, only include if the published state is intentionally changing.
- **Icon fields** — if the FAQ template introduces icon or image fields (e.g. per-category icons), those cannot be set via `applyChanges` DSL. Flag them as `Manual actions` in the bundle.
- **Static page variant** — if the FAQ page is a non-CMS Framer static page with FAQ content managed as a code component or hard-coded, this skill cannot publish to it. Surface this clearly if the live preflight returns no FAQs collection.

---

## Framer Publishing Field Mapping

When producing output that will be published to Framer, structure the deliverable with clear labels for each CMS field:

### SEO / Page Identity (if applicable)
- **Slug** (`TBD`) — URL path segment
- **Page Title** (`TBD`) — SEO title tag
- **Meta Description** (`TBD`) — SEO meta description

### FAQ Item Fields
- **Category** (`TBD`) — enum case name (confirm from live preflight)
- **Question** (`TBD`) — plain-text question string
- **Answer** (`TBD`) — HTML-formatted answer (formattedText)
- **Order** (`TBD`) — numeric sort position within category
- **Published** (`TBD`) — `true` / `false`

> Replace every `TBD` with the confirmed field ID from the Step 1.5 preflight output before this reference is used in a live forward-mode run.
