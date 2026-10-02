# Loomworks

An architectural proof for StoryTangl's state-machine style authoring: graph
topology and traversal perform the computation, while prose is merely one
projection of that machine.

The original question is intentionally excessive for a story engine: can
StoryTangl assemble useful computation out of blocks, groups, and re-entrant
structure without handing arbitrary authored code to `exec` or `eval`? The
parity checker, half adder, and full adder are the answer.

## What it demonstrates

- `LogicBlock` as a typed domain block;
- parity checker, half adder, and full adder machines authored directly in YAML;
- traversal correctness encoded in graph topology rather than journal-time logic;
- narrative skins: swappable prose voices over the same stable machine;
- graph projection, DOT export, runtime overlays, and chain-collapse views.

## Narrative skins

The machine and its presentation are deliberately separate layers:

- **Shared (never varies):** script topology, gate types, traversal behavior, and
  SVG badges. `script.yaml` is identical under every skin.
- **Varied (per skin):** prose voice. Each skin in
  `logic_demo/domain.py::_SKIN_PROSE` is a sparse overlay keyed by block
  label; labels a skin does not cover fall back to the shared schematic voice.

The bundled `loomworks` skin re-voices the parity machine as a weaving hall
while the adders retain the schematic voice. Skin selection rides the ordinary
namespace scope ladder through the `logic_skin` chunk rather than introducing
skin-specific runtime machinery.

See `docs/src/design/story/BEAT_COMPOSITION.md` for the chunk-override ladder
this uses.

## Suggested inspection pipeline

`project_story_graph(...) -> annotate_runtime(...) -> focus_runtime_window(...) -> cluster_by_scene() -> collapse_linear_chains(...) -> mark_runtime_styles() -> to_dot(...)`

## Related worlds

- `twine_reference/` is the simpler first example of foreign Twee/Twine source
  compiling into StoryTangl.
- `twine_logic_demo/` repeats the parity idea through that codec and remains a
  useful secondary parity fixture, not a separate architectural concept.
