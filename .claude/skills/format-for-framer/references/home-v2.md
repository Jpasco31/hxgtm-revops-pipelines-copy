# Home v2 — Framer Page Reference

Framer structure for the home-v2 homepage redesign: page URL, section node IDs, editable component properties, text node IDs, layout zones, and publishing field mapping. This page is used for editorial copy mapping and copy updates.

> **These node IDs are a cache, not the source of truth.** Node IDs and component $control__ keys can change when the Framer canvas is restructured. `format-for-framer` should reconcile this file against the live schema via a `framer.agent.getNodesOfTypes` preflight before any forward-mode SET operations. Update cached values here opportunistically when drift is detected.

> **Static page — no CMS collection.** Unlike `platform-new`, `events`, and `newsroom`, home-v2 is not driven by a Framer CMS collection. Content is stored directly on canvas text nodes (`RichTextNode`) and component instance properties (`$control__*` attributes). Publishing does not use `+CollectionItemNode`; it uses `SET <nodeId> <attribute>=<value>` operations via `framer.agent.applyChanges`. See Edit Notes below.

---

## Framer Page Structure

### Page

- URL: `/home-v2`
- Node ID: `SKNo5ujtA`
- Node type: `WebPageNode`

### Editable Zones

Nine zones in the Desktop frame (`p3EF40AzV`) under the main frame (`P4zrFEC9m`). Field types below distinguish **RichTextNode** (text node direct edits) from **component** ($control__ attribute SET operations on a `ComponentInstanceNode`).

---

#### Zone 1 — Hero (`Z7e_f1L_x`)

Container path: `Hero → Container → Header → Title`

| Node ID | Field Name | Type | Current content |
|---|---|---|---|
| `ZgC8h0IB9` | Main Heading | RichTextNode | "Underwrite Exponentially" (line break between words) |
| `BV38Isfa0` | Subheading | RichTextNode | "Leading insurance carriers use hx to reduce manual underwriting tasks and make faster, better decisions." |

---

#### Zone 2 — Social Proof / Stats (`cHnFs3zIs`)

Container path: `Section → Container`

| Node ID | $control__ key | Type | Current content / Notes |
|---|---|---|---|
| `k4sO9Znm9` | `content` | component string | "Trusted by 50+ leading commercial insurers across $75bn of premium every year." Scroll-animated gradient text. |
| `pzHgTO0Q1` | `title` | component string | Feature card 1 title: "Move work forward" |
| `pzHgTO0Q1` | `description` | component string | Feature card 1 body: "Analyze submissions, prepare decisions, and complete work inside your governance." |
| `oaeKUPJFm` | `title` | component string | Feature card 2 title: "Build your underwriting edge" |
| `oaeKUPJFm` | `description` | component string | Feature card 2 body: "Turn pricing, appetite, referral, and portfolio logic into tools AI agents can act on." |
| `PH41viekt` | `title` | component string | Feature card 3 title: "Write a better book" |
| `PH41viekt` | `description` | component string | Feature card 3 body: "Use outcomes, overrides, and rationale to strengthen guidance and portfolio steering." |

**Customer logo carousel** (`PDl64_4MU`, variant `Dark - Interactive`) sits at the top of this zone. It sources logos from the Customer Logos collection (`PqEpzH5pc`) internally — no editorial controls exposed here.

---

#### Zone 3 — Workbench Carousel (`Z6klyUCht`)

Container path: `Section → Container → Text wrap / Content`

**Section heading:**

| Node ID | Field Name | Type | Current content |
|---|---|---|---|
| `MhC0o8Lav` | Section Heading | RichTextNode | "Built for commercial P&C underwriting. AI handles the work from ingestion to pricing. Underwriters keep the calls that matter." |

**Use-case slides** — Desktop carousel (`iIkoallFQ`), Mobile carousel (`D_Y_9pbJO`). Each slide is a `ComponentInstanceNode` with a `title`, `description`, `pillColor`, and `pill01`–`pill04` controls.

