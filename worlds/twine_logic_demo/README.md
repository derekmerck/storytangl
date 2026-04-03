# Twine Logic Demo

Twee/Twine-authored parity checker used to demonstrate StoryTangl's codec path.

## What It Demonstrates

- alternate story authoring style through the built-in `twee3_1_0` codec
- the same "graph as machine" idea expressed as Twine passages and links
- StoryTangl compilation into the same runtime graph/traversal model used by
  native YAML worlds

## Relationship To `logic_demo`

`logic_demo/` is the native YAML, typed-domain showcase.

`twine_logic_demo/` is intentionally simpler. It proves that the engine can
compile a state-machine-like story from a different scripting style without
changing the runtime model.
