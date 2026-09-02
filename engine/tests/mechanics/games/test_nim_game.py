"""Tests for nim-style contest mechanics over fungible token heaps."""

from __future__ import annotations

import pytest

from tangl.core import Graph
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.nim_game import DEFAULT_HEAP, NimGame, NimGameHandler, NimMove
from tangl.mechanics.games.handlers import inject_game_context, provision_game_moves
from tangl.story import Action, Block
from tangl.vm import Frame, Ledger, TraversableEdge as ChoiceEdge


class NimBlock(HasGame, Block):
    """Test block embedding a nim game."""

    _game_class = NimGame
    _game_handler_class = NimGameHandler


def _ready(**kwargs) -> tuple[NimGame, NimGameHandler]:
    game = NimGame(**kwargs)
    handler = NimGameHandler()
    handler.setup(game)
    return game, handler


class TestNimCore:
    """Core nim behavior over a single heap."""

    def test_available_moves_shrink_with_heap(self) -> None:
        game, handler = _ready(opening_heaps={DEFAULT_HEAP: 2}, max_take=3)

        assert handler.get_available_moves(game) == [
            NimMove(pile=DEFAULT_HEAP, count=1),
            NimMove(pile=DEFAULT_HEAP, count=2),
        ]

    def test_taking_the_last_token_wins_by_default(self) -> None:
        game, handler = _ready(opening_heaps={DEFAULT_HEAP: 1}, last_token_wins=True)

        result = handler.receive_move(game, NimMove(pile=DEFAULT_HEAP, count=1))

        assert result.name == "WIN"
        assert game.total_tokens == 0

    def test_taking_the_last_token_can_lose(self) -> None:
        game, handler = _ready(opening_heaps={DEFAULT_HEAP: 1}, last_token_wins=False)

        result = handler.receive_move(game, NimMove(pile=DEFAULT_HEAP, count=1))

        assert result.name == "LOSE"

    def test_namespace_reports_heaps_and_totals(self) -> None:
        game, _ = _ready(opening_heaps={DEFAULT_HEAP: 5})

        namespace = game.to_namespace()

        assert namespace["nim_heaps"] == {DEFAULT_HEAP: 5}
        assert namespace["nim_total"] == 5
        assert namespace["nim_max_take"] == 3

    def test_quantity_payload_resolves_to_legal_take(self) -> None:
        game, handler = _ready(opening_heaps={DEFAULT_HEAP: 2}, max_take=3)
        selector = handler.get_provisioned_moves(game)[0]

        resolved = handler.resolve_move_payload(game, selector, {"quantity": 2})
        assert resolved == NimMove(pile=DEFAULT_HEAP, count=2)

        with pytest.raises(ValueError, match="Invalid take"):
            handler.resolve_move_payload(game, selector, {"quantity": 3})


class TestSingleHeapIsSolved:
    """One heap is the configuration with no strategy left in it."""

    def test_first_player_wins_unless_the_heap_is_a_multiple(self) -> None:
        # Under a take bound of k, losing positions are multiples of k + 1.
        winnable, _ = _ready(opening_heaps={DEFAULT_HEAP: 7}, max_take=3)
        lost, _ = _ready(opening_heaps={DEFAULT_HEAP: 8}, max_take=3)

        assert winnable.is_losing_position is False
        assert lost.is_losing_position is True

    def test_the_bound_sets_the_modulus(self) -> None:
        # take 1..4 makes multiples of 5 the losing positions, not multiples of 4
        by_four, _ = _ready(opening_heaps={DEFAULT_HEAP: 8}, max_take=4)
        by_five, _ = _ready(opening_heaps={DEFAULT_HEAP: 10}, max_take=4)

        assert by_four.is_losing_position is False
        assert by_five.is_losing_position is True

    def test_optimal_play_leaves_a_multiple_of_the_modulus(self) -> None:
        game, handler = _ready(
            opening_heaps={DEFAULT_HEAP: 7},
            max_take=3,
            opponent_strategy="nim_optimal",
        )
        handler._preselect_opponent_move(game)

        # 7 -> take 3 -> 4, a losing position for whoever moves next
        assert game.opponent_next_move == NimMove(pile=DEFAULT_HEAP, count=3)