| Node ID | `$control__title` | `$control__pillColor` | `$control__pill01` | `$control__pill02` | `$control__pill03` | `$control__pill04` |
|---|---|---|---|---|---|---|
| `SwHEe0_O9` | Submission triage | Blue | Overnight queue | Bordereaux ingestion | ACORD extraction | Appetite scoring |
| `apUblPfMf` | Complex risk assessment | Green | Quote generation | Novel risk pricing | Rate justification | What-if scenarios |
| `f1TNEs2pL` | Renewals | Purple | Renewal pipeline | Terms drafting | Rate change rationale | Senior referral flagging |
| `wui6DNvP7` | Portfolio Monitoring | Orange | Book-shape reporting | Concentration limits | Exposure alerts | Rate change analysis |
| `eDPa9s4J9` | Reinsurance management | Red | Program stress-testing | Cession optimisation | Treaty fit analysis | Treaty breach alerts |
| `HIBCG6vlL` | Wording & regulation | Yellow | Regulatory sweep | Wording-update monitoring | Lloyd's bulletin tracking | Wording analysis |
| `pY0ILBPqz` | Actuarial modeling | Blue | Batch portfolio runs | Loss curve benchmarking | Model re-parameterisation | Version publishing |

Each slide also has `$control__description` — a one-sentence explanation of the workflow. See Publishing Field Mapping below for the current descriptions.

---

#### Zone 4 — Testimonial Carousel (`Ibs8zUYfE`)

`ComponentInstanceNode` — variant `Desktop`.

| Attribute | Current value | Notes |
|---|---|---|
| `$control__testimonial` | `mXwRT9GQP` | Item ID from the Customer Story Quotes collection (`vWjx7C_pn`). Change this value to swap the featured quote. The referenced item must exist in that collection. |

---

#### Zone 5 — Comparison (`ddmhaQnA2`)

Container path: `Section → Container → Content`

**Section heading:**

| Node ID | Field Name | Type | Current content |
|---|---|---|---|
| `el1JC1p09` | Section Heading | RichTextNode | "More than an underwriting workbench. A partner in doing actual underwriting work." |

**Card 01 — "Traditional workbenches"** (`eru4_gMaK`):

| Node ID | Field Name | Type | Current content |
|---|---|---|---|
| `k4oBI6YYt` | Card 01 Title | RichTextNode | "Traditional workbenches" |
| `CmE7oDPbP` | `$control__text` | component string | "Collect information around a decision" |
| `SjWpAZiZS` | `$control__text` | component string | "Route work, but don't act on it" |
| `TET8H4kh6` | `$control__text` | component string | "Record decisions after they happen" |

**Card 02 — "hyperexponential"** (`YR6PGvVrA`):

| Node ID | Field Name | Type | Current content |
|---|---|---|---|
| `uWow99S1l` | Card 02 Title | RichTextNode | "hyperexponential" |
| `yS5gkZ4yq` | `$control__text` | component string | "Ingest, triage, cleanse, and enrich submissions" |
| `lQmZZVOSA` | `$control__text` | component string | "Assess risks and calculate pricing" |
| `C6Me4Blr_` | `$control__text` | component string | "Manage portfolio impacts" |
| `T6U5qKWbp` | `$control__text` | component string | "Prepare decisions" |
| `CauFHSwlD` | `$control__text` | component string | "Improves outcomes" |

---

#### Zone 6 — Platform Capabilities (`huAdltotQ`)

Container path: `Section → Container → Products overview / Main Container`

**Section title text node:**

| Node ID | Field Name | Type | Current content |
|---|---|---|---|
| `VLWsMJyFg` | Section Title | RichTextNode | "Explore the hx platform" |

**Platform tabs component** (`hq496H3MR`): a single `ComponentInstanceNode` that controls all four capability tab panels. All four capability headings, descriptions, bullet sets, and images are SET on this one node.

