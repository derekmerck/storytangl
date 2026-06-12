# Logic Demo

Native YAML showcase for StoryTangl's state-machine style authoring.

## What It Demonstrates

- `LogicBlock` as a typed domain block
- parity checker, half adder, and full adder machines authored directly in YAML
- traversal correctness encoded in graph topology rather than journal-time logic
- narrative skins: swappable prose voices over the same stable machine
- graph projection, DOT export, runtime overlays, and chain-collapse views

## Why This World Exists

This bundle is the "near-native" reference for finite-state-machine-style
StoryTangl authoring. It shows the engine behaving like an explicit graph
machine while still supporting prose and media projection.

## Narrative Skins

The machine and its presentation are deliberately separate layers:

- **Shared (never varies):** the script topology, gate types, traversal
  behavior, and SVG badges. `script.yaml` is identical under every skin.
- **Varied (per skin):** the prose voice. Each skin in
  `logic_demo/domain.py::_SKIN_PROSE` is a *sparse* overlay of prose chunks
  keyed by block label; labels a skin does not cover fall back to the shared
  schematic voice.

Skin selection rides the ordinary namespace scope ladder: `logic_skin` is a
named chunk, so it can be set in story-graph `locals:`, overridden per-block
in block `locals:`, or computed by a `gather_ns` handler — no skin-specific
machinery. The bundled alternate skin is `loomworks`, which re-voices the
parity machine as a weaving hall while the adders keep the schematic voice.

See `docs/src/design/story/BEAT_COMPOSITION.md` for the chunk-override
ladder this rides on.

## Suggested Inspection Pipeline

The intended graph-analysis flow is:

`project_story_graph(...) -> annotate_runtime(...) -> focus_runtime_window(...) -> cluster_by_scene() -> collapse_linear_chains(...) -> mark_runtime_styles() -> to_dot(...)`

## Related Worlds

- `twine_logic_demo/` shows the same basic parity-checker idea authored in
  Twee/Twine and compiled through the Twine codec.
