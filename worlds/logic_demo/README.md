# Logic Demo

Native YAML showcase for StoryTangl's state-machine style authoring.

## What It Demonstrates

- `LogicBlock` as a typed domain block
- parity checker, half adder, and full adder machines authored directly in YAML
- traversal correctness encoded in graph topology rather than journal-time logic
- graph projection, DOT export, runtime overlays, and chain-collapse views

## Why This World Exists

This bundle is the "near-native" reference for finite-state-machine-style
StoryTangl authoring. It shows the engine behaving like an explicit graph
machine while still supporting prose and media projection.

## Suggested Inspection Pipeline

The intended graph-analysis flow is:

`project_story_graph(...) -> annotate_runtime(...) -> focus_runtime_window(...) -> cluster_by_scene() -> collapse_linear_chains(...) -> mark_runtime_styles() -> to_dot(...)`

## Related Worlds

- `twine_logic_demo/` shows the same basic parity-checker idea authored in
  Twee/Twine and compiled through the Twine codec.
