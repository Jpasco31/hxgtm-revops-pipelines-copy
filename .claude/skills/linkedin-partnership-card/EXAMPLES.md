# linkedin-partnership-card examples

## Reference rendering

A canonical, validated output of this skill lives at:

- 1x: [`samples/reference-partnership-card_oliver-wyman.png`](samples/reference-partnership-card_oliver-wyman.png) (1200x675)
- 2x: [`samples/reference-partnership-card_oliver-wyman@2x.png`](samples/reference-partnership-card_oliver-wyman@2x.png) (2400x1350)

It shows the expected lockup: hyperexponential wordmark on the left, white "+" mark in the center, partner logo on the right, dark blue background with blue glow and dot field. Use it as the optical reference when checking new cards in step 7.

## Worked example brief

```
Partner: Acme Insurance
Partner logo: /Users/david.spitz/Downloads/acme-insurance-logo.png
Filename date: 20260501
Campaign folder: /Users/david.spitz/Library/CloudStorage/Egnyte-spitzfamily/Shared/Agent Brain/gtmos/Projects/Rev Ops Pipelines/campaigns/acme-partnership
```

Expected processed logo:

```
campaigns/acme-partnership/
└── working/
    └── assets/
        └── acme-insurance-logo-white-transparent.png
```

Expected card outputs:

```
campaigns/acme-partnership/
├── working/
│   └── linkedin-partnership-card_20260501_acme-insurance.html
└── export/
    ├── linkedin-partnership-card_20260501_acme-insurance.png
    └── linkedin-partnership-card_20260501_acme-insurance@2x.png
```

## Adjacent Skills

- [`../design-system/SKILL.md`](../design-system/SKILL.md) - brand tokens, logo assets, and design-system references.
- [`../webinar-promo-card/SKILL.md`](../webinar-promo-card/SKILL.md) - structural reference for visual-card skill orchestration.
