#!/usr/bin/env python3
"""Capture pygame client frames for a world, once per art pack.

The pygame client renders headlessly and can save a single frame, so a
screenshot is reproducible rather than something someone took by hand::

    SDL_VIDEODRIVER=dummy PYTHONPATH=engine/src:apps/pygame/src \
        python -m tangl.pygame_client --world repartee_loop \
            --advance 1 --screenshot out.png

Two things about that are easy to get wrong, which is why this script exists.

**The client's ``--assets`` flag does not switch art packs.** It only applies to
*relative* media sources (``Stage._load``), and the engine hands the client
absolute paths resolved through the world bundle, so ``--assets`` is ignored for
world-owned media and every pack renders identically. A pack is selected by the
world, with one line in ``world.yaml``::

    media_dir: media_spaceport   # default: media

This script writes that line, captures, and restores the file. It refuses to run
on a modified ``world.yaml`` so an interrupted run cannot lose your edits.

**pygame is not installed by default.** ``pygame-ce`` is in the dev group
(``poetry install --with dev``); it is a renderer test dependency, not a runtime
one.

Frames land at the client's own window size. Advance the same number of turns
for every pack to capture one beat across skins: the prose and choices are
identical because the graph is, which is the whole point of a reskin.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIR_LINE = re.compile(r"^media_dir:.*$\n?", re.MULTILINE)


def world_yaml(world: str) -> Path:
    path = ROOT / "worlds" / world / "world.yaml"
    if not path.is_file():
        sys.exit(f"No world.yaml for {world} at {path}")
    return path


def is_clean(path: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", str(path)],
        cwd=ROOT, capture_output=True, text=True,
    )
    return not result.stdout.strip()


def capture(world: str, advance: int, out: Path) -> None:
    env = {
        **os.environ,
        "SDL_VIDEODRIVER": "dummy",
        "PYTHONPATH": f"{ROOT / 'engine/src'}:{ROOT / 'apps/pygame/src'}",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "tangl.pygame_client", "--world", world,
         "--advance", str(advance), "--screenshot", str(out)],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-5:]
        if any("No module named 'pygame'" in line for line in tail):
            sys.exit("pygame is missing; run: poetry install --with dev")
        sys.exit("pygame client failed:\n  " + "\n  ".join(tail))
    if not out.is_file():
        sys.exit(f"client exited cleanly but wrote no frame at {out}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--world", default="repartee_loop")
    ap.add_argument("--advance", type=int, default=1,
                    help="turns to take before capturing; same value for every pack")
    ap.add_argument("--pack", action="append", metavar="NAME=MEDIA_DIR", default=None,
                    help="output name and the media_dir to render it with; repeatable")
    ap.add_argument("--out-dir", type=Path, default=ROOT / ".github/assets")
    ap.add_argument("--prefix", default="repartee-")
    args = ap.parse_args()

    packs = args.pack or ["quay=media", "spaceport=media_spaceport"]
    path = world_yaml(args.world)

    if not is_clean(path):
        sys.exit(f"{path.relative_to(ROOT)} has uncommitted changes; "
                 "commit or stash them so this script can restore it safely.")

    original = path.read_text()
    try:
        for entry in packs:
            name, _, media_dir = entry.partition("=")
            if not media_dir:
                sys.exit(f"--pack expects NAME=MEDIA_DIR, got {entry!r}")
            body = MEDIA_DIR_LINE.sub("", original).rstrip("\n")
            path.write_text(f"{body}\nmedia_dir: {media_dir}\n")
            out = args.out_dir / f"{args.prefix}{name}.png"
            capture(args.world, args.advance, out)
            print(f"{out.relative_to(ROOT)}  {media_dir}  advance={args.advance}  "
                  f"{out.stat().st_size // 1024} KB")
    finally:
        path.write_text(original)


if __name__ == "__main__":
    main()
