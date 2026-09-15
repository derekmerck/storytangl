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

Seventeen images, about 1.1 MB, all at target resolution: two interchangeable
packs of seven, plus three sprite sheets in the spaceport pack. Each sheet's
frames and clips live in a small JSON sidecar beside it.

They are stored as **ordinary git blobs**, not LFS, via the `.gitattributes`
beside this file. Root rule 3 forbids CI depending on LFS having materialized,
and `test_repartee_art_packs.py` reads the bytes of every one of them.

Source renders stay out. The 1280x800 originals behind the plates are 3.5 MB for
two files — more than every shipped asset here combined — and are referenced by
sha256 from `media_spaceport/provenance/` instead of committed. See
`worlds/*/incoming/` and `provenance/source-assets/` in the root `.gitignore`.

## Screenshots of a pack

Do not take them by hand. `scripts/capture_world_frames.py` renders one frame
per pack headlessly and restores `world.yaml` afterwards; see "Capturing a pack"
in [`README.md`](README.md) for the two traps it exists to absorb. Frames that
ship in the repository are adjudicated in
[`.github/assets/AGENTS.md`](../../.github/assets/AGENTS.md), not here — they
are repository chrome rather than world media, and nothing loads them at
runtime.

## Adding to this world

- Conform first: backgrounds and plates to 320x200, sprites trimmed to alpha
  bounds at a common height, nearest-neighbour. Then write the manifest entry.
- Both packs or neither, for everything a client needs to draw the world.
  `test_packs_are_interchangeable_by_name` asserts an exact match on those
  names, and it is right to: a pack missing a required asset is a reskin that
  half works.
- Sprite sheets are the one exemption, and a deliberate one. A sheet is an
  optional alternative to a still every client can already draw, so a pack
  without sheets is a complete reskin that simply does not animate. The test
  exempts only files that parse as sheets of a shipped still.
- A new *kind* of asset — a second plate, an animation — is a design question
  first. Say what surface it exercises here before adding files.

## Sprite sheets

The surface they exercise: **a clip chosen per use, from three different
places.** Each portrait's still is unchanged and remains the floor; a client that
understands sheets may play a named clip from the sheet beside it instead.

- An **authored loop**: locations stage their character with
  `media_clip: idle` and `media_timing: loop`.
- A **posture from game state**: contest blocks name no clip, and
  `tangl.mechanics.games.call_response_presentation` poses the opponent each
  turn — `call` while it holds the initiative, `response` while it waits on the
  player's line. The clip names are the kernel's own phrase roles.
- An **authored outcome**: `dockhand_aftermath` holds `response`, because he won
  by parrying; the answered master drops back to `idle`.

Format and naming are Aseprite's JSON export, filename
`<still>-<columns>x<rows>` with the export as a sidecar; see
`tangl.presentation.sprite_sheet` and issue #418.

**Spaceport only, for now.** The quayside pack has no generation-scale sources
for its characters and its cutouts went through an unrecorded cleanup step, so
its sheets need its stills re-conformed first. Its portraits stage the same
clips and draw their stills.

Every frame is edited at generation resolution from the still's own recovered
source and composited back onto it inside a mask, then all frames are downscaled
once on the still's own sampling grid — so **frame 0 of each sheet is the shipped
still, pixel for pixel**, which `test_frame_zero_of_a_shipped_sheet_is_its_still`
checks on the committed bytes. The full reconstruction record, with every prompt,
seed, mask derivation and hash, is `media_spaceport/provenance/sprite-sheets.json`.
Masks and 1024x1024 renders are intermediates and are recorded by hash, not
committed.
