from __future__ import annotations

from collections.abc import ItemsView, Mapping
from typing import Self
from uuid import UUID

from pydantic import Field

from tangl.core.bases import Unstructurable
from tangl.core.singleton import Singleton

from .asset_type import CountableAsset

AssetKey = str | Singleton


class AssetWallet(Unstructurable):
    """Count named pools and singleton-defined fungible assets independently."""

    amounts: dict[AssetKey, int] = Field(default_factory=dict)

    def __contains__(self, asset: AssetKey) -> bool:
        return self.has_asset(asset)

    def __getitem__(self, asset: AssetKey) -> int:
        return self.amounts.get(asset, 0)

    def __len__(self) -> int:
        return len(self.amounts)

    def items(self) -> ItemsView[AssetKey, int]:
        return self.amounts.items()

    def has_asset(self, asset: AssetKey, count: int = 1) -> bool:
        return type(count) is int and count >= 0 and self[asset] >= count

    def can_add_asset(self, asset: AssetKey, count: int = 1) -> bool:
        return type(count) is int and count >= 0

    def can_remove_asset(self, asset: AssetKey, count: int = 1) -> bool:
        return self.has_asset(asset, count)

    def add_asset(self, asset: AssetKey, count: int = 1) -> None:
        self.gain({asset: count})

    def remove_asset(self, asset: AssetKey, count: int = 1) -> None:
        self.spend({asset: count})

    def gain(self, assets: Mapping[AssetKey, int] | None = None, **kwargs: int) -> None:
        """Add counts atomically after checking every entry."""
        deltas = dict(assets or {}) | kwargs
        for asset, amount in deltas.items():
            if type(amount) is not int or amount < 0 or not self.can_add_asset(asset, amount):
                raise ValueError(f"Cannot gain negative amount or refused asset: {asset!r}")
        for asset, amount in deltas.items():
            if amount:
                self.amounts[asset] = self[asset] + amount

    def can_afford(self, assets: Mapping[AssetKey, int] | None = None, **kwargs: int) -> bool:
        cost = dict(assets or {}) | kwargs
        return all(
            self.has_asset(asset, amount) and self.can_remove_asset(asset, amount)
            for asset, amount in cost.items()
        )

    def spend(self, assets: Mapping[AssetKey, int] | None = None, **kwargs: int) -> None:
        """Deduct counts atomically after checking every entry."""
        cost = dict(assets or {}) | kwargs
        for asset, amount in cost.items():
            if type(amount) is not int or amount < 0:
                raise ValueError(f"Cannot spend negative amount or invalid count: {asset!r}")
            if not self.has_asset(asset, amount) or not self.can_remove_asset(asset, amount):
                raise ValueError(f"Insufficient assets or refused removal: {asset!r}")
        for asset, amount in cost.items():
            next_amount = self[asset] - amount
            if next_amount:
                self.amounts[asset] = next_amount
            else:
                self.amounts.pop(asset, None)

    def unstructure(self) -> dict:
        def sort_key(asset: AssetKey) -> tuple[str, str, str]:
            if isinstance(asset, str):
                return ("string", "", asset)
            kind = f"{type(asset).__module__}.{type(asset).__qualname__}"
            return ("singleton", kind, asset.label)

        return {
            "kind": type(self),
            "entries": [
                {"asset": asset if isinstance(asset, str) else asset.unstructure(), "count": count}
                for asset, count in sorted(
                    self.amounts.items(), key=lambda entry: sort_key(entry[0])
                )
            ],
        }

    @classmethod
    def structure(cls, data: dict, _ctx=None) -> Self:
        amounts: dict[AssetKey, int] = {}
        for entry in data["entries"]:
            asset = entry["asset"]
            if isinstance(asset, dict):
                reference = dict(asset)
                reference["label"] = str(reference["label"])
                asset = Singleton.structure(reference)
                if asset is None:
                    raise LookupError(f"Unregistered wallet asset: {entry['asset']!r}")
            elif isinstance(asset, UUID):
                asset = str(asset)
            amounts[asset] = entry["count"]
        return cls(amounts=amounts)

    def total_value(self, asset_types: Mapping[str, CountableAsset] | None = None) -> float:
        """Return aggregate value for singleton keys and known named definitions."""
        known = asset_types if asset_types is not None else {
            asset.label: asset for asset in CountableAsset.all_instances()
        }
        return sum(
            amount * (asset.value if isinstance(asset, CountableAsset) else known[asset].value)
            for asset, amount in self.amounts.items()
            if isinstance(asset, CountableAsset) or (isinstance(asset, str) and asset in known)
        )

    def describe(self) -> str:
        if not self.amounts:
            return "empty"
        parts = [
            (asset if isinstance(asset, str) else asset.label, count)
            for asset, count in self.amounts.items()
        ]
        return ", ".join(
            f"{count} {label}" for label, count in sorted(parts, key=lambda x: (-x[1], x[0]))
        )
