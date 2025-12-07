from __future__ import annotations

"""Facet mixin for blocks hosting game instances."""

from typing import Any, ClassVar, Optional, TYPE_CHECKING
from uuid import UUID

from tangl.mechanics.games import Game, GameHandler

if TYPE_CHECKING:
    from tangl.core import Graph, Node


class HasGame:
    """
    Mixin for story nodes that embed a game instance and handler.

    Why
    ----
    Wraps Layer 2 game state (:class:`~tangl.mechanics.games.Game`) inside story
    nodes so the VM can drive rounds and post-requisite exits. Mirrors
    :class:`~tangl.mechanics.assembly.base.HasSlottedContainer` with lazy
    initialization, serialization hooks, and a convenience factory.

    Key Features
    ------------
    - **Lazy accessors**: instantiate the game and handler on first property
      access.
    - **Serializable game state**: persist ``_game`` with the block; handler is
      recreated when needed.
    - **Factory wiring**: :meth:`create_game_block` adds POSTREQS edges for
      victory/defeat/draw exits.
    """

    _game_class: ClassVar[type[Game]] = Game
    _game_handler_class: ClassVar[type[GameHandler]] = GameHandler

    _game: Optional[Game] = None
    _game_handler: Optional[GameHandler] = None

    victory_edge_id: UUID | None = None
    defeat_edge_id: UUID | None = None
    draw_edge_id: UUID | None = None

    @property
    def game(self) -> Game:
        """Return the game instance, creating it on first access."""

        if self._game is None:
            self._game = self._game_class()
        return self._game

    @property
    def game_handler(self) -> GameHandler:
        """Return the game handler, creating it on first access."""

        if self._game_handler is None:
            self._game_handler = self._game_handler_class()
        return self._game_handler

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        """Serialize the block, including game state if initialized."""

        data = super().model_dump(**kwargs)  # type: ignore[misc]
        if self._game is not None:
            data["_game"] = self._game.model_dump()
        return data

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any):  # type: ignore[override]
        """Deserialize the block and restore game state when present."""

        instance = super().model_validate(obj, **kwargs)  # type: ignore[misc]
        if "_game" in obj:
            game_data = obj["_game"]
            instance._game = instance._game_class.model_validate(game_data)
        return instance

    @classmethod
    def create_game_block(
        cls,
        graph: Graph,
        *,
        game_class: type[Game] | None = None,
        handler_class: type[GameHandler] | None = None,
        victory_dest: Node | None = None,
        defeat_dest: Node | None = None,
        draw_dest: Node | None = None,
        label: str | None = None,
        **kwargs: Any,
    ) -> HasGame:
        """
        Create a game-enabled node and wire optional POSTREQS exits.

        Parameters
        ----------
        graph:
            Target graph for the new node.
        game_class:
            Optional override for the game type used by this instance.
        handler_class:
            Optional override for the stateless handler type.
        victory_dest:
            Destination node to follow when ``game_won`` predicate passes.
        defeat_dest:
            Destination node to follow when ``game_lost`` predicate passes.
        draw_dest:
            Destination node to follow when ``game_draw`` predicate passes.
        label:
            Node label for readability.

        Returns
        -------
        HasGame
            The created node instance.
        """

        from tangl.vm import ChoiceEdge
        from tangl.vm.resolution_phase import ResolutionPhase as P

        node = graph.add_node(obj_cls=cls, label=label, **kwargs)

        if game_class is not None:
            object.__setattr__(node, "_game_class", game_class)
        if handler_class is not None:
            object.__setattr__(node, "_game_handler_class", handler_class)

        if victory_dest is not None:
            victory_edge = ChoiceEdge(
                graph=graph,
                source_id=node.uid,
                destination_id=victory_dest.uid,
                trigger_phase=P.POSTREQS,
                predicate="game_won",
                label="Victory!",
            )
            node.victory_edge_id = victory_edge.uid

        if defeat_dest is not None:
            defeat_edge = ChoiceEdge(
                graph=graph,
                source_id=node.uid,
                destination_id=defeat_dest.uid,
                trigger_phase=P.POSTREQS,
                predicate="game_lost",
                label="Defeat",
            )
            node.defeat_edge_id = defeat_edge.uid

        if draw_dest is not None:
            draw_edge = ChoiceEdge(
                graph=graph,
                source_id=node.uid,
                destination_id=draw_dest.uid,
                trigger_phase=P.POSTREQS,
                predicate="game_draw",
                label="Draw",
            )
            node.draw_edge_id = draw_edge.uid

        return node
