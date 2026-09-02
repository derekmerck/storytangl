"""Constructor-form round-trip coverage for game kernels.

`model_dump()` / `model_validate()` is not the persistence contract, so these
go through `Graph.unstructure()` / `Graph.structure()`. In-place mutation of a
nested value object — a wallet's `gain()` — is invisible to a recursive
`exclude_unset` dump unless the field opts in explicitly, which is exactly how
a saved game silently loses its board.
"""

from __future__ import annotations

import pytest

from tangl.core import Graph
from tangl.mechanics.games import (
    AggregateForceGame,
    BagRpsGame,
    BagRpsGameHandler,
    BlackjackGame,
    BlackjackGameHandler,
    BlackjackMove,
    HasGame,
    NimGame,
    NimGameHandler,
    NimMove,
    TrackGame,
    TrackGameHandler,
    TrackMove,
)
from tangl.mechanics.games.aggregate_force_game import ForceCommitMove
from tangl.persistence.serializers import JsonSerializationHandler
from tangl.story import Block
from tangl.story.concepts.asset import AssetWallet


class NimPersistBlock(HasGame, Block):
    _game_class = NimGame
    _game_handler_class = NimGameHandler


class BagPersistBlock(HasGame, Block):
    _game_class = BagRpsGame
    _game_handler_class = BagRpsGameHandler


class TrackPersistBlock(HasGame, Block):
    _game_class = TrackGame
    _game_handler_class = TrackGameHandler


class BlackjackPersistBlock(HasGame, Block):
    _game_class = BlackjackGame
    _game_handler_class = BlackjackGameHandler


def _played(block_class, moves=(), **game_kwargs):
    """Return a graph with a set-up, partly played game on one block."""

    graph = Graph(label="persistence")
    block = graph.add_node(kind=block_class, label="game")
    for field, value in game_kwargs.items():
        setattr(block.game, field, value)
    block.game_handler.setup(block.game)
    for move in moves:
        block.game_handler.receive_move(block.game, move)
    return graph, block.game


def _reload(graph, *, through_json: bool = False):
    """Reload a graph through constructor form, optionally crossing JSON.

    The in-process path hands the same live objects back, so it cannot detect a
    field that dumps an un-serializable object. Crossing a real serializer is
    what proves the dump is data rather than references.
    """

    data = graph.unstructure()
    if through_json:
        data = JsonSerializationHandler.deserialize(
            JsonSerializationHandler.serialize(data)
        )
    restored = Graph.structure(data)
    return next(
        node for node in restored.nodes if getattr(node, "label", None) == "game"
    ).game


def _round_trip(block_class, moves=(), *, through_json: bool = False, **game_kwargs):
    graph, before = _played(block_class, moves, **game_kwargs)
    return before, _reload(graph, through_json=through_json)


class TestWalletsSurvivePersistence:
    """Wallet contents are mutated in place and must opt into the dump."""

    def test_nim_heaps_reload_with_their_tokens(self) -> None:
        before, after = _round_trip(
            NimPersistBlock, opening_heaps={"heap": 7}
        )

        assert before.heaps.amounts == {"heap": 7}
        assert after.heaps.amounts == before.heaps.amounts

    def test_multi_heap_boards_reload_intact(self) -> None:
        _, after = _round_trip(
            NimPersistBlock, opening_heaps={"red": 5, "blue": 3}
        )

        assert after.heaps.amounts == {"red": 5, "blue": 3}
        assert after.pile_labels() == ["blue", "red"]

    def test_a_partly_played_board_keeps_its_remainder(self) -> None:
        before, after = _round_trip(
            NimPersistBlock,
            moves=[NimMove(pile="heap", count=1)],
            opening_heaps={"heap": 7},
            opponent_strategy=None,
        )

        assert before.heaps["heap"] == 6
        assert after.heaps["heap"] == 6

    def test_aggregate_force_reserves_reload(self) -> None:
        before, after = _round_trip(BagPersistBlock)

        assert before.player_reserve.amounts
        assert after.player_reserve.amounts == before.player_reserve.amounts
        assert after.opponent_reserve.amounts == before.opponent_reserve.amounts

    def test_active_and_eliminated_pools_reload(self) -> None:
        before, after = _round_trip(
            BagPersistBlock,
            moves=[ForceCommitMove(profile=(("rock", 1),))],
        )

        assert after.player_active.amounts == before.player_active.amounts
        assert after.player_eliminated.amounts == before.player_eliminated.amounts
        assert after.opponent_eliminated.amounts == before.opponent_eliminated.amounts


