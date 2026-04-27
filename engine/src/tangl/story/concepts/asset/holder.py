from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field

from tangl.core import HasNamespace, Token, contribute_ns

from .asset_type import AssetType
from .wallet import AssetWallet


class HasAssets(HasNamespace):
    """Story concept facet for holders of fungible and discrete assets."""

    wallet: AssetWallet = Field(default_factory=AssetWallet)
    assets: dict[str, Token] = Field(default_factory=dict)

    def _asset_key(self, asset: Token, label: str | None = None) -> str:
        key = label or asset.get_label() or asset.token_from
        if not key:
            raise ValueError("Held asset requires a label")
        return key

    def add_asset(self, asset: Token, *, label: str | None = None) -> None:
        """Add a discrete asset token to this holder."""
        if not asset.has_kind(AssetType):
            raise TypeError("Held asset must be a Token wrapping an AssetType")
        self.assets[self._asset_key(asset, label)] = asset

    def get_asset(self, label: str) -> Token | None:
        """Return a held asset by holder key, token label, or token reference."""
        if label in self.assets:
            return self.assets[label]
        for asset in self.assets.values():
            if label == asset.get_label() or label == asset.token_from:
                return asset
        return None

    def has_asset(self, asset: Token | str) -> bool:
        """Return whether this holder currently has the asset."""
        if isinstance(asset, str):
            return self.get_asset(asset) is not None
        return any(item is asset for item in self.assets.values())

    def remove_asset(self, asset: Token | str) -> Token:
        """Remove and return a held discrete asset."""
        if isinstance(asset, str):
            resolved = self.get_asset(asset)
            if resolved is None:
                raise KeyError(asset)
            asset = resolved
        for label, item in list(self.assets.items()):
            if item is asset:
                return self.assets.pop(label)
        raise KeyError(asset.get_label() or asset.token_from)

    def can_give_asset(self, asset: Token, receiver: "HasAssets | None" = None) -> bool:
        """Return whether this holder is willing and able to give a discrete asset."""
        _ = receiver
        return self.has_asset(asset)

    def can_receive_asset(self, asset: Token, giver: "HasAssets | None" = None) -> bool:
        """Return whether this holder is willing and able to receive a discrete asset."""
        _ = (asset, giver)
        return True

    def can_give_countable(
        self,
        asset_label: str,
        amount: int,
        receiver: "HasAssets | None" = None,
    ) -> bool:
        """Return whether this holder can give a fungible asset count."""
        _ = receiver
        return self.wallet.can_afford({asset_label: amount})

    def can_receive_countable(
        self,
        asset_label: str,
        amount: int,
        giver: "HasAssets | None" = None,
    ) -> bool:
        """Return whether this holder can receive a fungible asset count."""
        _ = (asset_label, amount, giver)
        return amount >= 0

    @contribute_ns
    def provide_asset_symbols(self) -> Mapping[str, object]:
        """Publish held assets and wallet state into the local namespace."""
        inventory = dict(self.assets)
        return {
            "asset_holder": self,
            "asset_wallet": self.wallet,
            "assets": inventory,
            "inv": inventory,
            "wallet": self.wallet,
        }
