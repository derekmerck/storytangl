"""Tests for ``tangl.vm38.traversal`` — pure cursor history and call stack queries."""

from __future__ import annotations

from uuid import uuid4

from tangl.vm38.traversal import (
    count_turns,
    get_call_depth,
    get_round,
    get_visit_count,
    in_subroutine,
    is_first_visit,
    is_self_loop,
    steps_since_last_visit,
)


class TestGetVisitCount:
    def test_empty_history(self) -> None:
        assert get_visit_count(uuid4(), []) == 0

    def test_never_visited(self) -> None:
        a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
        assert get_visit_count(d, [a, b, c]) == 0

    def test_single_visit(self) -> None:
        a, b = uuid4(), uuid4()
        assert get_visit_count(b, [a, b]) == 1

    def test_multiple_visits(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        assert get_visit_count(b, [a, b, c, b, a, b]) == 3

    def test_self_loops_count(self) -> None:
        game = uuid4()
        assert get_visit_count(game, [game, game, game]) == 3


class TestIsFirstVisit:
    def test_empty_history(self) -> None:
        assert is_first_visit(uuid4(), []) is False

    def test_true_on_first_arrival(self) -> None:
        a, b = uuid4(), uuid4()
        assert is_first_visit(b, [a, b]) is True

    def test_false_on_repeat(self) -> None:
        a, b = uuid4(), uuid4()
        assert is_first_visit(b, [a, b, b]) is False

    def test_false_when_not_current(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        assert is_first_visit(b, [a, b, c]) is False

    def test_true_single_entry(self) -> None:
        a = uuid4()
        assert is_first_visit(a, [a]) is True


class TestStepsSinceLastVisit:
    def test_never_visited(self) -> None:
        a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
        assert steps_since_last_visit(d, [a, b, c]) == -1

    def test_current_position(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        assert steps_since_last_visit(c, [a, b, c]) == 0

    def test_one_step_ago(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        assert steps_since_last_visit(b, [a, b, c]) == 1

    def test_multiple_steps_ago(self) -> None:
        nodes = [uuid4() for _ in range(5)]
        assert steps_since_last_visit(nodes[1], nodes) == 3

    def test_uses_most_recent_occurrence(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        history = [a, b, c, b, a]
        assert steps_since_last_visit(b, history) == 1

    def test_empty_history(self) -> None:
        assert steps_since_last_visit(uuid4(), []) == -1


class TestGetRound:
    def test_empty_history(self) -> None:
        assert get_round(uuid4(), []) == 0

    def test_not_current_position(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        assert get_round(b, [a, b, c]) == 0

    def test_first_arrival(self) -> None:
        a, b = uuid4(), uuid4()
        assert get_round(b, [a, b]) == 1

    def test_self_loop_rounds(self) -> None:
        a, b = uuid4(), uuid4()
        assert get_round(b, [a, b, b, b]) == 3


class TestIsSelfLoop:
    def test_true(self) -> None:
        a, b = uuid4(), uuid4()
        assert is_self_loop([a, b, b]) is True

    def test_false(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        assert is_self_loop([a, b, c]) is False

    def test_empty(self) -> None:
        assert is_self_loop([]) is False

    def test_single_entry(self) -> None:
        assert is_self_loop([uuid4()]) is False


class TestCountTurns:
    def test_empty(self) -> None:
        assert count_turns([]) == 0

    def test_single_position(self) -> None:
        assert count_turns([uuid4()]) == 1

    def test_linear_path(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        assert count_turns([a, b, c]) == 3

    def test_self_loops_ignored(self) -> None:
        a, b = uuid4(), uuid4()
        assert count_turns([a, b, b, b, a]) == 3

    def test_all_self_loops(self) -> None:
        a = uuid4()
        assert count_turns([a, a, a, a]) == 1

    def test_alternating(self) -> None:
        a, b = uuid4(), uuid4()
        assert count_turns([a, b, a, b]) == 4


class TestInSubroutine:
    def test_empty(self) -> None:
        assert in_subroutine([]) is False

    def test_nonempty(self) -> None:
        assert in_subroutine([uuid4()]) is True


class TestGetCallDepth:
    def test_empty(self) -> None:
        assert get_call_depth([]) == 0

    def test_single(self) -> None:
        assert get_call_depth([uuid4()]) == 1

    def test_nested(self) -> None:
        assert get_call_depth([uuid4(), uuid4(), uuid4()]) == 3
