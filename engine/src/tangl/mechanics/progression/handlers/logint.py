from __future__ import annotations

import math

from .base import StatHandler


class LogIntStatHandler(StatHandler):
    """
    Exponential-ish handler, useful for “cookie-clicker” style systems.

    - fv grows roughly exponentially with qv.
    - likelihood interprets delta in log space to make each tier jump
      feel more dramatic.
    """

    BASE_FV: float = 4.0
    GROWTH: float = 2.0  # multiplicative per tier

    @classmethod
    def fv_from_qv(cls, qv: int) -> float:
        if not 1 <= qv <= 5:
            raise ValueError(f"qv must be in [1, 5], got {qv!r}")
        # qv=1→4, qv=2→8, qv=3→16, ...
        return cls.BASE_FV * (cls.GROWTH ** (qv - 1))

    @classmethod
    def qv_from_fv(cls, fv: float) -> int:
        if fv <= cls.BASE_FV:
            return 1
        # invert fv_from_qv, clamp to [1, 5]
        ratio = fv / cls.BASE_FV
        qv = 1 + int(math.log(ratio, cls.GROWTH))
        return max(1, min(5, qv))

    @classmethod
    def likelihood(cls, delta: float) -> float:
        """
        Interpret delta as a log-gap.

        Rough heuristic:
            - delta <= -10 → ~0
            - delta >= +10 → ~1
        """
        # squashed sigmoid in log-domain
        x = delta / 5.0
        return 1.0 / (1.0 + math.exp(-x))
