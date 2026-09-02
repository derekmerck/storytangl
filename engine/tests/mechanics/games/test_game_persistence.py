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
from tangl.story import Block


def _round_trip(game_class, handler_class, moves=(), **game_kwargs):
    """Set a game up inside a graph, play some moves, and reload it."""

    class _Block(HasGame, Block):
        _game_class = game_class
        _game_handler_class = handler_class

    graph = Graph(label="persistence")
    block = graph.add_node(kind=_Block, label="game")
    for field, value in game_kwargs.items():
        setattr(block.game, field, value)
    block.game_handler.setup(block.game)
    for move in moves:
        block.game_handler.receive_move(block.game, move)

    restored = Graph.structure(graph.unstructure())
    reloaded = next(
        node for node in restored.nodes if getattr(node, "label", None) == "game"
    )
    return block.game, reloaded.game


class TestWalletsSurvivePersistence:
    """Wallet contents are mutated in place and must opt into the dump."""

    def test_nim_heaps_reload_with_their_tokens(self) -> None:
        before, after = _round_trip(
            NimGame, NimGameHandler, opening_heaps={"heap": 7}
        )

        assert before.heaps.amounts == {"heap": 7}
        assert after.heaps.amounts == before.heaps.amounts

    def test_multi_heap_boards_reload_intact(self) -> None:
        _, after = _round_trip(
            NimGame, NimGameHandler, opening_heaps={"red": 5, "blue": 3}
        )

        assert after.heaps.amounts == {"red": 5, "blue": 3}
        assert after.pile_labels() == ["blue", "red"]

    def test_a_partly_played_board_keeps_its_remainder(self) -> None:
        before, after = _round_trip(
            NimGame,
            NimGameHandler,
            moves=[NimMove(pile="heap", count=1)],
            opening_heaps={"heap": 7},
            opponent_strategy=None,
        )

        assert before.heaps["heap"] == 6
        assert after.heaps["heap"] == 6

    def test_aggregate_force_reserves_reload(self) -> None:
        before, after = _round_trip(BagRpsGame, BagRpsGameHandler)

        assert before.player_reserve.amounts
        assert after.player_reserve.amounts == before.player_reserve.amounts
        assert after.opponent_reserve.amounts == before.opponent_reserve.amounts

    def test_active_and_eliminated_pools_reload(self) -> None:
        before, after = _round_trip(
            BagRpsGame,
            BagRpsGameHandler,
            moves=[ForceCommitMove(profile=(("rock", 1),))],
        )

        assert after.player_active.amounts == before.player_active.amounts
        assert after.player_eliminated.amounts == before.player_eliminated.amounts
        assert after.opponent_eliminated.amounts == before.opponent_eliminated.amounts


class TestMovesSurvivePersistence:
    """Dataclass moves must come back as moves, not dictionaries."""

    def test_pending_opponent_move_restores_as_a_move(self) -> None:
        _, after = _round_trip(NimGame, NimGameHandler, opening_heaps={"heap": 7})

        assert isinstance(after.opponent_next_move, NimMove)

    def test_recorded_moves_restore_as_moves(self) -> None:
        _, after = _round_trip(
            NimGame,
            NimGameHandler,
            moves=[NimMove(pile="heap", count=1)],
            opening_heaps={"heap": 7},
        )

        assert isinstance(after.history[0].player_move, NimMove)

    def test_a_reloaded_game_can_keep_playing(self) -> None:
        # The failure this guards is a dict-valued move reaching `.pile`.
        _, after = _round_trip(
            NimGame,
            NimGameHandler,
            moves=[NimMove(pile="heap", count=1)],
            opening_heaps={"heap": 7},
        )
        handler = NimGameHandler()

        result = handler.receive_move(after, NimMove(pile="heap", count=1))

        assert result.name in {"CONTINUE", "WIN", "LOSE"}

    def test_track_pieces_and_moves_reload(self) -> None:
        before, after = _round_trip(TrackGame, TrackGameHandler)

        assert len(after.tokens) == len(before.tokens)
        assert [piece.position for piece in after.tokens] == [
            piece.position for piece in before.tokens
        ]

    def test_blackjack_hands_reload(self) -> None:
        before, after = _round_trip(BlackjackGame, BlackjackGameHandler)

        assert [card.short_name for card in after.player_hand] == [
            card.short_name for card in before.player_hand
        ]
        assert [card.face_up for card in after.dealer_hand] == [True, False]


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
