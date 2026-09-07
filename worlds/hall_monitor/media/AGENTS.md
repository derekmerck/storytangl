# Why this pack ships binaries

Two 320x200 PNGs, committed to regular git rather than LFS.

**They are required.** Both are named in `script.yaml` as block media, so the world
renders differently without them. `test_scene_plate_packs.py` reads their bytes: it
decodes each plate with `Image.load()` and hashes the file, because `open` reads a
header and defers the pixels, so a truncated plate reports its declared size and
mode quite happily. That decode is the reason they are not in LFS (`AGENTS.md`
media rule 3) — a test that reads bytes cannot depend on LFS having materialized,
so the bytes have to be in every checkout. For the same reason they must survive
`git archive`, which is pinned by `test_shipped_assets_survive_archive.py`.

**They cannot be SVG.** Rule 1 prefers vector for anything vector-shaped. These are
dithered raster scenes with tens of thousands of colours; there is no vector form.

**They are shipped assets, not source.** Each is conformed from a 1280x800 render to
the client's logical surface. The generation-size originals are not committed — rule
2 — and are reconstructible from `provenance/jobs.json`, which records the workflow,
models, parameters, prompts, seeds, and the sha256 of every reference image.

**Two, and it stays two.** `attendance_note` reads a note the attendance office
*filed*; no block travels there, and `attendance_office` exists in
`credential_types.yaml` as a credential issuer rather than a location. A third plate
would depict a room the world never visits. Rule 5 says pause at dozens; this pack is
nowhere near, and the discipline is still worth keeping.

## The B

The wall panel bearing a large `B` is an artefact of the reference photograph
(Boston City Hall) that survived several attempts to prompt it away. Rather than
fight it, it is read as the school's own insignia. The world does not name the
school; if it ever does, that mark is the reason.
