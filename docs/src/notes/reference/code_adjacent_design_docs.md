# Code-Adjacent Design Docs

Some design material still lives beside the source tree rather than under
`docs/src/design/`. These files are still useful during implementation and
review, but they should be migrated or linked more directly into the published
design section over time.

## Status

- Last reviewed: November 14, 2026
- Migration status: active

Several packages now treat the note beside the code as the contract for that
package, with a short entry page under `docs/src/design/` (media and service
work this way). The inventory below is everything that currently lives beside
the source.

## Current inventory

Layers and shared packages:

- `engine/src/tangl/core/CORE_DESIGN.md`
- `engine/src/tangl/vm/VM_DESIGN.md`
- `engine/src/tangl/vm/provision/SCOPE_MATCHING_DESIGN.md`
- `engine/src/tangl/vm/replay/design_notes.md`
- `engine/src/tangl/story/STORY_DESIGN.md`
- `engine/src/tangl/story/OBSERVATION_DESIGN.md`
- `engine/src/tangl/story/concepts/asset/ASSET_DESIGN.md`
- `engine/src/tangl/service/SERVICE_DESIGN.md`
- `engine/src/tangl/presentation/PRESENTATION_DESIGN.md`
- `engine/src/tangl/prose/PROSE_DESIGN.md`
- `engine/src/tangl/media/MEDIA_DESIGN.md`
- `engine/src/tangl/devref/CURATION_DESIGN.md`

Mechanics:

- `engine/src/tangl/mechanics/TRANSACTION_OFFER_DESIGN.md`
- `engine/src/tangl/mechanics/assembly/COMPONENT_DESIGN.md`
- `engine/src/tangl/mechanics/sandbox/SANDBOX_DESIGN.md`
- `engine/src/tangl/mechanics/presence/PRESENCE_ASSEMBLY_DESIGN.md`
- `engine/src/tangl/mechanics/demographics/DEMOGRAPHICS_DESIGN.md`
- `engine/src/tangl/mechanics/demographics/DEMOGRAPHICS_RETROFIT_PLAN.md`
- `engine/src/tangl/mechanics/games/GAME_MECHANICS_DESIGN.md`
- `engine/src/tangl/mechanics/games/COMPOSITE_GAME_LOOPS_DESIGN.md`
- `engine/src/tangl/mechanics/games/CORRIDOR_CONTEST_DESIGN.md`
- `engine/src/tangl/mechanics/games/CREDENTIALS_LOOP_DESIGN.md`
- `engine/src/tangl/mechanics/games/REPERTOIRE_LOOP_DESIGN.md`
- `engine/src/tangl/mechanics/credentials/CREDENTIAL_MECHANIC.md`
- `engine/src/tangl/mechanics/credentials/CREDENTIAL_ASSEMBLY_RETROFIT.md`
- `engine/src/tangl/mechanics/credentials/PHASE_6A_FACET_BRIDGE_CONTRACT.md`
- `engine/src/tangl/mechanics/credentials/PHASE_6B_REQUEST_DOCUMENT_HANDOFF.md`
- `engine/src/tangl/mechanics/credentials/PHASE_6C_AUTHORED_CATALOG_HANDOFF.md`
- `engine/src/tangl/mechanics/credentials/PHASE_6D_HALL_MONITOR_SCENARIO_HANDOFF.md`

(asset-design)=

### Asset design

The canonical [asset design note](https://github.com/derekmerck/storytangl/blob/main/engine/src/tangl/story/concepts/asset/ASSET_DESIGN.md)
describes wallet ownership, holder migration, and transaction boundaries.

(assembly-design)=

### Assembly design

The canonical [component design note](https://github.com/derekmerck/storytangl/blob/main/engine/src/tangl/mechanics/assembly/COMPONENT_DESIGN.md)
describes owner-bound managers and their planned use of shared membership.

## Intended follow-up

- Move stable architectural content into `docs/src/design/`.
- Leave temporary migration or implementation notes in `docs/src/notes/`.
- Update API pages so subsystem reference pages point at the canonical design
  page instead of this inventory once the migration is complete.

## Migrated

- Service architecture is now summarized in
  `docs/src/design/service/SERVICE_DESIGN.md`; the source-adjacent service note
  remains its implementation companion rather than the only published entry.
