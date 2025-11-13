"""Wallet utilities for countable assets."""

from __future__ import annotations

from collections import Counter
from typing import Optional

from .countable_asset import CountableAsset


class AssetWallet(Counter[str]):
    """Counter-backed store for countable assets.

    Why
    ====
    Keep fungible asset tracking lightweight without creating graph nodes.

    Key Features
    ============
    - Maintains quantities keyed by asset label.
    - Provides ergonomic helpers for gain/spend flows.
    - Computes aggregate value with supplied asset definitions.
    """

    def gain(self, **amounts: float) -> None:
        """Add assets to the wallet."""
        for label, amount in amounts.items():
            if amount < 0:
                raise ValueError(f"Cannot gain negative amount: {label}={amount}")
            self[label] += amount

    def can_afford(self, **amounts: float) -> bool:
        """Return ``True`` if the wallet satisfies every requested amount."""
        for label, required in amounts.items():
            if self[label] < required:
                return False
        return True

    def spend(self, **amounts: float) -> None:
        """Remove assets after validating balances."""
        if not self.can_afford(**amounts):
            shortage = {
                label: required - self[label]
                for label, required in amounts.items()
                if self[label] < required
            }
            raise ValueError(
                f"Insufficient assets. Short: {shortage}, Have: {dict(self)}"
            )

        for label, amount in amounts.items():
            self[label] -= amount
            if self[label] <= 0:
                del self[label]

    def total_value(self, asset_types: dict[str, CountableAsset]) -> float:
        """Return total value using provided asset definitions."""
        total = 0.0
        for label, count in self.items():
            if label in asset_types:
                total += asset_types[label].value * count
        return total

    def describe(self) -> str:
        """Return a concise textual description of holdings."""
        if not self:
            return "empty"

        items = sorted(self.items(), key=lambda item: -item[1])
        parts = [f"{count:.0f} {label}" for label, count in items if count > 0]
        return ", ".join(parts)


class HasAssetWallet:
    """Mixin providing a lazily-initialised :class:`AssetWallet`."""

    _wallet: Optional[AssetWallet] = None

    @property
    def wallet(self) -> AssetWallet:
        """Return the wallet, creating it on first access."""
        if self._wallet is None:
            self._wallet = AssetWallet()
        return self._wallet
