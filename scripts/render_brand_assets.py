#!/usr/bin/env python3
"""Rasterize the brand SVGs with the real webfonts embedded.

The shipped SVGs in ``brand/assets/`` name Newsreader and JetBrains Mono by
family only, so any renderer lacking those faces silently substitutes a
fallback. For the wordmark that is not a cosmetic downgrade: the turned-G is
tuned per font (``brand/USAGE.md`` sec.1), and under a fallback serif the glyph
collides with the following ``l``. GitHub cannot load webfonts for an SVG in a
README, so the README and social-preview artwork ship as PNG rendered here.

Fonts are not vendored. Fetch the two OFL families into ``--fonts`` first::

    mkdir -p tmp/brandbuild/fonts && cd tmp/brandbuild/fonts
    curl -sSLO https://github.com/google/fonts/raw/main/ofl/newsreader/'Newsreader[opsz,wght].ttf'
    curl -sSLO https://github.com/google/fonts/raw/main/ofl/newsreader/'Newsreader-Italic[opsz,wght].ttf'
    curl -sSLO https://github.com/google/fonts/raw/main/ofl/jetbrainsmono/'JetBrainsMono[wght].ttf'

Then::

    python scripts/render_brand_assets.py

The social preview is not settable through the GitHub API; upload the generated
``.github/assets/social-card.png`` under repository Settings -> Social preview.
"""

from __future__ import annotations

import argparse
import base64
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (svg source, css width, css height, device scale, output)
TARGETS = [
    ("brand/assets/README-banner.svg", 1280, 360, 2, ".github/assets/README-banner.png"),
    ("brand/assets/social-card.svg", 1280, 640, 1, ".github/assets/social-card.png"),
]

# (css family, css style, filename must contain, filename must not contain)
FACES = [
    ("Newsreader", "normal", "newsreader", "italic"),
    ("Newsreader", "italic", "newsreader", None),
    ("JetBrains Mono", "normal", "jetbrains", None),
]

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
]


def find_chrome(explicit: str | None) -> str:
    for cand in ([explicit] if explicit else []) + CHROME_CANDIDATES:
        if cand and (Path(cand).exists() or shutil.which(cand)):
            return cand
    sys.exit("No Chrome/Chromium found; pass --chrome with a path to the binary.")


def build_faces(fonts: Path) -> str:
    """Embed each face as a data URI, tolerating either Google Fonts naming
    convention (``Newsreader[opsz,wght].ttf`` or a flattened ``Newsreader.ttf``)."""
    ttfs = sorted(p for p in fonts.iterdir() if p.suffix.lower() in (".ttf", ".otf"))
    out = []
    for family, style, must, must_not in FACES:
        want_italic = style == "italic"
        hits = [p for p in ttfs
                if must in p.name.lower()
                and ("italic" in p.name.lower()) == want_italic]
        if not hits:
            sys.exit(f"Missing {family} ({style}) in {fonts}; see this script's docstring.")
        b64 = base64.b64encode(hits[0].read_bytes()).decode()
        out.append(
            f"@font-face{{font-family:'{family}';"
            f"src:url(data:font/ttf;base64,{b64}) format('truetype-variations');"
            f"font-weight:100 900;font-style:{style};font-display:block}}"
        )
    return "\n".join(out)


def render(chrome: str, faces: str, work: Path, svg_rel: str, w: int, h: int,
           scale: int, out_rel: str) -> None:
    svg = (ROOT / svg_rel).read_text().replace('<?xml version="1.0"?>\n', "")
    svg = re.sub(r"<svg ", f'<svg width="{w}" height="{h}" ', svg, count=1)
    page = work / (Path(out_rel).stem + ".html")
    page.write_text(
        '<meta charset="utf-8">'
        f"<style>{faces}\nhtml,body{{margin:0;padding:0;overflow:hidden}}"
        f"svg{{display:block}}</style>{svg}",
        encoding="utf-8",
    )
    out = ROOT / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         f"--force-device-scale-factor={scale}", f"--window-size={w},{h}",
         "--virtual-time-budget=10000", f"--screenshot={out}", page.as_uri()],
        check=True, capture_output=True,
    )
    print(f"{out_rel}  {w * scale}x{h * scale}  {out.stat().st_size // 1024} KB")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fonts", type=Path, default=ROOT / "tmp/brandbuild/fonts",
                    help="directory holding the Newsreader and JetBrains Mono TTFs")
    ap.add_argument("--chrome", help="path to a Chrome/Chromium binary")
    ap.add_argument("--work", type=Path, default=ROOT / "tmp/brandbuild",
                    help="scratch directory for the generated HTML")
    args = ap.parse_args()

    if not args.fonts.is_dir():
        sys.exit(f"Font directory {args.fonts} does not exist; see this script's docstring.")
    args.work.mkdir(parents=True, exist_ok=True)

    chrome = find_chrome(args.chrome)
    faces = build_faces(args.fonts)
    for svg_rel, w, h, scale, out_rel in TARGETS:
        render(chrome, faces, args.work, svg_rel, w, h, scale, out_rel)


if __name__ == "__main__":
    main()