| $control__ key | Capability | Current content / Notes |
|---|---|---|
| `hOHeading` | hyperoperator heading | "The AI agent for end-to-end underwriting work" |
| `hODescription` | hyperoperator description | "hyperoperator plans and executes multi-step underwriting work inside your rules, permissions, models…" |
| `hOBullet01` | hyperoperator bullet 1 | "Purpose-built for insurance" |
| `hOBullet02` | hyperoperator bullet 2 | "Governed by your rules and controls" |
| `hOBullet03` | hyperoperator bullet 3 | "Executes routine and ad-hoc work" |
| `hOBullet04` | hyperoperator bullet 4 | "Coordinates specialist agents end to end" |
| `hOImage` | hyperoperator image | `https://framerusercontent.com/images/fiWZL7mEIBj0lQZddJGq2FOvYWY.png` |
| `wBHeading` | Workflow Builder heading | ⚠ **PLACEHOLDER** — "Lorem ipsum lorem ipsum. Agents do the rest." Needs real copy. |
| `wBDescription` | Workflow Builder description | ⚠ **PLACEHOLDER** — lorem ipsum body. Needs real copy. |
| `wBBullet01` | Workflow Builder bullet 1 | "Purpose-built for insurance" |
| `wBBullet02` | Workflow Builder bullet 2 | "Governed, not autonomous" |
| `wBBullet03` | Workflow Builder bullet 3 | "Routine workflows, ad-hoc explorations, continuous monitoring" |
| `wBBullet04` | Workflow Builder bullet 4 | "Specialist agents coordinated under one orchestration layer" |
| `wBImage` | Workflow Builder image | `https://framerusercontent.com/images/4V0vstI3f2MEKPAAOX54kZPGoRQ.png` |
| `cEHeading` | Calculation Engines heading | "The platform's engines encode your rules." |
| `cEDescription` | Calculation Engines description | "The platform's engines encode your rules, ground your data, and govern the constraints behind every decision." |
| `cEBullet01` | Calculation Engines bullet 1 | "Carrier-owned stage logic" |
| `cEBullet02` | Calculation Engines bullet 2 | "Engines callable by agents and humans" |
| `cEBullet03` | Calculation Engines bullet 3 | "Memory across operational records and institutional IP" |
| `cEBullet04` | Calculation Engines bullet 4 | "Controls govern authority, budgets, confidence, and review points" |
| `cEImage` | Calculation Engines image | `https://framerusercontent.com/images/493RZPGu4FOKYFYcOYmNPiS4LA.png` |
| `pIHeading` | Portfolio Intelligence heading | "Steer the book before it drifts." |
| `pIDescription` | Portfolio Intelligence description | "Connect portfolio signals (exposure concentration, loss ratio trends, adequacy drift) to the decision layer." |
| `pIBullet01` | Portfolio Intelligence bullet 1 | ⚠ Currently reuses CE copy: "Carrier-owned stage logic" — needs real PI-specific copy. |
| `pIBullet02` | Portfolio Intelligence bullet 2 | ⚠ Currently reuses CE copy: "Engines callable by agents and humans" |
| `pIBullet03` | Portfolio Intelligence bullet 3 | ⚠ Currently reuses CE copy: "Memory across operational records and institutional IP" |
| `pIBullet04` | Portfolio Intelligence bullet 4 | ⚠ Currently reuses CE copy: "Controls govern authority, budgets, confidence, and review points" |
| `pIImage` | Portfolio Intelligence image | `https://framerusercontent.com/images/tJSOfTfJhg1BA6qTOesB3sDSRw.png` |

**Governance subzone** (Main Container: `vYP7xD4Nw`):