class TestMultipleHeaps:
    """More than one heap, or more than one token type, is the same thing."""

    def test_heaps_are_token_types_in_one_wallet(self) -> None:
        game, handler = _ready(opening_heaps={"red": 5, "blue": 3})

        assert game.heaps.amounts == {"red": 5, "blue": 3}
        assert game.total_tokens == 8
        assert game.pile_labels() == ["blue", "red"]

    def test_moves_span_every_non_empty_heap(self) -> None:
        game, handler = _ready(opening_heaps={"red": 2, "blue": 1}, max_take=3)

        assert handler.get_available_moves(game) == [
            NimMove(pile="blue", count=1),
            NimMove(pile="red", count=1),
            NimMove(pile="red", count=2),
        ]

    def test_emptying_one_heap_leaves_the_other_playable(self) -> None:
        game, handler = _ready(
            opening_heaps={"red": 1, "blue": 3},
            opponent_strategy=None,
        )

        result = handler.receive_move(game, NimMove(pile="red", count=1))

        assert result.name == "CONTINUE"
        assert game.pile_labels() == ["blue"]

    def test_grundy_values_use_the_take_bound(self) -> None:
        game, _ = _ready(opening_heaps={"red": 5, "blue": 3}, max_take=3)

        assert game.grundy_values() == [3, 1]     # blue then red, 3 % 4 and 5 % 4
        assert game.is_losing_position is False   # 3 xor 1 is non-zero

    def test_balanced_heaps_are_lost_for_the_mover(self) -> None:
        game, _ = _ready(opening_heaps={"red": 3, "blue": 3}, max_take=3)

        assert game.is_losing_position is True

    def test_optimal_play_balances_the_xor(self) -> None:
        game, handler = _ready(
            opening_heaps={"red": 5, "blue": 3},
            max_take=3,
            opponent_strategy="nim_optimal",
        )
        handler._preselect_opponent_move(game)
        move = game.opponent_next_move

        remaining = dict(game.heaps.amounts)
        remaining[move.pile] -= move.count
        modulus = game.max_take + 1
        residuals = [count % modulus for count in remaining.values() if count > 0]
        xor = 0
        for value in residuals:
            xor ^= value

        assert xor == 0

    def test_labels_name_the_pile_only_when_it_matters(self) -> None:
        single, handler = _ready(opening_heaps={DEFAULT_HEAP: 3})
        multi, _ = _ready(opening_heaps={"red": 3, "blue": 3})

        assert handler.get_move_label(single, NimMove(DEFAULT_HEAP, 0)) == "Take tokens"
        assert handler.get_move_label(multi, NimMove("red", 2)) == "Take 2 tokens from red"


class TestNimIntegration:
    """VM and HasGame integration tests for nim."""

    def test_move_labels_reflect_take_counts(self) -> None:
        graph = Graph(label="nim_labels")
        block = graph.add_node(kind=NimBlock, label="heap")
        block.game.opening_heaps = {DEFAULT_HEAP: 3}
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        actions = provision_game_moves(block, ctx=ctx)

        assert [action.label for action in actions] == ["Take tokens"]
        assert actions[0].accepts is not None
        assert actions[0].accepts.kind == "quantity"
        assert actions[0].accepts.min == 1
        assert actions[0].accepts.max == 3

    def test_multi_heap_provisions_one_selector_per_pile(self) -> None:
        graph = Graph(label="nim_multi_labels")
        block = graph.add_node(kind=NimBlock, label="heaps")
        block.game.opening_heaps = {"red": 3, "blue": 2}
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        actions = provision_game_moves(block, ctx=ctx)

        assert [action.label for action in actions] == [
            "Take tokens from blue",
            "Take tokens from red",
        ]
        assert [action.accepts.max for action in actions] == [2, 3]

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
        block.game.opening_heaps = {DEFAULT_HEAP: 1}
        block.game_handler.setup(block.game)

        intro_to_heap = ChoiceEdge(
            graph=graph,
            predecessor_id=intro.uid,
            successor_id=block.uid,
            label="Approach the heap",
        )

        ledger = Ledger.from_graph(graph=graph, entry_id=intro.uid)
        ledger.resolve_choice(intro_to_heap.uid)

        take = next(
            action
            for action in ledger.cursor.edges_out()
            if isinstance(action, Action) and action.label == "Take tokens"
        )
        ledger.resolve_choice(take.uid, choice_payload={"quantity": 1})

        assert ledger.cursor_id == victory.uid
        content = " ".join(
            fragment.content
            for fragment in ledger.get_journal()
            if isinstance(fragment.content, str)
        )
        assert "heap collapses" in content.lower()

    def test_context_exports_next_take_hint(self) -> None:
        graph = Graph(label="nim_context")
        block = graph.add_node(kind=NimBlock, label="heap")
        block.game.opening_heaps = {DEFAULT_HEAP: 4}
        block.game.opponent_strategy = "nim_greedy"
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        namespace = inject_game_context(block, ctx=ctx)

        assert namespace["nim_total"] == 4
        assert namespace["nim_opponent_next_take"] == NimMove(pile=DEFAULT_HEAP, count=3)
