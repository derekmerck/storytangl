"""Tests for traversal utility functions."""

from uuid import uuid4

from tangl.vm.frame import StackFrame
from tangl.vm.traversal import (
    get_visit_count,
    is_first_visit,
    steps_since_last_visit,
    is_self_loop,
    in_subroutine,
    get_caller_frame,
    get_call_depth,
    get_root_caller,
)


class TestCursorHistoryQueries:
    """Tests for history-based traversal queries."""

    def test_get_visit_count_empty_history(self) -> None:
        """Visit count is ``0`` for an empty history."""

        node_id = uuid4()

        assert get_visit_count(node_id, []) == 0

    def test_get_visit_count_never_visited(self) -> None:
        """Visit count is ``0`` for a node not present in the history."""

        a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
        history = [a, b, c]

        assert get_visit_count(d, history) == 0

    def test_get_visit_count_single_visit(self) -> None:
        """Visit count is ``1`` when the node appears once."""

        a, b = uuid4(), uuid4()
        history = [a, b]

        assert get_visit_count(b, history) == 1

    def test_get_visit_count_multiple_visits(self) -> None:
        """Visit count handles repeated visits."""

        a, b, c = uuid4(), uuid4(), uuid4()
        history = [a, b, c, b, a, b]

        assert get_visit_count(b, history) == 3

    def test_get_visit_count_self_loops(self) -> None:
        """Self-loops contribute multiple visits."""

        game = uuid4()
        history = [game, game, game]

        assert get_visit_count(game, history) == 3

    def test_is_first_visit_empty_history(self) -> None:
        """Empty history is not a first visit."""

        node_id = uuid4()

        assert is_first_visit(node_id, []) is False

    def test_is_first_visit_true(self) -> None:
        """Returns ``True`` on a first arrival at the node."""

        a, b = uuid4(), uuid4()
        history = [a, b]

        assert is_first_visit(b, history) is True

    def test_is_first_visit_false_on_second(self) -> None:
        """Returns ``False`` on a repeat visit."""

        a, b = uuid4(), uuid4()
        history = [a, b, b]

        assert is_first_visit(b, history) is False

    def test_is_first_visit_requires_current(self) -> None:
        """Returns ``False`` when the node is not the current cursor position."""

        a, b, c = uuid4(), uuid4(), uuid4()
        history = [a, b, c]

        assert is_first_visit(b, history) is False

    def test_steps_since_last_visit_never(self) -> None:
        """Returns ``-1`` when the node has never been visited."""

        a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
        history = [a, b, c]

        assert steps_since_last_visit(d, history) == -1

    def test_steps_since_last_visit_immediate(self) -> None:
        """Returns ``0`` when the node is the current position."""

        a, b, c = uuid4(), uuid4(), uuid4()
        history = [a, b, c]

        assert steps_since_last_visit(c, history) == 0

    def test_steps_since_last_visit_one_ago(self) -> None:
        """Returns ``1`` when the previous position matches the node."""

        a, b, c = uuid4(), uuid4(), uuid4()
        history = [a, b, c]

        assert steps_since_last_visit(b, history) == 1

    def test_steps_since_last_visit_multiple(self) -> None:
        """Counts steps correctly when the node was visited earlier."""

        a, b, c, d, e = [uuid4() for _ in range(5)]
        history = [a, b, c, d, e]

        assert steps_since_last_visit(b, history) == 3

    def test_is_self_loop_true(self) -> None:
        """Returns ``True`` when the last move was a self-loop."""

        a, b = uuid4(), uuid4()
        history = [a, b, b]

        assert is_self_loop(history) is True

    def test_is_self_loop_false(self) -> None:
        """Returns ``False`` when the cursor changed position."""

        a, b, c = uuid4(), uuid4(), uuid4()
        history = [a, b, c]

        assert is_self_loop(history) is False

    def test_is_self_loop_empty(self) -> None:
        """Empty history cannot represent a self-loop."""

        assert is_self_loop([]) is False

    def test_is_self_loop_single(self) -> None:
        """Single-entry history is not a self-loop."""

        a = uuid4()

        assert is_self_loop([a]) is False


class TestCallStackQueries:
    """Tests for call stack traversal queries."""

    def test_in_subroutine_empty(self) -> None:
        """Empty stack indicates no active subroutine."""

        assert in_subroutine([]) is False

    def test_in_subroutine_nonempty(self) -> None:
        """Non-empty stack means traversal is inside a subroutine."""

        frame = StackFrame(return_cursor_id=uuid4(), call_site_label="test", depth=0)

        assert in_subroutine([frame]) is True

    def test_get_caller_frame_empty(self) -> None:
        """Empty stack returns ``None`` for caller frame."""

        assert get_caller_frame([]) is None

    def test_get_caller_frame_returns_top(self) -> None:
        """The caller frame helper returns the top-most frame."""

        frame1 = StackFrame(return_cursor_id=uuid4(), call_site_label="outer", depth=0)
        frame2 = StackFrame(return_cursor_id=uuid4(), call_site_label="inner", depth=1)

        assert get_caller_frame([frame1, frame2]) is frame2

    def test_get_call_depth_empty(self) -> None:
        """Depth is ``0`` for an empty stack."""

        assert get_call_depth([]) == 0

    def test_get_call_depth_counts_frames(self) -> None:
        """Depth equals the number of frames on the stack."""

        frames = [
            StackFrame(return_cursor_id=uuid4(), call_site_label=f"f{i}", depth=i) for i in range(3)
        ]

        assert get_call_depth(frames) == 3

    def test_get_root_caller_empty(self) -> None:
        """Root caller returns ``None`` for an empty stack."""

        assert get_root_caller([]) is None

    def test_get_root_caller_returns_bottom(self) -> None:
        """Root caller helper returns the bottom frame's return address."""

        bottom_return = uuid4()
        frame1 = StackFrame(return_cursor_id=bottom_return, call_site_label="bottom", depth=0)
        frame2 = StackFrame(return_cursor_id=uuid4(), call_site_label="top", depth=1)

        assert get_root_caller([frame1, frame2]) == bottom_return
