# Coronate the Regent

A compact four-week preparation loop. Each week offers limited training, then a
scheduled event tests accumulated state. Early choices — impress the prince,
provoke the dragon, buy the sword — pay off at the coronation.

Named for the mechanic of stat-training succession games, not for any particular
one: constrained repeated choices, predictable deadline pressure, and delayed
consequences from earlier decisions.

Consequences travel as state rather than as wiring. Warning the dragon grants an
`irritated_dragon` condition; a later scene tests for it and compels a
confrontation the story otherwise skips. The merchant's sword, offered one beat
earlier, is the hedge against exactly that. Neither choice references the other.

## Art

<p align="center">
  <img src="../../.github/assets/coronate-merchant.png" alt="The border market in week three: the envoy has returned, the dragon is irritated, and the merchant's sword is the hedge against a confrontation the story has not yet forced" width="620">
</p>

The border market in week three: the envoy has returned, the dragon is irritated, and the merchant's sword is the hedge against a confrontation the story has not yet forced.

`media/` ships five illuminated-manuscript plates, conformed to the client's
320x200 logical surface. Five plates cover twenty-three blocks: beats reuse
locations, so every training week shares the study, both dragon beats share the
burning valley, and every ending but one shares the cathedral. Plate count tracks
authored *locations*, not blocks.

The register is manuscript filtered through pixel art — the references carry
palette and ornament, the prompt carries the surface, and ornament is worked into
architecture rather than into margins.

The world plays identically without any of it. Every plate is `media_role:
narrative_im`, which a client may ignore, and the CLI never asks for one.

`media/manifest.json` records what ships; `media/provenance/jobs.json` records the
workflow, models, parameters, prompts, seeds and reference-image hashes, with the
worker endpoint redacted. `media/AGENTS.md` adjudicates why these are committed
binaries.

### Two things the art deliberately does not do

The dragon plate has no dragon. The valley burns and the shadow falls, but the
creature belongs in the air as a sprite rather than baked into scenery it would
then have to match forever.

Two plates carry a gold keyline border the model produced unbidden. That border is
being extracted as a separate overlay so scene content can slide beneath it
(#443), and is deliberately not committed here — nothing can draw it yet, and an
asset with no consumer does not ship.
