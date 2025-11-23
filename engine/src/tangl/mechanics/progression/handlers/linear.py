from __future__ import annotations

from .base import StatHandler


class LinearStatHandler(StatHandler):
    """
    Handler with a simple linear mapping.

    - fv is still in ~[1, 20], centered around 10.
    - qv tiers are equally spaced around 10.
    - likelihood is a clipped linear ramp: 0 at delta=-10, 1 at delta=+10.
    """

    CENTER: float = 10.0
    HALF_RANGE: float = 10.0  # ±10 → [0, 1] ramp

    @classmethod
    def qv_from_fv(cls, fv: float) -> int:
        # Map fv into buckets around CENTER:
        # [ -inf, 8 )   → 1
        # [ 8,   9.5 )  → 2
        # [ 9.5, 11.5 ) → 3
        # [ 11.5, 13 )  → 4
        # [ 13, +inf )  → 5
        if fv < 8.0:
            return 1
        if fv < 9.5:
            return 2
        if fv < 11.5:
            return 3
        if fv < 13.0:
            return 4
        return 5

    @classmethod
    def fv_from_qv(cls, qv: int) -> float:
        if not 1 <= qv <= 5:
            raise ValueError(f"qv must be in [1, 5], got {qv!r}")
        # Tiers 1..5 → 6, 8, 10, 12, 14
        return 4.0 + 2.0 * qv

    @classmethod
    def likelihood(cls, delta: float) -> float:
        """Clipped linear ramp from delta=-10→0.0 to delta=+10→1.0."""
        x = (delta + cls.HALF_RANGE) / (2 * cls.HALF_RANGE)
        return max(0.0, min(1.0, x))
