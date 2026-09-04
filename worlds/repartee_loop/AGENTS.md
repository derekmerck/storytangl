# Binary assets here are adjudicated

The root `AGENTS.md` says to prefer SVG and not to commit binaries casually.
This world is the exception, deliberately, and this file is the record of that
decision rather than a request to make it again.

## Why these must be raster

`repartee_loop` is the reference world for the media path. What it demonstrates
*is* the images: authored `media:` entries, `media_role` for intent,
`staging_hints` for per-usage presentation, two interchangeable art packs, and a
map plate whose regions a client binds hitboxes to. An SVG stand-in would
demonstrate the plumbing while removing the thing under test — pixel art
conformed to a 320x200 logical surface, on a real pixel grid.

`engine/tests/loaders/test_repartee_art_packs.py` asserts the size, mode, and
sha256 of every shipped file against each pack's `manifest.json`, because
conforming an image after writing its manifest is exactly how the two drift
apart. That test reads bytes, which makes these **required assets** under root
rule 3: CI must not need LFS to have materialized in order to pass.

## The budget

Fourteen files, about 1 MB, all at target resolution: two interchangeable
packs of seven. That is the whole binary footprint of the repository.

They are stored as **ordinary git blobs**, not LFS, via the `.gitattributes`
beside this file. Root rule 3 forbids CI depending on LFS having materialized,
and `test_repartee_art_packs.py` reads the bytes of every one of them.

Source renders stay out. The 1280x800 originals behind the plates are 3.5 MB for
two files — more than every shipped asset here combined — and are referenced by
sha256 from `media_spaceport/provenance/` instead of committed. See
`worlds/*/incoming/` and `provenance/source-assets/` in the root `.gitignore`.

## Adding to this world

- Conform first: backgrounds and plates to 320x200, sprites trimmed to alpha
  bounds at a common height, nearest-neighbour. Then write the manifest entry.
- Both packs or neither. `test_packs_are_interchangeable_by_name` asserts an
  exact match on asset names, and it is right to: a pack missing an asset is a
  reskin that half works.
- A new *kind* of asset — a second plate, an animation — is a design question
  first. Say what surface it exercises here before adding files.
