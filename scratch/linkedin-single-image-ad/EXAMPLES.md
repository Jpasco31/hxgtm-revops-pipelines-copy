# linkedin-single-image-ad - examples and references

## Canonical layout

The four templates in [`templates/`](templates/) ARE the canonical layouts. When in doubt about hero-slot dimensions, gradient stack, type sizes, or CTA pill geometry, read them directly. The hero-slot dimensions are also locked in [`hero-images/manifest.json`](hero-images/manifest.json).

## Worked example brief

```
Headline: See your portfolio in real time
Variant: gradient-center
Gradient: forest
Hero: portfolio
Subtitle: (none)
Campaign folder: /Users/.../Projects/Rev Ops Pipelines/campaigns/portfolio-2026
```

Steps:

1. Read brand context (`../design-system/SKILL.md` etc.).
2. Pick scaffold: `templates/card-gradient-center.html`.
3. Resolve hero: copy `hero-images/portfolio--center.png` to `[campaign-folder]/working/hero/portfolio--center.png` (since `gradient-center` uses the `center` slot).
4. Compose: replace `{{FONT_FACE_BLOCK}}` with `../design-system/tokens/fonts-inline-card.css`, `{{HEADLINE}}` with `See your portfolio in real time`, `{{SUBTITLE}}` with empty string, `{{HERO_IMAGE_NODE}}` with `<img src="hero/portfolio--center.png" alt="">`, `{{GRADIENT_BASE}}` with `#01514F`, swap the `BG_STACK` block for the Forest recipe from `README.md`.
5. Write to `[campaign-folder]/working/linkedin-ad_20260618_see-your-portfolio-in-real-time.html`.
6. Run `node scripts/export_card.js <html-path> [campaign-folder]/export`.

Expected outputs:

```
campaigns/portfolio-2026/
├── working/
│   ├── hero/
│   │   └── portfolio--center.png
│   └── linkedin-ad_20260618_see-your-portfolio-in-real-time.html
└── export/
    ├── linkedin-ad_20260618_see-your-portfolio-in-real-time.png       # 1080x1080
    └── linkedin-ad_20260618_see-your-portfolio-in-real-time@2x.png    # 2160x2160
```

The HTML is fully self-contained - base64 fonts inlined, inline CSS, inline lockup SVG. The only sibling dependency is `working/hero/portfolio--center.png`.

## Worked example: user-supplied hero image

```
Headline: Try AI-powered underwriting
Variant: gradient-left
Gradient: wine
Hero: /Users/.../my-product-screenshot.png
CTA label: Schedule a demo
Campaign folder: /Users/.../campaigns/q3-demo-push
```

Step 6 changes - instead of copying a pre-cropped hero, run the cropper:

```
node scripts/crop_hero.js \
  /Users/.../my-product-screenshot.png \
  left \
  "/Users/.../campaigns/q3-demo-push/working/hero/my-product-screenshot--left.png" \
  --auto-focal
```

Then proceed with compose (step 7 onward), inlining `<img src="hero/my-product-screenshot--left.png" alt="">` into the template's `{{HERO_IMAGE_NODE}}` slot.

## Worked example: two-line headline (white-left)

```
Headline line 1: Smarter triage.
Headline line 2: Quote in minutes.
Variant: white-left
Hero: portfolio
CTA label: Schedule a demo
Campaign folder: /Users/.../campaigns/triage-2026
```

Step 4 picks `templates/card-white-left.html`. Step 6 copies `hero-images/portfolio--white-left.png` to `working/hero/`. Step 7 fills `{{HEADLINE_LINE_1}}` = `Smarter triage.` (dark) and `{{HEADLINE_LINE_2}}` = `Quote in minutes.` (muted gray).

## Adjacent skills

- [`../design-system/SKILL.md`](../design-system/SKILL.md) - brand tokens, voice, logos, decorations. Required by this skill (`requires: [design-system]`).
- [`../webinar-promo-card/SKILL.md`](../webinar-promo-card/SKILL.md) - the sister skill for 1200x627 webinar / virtual-event / panel cards with named speakers. Use that one for events, not this one.
