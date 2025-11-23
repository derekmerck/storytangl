from __future__ import annotations

from typing import Dict, Mapping, Optional, Set

from pydantic import BaseModel, ConfigDict, Field

from ..definition.stat_system import StatSystemDefinition


class Task(BaseModel):
    """
    A challenge / check to be resolved against an entity's stats.

    Fields
    ------
    name:
        Optional label for debugging/UI.
    domain:
        Preferred primary domain to test (e.g. "body", "sword").
        If None, resolution will:
            1) look at `difficulty` keys,
            2) fall back to the stat system's default_domain,
            3) fall back to None (average intrinsic competency).
    difficulty:
        Mapping from domain_name → target value in fv space.
        Typically 8–14 for Probit-style systems.
    cost:
        Optional currency cost: currency_name → amount.
    reward:
        Optional currency reward: currency_name → amount.
    tags:
        Scenario tags used to match situational effects, e.g. {"#combat"}.
    """

    model_config = ConfigDict(frozen=True)

    name: Optional[str] = None
    domain: Optional[str] = None

    difficulty: Dict[str, float] = Field(default_factory=dict)
    cost: Dict[str, int] = Field(default_factory=dict)
    reward: Dict[str, int] = Field(default_factory=dict)

    tags: Set[str] = Field(default_factory=set)

    # ------------------------------------------------------------------ #
    # Difficulty helpers
    # ------------------------------------------------------------------ #

    def infer_domain(self, system: Optional[StatSystemDefinition] = None) -> Optional[str]:
        """
        Determine the primary domain for this task.

        Priority:
            1. self.domain if set
            2. first key in difficulty mapping if present
            3. system.default_domain if provided
            4. None
        """
        if self.domain is not None:
            return self.domain
        if self.difficulty:
            return next(iter(self.difficulty.keys()))
        if system is not None:
            return system.default_domain
        return None

    def get_difficulty(
        self,
        *,
        domain: Optional[str],
        system: Optional[StatSystemDefinition] = None,
    ) -> float:
        """
        Get effective difficulty for a given domain.

        Rules
        -----
        - If `domain` is not None and present in `difficulty`, use that.
        - Else, if `difficulty` has entries, use their average.
        - Else, return 10.0 (neutral).
        """
        if domain is not None and domain in self.difficulty:
            return self.difficulty[domain]

        if self.difficulty:
            values = list(self.difficulty.values())
            return sum(values) / len(values)

        return 10.0

    # ------------------------------------------------------------------ #
    # Currency helpers
    # ------------------------------------------------------------------ #

    def can_afford(self, wallet: Mapping[str, int]) -> bool:
        """
        Return True if the wallet can pay `cost`.

        Zero or negative costs are considered trivially affordable.
        """
        for currency, amount in self.cost.items():
            if amount <= 0:
                continue
            if wallet.get(currency, 0) < amount:
                return False
        return True

    def apply_cost(self, wallet: Mapping[str, int]) -> Dict[str, int]:
        """
        Return a *new* wallet mapping with cost deducted.

        Raises
        ------
        ValueError
            If `wallet` cannot afford the cost.
        """
        if not self.can_afford(wallet):
            raise ValueError(f"Insufficient funds for task cost: {self.cost!r}")

        new_wallet: Dict[str, int] = dict(wallet)
        for currency, amount in self.cost.items():
            if amount <= 0:
                continue
            new_wallet[currency] = new_wallet.get(currency, 0) - amount
        return new_wallet

    def apply_reward(self, wallet: Mapping[str, int]) -> Dict[str, int]:
        """
        Return a *new* wallet mapping with reward added.
        """
        new_wallet: Dict[str, int] = dict(wallet)
        for currency, amount in self.reward.items():
            if amount == 0:
                continue
            new_wallet[currency] = new_wallet.get(currency, 0) + amount
        return new_wallet
