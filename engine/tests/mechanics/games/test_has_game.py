"""Unit tests for the HasGame facet."""

from __future__ import annotations

from uuid import UUID

from tangl.core import Graph
from tangl.mechanics.games import Game, GameHandler, GamePhase, RoundResult, HasGame
from tangl.story.episode import Block


class SampleGame(Game):
    """Minimal test game for facet behavior."""


class SampleGameHandler(GameHandler[SampleGame]):
    """Minimal handler that always returns draw."""

    def get_available_moves(self, game: SampleGame) -> list[str]:
        return []

    def resolve_round(
        self, game: SampleGame, player_move: str, opponent_move: str | None
    ) -> RoundResult:
        return RoundResult.DRAW


class GameBlock(HasGame, Block):
    """Block with an attached game facet for tests."""

    _game_class = SampleGame
    _game_handler_class = SampleGameHandler


GameBlock.model_rebuild(_types_namespace={"UUID": UUID})


class TestHasGameFacet:
    def test_game_lazy_initialization(self) -> None:
        graph = Graph(label="test")
        block = graph.add_node(obj_cls=GameBlock, label="game_block")

        assert block._game is None

        game = block.game
        assert isinstance(game, SampleGame)
        assert block.game is game

    def test_handler_lazy_initialization(self) -> None:
        graph = Graph(label="test")
        block = graph.add_node(obj_cls=GameBlock, label="game_block")

        assert block._game_handler is None

        handler = block.game_handler
        assert isinstance(handler, SampleGameHandler)
        assert block.game_handler is handler

    def test_game_state_serialization(self) -> None:
        graph = Graph(label="test")
        block = graph.add_node(obj_cls=GameBlock, label="game_block")

        _ = block.game
        block.game.phase = GamePhase.READY
        block.game.round = 5

        data = block.model_dump()
        assert data["_game"]["phase"] is GamePhase.READY
        assert data["_game"]["round"] == 5

        restored = GameBlock.model_validate(data)
        assert restored.game.phase is GamePhase.READY
        assert restored.game.round == 5

    def test_handler_not_serialized(self) -> None:
        graph = Graph(label="test")
        block = graph.add_node(obj_cls=GameBlock, label="game_block")

        _ = block.game_handler
        data = block.model_dump()
        assert "_game_handler" not in data

        restored = GameBlock.model_validate(data)
        assert restored._game_handler is None
        assert isinstance(restored.game_handler, SampleGameHandler)


class TestGameBlockFactory:
    def test_factory_creates_block(self) -> None:
        graph = Graph(label="test")

        block = GameBlock.create_game_block(graph=graph, label="test_game")

        assert block.label == "test_game"
        assert hasattr(block, "game")
        assert hasattr(block, "game_handler")

    def test_factory_creates_victory_edge(self) -> None:
        from tangl.vm.resolution_phase import ResolutionPhase as P

        graph = Graph(label="test")
        victory = graph.add_node(obj_cls=Block, label="victory")

        block = GameBlock.create_game_block(
            graph=graph, victory_dest=victory, label="game"
        )

        assert block.victory_edge_id is not None

        edge = graph.get(block.victory_edge_id)
        assert edge.predicate == "game_won"
        assert edge.available({"game_won": True}) is True
        assert edge.available({"game_won": False}) is False
        assert edge.source_id == block.uid
        assert edge.destination_id == victory.uid
        assert edge.trigger_phase is P.POSTREQS

    def test_factory_creates_defeat_edge(self) -> None:
        graph = Graph(label="test")
        defeat = graph.add_node(obj_cls=Block, label="defeat")

        block = GameBlock.create_game_block(
            graph=graph, defeat_dest=defeat, label="game"
        )

        assert block.defeat_edge_id is not None

        edge = graph.get(block.defeat_edge_id)
        assert edge.predicate == "game_lost"
        assert edge.available({"game_lost": True}) is True
        assert edge.available({"game_lost": False}) is False

    def test_factory_creates_draw_edge(self) -> None:
        graph = Graph(label="test")
        draw = graph.add_node(obj_cls=Block, label="draw")

        block = GameBlock.create_game_block(graph=graph, draw_dest=draw, label="game")

        assert block.draw_edge_id is not None

        edge = graph.get(block.draw_edge_id)
        assert edge.predicate == "game_draw"
        assert edge.available({"game_draw": True}) is True
        assert edge.available({"game_draw": False}) is False

    def test_factory_without_exits(self) -> None:
        graph = Graph(label="test")

        block = GameBlock.create_game_block(graph=graph, label="game")

        assert block.victory_edge_id is None
        assert block.defeat_edge_id is None
        assert block.draw_edge_id is None

    def test_factory_overrides_game_class(self) -> None:
        from tangl.mechanics.games.rps_game import RpsGame

        graph = Graph(label="test")

        block = GameBlock.create_game_block(
            graph=graph, game_class=RpsGame, label="game"
        )

        assert block._game_class is RpsGame
        assert isinstance(block.game, RpsGame)
