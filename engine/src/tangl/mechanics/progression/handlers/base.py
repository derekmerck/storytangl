from __future__ import annotations

from abc import ABC, abstractmethod

from ..measures import Quality


class StatHandler(ABC):
    """
    Abstract handler for stat conversions and probability.

    Responsibilities:
        - Map continuous fv (float value) ↔ discrete qv (1–5 tier).
        - Convert delta = competency - difficulty into p_success.
    """

    # Optional: subclasses can override to tune global clamp, etc.
    MODIFIER_CLAMP: float = 2.5

    @classmethod
    @abstractmethod
    def qv_from_fv(cls, fv: float) -> int:
        """Convert continuous value to quantized tier in [1, 5]."""

    @classmethod
    @abstractmethod
    def fv_from_qv(cls, qv: int) -> float:
        """Convert quantized tier (1–5) to a representative continuous value."""

    @classmethod
    @abstractmethod
    def likelihood(cls, delta: float) -> float:
        """
        Probability of success given delta = competency - difficulty.

        Returns:
            float in [0, 1].
        """

    # Convenience helpers:

    @classmethod
    def quality_from_fv(cls, fv: float) -> Quality:
        """Convert fv to a Quality enum."""
        return Quality(cls.qv_from_fv(fv))

    @classmethod
    def clamp_modifiers(cls, total: float) -> float:
        """Clamp aggregated modifiers to ±MODIFIER_CLAMP."""
        cap = cls.MODIFIER_CLAMP
        return max(-cap, min(cap, total))
