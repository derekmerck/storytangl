# Story VM game integration

Layer-2 game logic lives in `tangl.mechanics.games`. This package wires games to
story nodes so the VM can drive phases and exit edges.

- `has_game.py` – facet mixin following the HasSlottedContainer pattern
- `__init__.py` – re-export for `tangl.story.mechanics.games`
