"""Tests for the soft attention/time budget (CREDENTIALS_LOOP_DESIGN.md
"Engine review" §1).

A per-shift budget; every probe and decision costs time; time spent over the
budget converts to penalty toward the failure threshold. Actions are never
blocked -- the pressure is economic (go thorough and pay in time, or go fast and
risk wrong calls).
"""

from __future__ import annotations

from tangl.mechanics.games import (
    CredentialDisposition,
    CredentialsGame,
    CredentialsGameHandler,
    CredentialsMove,
    move_time_cost,
)
from engine.tests.mechanics.games.credentials_helpers import make_credential_case as CredentialCase

D = CredentialDisposition


def _move(kind: str, target: str = "") -> CredentialsMove:
    return CredentialsMove(kind=kind, target=target)


class TestMoveCosts:
    def test_tiered_costs(self) -> None:
        assert move_time_cost(_move("inspect", "passport")) == 1
        assert move_time_cost(_move("request_disclosure")) == 1
        assert move_time_cost(_move("verify_id")) == 2
        assert move_time_cost(_move("request_document", "work")) == 2
        assert move_time_cost(_move("request_search")) == 3

    def test_arrest_costs_more_than_a_quick_call(self) -> None:
        assert move_time_cost(_move("decide", "pass")) == 1
        assert move_time_cost(_move("decide", "deny")) == 1
        assert move_time_cost(_move("decide", "arrest")) == 3


def _game(**overrides) -> tuple[CredentialsGame, CredentialsGameHandler]:
    roster = [
        CredentialCase(candidate_name="A", correct_disposition=D.PASS),
        CredentialCase(candidate_name="B", correct_disposition=D.PASS),
    ]
    game = CredentialsGame(roster=roster, **overrides)
    handler = CredentialsGameHandler()
    handler.setup(game)
    return game, handler


def _process(handler, game, call: str) -> None:
    inspect = handler.get_available_inspect_targets(game)
    if inspect:
        handler.receive_move(game, ("inspect", inspect[0]))
    else:
        game.current_stage = "packet"
    handler.receive_move(game, ("decide", call))


class TestTimeAccrual:
    def test_no_budget_means_no_overtime(self) -> None:
        game, handler = _game()  # time_budget defaults to None
        _process(handler, game, "pass")
        _process(handler, game, "pass")
        assert game.time_spent > 0  # time still accrues
        assert game.overtime == 0
        assert game.total_penalty == 0
        assert game.result.name == "WIN"

    def test_time_accrues_per_action(self) -> None:
        game, handler = _game(time_budget=100)
        handler.receive_move(game, ("inspect", "passport"))  # +1
        handler.receive_move(game, ("request_search", ""))   # +3
        assert game.time_spent == 4


class TestOvertimePenalty:
    def test_within_budget_no_penalty(self) -> None:
        # Two candidates, inspect+pass each = 2 each = 4 total; budget 4 -> no overtime.
        game, handler = _game(time_budget=4)
        _process(handler, game, "pass")
        _process(handler, game, "pass")
        assert game.time_spent == 4
        assert game.overtime == 0
        assert game.total_penalty == 0
        assert game.result.name == "WIN"

    def test_overtime_converts_to_penalty_and_can_lose_a_clean_shift(self) -> None:
        # Same correct play, but a stingy budget of 1 -> 3 overtime -> penalty 3,
        # over the strict threshold 0, so even a flawless shift is lost on time.
        game, handler = _game(time_budget=1)
        _process(handler, game, "pass")
        _process(handler, game, "pass")
        assert game.decision_penalty == 0  # every call correct
        assert game.overtime == 3
        assert game.total_penalty == 3
        assert game.result.name == "LOSE"

    def test_overtime_rate_scales(self) -> None:
        game, handler = _game(time_budget=2, overtime_penalty_rate=2)
        _process(handler, game, "pass")  # 2
        _process(handler, game, "pass")  # 4 total -> 2 over
        assert game.overtime == 2
        assert game.total_penalty == 4  # 2 over * rate 2

    def test_threshold_can_absorb_some_overtime(self) -> None:
        game, handler = _game(time_budget=2, penalty_threshold=3)
        _process(handler, game, "pass")
        _process(handler, game, "pass")  # 2 overtime -> penalty 2 <= 3
        assert game.total_penalty == 2
        assert game.result.name == "WIN"

    def test_namespace_exposes_budget(self) -> None:
        game, handler = _game(time_budget=5)
        handler.receive_move(game, ("inspect", "passport"))
        ns = game.to_namespace()
        assert ns["credential_time_budget"] == 5
        assert ns["credential_time_spent"] == 1
        assert ns["credential_overtime"] == 0
