from __future__ import annotations

from collections.abc import Mapping
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..entity.has_stats import HasStats
from ..handlers import StatHandler
from ..stats.stat import Stat, ValueLike
from ..tasks.task import Task
from ..outcomes import Outcome


class StatRequirement(BaseModel):
    """Minimum and optional maximum thresholds for a broad stat gate."""

    model_config = ConfigDict(frozen=True)

    minimum: ValueLike | None = None
    maximum: ValueLike | None = None

    def is_satisfied(
        self,
        value: float,
        *,
        handler: type[StatHandler],
    ) -> bool:
        if self.minimum is not None:
            minimum_fv = Stat.normalize_value(self.minimum, handler=handler)
            if value < minimum_fv:
                return False

        if self.maximum is not None:
            maximum_fv = Stat.normalize_value(self.maximum, handler=handler)
            if value > maximum_fv:
                return False

        return True


class ChallengePayout(BaseModel):
    """Outcome-conditioned wallet deltas for a resolved challenge."""

    model_config = ConfigDict(frozen=True)

    by_outcome: dict[Outcome, dict[str, int]] = Field(default_factory=dict)

    @field_validator("by_outcome", mode="before")
    @classmethod
    def _normalize_outcome_keys(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value

        normalized: dict[Outcome, dict[str, int]] = {}
        for key, reward in value.items():
            if isinstance(key, Outcome):
                outcome = key
            elif isinstance(key, str):
                outcome = Outcome[key.strip().upper()]
            else:
                outcome = Outcome(int(key))
            normalized[outcome] = dict(reward)
        return normalized

    def reward_for(self, outcome: Outcome) -> dict[str, int]:
        """Return the wallet delta associated with a specific outcome."""
        reward = self.by_outcome.get(outcome)
        if reward is not None:
            return dict(reward)

        if outcome is Outcome.MAJOR_SUCCESS:
            fallback = self.by_outcome.get(Outcome.SUCCESS)
            if fallback is not None:
                return dict(fallback)

        return {}


DifficultySpec = ValueLike | dict[str, ValueLike]


class StatChallenge(BaseModel):
    """Authored one-shot stat challenge built on top of a low-level Task."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Optional[str] = None
    domain: Optional[str] = None
    difficulty: DifficultySpec = 10.0
    cost: dict[str, int] = Field(default_factory=dict)
    payout: ChallengePayout = Field(default_factory=ChallengePayout)
    tags: set[str] = Field(default_factory=set)
    requirements: dict[str, StatRequirement] = Field(default_factory=dict)
    opposed_domain: Optional[str] = None

    @field_validator("payout", mode="before")
    @classmethod
    def _coerce_payout(cls, value: object) -> object:
        if isinstance(value, ChallengePayout):
            return value
        if isinstance(value, Mapping):
            return ChallengePayout(by_outcome=dict(value))
        return value

    @field_validator("requirements", mode="before")
    @classmethod
    def _coerce_requirements(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value

        normalized: dict[str, StatRequirement] = {}
        for stat_name, requirement in value.items():
            if isinstance(requirement, StatRequirement):
                normalized[stat_name] = requirement
            elif isinstance(requirement, Mapping):
                normalized[stat_name] = StatRequirement(**dict(requirement))
            else:
                normalized[stat_name] = StatRequirement(minimum=requirement)
        return normalized

    def normalized_difficulty(
        self,
        *,
        handler: type[StatHandler],
        domain: str | None = None,
    ) -> dict[str, float]:
        """Return the challenge difficulty in fv space."""
        if isinstance(self.difficulty, Mapping):
            return {
                stat_name: Stat.normalize_value(value, handler=handler)
                for stat_name, value in self.difficulty.items()
            }

        resolved_domain = self.domain if self.domain is not None else domain
        if resolved_domain is None:
            return {}

        return {resolved_domain: Stat.normalize_value(self.difficulty, handler=handler)}

    def unmet_requirements(
        self,
        entity: HasStats,
        *,
        handler: type[StatHandler],
    ) -> dict[str, StatRequirement]:
        """Return any stat-based gating requirements that are not satisfied."""
        unmet: dict[str, StatRequirement] = {}
        for stat_name, requirement in self.requirements.items():
            stat = entity.stats.get(stat_name)
            if stat is None or not requirement.is_satisfied(stat.fv, handler=handler):
                unmet[stat_name] = requirement
        return unmet

    def to_task(
        self,
        *,
        handler: type[StatHandler],
        domain: str | None = None,
        difficulty: dict[str, float] | None = None,
        cost: Mapping[str, int] | None = None,
        tags: set[str] | None = None,
    ) -> Task:
        """Compile this challenge to a low-level task."""
        resolved_domain = domain if domain is not None else self.domain
        resolved_difficulty = (
            difficulty
            if difficulty is not None
            else self.normalized_difficulty(handler=handler, domain=domain)
        )
        resolved_cost = cost if cost is not None else self.cost
        resolved_tags = tags if tags is not None else self.tags
        return Task(
            name=self.name,
            domain=resolved_domain,
            difficulty=resolved_difficulty,
            cost=dict(resolved_cost),
            reward={},
            tags=set(resolved_tags),
        )
