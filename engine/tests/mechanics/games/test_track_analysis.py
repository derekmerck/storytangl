"""Tests for Markov analysis of no-choice track layouts."""

from __future__ import annotations

from tangl.mechanics.games import (
    TrackGame,
    analyze_track,
    expected_rolls_to_finish,
    finish_distribution,
)


def _board(**kwargs) -> TrackGame:
    config = {
        "track_length": 24,
        "finish_distance": 24,
        "tokens_per_side": 1,
        "min_roll": 1,
        "max_roll": 6,
    }
    config.update(kwargs)
    return TrackGame(**config)


class TestExpectedRolls:
    """The chain solves to a closed-form expectation."""

    def test_single_square_board_takes_one_roll(self) -> None:
        game = _board(track_length=1, finish_distance=1, min_roll=1, max_roll=1)

        assert expected_rolls_to_finish(game) == 1.0

    def test_two_square_board_matches_hand_computation(self) -> None:
        # From square 1 a roll of 2 overshoots and is forfeited, so the tail
        # is geometric: E[1] = 2, and E[0] = 1 + 0.5 * E[1] = 2.
        game = _board(track_length=2, finish_distance=2, min_roll=1, max_roll=2)

        assert expected_rolls_to_finish(game) == 2.0

    def test_exact_landing_lengthens_the_endgame(self) -> None:
        forgiving = _board(finish_distance=24, min_roll=1, max_roll=2)
        punishing = _board(finish_distance=24, min_roll=1, max_roll=6)

        # A wider die advances faster but wastes more rolls at the finish, so
        # the endgame tax is real rather than assumed.
        assert expected_rolls_to_finish(punishing) < expected_rolls_to_finish(forgiving)
        assert expected_rolls_to_finish(punishing) > 24 / 3.5

    def test_ladders_shorten_and_chutes_lengthen(self) -> None:
        plain = expected_rolls_to_finish(_board())
        laddered = expected_rolls_to_finish(_board(redirects={2: 14, 5: 18}))
        chuted = expected_rolls_to_finish(_board(redirects={14: 2, 18: 5}))

        assert laddered < plain < chuted

    def test_analysis_does_not_mutate_the_game(self) -> None:
        game = _board(redirects={2: 14})

        analyze_track(game)

        assert game.redirects == {2: 14}


class TestLayoutCharacter:
    """The advisory classification names the dramatic shape."""

    def test_bare_board_is_a_footrace(self) -> None:
        analysis = analyze_track(_board())

        assert analysis.character == "footrace"
        assert analysis.net_vector == 0
        assert analysis.drag_ratio == 1.0

    def test_late_chutes_make_a_heartbreak_board(self) -> None:
        analysis = analyze_track(
            _board(redirects={3: 9, 21: 3, 22: 2, 19: 4, 17: 5})
        )

        assert analysis.character == "heartbreak"
        assert analysis.net_vector < 0
        assert analysis.drag_ratio > 1.4

    def test_balanced_board_counts_ladders_and_chutes(self) -> None:
        analysis = analyze_track(
            _board(redirects={2: 11, 6: 15, 9: 17, 13: 4, 19: 8})
        )

        assert analysis.ladder_count == 3
        assert analysis.chute_count == 2
        assert 0.15 <= analysis.modifier_density <= 0.25
        assert analysis.character == "balanced"

    def test_dense_board_reads_as_chaotic(self) -> None:
        redirects = {index: (index + 5) % 24 for index in range(0, 22, 2)}
        analysis = analyze_track(_board(redirects=redirects))

        assert analysis.modifier_density > 0.25
        assert analysis.character in {"chaotic", "heartbreak"}


class TestFinishDistribution:
    """The cumulative curve exposes fat tails."""

    def test_distribution_is_monotone_and_approaches_certainty(self) -> None:
        curve = finish_distribution(_board(), max_rolls=120)

        assert all(b >= a - 1e-12 for a, b in zip(curve, curve[1:]))
        assert curve[-1] > 0.999

    def test_heartbreak_board_has_the_fatter_tail(self) -> None:
        plain = finish_distribution(_board(), max_rolls=40)
        cruel = finish_distribution(
            _board(redirects={21: 3, 22: 2, 19: 4}), max_rolls=40
        )

        assert cruel[-1] < plain[-1]
