from __future__ import annotations

from enum import IntEnum
from typing import Optional

import random


class Outcome(IntEnum):
    """
    Coarse-grained result of a task / challenge.

    Ordering:
        DISASTER < FAILURE < SUCCESS < MAJOR_SUCCESS
    """

    DISASTER = 1
    FAILURE = 2
    SUCCESS = 3
    MAJOR_SUCCESS = 4


def sample_outcome(
    p_success: float,
    *,
    roll: Optional[float] = None,
    margin: float = 0.15,
) -> Outcome:
    """
    Sample an Outcome given probability of success (0–1).

    Heuristic:
        - `p_success` is the probability of at least a basic SUCCESS.
        - We carve out a margin around `p_success` for graded results:

            roll < p - margin  → MAJOR_SUCCESS
            p - margin ≤ roll < p → SUCCESS
            p ≤ roll < p + margin → FAILURE
            roll ≥ p + margin → DISASTER

    This is intentionally simple and monotone in `p_success`
    for any fixed `roll`.
    """
    if not 0.0 <= p_success <= 1.0:
        raise ValueError(f"p_success must be in [0, 1], got {p_success!r}")

    if roll is None:
        roll = random.random()

    low = p_success - margin
    high = p_success + margin

    if roll < low:
        return Outcome.MAJOR_SUCCESS
    if roll < p_success:
        return Outcome.SUCCESS
    if roll < high:
        return Outcome.FAILURE
    return Outcome.DISASTER
