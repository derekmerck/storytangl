from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field

from ..entity.has_stats import HasStats
from ..outcomes import Outcome


class GrowthReceipt(BaseModel):
    """Explicit record of stat growth computed from a resolved challenge."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    curve: str
    target_stat: str | None = None
    applied_deltas: dict[str, float] = Field(default_factory=dict)
    applied: bool = False
    challenge_pressure: float = 0.0
    outcome_weight: float = 0.0
    headroom_factor: float = 0.0


class GrowthHandler(ABC):
    """Base contract for challenge-driven stat growth."""

    BASE_GAIN: float = 0.4
    GOVERNOR_RATIO: float = 0.25

    def grow(
        self,
        entity: HasStats,
        challenge,
        result,
        *,
        apply: bool = True,
    ) -> GrowthReceipt:
        target_stat = result.domain
        if target_stat is None or target_stat not in entity.stats:
            return GrowthReceipt(curve=self.curve_name, applied=False)

        current_value = entity.stats[target_stat].fv
        challenge_pressure = self._challenge_pressure(result.delta)
        outcome_weight = self._outcome_weight(result.outcome)
        headroom_factor = self._headroom_factor(current_value)

        primary_delta = self._curve_delta(
            base_gain=self.BASE_GAIN,
            challenge_pressure=challenge_pressure,
            outcome_weight=outcome_weight,
            headroom_factor=headroom_factor,
        )

        deltas: dict[str, float] = {}
        if primary_delta > 0:
            deltas[target_stat] = primary_delta

            governor_name = entity.stat_system.intrinsic_map.get(target_stat)
            if governor_name and governor_name in entity.stats:
                deltas[governor_name] = primary_delta * self.GOVERNOR_RATIO

        if apply and deltas:
            for stat_name, delta in deltas.items():
                current = entity.stats[stat_name]
                entity.stats[stat_name] = current.__class__(current.fv + delta)

        return GrowthReceipt(
            curve=self.curve_name,
            target_stat=target_stat,
            applied_deltas=deltas,
            applied=apply and bool(deltas),
            challenge_pressure=challenge_pressure,
            outcome_weight=outcome_weight,
            headroom_factor=headroom_factor,
        )

    @property
    def curve_name(self) -> str:
        return type(self).__name__.replace("GrowthHandler", "").lower() or "growth"

    @staticmethod
    def _outcome_weight(outcome: Outcome) -> float:
        return {
            Outcome.DISASTER: 1.0,
            Outcome.FAILURE: 0.85,
            Outcome.SUCCESS: 0.6,
            Outcome.MAJOR_SUCCESS: 0.35,
        }[outcome]

    @staticmethod
    def _challenge_pressure(delta: float) -> float:
        return max(0.75, min(2.0, 0.75 + (abs(delta) / 3.0)))

    @staticmethod
    def _headroom_factor(current_value: float) -> float:
        return max(0.2, min(1.0, (20.0 - current_value) / 20.0))

    @abstractmethod
    def _curve_delta(
        self,
        *,
        base_gain: float,
        challenge_pressure: float,
        outcome_weight: float,
        headroom_factor: float,
    ) -> float:
        raise NotImplementedError


class LinearGrowthHandler(GrowthHandler):
    """Linear challenge growth."""

    def _curve_delta(
        self,
        *,
        base_gain: float,
        challenge_pressure: float,
        outcome_weight: float,
        headroom_factor: float,
    ) -> float:
        return base_gain * challenge_pressure * outcome_weight * headroom_factor


class SteppedGrowthHandler(GrowthHandler):
    """Growth quantized into quarter-step increments."""

    STEP_SIZE: float = 0.25

    def _curve_delta(
        self,
        *,
        base_gain: float,
        challenge_pressure: float,
        outcome_weight: float,
        headroom_factor: float,
    ) -> float:
        raw = base_gain * challenge_pressure * outcome_weight * headroom_factor
        steps = int(raw / self.STEP_SIZE)
        return steps * self.STEP_SIZE


class DiminishingGrowthHandler(GrowthHandler):
    """Growth curve with stronger high-end diminishing returns."""

    def _curve_delta(
        self,
        *,
        base_gain: float,
        challenge_pressure: float,
        outcome_weight: float,
        headroom_factor: float,
    ) -> float:
        return base_gain * challenge_pressure * outcome_weight * (headroom_factor**2)
