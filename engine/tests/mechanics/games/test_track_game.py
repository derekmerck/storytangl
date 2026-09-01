"""Tests for the cyclic-track race kernel (the board rung)."""

from __future__ import annotations

from tangl.core import Graph
from tangl.mechanics.games import (
    FORFEIT_TOKEN,
    HasGame,
    TrackGame,
    TrackGameHandler,
    TrackMove,
)
from tangl.mechanics.games.handlers import provision_game_moves
from tangl.story import Block
from tangl.vm import Frame


class TrackBlock(HasGame, Block):
    """Test block embedding a track race."""

    _game_class = TrackGame
    _game_handler_class = TrackGameHandler


def _game(**kwargs) -> TrackGame:
    config = {
        "track_length": 8,
        "finish_distance": 10,
        "tokens_per_side": 2,
        "tokens_to_finish": 1,
        "roll_sequence": [2],
        "opponent_strategy": "track_optimal",
    }
    config.update(kwargs)
    return TrackGame(**config)


def _ready(**kwargs) -> tuple[TrackGame, TrackGameHandler]:
    game = _game(**kwargs)
    handler = TrackGameHandler()
    handler.setup(game)
    return game, handler


def _place(game: TrackGame, owner: str, token_id: int, position: int | None) -> None:
    token = game.get_token(owner, token_id)
    assert token is not None
    token.position = position


class TestTrackRules:
    """Exact landing, eviction, and the assignment choice itself."""

    def test_roll_is_assignable_to_any_own_token(self) -> None:
        game, handler = _ready()
        moves = handler.get_available_moves(game)

        assert [move.token_id for move in moves] == [0, 1]

    def test_overshooting_the_finish_is_illegal(self) -> None:
        game, handler = _ready(roll_sequence=[3])
        _place(game, "player", 0, 8)
        _place(game, "player", 1, 5)

        # token 0 would reach 11 past a finish distance of 10; token 1 reaches 8
        assert [move.token_id for move in handler.get_available_moves(game)] == [1]

    def test_exact_landing_finishes_and_wins(self) -> None:
        game, handler = _ready(roll_sequence=[2])
        _place(game, "player", 0, 8)

        result = handler.receive_move(game, TrackMove(token_id=0))

        assert result.name == "WIN"
        assert game.get_token("player", 0).finished is True
        assert game.finished_count("player") == 1

    def test_arrival_evicts_the_earlier_occupant(self) -> None:
        game, handler = _ready(roll_sequence=[2])
        _place(game, "player", 0, 1)
        _place(game, "opponent", 0, 3)
        _place(game, "opponent", 1, 9)

        handler.receive_move(game, TrackMove(token_id=0))

        # player token 0 advances 1 -> 3, landing on the rival already there.
        # Assert through the round record: the rival may relaunch from the pile
        # later in the same round.
        assert game.get_token("player", 0).position == 3
        assert (game.last_round.notes or {})["player_evicted"] == {
            "owner": "opponent",
            "token_id": 0,
        }

    def test_eviction_uses_the_cyclic_board_index(self) -> None:
        game, handler = _ready(roll_sequence=[2])
        # track_length 8: position 9 and position 1 share board index 1
        _place(game, "player", 0, 7)
        _place(game, "opponent", 0, 1)
        _place(game, "opponent", 1, 5)

        handler.receive_move(game, TrackMove(token_id=0))

        assert game.get_token("player", 0).position == 9
        assert (game.last_round.notes or {})["player_evicted"] == {
            "owner": "opponent",
            "token_id": 0,
        }

    def test_unusable_roll_is_forfeited(self) -> None:
        game, handler = _ready(roll_sequence=[5])
        _place(game, "player", 0, 9)
        _place(game, "player", 1, 8)

        moves = handler.get_available_moves(game)
        assert [move.token_id for move in moves] == [FORFEIT_TOKEN]

        handler.receive_move(game, moves[0])

        assert game.get_token("player", 0).position == 9
        assert (game.last_round.notes or {}).get("player_forfeited") is True