class TestJsonBoundary:
    """Crossing a real serializer, not just handing live objects back.

    An in-process constructor-form round trip cannot tell a dumped mapping from
    a dumped live object, because `Graph.structure()` accepts the object it was
    just given. Every wallet field looked fine under that test while the dump
    still contained an `AssetWallet` instance.
    """

    def test_no_live_wallet_objects_reach_the_dump(self) -> None:
        graph, _ = _played(NimPersistBlock, opening_heaps={"heap": 7})

        def contains_wallet(value) -> bool:
            if isinstance(value, AssetWallet):
                return True
            if isinstance(value, dict):
                return any(contains_wallet(item) for item in value.values())
            if isinstance(value, (list, tuple)):
                return any(contains_wallet(item) for item in value)
            return False

        assert contains_wallet(graph.unstructure()) is False

    def test_nim_heaps_survive_a_json_round_trip(self) -> None:
        _, after = _round_trip(
            NimPersistBlock, opening_heaps={"red": 5, "blue": 3}, through_json=True
        )

        assert after.heaps.amounts == {"red": 5, "blue": 3}

    def test_aggregate_force_pools_survive_a_json_round_trip(self) -> None:
        before, after = _round_trip(
            BagPersistBlock,
            moves=[ForceCommitMove(profile=(("rock", 1),))],
            through_json=True,
        )

        assert after.player_reserve.amounts == before.player_reserve.amounts
        assert after.opponent_eliminated.amounts == before.opponent_eliminated.amounts

    def test_a_json_reloaded_game_can_keep_playing(self) -> None:
        _, after = _round_trip(
            NimPersistBlock,
            moves=[NimMove(pile="heap", count=1)],
            opening_heaps={"heap": 7},
            through_json=True,
        )

        result = NimGameHandler().receive_move(after, NimMove(pile="heap", count=1))

        assert result.name in {"CONTINUE", "WIN", "LOSE"}
        assert after.heaps["heap"] < 6


class TestMovesSurvivePersistence:
    """Dataclass moves must come back as moves, not dictionaries."""

    def test_pending_opponent_move_restores_as_a_move(self) -> None:
        _, after = _round_trip(NimPersistBlock, opening_heaps={"heap": 7})

        assert isinstance(after.opponent_next_move, NimMove)

    def test_recorded_moves_restore_as_moves(self) -> None:
        _, after = _round_trip(
            NimPersistBlock,
            moves=[NimMove(pile="heap", count=1)],
            opening_heaps={"heap": 7},
        )

        assert isinstance(after.history[0].player_move, NimMove)

    def test_a_reloaded_game_can_keep_playing(self) -> None:
        # The failure this guards is a dict-valued move reaching `.pile`.
        _, after = _round_trip(
            NimPersistBlock,
            moves=[NimMove(pile="heap", count=1)],
            opening_heaps={"heap": 7},
        )
        handler = NimGameHandler()

        result = handler.receive_move(after, NimMove(pile="heap", count=1))

        assert result.name in {"CONTINUE", "WIN", "LOSE"}

    def test_track_pieces_and_moves_reload(self) -> None:
        before, after = _round_trip(TrackPersistBlock)

        assert len(after.tokens) == len(before.tokens)
        assert [piece.position for piece in after.tokens] == [
            piece.position for piece in before.tokens
        ]

    def test_blackjack_hands_reload(self) -> None:
        before, after = _round_trip(BlackjackPersistBlock)

        assert [card.short_name for card in after.player_hand] == [
            card.short_name for card in before.player_hand
        ]
        assert [card.face_up for card in after.dealer_hand] == [True, False]


class TestUnsupportedConfigurations:
    """Reject what the rules do not define rather than crashing later."""

    def test_a_larger_minimum_take_is_refused(self) -> None:
        # min_take > 1 creates boards with tokens left and no legal move; who
        # wins a stuck board is an undesigned rule, and the old code reached
        # `legal[0]` on an empty list and raised IndexError mid-resolution.
        with pytest.raises(ValueError, match="min_take=1 only"):
            NimGame(opening_heaps={"heap": 4}, min_take=2, max_take=3)


