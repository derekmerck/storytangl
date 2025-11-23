from __future__ import annotations

import math

from .base import StatHandler


class ProbitStatHandler(StatHandler):
    """
    Normal-distribution handler N(10, 3).

    Conventions:
        - fv is roughly in [1, 20], centered around 10.
        - Tiers (qv) are spaced by ~1 std dev in fv space:
            qv=1: z < -1.5
            qv=2: -1.5 ≤ z < -0.5
            qv=3: -0.5 ≤ z < 0.5
            qv=4: 0.5 ≤ z < 1.5
            qv=5: z ≥ 1.5
        Where z = (fv - MU) / SIGMA.
    """

    MU: float = 10.0
    SIGMA: float = 3.0

    @classmethod
    def qv_from_fv(cls, fv: float) -> int:
        z = (fv - cls.MU) / cls.SIGMA
        if z < -1.5:
            return 1
        if z < -0.5:
            return 2
        if z < 0.5:
            return 3
        if z < 1.5:
            return 4
        return 5

    @classmethod
    def fv_from_qv(cls, qv: int) -> float:
        if not 1 <= qv <= 5:
            raise ValueError(f"qv must be in [1, 5], got {qv!r}")
        z_map = {1: -2.0, 2: -1.0, 3: 0.0, 4: 1.0, 5: 2.0}
        z = z_map[qv]
        return cls.MU + z * cls.SIGMA

    @classmethod
    def likelihood(cls, delta: float) -> float:
        """
        Interpret delta in fv units, scaled by SIGMA.

        We treat success probability as Φ(delta / SIGMA),
        where Φ is the standard normal CDF.
        """
        z = delta / cls.SIGMA
        return cls._norm_cdf(z)

    @staticmethod
    def _norm_cdf(z: float) -> float:
        """Standard normal CDF using erf."""
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
