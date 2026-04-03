"""Tests for the scalar corridor contest and TwentyTwo skin."""

from __future__ import annotations

from tangl.core import Graph
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.corridor_game import (
    CorridorGame,
    CorridorGameHandler,
    CorridorMove,
    TwentyTwoGame,
    TwentyTwoGameHandler,
)
from tangl.mechanics.games.handlers import inject_game_context, provision_game_moves
from tangl.story import Action, Block
from tangl.vm import Frame, Ledger, TraversableEdge as ChoiceEdge


class CorridorBlock(HasGame, Block):
    """Test block embedding a corridor game."""

    _game_class = TwentyTwoGame
    _game_handler_class = TwentyTwoGameHandler


class TestCorridorCore:
    """Core corridor behavior tests."""

    def test_hold_can_trap_opponent_between_score_and_target(self) -> None:
        game = CorridorGame(
            shared_target=10,
            starting_player_score=3,
            starting_opponent_score=7,
        )
        handler = CorridorGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, CorridorMove.HOLD)

        assert result.name == "WIN"
        assert game.result.name == "WIN"

    def test_advancing_to_threshold_loses(self) -> None:
        game = CorridorGame(
            shared_target=10,
            source_sequence=[3],
            starting_player_score=7,
        )
        handler = CorridorGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, CorridorMove.ADVANCE)

        assert result.name == "LOSE"
        assert game.result.name == "LOSE"

    def test_shared_source_advances_in_order(self) -> None:
        game = CorridorGame(
            shared_target=20,
            source_sequence=[4, 2, 3],
            initial_player_has_initiative=True,
        )
        handler = CorridorGameHandler()
        handler.setup(game)

        handler.receive_move(game, CorridorMove.ADVANCE)

        assert game.player_score_value == 4
        assert game.opponent_score_value == 2
        assert game.next_source_value() == 3


class TestCorridorIntegration:
    """Integration tests for the corridor family."""

    def test_move_labels_use_advance_and_hold(self) -> None:
        graph = Graph(label="corridor_labels")
        block = graph.add_node(kind=CorridorBlock, label="corridor")
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        labels = [action.label for action in provision_game_moves(block, ctx=ctx)]

        assert labels == ["Advance", "Hold"]

    def test_twentytwo_can_route_to_victory(self) -> None:
        graph = Graph(label="corridor_flow")
        intro = graph.add_node(kind=Block, label="intro")
        victory = graph.add_node(kind=Block, label="victory")
        defeat = graph.add_node(kind=Block, label="defeat")

        block = CorridorBlock.create_game_block(
            graph=graph,
            game_class=TwentyTwoGame,
            handler_class=TwentyTwoGameHandler,
            victory_dest=victory,
            defeat_dest=defeat,
            label="corridor",
        )
        block.game.shared_target = 10
        block.game.starting_player_score = 3
        block.game.starting_opponent_score = 7
        block.game_handler.setup(block.game)

        intro_to_corridor = ChoiceEdge(
            graph=graph,
            predecessor_id=intro.uid,
            successor_id=block.uid,
            label="Enter the corridor",
        )

        ledger = Ledger.from_graph(graph=graph, entry_id=intro.uid)
        ledger.resolve_choice(intro_to_corridor.uid)

        hold = next(
            action
            for action in ledger.cursor.edges_out()
            if isinstance(action, Action) and action.label == "Hold"
        )
        ledger.resolve_choice(hold.uid, choice_payload=hold.payload)

        assert ledger.cursor_id == victory.uid
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "close the corridor" in content.lower()

    def test_context_exports_target_and_scores(self) -> None:
        graph = Graph(label="corridor_context")
        block = graph.add_node(kind=CorridorBlock, label="corridor")
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        namespace = inject_game_context(block, ctx=ctx)

        assert namespace["corridor_target"] == 22
        assert namespace["corridor_player_score"] == 0
