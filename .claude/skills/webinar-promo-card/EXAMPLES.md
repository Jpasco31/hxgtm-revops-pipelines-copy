# webinar-promo-card — examples and references

## Canonical layout

The templates in [`templates/`](templates/) ARE the canonical layouts. When in doubt about gradient SVG placement, grain layer, vignette, type sizes, or speaker-tile geometry, read them directly.

The brand-team reference renders below show the visual targets these templates aim to match.

## Brand reference renders (from design-system)

These two PNGs are the brand-team renders that anchor the layout. They use the Wine gradient and bracket the tile sizing for 2 vs 3 speakers.

- 2-speaker: [`../design-system/assets/reference-renders/Social Media Webinar Promo - 2 Speakers.png`](../design-system/assets/reference-renders/Social%20Media%20Webinar%20Promo%20-%202%20Speakers.png)
- 3-speaker: [`../design-system/assets/reference-renders/Social Media Webinar Promo - 3 Speakers.png`](../design-system/assets/reference-renders/Social%20Media%20Webinar%20Promo%20-%203%20Speakers.png)

Note the 3-speaker layout is structurally different from the 2-speaker layout: the headline goes full-width and the speaker row sits horizontally across the bottom, instead of a right-column stack.

The **4-speaker** variant (`templates/card-4-speakers.html`) reuses the 3-speaker single-column layout with a fourth tile added; the four-tile row spans the full content width (≈edge-to-edge) rather than ending short. There is no separate brand-team reference render — it derives from the Figma "Type=4 Speakers" frame and the 3-speaker comp above.

## Worked example brief

```
Event: State of AI in Underwriting 2026
Headline: State of AI in underwriting 2026
Subtitle: What's working, what's not, and what's next
Date / time: March 26, 2026, 11am EST / 4pm GMT
Gradient: ink
Speakers:
  - Richard Gunn, President, hyperexponential, /Users/.../richard.jpg
  - Krzysztof Wanatowicz, CTO, Allianz Commercial NA, /Users/.../krzysztof.jpg
Campaign folder: /Users/.../hx-plugins/campaigns/state-of-ai-2026
```

Expected outputs:

```
campaigns/state-of-ai-2026/
├── working/
│   ├── headshots/
│   │   ├── richard-gunn_504.png
│   │   └── krzysztof-wanatowicz_504.png
│   └── linkedin-card_20260326_state-of-ai-in-underwriting-2026.html
└── export/
    ├── linkedin-card_20260326_state-of-ai-in-underwriting-2026.png
    └── linkedin-card_20260326_state-of-ai-in-underwriting-2026@2x.png
```

The HTML is fully self-contained — base64 fonts and the chosen gradient SVG are inlined, with no sibling `fonts/` folder and no external stylesheets.

## Adjacent skills

- [`../design-system/SKILL.md`](../design-system/SKILL.md) — brand tokens, voice, logos, decorations. Required by this skill (`requires: [design-system]`).
