"""Tests for nim-style contest mechanics."""

from __future__ import annotations

from tangl.core import Graph
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.nim_game import NimGame, NimGameHandler
from tangl.mechanics.games.handlers import inject_game_context, provision_game_moves
from tangl.story import Action, Block
from tangl.vm import Frame, Ledger, TraversableEdge as ChoiceEdge


class NimBlock(HasGame, Block):
    """Test block embedding a nim game."""

    _game_class = NimGame
    _game_handler_class = NimGameHandler


class TestNimCore:
    """Core nim behavior tests."""

    def test_available_moves_shrink_with_heap(self) -> None:
        game = NimGame(opening_heap_size=2, max_take=3)
        handler = NimGameHandler()
        handler.setup(game)

        assert handler.get_available_moves(game) == [1, 2]

    def test_last_token_can_win(self) -> None:
        game = NimGame(opening_heap_size=1, last_token_wins=True)
        handler = NimGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, 1)

        assert result.name == "WIN"
        assert game.result.name == "WIN"

    def test_last_token_can_lose(self) -> None:
        game = NimGame(opening_heap_size=1, last_token_wins=False)
        handler = NimGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, 1)

        assert result.name == "LOSE"
        assert game.result.name == "LOSE"

    def test_namespace_exports_heap_pressure(self) -> None:
        game = NimGame(opening_heap_size=5)
        handler = NimGameHandler()
        handler.setup(game)

        ns = game.to_namespace()

        assert ns["nim_heap_size"] == 5
        assert ns["nim_max_take"] == 3


class TestNimIntegration:
    """VM and HasGame integration tests for nim."""

    def test_move_labels_reflect_take_counts(self) -> None:
        graph = Graph(label="nim_labels")
        block = graph.add_node(kind=NimBlock, label="heap")
        block.game.opening_heap_size = 3
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        actions = provision_game_moves(block, ctx=ctx)

        assert [action.label for action in actions] == [
            "Take 1 token",
            "Take 2 tokens",
            "Take 3 tokens",
        ]

    def test_nim_routes_to_victory(self) -> None:
        graph = Graph(label="nim_flow")
        intro = graph.add_node(kind=Block, label="intro")
        victory = graph.add_node(kind=Block, label="victory")
        defeat = graph.add_node(kind=Block, label="defeat")

        block = NimBlock.create_game_block(
            graph=graph,
            game_class=NimGame,
            handler_class=NimGameHandler,
            victory_dest=victory,
            defeat_dest=defeat,
            label="heap",
        )
        block.game.opening_heap_size = 1
        block.game_handler.setup(block.game)

        intro_to_heap = ChoiceEdge(
            graph=graph,
            predecessor_id=intro.uid,
            successor_id=block.uid,
            label="Approach the heap",
        )

        ledger = Ledger.from_graph(graph=graph, entry_id=intro.uid)
        ledger.resolve_choice(intro_to_heap.uid)

        take_one = next(
            action
            for action in ledger.cursor.edges_out()
            if isinstance(action, Action) and action.payload and action.payload["move"] == 1
        )
        ledger.resolve_choice(take_one.uid, choice_payload=take_one.payload)

        assert ledger.cursor_id == victory.uid
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "heap collapses" in content.lower()

    def test_context_exports_next_take_hint(self) -> None:
        graph = Graph(label="nim_context")
        block = graph.add_node(kind=NimBlock, label="heap")
        block.game.opening_heap_size = 4
        block.game.opponent_strategy = "nim_greedy"
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        namespace = inject_game_context(block, ctx=ctx)

        assert namespace["nim_heap_size"] == 4
        assert namespace["nim_opponent_next_take"] == 3
