from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CircularDominance:
    """
    Helper for generating "rock-paper-scissors" style dominance matrices.

    Items are arranged in a circle. For each offset k in `pattern`:
        pattern[k] = m  implies:
            item[i] dominates item[(i + k) mod n] by +m
            and item[(i + k) mod n] is dominated by item[i] by -m.

    Self-dominance is always 0.0.
    """

    @staticmethod
    def generate(items: Iterable[str], pattern: Dict[int, float]) -> Dict[str, Dict[str, float]]:
        names: List[str] = list(items)
        n = len(names)
        if n == 0:
            return {}

        matrix: Dict[str, Dict[str, float]] = {name: {} for name in names}

        for name in names:
            matrix[name][name] = 0.0

        for i, attacker in enumerate(names):
            for offset, magnitude in pattern.items():
                if offset <= 0 or offset >= n:
                    continue

                j = (i + offset) % n
                defender = names[j]

                if defender in matrix[attacker]:
                    continue

                matrix[attacker][defender] = magnitude
                matrix[defender][attacker] = -magnitude

        return matrix
