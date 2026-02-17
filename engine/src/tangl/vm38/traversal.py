# tangl/vm38/traversal.py
"""Pure traversal queries over cursor history and call stack.

All functions are pure — they take immutable data (lists of UUIDs) and
return derived facts. No side effects, no graph lookups.
"""

from __future__ import annotations

from uuid import UUID

__all__ = [
    "get_visit_count",
    "is_first_visit",
    "steps_since_last_visit",
    "get_round",
    "is_self_loop",
    "count_turns",
    "in_subroutine",
    "get_call_depth",
]


def get_visit_count(cursor_id: UUID, history: list[UUID]) -> int:
    """Count how many times ``cursor_id`` appears in ``history``."""
    return history.count(cursor_id)


def is_first_visit(cursor_id: UUID, history: list[UUID]) -> bool:
    """True when this is the first time the cursor has reached ``cursor_id``."""
    if not history or cursor_id != history[-1]:
        return False
    return history.count(cursor_id) == 1


def steps_since_last_visit(cursor_id: UUID, history: list[UUID]) -> int:
    """Count edge-follows since the cursor last visited ``cursor_id``.

    Returns
    -------
    int
        ``0`` if ``cursor_id`` is current position, a positive count
        if visited earlier, or ``-1`` if never visited.
    """
    for index in range(len(history) - 1, -1, -1):
        if history[index] == cursor_id:
            return len(history) - 1 - index
    return -1


def get_round(cursor_id: UUID, history: list[UUID]) -> int:
    """Count trailing consecutive visits to ``cursor_id``.

    Returns
    -------
    int
        ``0`` if ``cursor_id`` is not current position, otherwise
        ``1`` on first arrival, ``2`` after one self-loop, etc.
    """
    if not history or history[-1] != cursor_id:
        return 0

    count = 0
    for index in range(len(history) - 1, -1, -1):
        if history[index] == cursor_id:
            count += 1
        else:
            break
    return count


def is_self_loop(history: list[UUID]) -> bool:
    """True when the last edge-follow returned to the same node."""
    return len(history) >= 2 and history[-1] == history[-2]


def count_turns(history: list[UUID]) -> int:
    """Count distinct position changes, ignoring consecutive self-loops."""
    if not history:
        return 0
    turns = 1
    for index in range(1, len(history)):
        if history[index] != history[index - 1]:
            turns += 1
    return turns


def in_subroutine(call_stack_ids: list[UUID]) -> bool:
    """True when traversal is inside any subroutine call."""
    return len(call_stack_ids) > 0


def get_call_depth(call_stack_ids: list[UUID]) -> int:
    """Current call stack depth (0 = top-level)."""
    return len(call_stack_ids)
