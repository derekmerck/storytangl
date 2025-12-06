# Game Mechanics Integration

Layer-3 package that connects game mechanics to the story virtual machine (VM).
Use the ``HasGame`` facet to attach a game instance and handler to a story block,
provision self-looped moves, and automatically route exits when the game finishes.

## Overview

- **What HasGame enables:** attach game state to story nodes, process player moves
  through the VM pipeline, and evaluate predicates for victory/defeat/draw exits.
- **Layer boundaries:** Layer 2 (``tangl.mechanics.games``) holds pure game logic;
  this package provides the Layer 3 integration with cursor history, dispatch, and
  VM phase handlers.
- **Facet pattern:** mirrors ``HasSlottedContainer`` and other ``HasX`` mixins with
  lazy initialization, serialization hooks, and class-level handler configuration.

## Quick Start

```python
from tangl.mechanics.games import RpsGame, RpsGameHandler
from tangl.story.mechanics.games import HasGame
from tangl.story.structure import Block

class RpsBlock(HasGame, Block):
    """Rock–Paper–Scissors block with game facet."""
    pass

block = RpsBlock.create_game_block(
    graph=story_graph,
    game_class=RpsGame,
    handler_class=RpsGameHandler,
    victory_dest=victory_scene,
    defeat_dest=defeat_scene,
    label="RPS Challenge",
)
```

## How It Works

1. **PREREQS** – first-visit setup via ``setup_game_on_first_visit``.
2. **PLANNING** – available moves become self-loop ``Action`` objects.
3. **UPDATE** – selected move processed by the handler, mutating game state.
4. **JOURNAL** – human-readable fragments describing the round and score.
5. **CONTEXT** – predicate namespace exposes ``game_won``/``game_lost`` flags.
6. **POSTREQS** – exit edges created by the factory auto-trigger when predicates
   resolve true.

Exit edges use string predicates (``"game_won"``, ``"game_lost"``, ``"game_draw"``)
that map directly to the keys injected by the ``inject_game_context`` handler, so
the VM reads the shared namespace instead of reaching into the facet internals.

## Creating New Games

1. Subclass ``Game`` and implement scoring/round resolution.
2. Subclass ``GameHandler`` with ``get_available_moves`` and ``receive_move``
   (or ``resolve_round``) that updates the game instance.
3. Create a story block with ``HasGame`` and configure the classes at the subclass
   or instance level.
4. Optionally customize exit destinations via the factory.
5. Add tests under ``engine/tests/story/mechanics/games`` to cover move flows and
   VM integration.

## Pattern Recognition

``HasGame`` follows the ``HasX`` facet pattern used throughout StoryTangl:
- ``HasSlottedContainer`` for assembly slots
- ``HasAssetWallet`` for inventory and assets
- ``HasStats`` for progression and traits

These mixins are converging on a shared lifecycle: lazy init, serialization, and
stateless helpers configured on the class.