| Node ID | Field Name | Type | Current content |
|---|---|---|---|
| `f8SKGKoXa` | Governance Header | RichTextNode | "Your logic. Your rules. Your audit trail." |
| `gpTvonuYa` | Controlled Title | RichTextNode | "Controlled" |
| `C2ym1XD3x` | Controlled Description | RichTextNode | "Agents act only inside the rules you set: authorities, permissions, budgets, and review points." |
| `U_uXQ8uma` | Audited Title | RichTextNode | "Audited" |
| `DLdd6XPzG` | Audited Description | RichTextNode | "Decision Trace captures every action, model call, and data touch. No additional instrumentation needed." |
| `Tphbu6m0U` | Defensible Title | RichTextNode | "Defensible" |
| `t5lvFCVGu` | Defensible Description | RichTextNode | "Audit trails and governed logic make agent-led underwriting explainable. Designed for PRA, NAIC, BMA, and Lloyd's." |
| `dFFbsSOoj` | Compliance Info | RichTextNode | "SOC 2 Type 2 · ISO 27001:2022 · PRA · NAIC · BMA · Lloyd's" |

---

#### Zone 7 — Customer Quote Carousel (`hNj3ZZfve`)

`ComponentInstanceNode` (`DgrqETItC`): slider with `$control__isMobile: Desktop` and `$control__slideBarGap: 32`. Quote content is baked into the component design — no editorial controls exposed via $control__ attributes. Edit quotes in Framer directly.

---

#### Zone 8 — Integrations (`Y2Qn1k198`)

Container path: `Section → Container → Text wrap / Content`

**Section text nodes:**

| Node ID | Field Name | Type | Current content |
|---|---|---|---|
| `JwaN9NGaA` | Section Heading | RichTextNode | "Connected to the systems your workflows runs on" |
| `PJxKnT5ja` | Section Description | RichTextNode | "hx connects to the policy admin systems, data providers, AI infrastructure, and market venues your underwriting already runs on." |

**Integration category slides** (carousel: `IcjPNhkfL`, 5 slides):

| Node ID | `$control__title` | `$control__description` |
|---|---|---|
| `K4xR7mXdg` | Policy admin systems | "Sits earlier in the cycle. Your PAS stays the system of record." |
| `qPbURTJ8F` | Insurance data & models | "Called as governed tools inside every workflow." |
| `wsT0Hu_2x` | AI infrastructure | "Foundation models, agent frameworks, and inference, governed for insurance." |
| `NDqahjfWP` | Productivity & portals | "Runs wherever the work happens: web, PAS, portal, API, or scheduled job." |
| `ojw3of5Pc` | Reinsurance & market access | "Continuous monitoring across Lloyd's and treaty markets." |

---

#### Zone 9 — CTA Footer (`AI7yEIHmu`)

`ComponentInstanceNode` with `$control__variant: Light | With image` and `$control__isMobile: false`. Content not exposed via editable controls; update in Framer directly.

---

### Page Layout Zones

