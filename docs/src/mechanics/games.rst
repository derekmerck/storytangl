Game mechanics integration
==========================

Layer 3 connects ``tangl.mechanics.games`` to the story VM so blocks can host
stateful games with automatic setup, move provisioning, journaling, and predicate
evaluation.

Quick start
-----------

.. code-block:: python

   from tangl.mechanics.games import RpsGame, RpsGameHandler
   from tangl.story.mechanics.games import HasGame
   from tangl.story.structure import Block

   class RpsBlock(HasGame, Block):
       """Rock–Paper–Scissors block with a game facet."""
       pass

   block = RpsBlock.create_game_block(
       graph=story_graph,
       game_class=RpsGame,
       handler_class=RpsGameHandler,
       victory_dest=victory_scene,
       defeat_dest=defeat_scene,
   )

VM pipeline
-----------

``HasGame`` nodes participate in the standard resolution phases:

- **PREREQS** – ``setup_game_on_first_visit`` prepares the game when the cursor
  enters for the first time.
- **PLANNING** – ``provision_game_moves`` emits self-loop ``Action`` instances for
  each available move reported by the handler.
- **UPDATE** – ``process_game_move`` routes the selected move into the handler and
  records round results in ``cursor.locals``.
- **JOURNAL** – ``generate_game_journal`` converts the round state into
  ``ContentFragment`` records for downstream renderers.
- **CONTEXT** – ``inject_game_context`` exposes predicate-friendly flags such as
  ``game_won`` and ``game_lost`` for POSTREQS exit edges.

Creating new games
------------------

1. Implement a :class:`tangl.mechanics.games.Game` subclass with scoring fields and
   history tracking.
2. Implement a :class:`tangl.mechanics.games.GameHandler` that returns available
   moves and resolves rounds by mutating the game instance.
3. Subclass :class:`tangl.story.mechanics.games.HasGame` on your story block and
   configure ``_game_class`` and ``_game_handler_class`` (or override via
   ``create_game_block``).
4. Wire exit destinations through the factory to route victory/defeat/draw states.
5. Add integration tests under ``engine/tests/story/mechanics/games`` to validate
   move flows and predicate-driven exits.

API reference
-------------

.. automodule:: tangl.story.mechanics.games
   :members:
   :undoc-members:
   :show-inheritance:
