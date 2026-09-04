# README and social artwork

`AGENTS.md` says never to create PNG or JPG inside the repository and to reach
for SVG primitives instead. These four files are a deliberate exception, and
the reason is the wordmark.

The brand SVGs in `brand/assets/` name Newsreader and JetBrains Mono by family
only; they embed no font. Anything that renders them without those faces
installed silently substitutes a fallback, and the turned-`G` is tuned per font
(`brand/USAGE.md` section 1) -- under a fallback serif it collides with the
following `l` and the wordmark reads "StoryTanol". GitHub does not load
webfonts for an SVG referenced from a README, and its social preview accepts
raster only. So this artwork ships pre-rendered with the real faces embedded.

| File | Used by | Size |
|------|---------|------|
| `README-banner.png` | `README.md`, light theme | 2560x720 |
| `README-banner-dark.png` | `README.md`, dark theme | 2560x720 |
| `social-card.png` | repository Settings -> Social preview | 1280x640 |
| `cli-session.png` | `README.md`, the "See It Run" section | 1136x1492 |

All four are Git LFS objects, per `.gitattributes`.

## Regenerating

The three brand images derive from the SVG sources and are reproducible:

```bash
python scripts/render_brand_assets.py
```

Do not hand-edit them, and do not re-render through a tool that resolves fonts
from the system -- `rsvg-convert`, ImageMagick, and CoreText-backed tools all
substitute a fallback without reporting it. See `brand/USAGE.md` section 3.

`cli-session.png` is a typeset capture of a real `tangl-cli` session rather
than a derived asset, so no script reproduces it. It was captured through a PTY
so the prompts are genuine, and typeset monochrome because the CLI emits no
ANSI even under a 256-colour `TERM`. Recapture it by hand if the CLI's output
changes materially.
