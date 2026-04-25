from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..effects import SituationalEffect
from ..growth import GrowthReceipt
from ..measures import Quality
from ..outcomes import Outcome
from ..projection import (
    project_outcome_label,
    project_payout_label,
    project_payout_quality,
    project_quality,
    project_quality_label,
)


class ChallengeResult(BaseModel):
    """Structured output for one resolved stat challenge."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    challenge_name: str | None = None
    domain: str | None = None

    effective_competency: float
    effective_difficulty: float
    delta: float
    success_likelihood: float

    outcome: Outcome
    cost_paid: dict[str, int] = Field(default_factory=dict)
    payout_granted: dict[str, int] = Field(default_factory=dict)
    active_effects: list[SituationalEffect] = Field(default_factory=list)
    growth_receipt: GrowthReceipt | None = None

    @property
    def competency_quality(self) -> Quality:
        return project_quality(self.effective_competency)

    @property
    def difficulty_quality(self) -> Quality:
        return project_quality(self.effective_difficulty)

    @property
    def competency_label(self) -> str:
        return project_quality_label(self.effective_competency)

    @property
    def difficulty_label(self) -> str:
        return project_quality_label(self.effective_difficulty)

    @property
    def outcome_label(self) -> str:
        return project_outcome_label(self.outcome)

    @property
    def payout_quality(self) -> Quality | None:
        return project_payout_quality(self.payout_granted)

    @property
    def payout_label(self) -> str:
        return project_payout_label(self.payout_granted)