```
WebPage /home-v2 (SKNo5ujtA)
└── Desktop (p3EF40AzV)
    ├── TRUE H1 HEADING (M0VdXNPey) — SEO h1, not visible
    ├── Nav (p_bZgY6j1)
    └── main (P4zrFEC9m)
        ├── Zone 1 — Hero (Z7e_f1L_x)
        │     ├── Main Heading ← ZgC8h0IB9 [RichTextNode]
        │     ├── Subheading ← BV38Isfa0 [RichTextNode]
        │     └── BG Video / Overlay (static)
        │
        ├── Zone 2 — Social Proof (cHnFs3zIs)
        │     ├── Logo Carousel ← PDl64_4MU [Customer Logos — internal]
        │     ├── Stat text ← k4sO9Znm9 · $content
        │     └── Feature cards
        │           ├── Card 1 ← pzHgTO0Q1 · $title / $description
        │           ├── Card 2 ← oaeKUPJFm · $title / $description
        │           └── Card 3 ← PH41viekt · $title / $description
        │
        ├── Zone 3 — Workbench Carousel (Z6klyUCht)
        │     ├── Section Heading ← MhC0o8Lav [RichTextNode]
        │     └── Use-case slides (Desktop: iIkoallFQ, Mobile: D_Y_9pbJO)
        │           ├── Slide 1 ← SwHEe0_O9 · $title / $description / $pillColor / $pill01–04
        │           ├── Slide 2 ← apUblPfMf
        │           ├── Slide 3 ← f1TNEs2pL
        │           ├── Slide 4 ← wui6DNvP7
        │           ├── Slide 5 ← eDPa9s4J9
        │           ├── Slide 6 ← HIBCG6vlL
        │           └── Slide 7 ← pY0ILBPqz
        │
        ├── Zone 4 — Testimonial Carousel (Ibs8zUYfE)
        │     └── $testimonial = Customer Story Quotes item ID ← $control__testimonial
        │
        ├── Zone 5 — Comparison (ddmhaQnA2)
        │     ├── Section Heading ← el1JC1p09 [RichTextNode]
        │     ├── Card 01 "Traditional workbenches"
        │     │     ├── Title ← k4oBI6YYt [RichTextNode]
        │     │     └── Bullets ← CmE7oDPbP / SjWpAZiZS / TET8H4kh6 · $text
        │     └── Card 02 "hyperexponential"
        │           ├── Title ← uWow99S1l [RichTextNode]
        │           └── Bullets ← yS5gkZ4yq / lQmZZVOSA / C6Me4Blr_ / T6U5qKWbp / CauFHSwlD · $text
        │
        ├── Zone 6 — Platform Capabilities (huAdltotQ)
        │     ├── Section Title ← VLWsMJyFg [RichTextNode]
        │     ├── Platform Tabs ← hq496H3MR (single node, all 4 capabilities)
        │     │     ├── hyperoperator: $hOHeading / $hODescription / $hOBullet01–04 / $hOImage
        │     │     ├── Workflow Builder: $wBHeading / $wBDescription / $wBBullet01–04 / $wBImage ⚠ placeholder
        │     │     ├── Calculation Engines: $cEHeading / $cEDescription / $cEBullet01–04 / $cEImage
        │     │     └── Portfolio Intelligence: $pIHeading / $pIDescription / $pIBullet01–04 / $pIImage ⚠ reused bullets
        │     └── Governance subzone (vYP7xD4Nw)
        │           ├── Header ← f8SKGKoXa [RichTextNode]
        │           ├── Controlled ← gpTvonuYa / C2ym1XD3x [RichTextNode]
        │           ├── Audited ← U_uXQ8uma / DLdd6XPzG [RichTextNode]
        │           ├── Defensible ← Tphbu6m0U / t5lvFCVGu [RichTextNode]
        │           └── Compliance ← dFFbsSOoj [RichTextNode]
        │
        ├── Zone 7 — Customer Quote Carousel (hNj3ZZfve)
        │     └── DgrqETItC [static, no editorial controls]
        │
        ├── Zone 8 — Integrations (Y2Qn1k198)
        │     ├── Section Heading ← JwaN9NGaA [RichTextNode]
        │     ├── Section Description ← PJxKnT5ja [RichTextNode]
        │     └── Integration slides (IcjPNhkfL)
        │           ├── Slide 1 ← K4xR7mXdg · $title / $description
        │           ├── Slide 2 ← qPbURTJ8F
        │           ├── Slide 3 ← wsT0Hu_2x
        │           ├── Slide 4 ← NDqahjfWP
        │           └── Slide 5 ← ojw3of5Pc
        │
        └── Zone 9 — CTA Footer (AI7yEIHmu)
              └── [static component, edit in Framer directly]
```

---

## Edit Notes

- **Static page — no CMS collection publishing.** Do not attempt `+CollectionItemNode` operations on this page. All edits go through `SET <nodeId> <attribute>=<value>` in `framer.agent.applyChanges`.

- **RichTextNode editing** — Text content in `RichTextNode` nodes lives in the node's child tree (`TextBlock → TextRun.attributes.text`). Use the Framer agent's text-edit API or a canvas `SET` that replaces the node's `children` array. Multi-word headings with line breaks encode as multiple `TextRun` items separated by a `TextLineBreak` node.

