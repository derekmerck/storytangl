"""
Traversal utilities for inspecting cursor history and call stacks.

These helpers provide semantic queries over the low-level tracking structures
(`cursor_history`, `call_stack`) maintained by :class:`~tangl.vm.frame.Frame`
and :class:`~tangl.vm.ledger.Ledger`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from tangl.vm.frame import StackFrame


# ---------------------------------------------------------------------------
# Cursor history queries
# ---------------------------------------------------------------------------

def get_visit_count(cursor_id: UUID, history: list[UUID]) -> int:
    """
    Count how many times a node has been visited.

    Parameters
    ----------
    cursor_id:
        Node identifier to count visits for.
    history:
        Complete cursor history from a :class:`~tangl.vm.frame.Frame` or
        :class:`~tangl.vm.ledger.Ledger`.

    Returns
    -------
    int
        Number of times ``cursor_id`` appears in ``history``.
    """

    return sum(1 for cid in history if cid == cursor_id)


def is_first_visit(cursor_id: UUID, history: list[UUID]) -> bool:
    """
    Determine whether the current position is the first visit to a node.

    True when the history ends at ``cursor_id`` and that identifier appears
    exactly once in the history.
    """

    if not history or cursor_id != history[-1]:
        return False

    return history.count(cursor_id) == 1


def steps_since_last_visit(cursor_id: UUID, history: list[UUID]) -> int:
    """
    Count the number of edge follows since the cursor last visited a node.

    Returns ``0`` when ``cursor_id`` is the current position, a positive count
    when the node was visited earlier, or ``-1`` if the node has never been
    visited.
    """

    for index in range(len(history) - 1, -1, -1):
        if history[index] == cursor_id:
            return len(history) - 1 - index

    return -1


def is_self_loop(history: list[UUID]) -> bool:
    """
    Check whether the most recent edge follow was a self-loop.

    Returns ``True`` when the last two history entries reference the same node.
    """

    return len(history) >= 2 and history[-1] == history[-2]


# ---------------------------------------------------------------------------
# Call stack queries
# ---------------------------------------------------------------------------

def in_subroutine(call_stack: list[StackFrame]) -> bool:
    """
    Indicate whether traversal is currently inside any subroutine call.
    """

    return len(call_stack) > 0


def get_caller_frame(call_stack: list[StackFrame]) -> StackFrame | None:
    """
    Retrieve the immediate caller frame if one exists.
    """

    return call_stack[-1] if call_stack else None


def get_call_depth(call_stack: list[StackFrame]) -> int:
    """
    Compute the current call stack depth.
    """

    return len(call_stack)


def get_root_caller(call_stack: list[StackFrame]) -> UUID | None:
    """
    Return the cursor identifier of the outermost call frame.

    Returns ``None`` when no calls have been made.
    """

    return call_stack[0].return_cursor_id if call_stack else None
