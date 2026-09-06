# Why this pack ships binaries

Five 320x200 PNGs, committed to regular git rather than LFS.

**They are required.** All five are named in `script.yaml` as block media across the
training weeks, the prince's audience, the merchant, the dragon and the coronation.
No test decodes their pixels; `test_scene_plate_packs.py` checks the manifest against size,
mode and sha256, so a checkout without `git-lfs` still passes (`AGENTS.md` media
rule 3).

**They cannot be SVG.** Rule 1 prefers vector where the subject is vector-shaped.
These are dithered raster scenes carrying tens of thousands of colours.

**They are shipped assets, not source.** Conformed from 1280x800 renders;
generation-size originals are not committed (rule 2) and are reconstructible from
`provenance/jobs.json`.

**Five plates, twenty-three blocks.** Beats reuse plates deliberately: every training
week shares the study, both dragon beats share the burning valley, every ending but
one shares the cathedral. Plate count tracks authored *locations*, not blocks.

## Composition notes

The register is illuminated manuscript filtered through pixel art — the manuscript
references carry palette and ornament, the prompt carries the surface. Ornament is
worked into architecture rather than into margins.

Two plates carry a gold keyline border the model produced unbidden while refusing it
elsewhere under an explicit negative. Rather than re-roll for consistency, the border
is being extracted as a **separate overlay** so scene content can slide beneath it —
see #443. That frame is deliberately **not** committed here: nothing can draw it yet,
and an asset with no consumer does not belong in the tree.

The dragon plate has no dragon in it. The valley burns and the shadow falls, but the
creature belongs in the air as a sprite, not baked into scenery it would then have to
match forever.
