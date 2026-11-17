# Code-Adjacent Design Docs

Some design material lives beside the source tree rather than under
`docs/src/design/`. Each note stays there, next to the code it describes, and
is included unchanged as a package overview page in the API reference, so it is
built, searched and link-checked with the rest of the documentation. The links
below go to those pages. Edit the note in the package, not the page.

## Status

- Last reviewed: November 14, 2026
- Placement: included in the API reference as package design notes

Several packages now treat the note beside the code as the contract for that
package, with a short entry page under `docs/src/design/` (media and service
work this way). The inventory below is everything that currently lives beside
the source.

## Current inventory

Layers and shared packages:

- [`engine/src/tangl/core/CORE_DESIGN.md`](../../api/core/CORE_DESIGN.md)
- [`engine/src/tangl/vm/VM_DESIGN.md`](../../api/vm/VM_DESIGN.md)
- [`engine/src/tangl/vm/provision/SCOPE_MATCHING_DESIGN.md`](../../api/vm/provision/SCOPE_MATCHING_DESIGN.md)
- [`engine/src/tangl/vm/replay/design_notes.md`](../../api/vm/replay/design_notes.md)
- [`engine/src/tangl/story/STORY_DESIGN.md`](../../api/story/STORY_DESIGN.md)
- [`engine/src/tangl/story/OBSERVATION_DESIGN.md`](../../api/story/OBSERVATION_DESIGN.md)
- [`engine/src/tangl/story/concepts/asset/ASSET_DESIGN.md`](../../api/story/concepts/asset/ASSET_DESIGN.md)
- [`engine/src/tangl/service/SERVICE_DESIGN.md`](../../api/service/SERVICE_DESIGN.md)
- [`engine/src/tangl/presentation/PRESENTATION_DESIGN.md`](../../api/presentation/PRESENTATION_DESIGN.md)
- [`engine/src/tangl/prose/PROSE_DESIGN.md`](../../api/prose/PROSE_DESIGN.md)
- [`engine/src/tangl/media/MEDIA_DESIGN.md`](../../api/media/MEDIA_DESIGN.md)
- [`engine/src/tangl/devref/CURATION_DESIGN.md`](../../api/devref/CURATION_DESIGN.md)

Mechanics:

- [`engine/src/tangl/mechanics/TRANSACTION_OFFER_DESIGN.md`](../../api/mechanics/TRANSACTION_OFFER_DESIGN.md)
- [`engine/src/tangl/mechanics/assembly/COMPONENT_DESIGN.md`](../../api/mechanics/assembly/COMPONENT_DESIGN.md)
- [`engine/src/tangl/mechanics/sandbox/SANDBOX_DESIGN.md`](../../api/mechanics/sandbox/SANDBOX_DESIGN.md)
- [`engine/src/tangl/mechanics/presence/PRESENCE_ASSEMBLY_DESIGN.md`](../../api/mechanics/presence/PRESENCE_ASSEMBLY_DESIGN.md)
- [`engine/src/tangl/mechanics/demographics/DEMOGRAPHICS_DESIGN.md`](../../api/mechanics/demographics/DEMOGRAPHICS_DESIGN.md)
- [`engine/src/tangl/mechanics/demographics/DEMOGRAPHICS_RETROFIT_PLAN.md`](../../api/mechanics/demographics/DEMOGRAPHICS_RETROFIT_PLAN.md)
- [`engine/src/tangl/mechanics/games/GAME_MECHANICS_DESIGN.md`](../../api/mechanics/games/GAME_MECHANICS_DESIGN.md)
- [`engine/src/tangl/mechanics/games/COMPOSITE_GAME_LOOPS_DESIGN.md`](../../api/mechanics/games/COMPOSITE_GAME_LOOPS_DESIGN.md)
- [`engine/src/tangl/mechanics/games/CORRIDOR_CONTEST_DESIGN.md`](../../api/mechanics/games/CORRIDOR_CONTEST_DESIGN.md)
- [`engine/src/tangl/mechanics/games/CREDENTIALS_LOOP_DESIGN.md`](../../api/mechanics/games/CREDENTIALS_LOOP_DESIGN.md)
- [`engine/src/tangl/mechanics/games/REPERTOIRE_LOOP_DESIGN.md`](../../api/mechanics/games/REPERTOIRE_LOOP_DESIGN.md)
- [`engine/src/tangl/mechanics/credentials/CREDENTIAL_MECHANIC.md`](../../api/mechanics/credentials/CREDENTIAL_MECHANIC.md)
- [`engine/src/tangl/mechanics/credentials/CREDENTIAL_ASSEMBLY_RETROFIT.md`](../../api/mechanics/credentials/CREDENTIAL_ASSEMBLY_RETROFIT.md)
- [`engine/src/tangl/mechanics/credentials/PHASE_6A_FACET_BRIDGE_CONTRACT.md`](../../api/mechanics/credentials/PHASE_6A_FACET_BRIDGE_CONTRACT.md)
- [`engine/src/tangl/mechanics/credentials/PHASE_6B_REQUEST_DOCUMENT_HANDOFF.md`](../../api/mechanics/credentials/PHASE_6B_REQUEST_DOCUMENT_HANDOFF.md)
- [`engine/src/tangl/mechanics/credentials/PHASE_6C_AUTHORED_CATALOG_HANDOFF.md`](../../api/mechanics/credentials/PHASE_6C_AUTHORED_CATALOG_HANDOFF.md)
- [`engine/src/tangl/mechanics/credentials/PHASE_6D_HALL_MONITOR_SCENARIO_HANDOFF.md`](../../api/mechanics/credentials/PHASE_6D_HALL_MONITOR_SCENARIO_HANDOFF.md)

(asset-design)=

### Asset design

The canonical [asset design note](../../api/story/concepts/asset/ASSET_DESIGN.md)
describes wallet ownership, holder migration, and transaction boundaries.

(assembly-design)=

### Assembly design

The canonical [component design note](../../api/mechanics/assembly/COMPONENT_DESIGN.md)
describes owner-bound managers and their planned use of shared membership.

## How these notes are meant to be used

A package note is the long form of its package docstring: what the package is
for, its contracts and its status. It belongs beside the code, and its page in
the API reference is the bridge between the conceptual and planning pages under
`docs/src/design/` and the generated reference. Design pages should link to the
API page for a note, not to the file on GitHub.

- Keep conceptual and cross-package design in `docs/src/design/`.
- Keep temporary migration or implementation notes in `docs/src/notes/`.
- A new note beside the code needs a page under `docs/src/api/` that includes
  it; a test checks that every note has one.

## Migrated

- Service architecture is now summarized in
  `docs/src/design/service/SERVICE_DESIGN.md`; the source-adjacent service note
  remains its implementation companion rather than the only published entry.