- **Component $control__ editing** — Set component instance properties via:
  ```
  SET <nodeId> $control__<key>="<value>";
  ```
  Multiple attributes can be chained in a single `SET` statement on the same node ID.

- **Placeholder content in Zone 6 (Workflow Builder)** — `$control__wBHeading` and `$control__wBDescription` are lorem ipsum placeholder text. These should be updated with real Workflow Builder copy before publishing home-v2.

- **Placeholder bullets in Zone 6 (Portfolio Intelligence)** — `$control__pIBullet01–04` currently reuse the Calculation Engines bullet set. They need Portfolio Intelligence–specific copy.

- **Testimonial (Zone 4)** — To swap the testimonial, SET `$control__testimonial` on node `Ibs8zUYfE` to the item ID of the desired quote from the Customer Story Quotes collection (`vWjx7C_pn`). Current value: `mXwRT9GQP`.

- **Zone 7 (Customer Quote Carousel)** — Content is baked into the component design. No editorial controls exposed. To change quoted content, edit the component in Framer directly or have the design team update it.

- **Zone 9 (CTA Footer)** — Content is static (`Light | With image` variant). No editorial controls exposed here.

---

## Framer Publishing Field Mapping

Key editable fields and their targeting info:

**Zone 1 — Hero**
- **Main Heading** (`ZgC8h0IB9`, RichTextNode) — primary page headline
- **Subheading** (`BV38Isfa0`, RichTextNode) — one-sentence supporting statement

**Zone 2 — Social Proof**
- **Stat line** (`k4sO9Znm9`, `$control__content`) — the "Trusted by 50+ leading commercial insurers…" gradient scroll text
- **Feature card 1** (`pzHgTO0Q1`) — `$control__title` + `$control__description`
- **Feature card 2** (`oaeKUPJFm`) — `$control__title` + `$control__description`
- **Feature card 3** (`PH41viekt`) — `$control__title` + `$control__description`

**Zone 3 — Workbench**
- **Section heading** (`MhC0o8Lav`, RichTextNode)
- **Slides 1–7** — each slide: `$control__title` + `$control__description` + `$control__pillColor` + `$control__pill01`–`$control__pill04`

**Zone 4 — Testimonial**
- **Testimonial reference** (`Ibs8zUYfE`, `$control__testimonial`) — Customer Story Quotes item ID

**Zone 5 — Comparison**
- **Section heading** (`el1JC1p09`, RichTextNode)
- **Card 01 bullets** (`CmE7oDPbP` / `SjWpAZiZS` / `TET8H4kh6`) — `$control__text` on each node
- **Card 02 bullets** (`yS5gkZ4yq` / `lQmZZVOSA` / `C6Me4Blr_` / `T6U5qKWbp` / `CauFHSwlD`) — `$control__text`

**Zone 6 — Platform Capabilities**
- **Section title** (`VLWsMJyFg`, RichTextNode)
- **Platform tabs** (`hq496H3MR`) — all hO*, wB*, cE*, pI* controls on this single node
- **Governance header** (`f8SKGKoXa`, RichTextNode)
- **Feature tiles** — 3 pairs: `gpTvonuYa`/`C2ym1XD3x`, `U_uXQ8uma`/`DLdd6XPzG`, `Tphbu6m0U`/`t5lvFCVGu`
- **Compliance bar** (`dFFbsSOoj`, RichTextNode)

**Zone 8 — Integrations**
- **Section heading** (`JwaN9NGaA`, RichTextNode)
- **Section description** (`PJxKnT5ja`, RichTextNode)
- **Integration slides** (`K4xR7mXdg`, `qPbURTJ8F`, `wsT0Hu_2x`, `NDqahjfWP`, `ojw3of5Pc`) — `$control__title` + `$control__description`
