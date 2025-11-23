from __future__ import annotations

import logging
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .stat_def import StatDef

logger = logging.getLogger(__name__)


class StatSystemDefinition(BaseModel):
    """
    Complete stat schema for a world.

    Contains:
        - a collection of StatDef entries,
        - optional dominance matrix,
        - optional context-specific bonuses.

    This layer is **pure configuration**: no dependency on Stat,
    handlers, or the VM.
    """

    model_config = ConfigDict(frozen=True)

    name: str = "custom"
    theme: str = "generic"
    complexity: int = 5
    handler: str = "probit"

    stats: List[StatDef] = Field(default_factory=list)
    dominance_matrix: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    context_bonuses: Dict[str, Dict[str, float]] = Field(default_factory=dict)

    @property
    def stat_names(self) -> List[str]:
        return [s.name for s in self.stats]

    @property
    def intrinsics(self) -> List[StatDef]:
        return [s for s in self.stats if s.is_intrinsic]

    @property
    def domains(self) -> List[StatDef]:
        return [s for s in self.stats if not s.is_intrinsic]

    @property
    def currencies(self) -> List[str]:
        return [s.currency_name for s in self.stats if s.currency_name]

    @property
    def intrinsic_map(self) -> Dict[str, str]:
        return {s.name: s.governed_by for s in self.stats if s.governed_by}

    @property
    def default_domain(self) -> Optional[str]:
        if self.domains:
            return self.domains[0].name
        if self.intrinsics:
            return self.intrinsics[0].name
        return None

    def get_stat(self, name: str) -> Optional[StatDef]:
        for stat in self.stats:
            if stat.name == name:
                return stat
        return None

    def get_dominance(self, attacker_domain: str, defender_domain: str) -> float:
        return self.dominance_matrix.get(attacker_domain, {}).get(defender_domain, 0.0)

    def get_context_bonus(self, context: str, stat_name: str) -> float:
        return self.context_bonuses.get(context, {}).get(stat_name, 0.0)

    @field_validator("dominance_matrix")
    @classmethod
    def _warn_if_unbalanced(cls, value: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        if not value:
            return value

        for attacker, row in value.items():
            for defender, mag_ab in row.items():
                if attacker == defender:
                    continue
                mag_ba = value.get(defender, {}).get(attacker)
                if mag_ba is None:
                    continue
                if abs(mag_ab + mag_ba) > 1e-3:
                    logger.warning(
                        "Dominance not antisymmetric: %s→%s=%s, %s→%s=%s",
                        attacker,
                        defender,
                        mag_ab,
                        defender,
                        attacker,
                        mag_ba,
                    )

        totals = {name: sum(row.values()) for name, row in value.items()}
        if totals:
            max_imbalance = max(abs(total) for total in totals.values())
            if max_imbalance > 0.1:
                logger.warning("Dominance may be unbalanced: %s", totals)

        return value

    @model_validator(mode="after")
    def _check_intrinsic_governance(self) -> StatSystemDefinition:  # type: ignore[name-defined]
        intrinsic_names = {s.name for s in self.stats if s.is_intrinsic}

        for stat in self.stats:
            if stat.governed_by and stat.governed_by not in intrinsic_names:
                logger.warning(
                    "Stat %r governed_by %r which is not an intrinsic in this system",
                    stat.name,
                    stat.governed_by,
                )

        return self
