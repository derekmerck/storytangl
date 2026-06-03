# StoryTangl Brand Assets

This directory is the canonical source package for StoryTangl brand assets.
It mirrors the reviewed design bundle and keeps source SVG/CSS/TXT assets in
Git. Deployment copies live in app- or docs-specific locations only when a
client naturally needs them.

## Files

- [`StoryTangl-Brand-Sheet.html`](StoryTangl-Brand-Sheet.html): visual reference.
- [`StoryTangl-brand-sheet.pdf`](StoryTangl-brand-sheet.pdf): print-to-PDF
  snapshot of the brand sheet for quick visual review.
- [`USAGE.md`](USAGE.md): usage rules for the mark, palette, type, and tone.
- [`assets/`](assets/): source SVGs, CSS tokens, and CLI splash text.

## Deployment Copies

- `apps/web/public/favicon.svg`
- `apps/web/src/styles/storytangl-palette.css`
- `apps/web/src/styles/storytangl-type.css`
- `docs/src/_static/favicon.svg`
- `docs/src/_static/storytangl-palette.css`
- `docs/src/_static/storytangl-type.css`
- `.github/social-card.svg` as source for a future raster social preview
- `apps/cli/src/tangl/cli/assets/splash.txt`

PNG/JPG exports are intentionally not committed in this pass.