class TestTrackOpponentSeam:
    """The opponent is plugged in; the kernel only asks for a move."""

    def test_optimal_prefers_finishing_over_capturing(self) -> None:
        game, handler = _ready(roll_sequence=[2], opponent_strategy="track_optimal")
        _place(game, "opponent", 0, 3)   # capture available at index 5
        _place(game, "opponent", 1, 8)   # exact finish available
        _place(game, "player", 0, 5)

        handler._preselect_opponent_move(game)

        assert game.opponent_next_move.token_id == 1

    def test_hapless_opponent_picks_the_worst_assignment(self) -> None:
        game, handler = _ready(roll_sequence=[2], opponent_strategy="track_hapless")
        _place(game, "opponent", 0, 3)   # capture available
        _place(game, "opponent", 1, 0)
        _place(game, "player", 0, 5)
        handler._preselect_opponent_move(game)

        assert game.opponent_next_move.token_id == 1

    def test_preselection_is_visible_as_a_tell(self) -> None:
        game, handler = _ready(roll_sequence=[2], opponent_strategy="track_optimal")
        _place(game, "opponent", 0, 3)
        _place(game, "player", 0, 5)
        handler._preselect_opponent_move(game)

        namespace = game.to_namespace()

        assert namespace["track_opponent_next_token"] == 0
        assert namespace["track_opponent_threatens"] is True

    def test_revision_can_retcon_the_roll_into_a_capture(self) -> None:
        game, handler = _ready(
            roll_sequence=[1],
            opponent_strategy="track_optimal",
            opponent_revision_strategy="track_force_capture",
        )
        _place(game, "player", 0, 6)
        _place(game, "player", 1, None)
        _place(game, "opponent", 0, 2)
        _place(game, "opponent", 1, None)

        handler.receive_move(game, TrackMove(token_id=1))

        # The rival needed a 4 to reach board index 6 from position 2, and got one.
        # Read it from the round record: the standing roll is redrawn for the
        # next round once this one resolves.
        notes = game.last_round.notes or {}
        assert notes["opponent_roll"] == 4
        assert game.get_token("player", 0).position is None
        assert notes["opponent_evicted"]["owner"] == "player"

    def test_revision_falls_back_when_no_capture_exists(self) -> None:
        game, handler = _ready(
            roll_sequence=[2],
            opponent_strategy="track_optimal",
            opponent_revision_strategy="track_force_capture",
        )
        for owner in ("player", "opponent"):
            for token_id in (0, 1):
                _place(game, owner, token_id, None)
        handler._preselect_opponent_move(game)

        result = handler.receive_move(game, TrackMove(token_id=0))

        assert result.name in {"CONTINUE", "WIN", "LOSE"}


class TestDegenerateRaceBoard:
    """One token per side and no choice is chutes and ladders."""

    def _run(self) -> list[tuple[int | None, int | None]]:
        game, handler = _ready(
            tokens_per_side=1,
            roll_sequence=[1, 3, 2, 5, 4, 2, 3, 1],
            opponent_strategy="track_optimal",
        )
        trace: list[tuple[int | None, int | None]] = []
        for _ in range(8):
            if game.is_terminal:
                break
            moves = handler.get_available_moves(game)
            assert len(moves) == 1, "a no-choice race offers exactly one move"
            handler.receive_move(game, moves[0])
            trace.append(
                (
                    game.get_token("player", 0).position,
                    game.get_token("opponent", 0).position,
                )
            )
        return trace

    def test_no_choice_race_is_deterministic_from_the_rolls(self) -> None:
        assert self._run() == self._run()


class TestTrackVmIntegration:
    """The kernel projects moves through the ordinary VM seam."""

    def test_moves_provision_as_actions(self) -> None:
        graph = Graph(label="track_flow")
        block = graph.add_node(kind=TrackBlock, label="race")
        block.game_state = _game()
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        actions = provision_game_moves(block, ctx=ctx)
        labels = [action.label for action in actions]

        assert len(labels) == 2
        assert all("Move token" in label for label in labels)


