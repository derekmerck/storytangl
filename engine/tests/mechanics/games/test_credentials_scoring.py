"""Tests for the graduated penalty-matrix scoring (CREDENTIALS_LOOP_DESIGN.md
"Engine review" §2)."""

from __future__ import annotations

import pytest

from tangl.mechanics.games import (
    CredentialDisposition,
    CredentialsGame,
    CredentialsGameHandler,
    disposition_penalty,
)
from engine.tests.mechanics.games.credentials_helpers import make_credential_case as CredentialCase

D = CredentialDisposition


class TestPenaltyMatrix:
    @pytest.mark.parametrize(
        "expected,chosen,penalty",
        [
            (D.PASS, D.PASS, 0), (D.PASS, D.DENY, 2), (D.PASS, D.ARREST, 5),
            (D.DENY, D.PASS, 2), (D.DENY, D.DENY, 0), (D.DENY, D.ARREST, 5),
            (D.ARREST, D.PASS, 5), (D.ARREST, D.DENY, 2), (D.ARREST, D.ARREST, 0),
        ],
    )
    def test_matrix(self, expected, chosen, penalty) -> None:
        assert disposition_penalty(expected, chosen) == penalty

    def test_arrest_when_wrong_is_always_heaviest(self) -> None:
        # Reaching for arrest wrongly costs 5 whether the correct call was allow
        # or deny -- the heavy hammer is uniformly high-stakes.
        assert disposition_penalty(D.PASS, D.ARREST) == 5
        assert disposition_penalty(D.DENY, D.ARREST) == 5

    def test_deny_is_the_low_variance_hedge(self) -> None:
        # For an ambiguous candidate (innocent vs guilty), denying caps the
        # downside at 2 either way, while the alternatives risk 5.
        assert disposition_penalty(D.PASS, D.DENY) == 2   # was innocent
        assert disposition_penalty(D.ARREST, D.DENY) == 2  # was a criminal
        # The risky alternatives: arrest an innocent (5), allow a criminal (5).
        assert disposition_penalty(D.PASS, D.ARREST) == 5
        assert disposition_penalty(D.ARREST, D.PASS) == 5


def _game(threshold: int = 0) -> tuple[CredentialsGame, CredentialsGameHandler]:
    roster = [
        CredentialCase(candidate_name="A", correct_disposition=D.PASS),
        CredentialCase(candidate_name="B", correct_disposition=D.DENY),
        CredentialCase(candidate_name="C", correct_disposition=D.ARREST),
    ]
    game = CredentialsGame(roster=roster, penalty_threshold=threshold)
    handler = CredentialsGameHandler()
    handler.setup(game)
    return game, handler


def _decide(handler, game, disposition: str) -> None:
    # reach packet stage then decide
    inspect = handler.get_available_inspect_targets(game)
    if inspect:
        handler.receive_move(game, ("inspect", inspect[0]))
    else:
        game.current_stage = "packet"
    handler.receive_move(game, ("decide", disposition))


class TestShiftPenaltyAccumulation:
    def test_perfect_shift_has_zero_penalty_and_wins(self) -> None:
        game, handler = _game()
        for call in ("pass", "deny", "arrest"):
            _decide(handler, game, call)
        assert game.total_penalty == 0
        assert game.result.name == "WIN"

    def test_penalty_accumulates_and_threshold_decides(self) -> None:
        # Deny A (should pass, +2), deny B (+0), deny C (should arrest, +2) = 4.
        game, handler = _game(threshold=3)
        for _ in range(3):
            _decide(handler, game, "deny")
        assert game.total_penalty == 4
        assert game.result.name == "LOSE"  # 4 > 3

    def test_threshold_tolerates_within_budget(self) -> None:
        game, handler = _game(threshold=4)
        for _ in range(3):
            _decide(handler, game, "deny")
        assert game.total_penalty == 4
        assert game.result.name == "WIN"  # 4 <= 4

    def test_per_case_penalty_recorded(self) -> None:
        game, handler = _game(threshold=10)
        _decide(handler, game, "arrest")  # A should pass -> +5
        _decide(handler, game, "deny")    # B correct -> +0
        _decide(handler, game, "pass")    # C should arrest -> +5
        assert [r.penalty for r in game.case_results] == [5, 0, 5]
        assert game.total_penalty == 10