class TestStaleOpponentMoves:
    """A pre-selected move can be invalidated by the player's own take."""

    def test_a_shared_heap_does_not_strand_the_round(self) -> None:
        game = NimGame(
            opening_heaps={"heap": 4}, max_take=3, opponent_strategy="nim_greedy"
        )
        handler = NimGameHandler()
        handler.setup(game)
        assert game.opponent_next_move == NimMove(pile="heap", count=3)

        # The player takes the same three the opponent had planned on.
        result = handler.receive_move(game, NimMove(pile="heap", count=3))

        assert result.name in {"WIN", "LOSE", "CONTINUE"}
        assert game.phase.name == "TERMINAL"
        assert (game.last_round.notes or {})["opponent_move_adjusted"] == {
            "pile": "heap",
            "count": 3,
        }

    def test_an_emptied_heap_falls_back_to_another(self) -> None:
        game = NimGame(
            opening_heaps={"red": 2, "blue": 4},
            max_take=3,
            opponent_strategy=None,
        )
        handler = NimGameHandler()
        handler.setup(game)
        game.opponent_next_move = NimMove(pile="red", count=2)

        handler.receive_move(game, NimMove(pile="red", count=2))

        assert game.heaps["red"] == 0
        assert game.heaps["blue"] < 4


class TestMisereAnalysis:
    """Taking the last token to lose is a different game."""

    def _dealt(self, **kwargs) -> NimGame:
        game = NimGame(**kwargs)
        NimGameHandler().setup(game)
        return game

    def test_single_heap_misere_shifts_the_modulus(self) -> None:
        # normal play: multiples of max_take + 1 are lost for the mover
        # misere: it is one *past* the multiple that is lost
        normal = self._dealt(
            opening_heaps={"heap": 4}, max_take=3, last_token_wins=True
        )
        misere = self._dealt(
            opening_heaps={"heap": 4}, max_take=3, last_token_wins=False
        )

        assert normal.is_losing_position is True
        assert misere.is_losing_position is False

    def test_the_solver_matches_an_exhaustive_search(self) -> None:
        # The previous heuristic disagreed with the exact recurrence in over a
        # hundred swept positions, including the two-heap case (3, 1) at k=2.
        from functools import lru_cache

        from tangl.mechanics.games.nim_game import is_losing

        def exact(piles, k, last_wins):
            @lru_cache(maxsize=None)
            def lose(pos):
                pos = tuple(sorted(p for p in pos if p > 0))
                if not pos:
                    return last_wins
                kids = set()
                for i, p in enumerate(pos):
                    for t in range(1, min(k, p) + 1):
                        nxt = list(pos)
                        nxt[i] = p - t
                        kids.add(tuple(sorted(x for x in nxt if x > 0)))
                return all(not lose(c) for c in kids)

            return lose(tuple(sorted(piles)))

        mismatches = [
            (k, a, b, last_wins)
            for k in (2, 3)
            for a in range(6)
            for b in range(6)
            for last_wins in (True, False)
            if exact((a, b), k, last_wins) != is_losing([a, b], k, last_wins)
        ]

        assert mismatches == []

    def test_bounded_multiheap_misere_is_exact(self) -> None:
        from tangl.mechanics.games.nim_game import is_losing

        # The case the heuristic got wrong.
        assert is_losing([3, 1], 2, False) is True

    def test_an_oversized_misere_board_declines_rather_than_guesses(self) -> None:
        from tangl.mechanics.games.nim_game import MAX_EXACT_TOKENS, is_losing

        with pytest.raises(ValueError, match="exact search"):
            is_losing([MAX_EXACT_TOKENS + 1], 3, False)

    def test_misere_losing_positions_are_one_past_the_multiple(self) -> None:
        for size, lost in [(1, True), (4, False), (5, True), (8, False), (9, True)]:
            game = self._dealt(
                opening_heaps={"heap": size}, max_take=3, last_token_wins=False
            )
            assert game.is_losing_position is lost, size

    def test_misere_optimal_leaves_the_last_token(self) -> None:
        game = NimGame(
            opening_heaps={"heap": 4},
            max_take=3,
            last_token_wins=False,
            opponent_strategy="nim_optimal",
        )
        handler = NimGameHandler()
        handler.setup(game)

        # taking 3 leaves one token the opponent is forced to take
        assert game.opponent_next_move == NimMove(pile="heap", count=3)

    def test_misere_optimal_refuses_to_take_the_last_token(self) -> None:
        game = self._dealt(
            opening_heaps={"heap": 1},
            max_take=3,
            last_token_wins=False,
            opponent_strategy="nim_optimal",
        )

        # Lost either way, but it must not be because the strategy volunteered.
        assert game.is_losing_position is True

    def test_all_ones_misere_is_decided_by_parity(self) -> None:
        odd = self._dealt(opening_heaps={"a": 1, "b": 1, "c": 1}, last_token_wins=False)
        even = self._dealt(opening_heaps={"a": 1, "b": 1}, last_token_wins=False)

        assert odd.is_losing_position is True
        assert even.is_losing_position is False