class TestRedirectSquares:
    """Chutes and ladders: the square you land on may send you elsewhere."""

    def test_ladder_carries_the_token_forward(self) -> None:
        game, handler = _ready(roll_sequence=[2], redirects={3: 6}, opponent_strategy=None)
        _place(game, "player", 0, 1)

        handler.receive_move(game, TrackMove(token_id=0))

        assert game.get_token("player", 0).position == 6
        notes = game.last_round.notes or {}
        assert notes["player_redirected"] == {"from": 3, "to": 6, "kind": "ladder"}

    def test_chute_sends_the_token_back(self) -> None:
        game, handler = _ready(roll_sequence=[2], redirects={7: 2}, opponent_strategy=None)
        _place(game, "player", 0, 5)

        handler.receive_move(game, TrackMove(token_id=0))

        assert game.get_token("player", 0).position == 2
        assert (game.last_round.notes or {})["player_redirected"]["kind"] == "chute"

    def test_redirect_is_a_same_lap_displacement(self) -> None:
        # track_length 8: position 11 is board index 3, same square as position 3
        game, handler = _ready(
            roll_sequence=[2],
            redirects={3: 6},
            finish_distance=30,
            opponent_strategy=None,
        )
        _place(game, "player", 0, 9)

        handler.receive_move(game, TrackMove(token_id=0))

        # advanced 9 -> 11 (index 3), then +3 up the ladder, staying on this lap
        assert game.get_token("player", 0).position == 14

    def test_redirects_do_not_chain(self) -> None:
        game, handler = _ready(
            roll_sequence=[2], redirects={3: 6, 6: 1}, opponent_strategy=None
        )
        _place(game, "player", 0, 1)

        handler.receive_move(game, TrackMove(token_id=0))

        assert game.get_token("player", 0).position == 6

    def test_eviction_is_judged_after_the_redirect(self) -> None:
        game, handler = _ready(roll_sequence=[2], redirects={3: 6})
        _place(game, "player", 0, 1)
        _place(game, "opponent", 0, 3)   # sits on the ladder foot, untouched
        _place(game, "opponent", 1, 6)   # sits at the ladder top, evicted

        handler.receive_move(game, TrackMove(token_id=0))

        notes = game.last_round.notes or {}
        assert notes["player_evicted"] == {"owner": "opponent", "token_id": 1}

    def test_a_ladder_may_deliver_a_token_home(self) -> None:
        # track_length 12 keeps finish_distance 10 on the first lap, so a ladder
        # from index 4 to index 10 lands exactly home
        game, handler = _ready(
            track_length=12,
            finish_distance=10,
            roll_sequence=[2],
            redirects={4: 10},
            opponent_strategy=None,
        )
        _place(game, "player", 0, 2)

        result = handler.receive_move(game, TrackMove(token_id=0))

        assert result.name == "WIN"
        assert game.get_token("player", 0).finished is True

    def test_chute_to_the_first_square_lands_on_the_lap_base(self) -> None:
        game, handler = _ready(
            roll_sequence=[2], redirects={3: 0}, opponent_strategy=None
        )
        _place(game, "player", 0, 1)

        handler.receive_move(game, TrackMove(token_id=0))

        # A redirect is a same-lap displacement, so it can reach the lap base
        # but never a negative position.
        assert game.get_token("player", 0).position == 0

    def test_optimal_play_accounts_for_chutes(self) -> None:
        game, handler = _ready(
            roll_sequence=[2],
            redirects={7: 1},
            opponent_strategy="track_optimal",
        )
        _place(game, "opponent", 0, 5)   # would advance to 7, then fall to 1
        _place(game, "opponent", 1, 2)   # plain advance to 4
        handler._preselect_opponent_move(game)

        assert game.opponent_next_move.token_id == 1

    def test_move_labels_name_the_redirect(self) -> None:
        game, handler = _ready(
            roll_sequence=[2], redirects={3: 6}, opponent_strategy=None
        )
        _place(game, "player", 0, 1)
        _place(game, "player", 1, 4)

        labels = [handler.get_move_label(game, m) for m in handler.get_available_moves(game)]

        assert "up a ladder" in labels[0]
        assert "ladder" not in labels[1]

    def test_a_ladder_may_not_overshoot_the_finish(self) -> None:
        game, handler = _ready(
            track_length=12,
            finish_distance=10,
            roll_sequence=[2],
            redirects={4: 11},
            opponent_strategy=None,
        )
        _place(game, "player", 0, 2)

        handler.receive_move(game, TrackMove(token_id=0))

        # The redirect would carry the token to 11, past an exact finish of 10,
        # so it does not apply and the token rests on the arrival square.
        assert game.get_token("player", 0).position == 4
        assert "player_redirected" not in (game.last_round.notes or {})
