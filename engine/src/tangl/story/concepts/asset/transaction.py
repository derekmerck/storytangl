from __future__ import annotations

from tangl.core import Token
from tangl.core.bases import BaseModelPlus

from .holder import HasAssets


class AssetTransactionResult(BaseModelPlus):
    """Preflight result for an asset transaction."""

    accepted: bool
    reason: str | None = None
    asset: Token | None = None


class AssetTransactionManager:
    """Validate and perform simple asset transfers between holders."""

    def can_give_asset(
        self,
        giver: HasAssets,
        receiver: HasAssets,
        asset: Token | str,
    ) -> AssetTransactionResult:
        """Return whether a discrete asset can move from giver to receiver."""
        resolved = giver.get_asset(asset) if isinstance(asset, str) else asset
        if resolved is None or not giver.has_asset(resolved):
            return AssetTransactionResult(
                accepted=False,
                reason="giver does not hold asset",
            )
        if not giver.can_give_asset(resolved, receiver):
            return AssetTransactionResult(
                accepted=False,
                reason="giver cannot give asset",
                asset=resolved,
            )
        if not receiver.can_receive_asset(resolved, giver):
            return AssetTransactionResult(
                accepted=False,
                reason="receiver cannot receive asset",
                asset=resolved,
            )
        return AssetTransactionResult(accepted=True, asset=resolved)

    def give_asset(self, giver: HasAssets, receiver: HasAssets, asset: Token | str) -> Token:
        """Move a discrete asset after preflight succeeds."""
        result = self.can_give_asset(giver, receiver, asset)
        if not result.accepted or result.asset is None:
            raise ValueError(result.reason or "asset transaction rejected")
        moved = giver.remove_asset(result.asset)
        receiver.add_asset(moved)
        return moved

    def can_transfer_countable(
        self,
        giver: HasAssets,
        receiver: HasAssets,
        asset_label: str,
        amount: int,
    ) -> AssetTransactionResult:
        """Return whether a fungible asset count can move between wallets."""
        if amount < 0:
            return AssetTransactionResult(
                accepted=False,
                reason="amount must be non-negative",
            )
        if not giver.can_give_countable(asset_label, amount, receiver):
            return AssetTransactionResult(
                accepted=False,
                reason="giver cannot give countable asset",
            )
        if not receiver.can_receive_countable(asset_label, amount, giver):
            return AssetTransactionResult(
                accepted=False,
                reason="receiver cannot receive countable asset",
            )
        return AssetTransactionResult(accepted=True)

    def transfer_countable(
        self,
        giver: HasAssets,
        receiver: HasAssets,
        asset_label: str,
        amount: int,
    ) -> None:
        """Move a fungible asset count after preflight succeeds."""
        result = self.can_transfer_countable(giver, receiver, asset_label, amount)
        if not result.accepted:
            raise ValueError(result.reason or "asset transaction rejected")
        giver.spend_countable(asset_label, amount)
        try:
            receiver.gain_countable(asset_label, amount)
        except Exception:
            giver.gain_countable(asset_label, amount)
            raise
