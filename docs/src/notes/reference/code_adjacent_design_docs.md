# Code-Adjacent Design Docs

Some design material still lives beside the source tree rather than under
`docs/src/design/`. These files are still useful during implementation and
review, but they should be migrated or linked more directly into the published
design section over time.

## Status

- Last reviewed: March 17, 2026
- Migration status: active

## Current inventory

- `engine/src/tangl/core/CORE_DESIGN.md`
- `engine/src/tangl/service/SERVICE_DESIGN.md`
- `engine/src/tangl/story/STORY_DESIGN.md`
- `engine/src/tangl/vm/VM_DESIGN.md`
- `engine/src/tangl/vm/provision/SCOPE_MATCHING_DESIGN.md`

## Intended follow-up

- Move stable architectural content into `docs/src/design/`.
- Leave temporary migration or implementation notes in `docs/src/notes/`.
- Update API pages so subsystem reference pages point at the canonical design
  page instead of this inventory once the migration is complete.
