from __future__ import annotations

from typing import Dict, Mapping

from pydantic import BaseModel, ConfigDict

from ..definition.stat_system import StatSystemDefinition


class HasWallet(BaseModel):
    """
    Mixin/base for entities that track currencies.

    Attributes
    ----------
    wallet:
        Mapping from currency name (e.g., "stamina", "credits") to integer amount.

    Notes
    -----
    - Does not know about tasks; it's just a thin accounting helper.
    """

    model_config = ConfigDict(extra="allow")

    wallet: Dict[str, int]

    # ------------------------------------------------------------------ #
    # Constructors
    # ------------------------------------------------------------------ #

    @classmethod
    def from_system(
        cls,
        stat_system: StatSystemDefinition,
        *,
        base_amount: int = 0,
        overrides: Mapping[str, int] | None = None,
        **extra,
    ) -> "HasWallet":
        """
        Construct a wallet based on currencies defined in a StatSystemDefinition.

        Parameters
        ----------
        stat_system:
            Source of `currencies`.
        base_amount:
            Default amount for each currency.
        overrides:
            Mapping of currency -> starting amount.
        extra:
            Extra fields for subclasses.
        """
        overrides = overrides or {}
        wallet: Dict[str, int] = {}
        for currency in stat_system.currencies:
            wallet[currency] = overrides.get(currency, base_amount)
        return cls(wallet=wallet, **extra)

    # ------------------------------------------------------------------ #
    # Accounting helpers
    # ------------------------------------------------------------------ #

    def can_afford(self, cost: Mapping[str, int]) -> bool:
        """Return True if the wallet can pay the given cost mapping."""
        for currency, amount in cost.items():
            if amount <= 0:
                continue
            if self.wallet.get(currency, 0) < amount:
                return False
        return True

    def spend(self, cost: Mapping[str, int]) -> None:
        """
        Deduct cost from the wallet in-place.

        Raises
        ------
        ValueError
            If the wallet cannot afford the cost.
        """
        if not self.can_afford(cost):
            raise ValueError(f"Insufficient funds for cost: {dict(cost)!r}")

        for currency, amount in cost.items():
            if amount <= 0:
                continue
            self.wallet[currency] = self.wallet.get(currency, 0) - amount

    def earn(self, reward: Mapping[str, int]) -> None:
        """Add reward amounts to the wallet in-place."""
        for currency, amount in reward.items():
            if amount == 0:
                continue
            self.wallet[currency] = self.wallet.get(currency, 0) + amount
