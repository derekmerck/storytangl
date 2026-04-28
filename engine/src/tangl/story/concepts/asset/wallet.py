from __future__ import annotations

from collections.abc import ItemsView, Mapping

from pydantic import Field

from tangl.core.bases import BaseModelPlus

from .asset_type import CountableAsset


class AssetWallet(BaseModelPlus):
    """Small counter for fungible story assets."""

    amounts: dict[str, int] = Field(default_factory=dict)

    def __contains__(self, label: str) -> bool:
        return self.amounts.get(label, 0) > 0

    def __getitem__(self, label: str) -> int:
        return self.amounts.get(label, 0)

    def __len__(self) -> int:
        return len(self.amounts)

    def items(self) -> ItemsView[str, int]:
        return self.amounts.items()

    def gain(self, assets: Mapping[str, int] | None = None, **kwargs: int) -> None:
        """Add positive asset counts to the wallet."""
        deltas = dict(assets or {}) | kwargs
        for label, amount in deltas.items():
            if amount < 0:
                raise ValueError(f"Cannot gain negative amount for {label}")
        for label, amount in deltas.items():
            if amount == 0:
                continue
            self.amounts[label] = self.amounts.get(label, 0) + amount

    def can_afford(self, assets: Mapping[str, int] | None = None, **kwargs: int) -> bool:
        """Return whether the wallet has at least the requested counts."""
        cost = dict(assets or {}) | kwargs
        return all(
            amount >= 0 and self.amounts.get(label, 0) >= amount
            for label, amount in cost.items()
        )

    def spend(self, assets: Mapping[str, int] | None = None, **kwargs: int) -> None:
        """Deduct asset counts, raising without mutation if any count is short."""
        cost = dict(assets or {}) | kwargs
        negative = [
            label
            for label, amount in cost.items()
            if amount < 0
        ]
        if negative:
            raise ValueError(f"Cannot spend negative amount for: {', '.join(sorted(negative))}")
        missing = [
            label
            for label, amount in cost.items()
            if self.amounts.get(label, 0) < amount
        ]
        if missing:
            raise ValueError(f"Insufficient assets: {', '.join(sorted(missing))}")
        for label, amount in cost.items():
            next_amount = self.amounts.get(label, 0) - amount
            if next_amount:
                self.amounts[label] = next_amount
            else:
                self.amounts.pop(label, None)

    def total_value(self, asset_types: Mapping[str, CountableAsset] | None = None) -> float:
        """Return aggregate value for known countable asset definitions."""
        known = (
            asset_types
            if asset_types is not None
            else {
                asset.label: asset
                for asset in CountableAsset.all_instances()
            }
        )
        return sum(
            amount * known[label].value
            for label, amount in self.amounts.items()
            if label in known
        )

    def describe(self) -> str:
        """Render a compact human-facing wallet summary."""
        if not self.amounts:
            return "empty"
        parts = [
            f"{amount} {label}"
            for label, amount in sorted(
                self.amounts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]
        return ", ".join(parts)
