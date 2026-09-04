# Binary assets here are adjudicated

The root `AGENTS.md` says to prefer SVG (rule 1). This directory is the
exception, deliberately, and this file is the record of that decision rather
than a request to make it again.

## Why these must be raster

The brand SVGs in `brand/assets/` name Newsreader and JetBrains Mono by family
and embed neither. Any renderer without those faces installed substitutes a
fallback without reporting it, and the turned-`G` is tuned per font
(`brand/USAGE.md` section 1) — under a fallback serif it collides with the
following `l` and the wordmark reads "StoryTanol". GitHub loads no webfont for
an SVG referenced from a README, so shipping the vector would show that broken
wordmark to every visitor. The social preview accepts raster only regardless.

The vector stays authoritative in `brand/assets/`. What ships here is rendered
from it with the real faces embedded.

## These stay in LFS

Nothing here is a *required asset* under root rule 4: no test asserts these
bytes and nothing in CI reads them. Rule 3 is not engaged, so they stay
LFS-tracked by the root `.gitattributes` rather than being un-LFS'd the way
`worlds/repartee_loop/` is. Where that world would fail its suite on a pointer
file, this directory degrades to a missing README image.

If something ever starts reading these bytes, that inverts: un-LFS them in a
scoped `.gitattributes` and amend this file.

## The budget

Six files, about 810 KB, none of them source.

| File | Used by | Size |
|------|---------|------|
| `README-banner.png` | `README.md`, light theme | 2560x720 |
| `README-banner-dark.png` | `README.md`, dark theme | 2560x720 |
| `social-card.png` | repository Settings -> Social preview | 1280x640 |
| `cli-session.png` | `README.md`, the "See It Run" section | 1136x1492 |
| `repartee-quay.png` | `README.md`, the reskin pair | 960x600 |
| `repartee-spaceport.png` | `README.md`, the reskin pair | 960x600 |

## Regenerating

The three brand images derive from the committed SVGs:

```bash
python scripts/render_brand_assets.py
```

The dark banner is not a separate drawing. It is the same SVG with the palette
substituted at render time, because `brand/USAGE.md` section 7 requires the ink
and paper modes to change in lockstep and a hand-maintained second file is how
that gets broken.

Do not hand-edit these, and do not re-render through a tool that resolves fonts
from the system — `rsvg-convert`, ImageMagick, and CoreText-backed tools all
substitute a fallback silently. See `brand/USAGE.md` section 3.

The two `repartee-*` frames are rendered by
[`scripts/capture_world_frames.py`](../../scripts/capture_world_frames.py),
which drives the pygame client headlessly once per art pack:

```bash
poetry run python scripts/capture_world_frames.py --advance 1
```

They are raster because they are screenshots of a pixel-art renderer; there
is no vector form to prefer. Both are the same beat at the same advance
count, so their prose and choices are identical and only the art differs --
which is the claim a reskin screenshot is making.

`cli-session.png` is a typeset capture of a real `tangl-cli` session, not a
derived asset, so no script reproduces it. It was captured through a PTY so the
prompts are genuine, and set monochrome because the CLI emits no ANSI even
under a 256-colour `TERM`. Recapture by hand if the CLI output changes.

## Adding here

Repository chrome only — artwork GitHub itself renders. Anything a client or a
world loads at runtime belongs with that world, under rules 4 and 5. A new file
here needs a row in the table above and a sentence saying why SVG will not
serve; if the answer is only "it was easier", the answer is SVG.
