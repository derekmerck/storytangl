# StoryTangl Proposal Fixtures

This directory contains non-gating JSON fixtures for proposed widget-contract
surfaces. They are examples for review, reference ports, and future migration
work; they are not part of the current conformance suite under `../fixtures/`.

Proposal fixtures must stay loadable as JSON and renderable through the generic
reference port, but they may use fragment types, `accepts.kind` values, or row
shapes that the engine does not yet model directly.

Current proposal set:

- `record_kvrow.json`: record-shaped scene-bound `kv` rows.
- `piece_realization.json`: `piece.realized=true/false` lifecycle pressure.
- `place_accepts.json`: `accepts.kind="place"` over source and target zones.
- `roll_fragment.json`: proposed `roll` fragment for auditable outcomes.
- `wireframe_v15_interpretation_samples.json`: UUID-shaped command feedback
  examples translated from the v1.5 wireframe's `gravel.interp_samples`.
- `carwars_garage_turn.json`: compact CarWars garage turn combining slot zones,
  catalog offers, `place`, `pieces`, and advisory drag/stat hints.
