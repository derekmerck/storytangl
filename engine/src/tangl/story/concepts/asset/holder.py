from __future__ import annotations

from collections.abc import Iterator, Mapping
from uuid import UUID

from pydantic import Field, PrivateAttr

from tangl.core import Graph, GraphItem, HasNamespace, Selector, Singleton, Token, contribute_ns
from tangl.story.story_graph import StoryGraph

from .discrete_wallet import DiscreteAssetWallet
from .wallet import AssetKey, AssetWallet


class HasFungibleAssets(HasNamespace):
    """Independent counted holdings for singleton definitions or named pools."""

    wallet: AssetWallet = Field(
        default_factory=AssetWallet,
        json_schema_extra={"include": True, "unstructurable": True},
    )

    def has_asset(self, asset: Singleton, count: int = 1) -> bool:
        return self.wallet.has_asset(asset, count)

    def can_add_asset(self, asset: Singleton, count: int = 1) -> bool:
        return self.wallet.can_add_asset(asset, count)

    def can_remove_asset(self, asset: Singleton, count: int = 1) -> bool:
        return self.wallet.can_remove_asset(asset, count)

    def add_asset(self, asset: Singleton, count: int = 1) -> None:
        self.wallet.add_asset(asset, count)

    def remove_asset(self, asset: Singleton, count: int = 1) -> None:
        self.wallet.remove_asset(asset, count)

    def can_give_countable(self, asset_label: AssetKey, amount: int,
                           receiver: HasFungibleAssets | None = None) -> bool:
        return self.wallet.can_remove_asset(asset_label, amount)

    def can_receive_countable(self, asset_label: AssetKey, amount: int,
                              giver: HasFungibleAssets | None = None) -> bool:
        return self.wallet.can_add_asset(asset_label, amount)

    def spend_countable(self, asset_label: AssetKey, amount: int) -> None:
        self.wallet.remove_asset(asset_label, amount)

    def gain_countable(self, asset_label: AssetKey, amount: int) -> None:
        self.wallet.add_asset(asset_label, amount)

    @contribute_ns
    def provide_fungible_symbols(self) -> Mapping[str, object]:
        return {"asset_holder": self, "asset_wallet": self.wallet, "wallet": self.wallet}


class HasDiscreteAssets(HasNamespace):
    """Graph-owned membership with explicitly bound embedded holders."""

    discrete_wallet_id: UUID | None = None
    asset_aliases: dict[str, UUID] = Field(default_factory=dict, json_schema_extra={"include": True})
    _asset_owner: GraphItem | None = PrivateAttr(default=None)

    def bind_asset_owner(self, owner: GraphItem) -> None:
        if self._asset_owner is not None and self._asset_owner is not owner:
            raise ValueError("Asset holder is already bound to another owner")
        self._asset_owner = owner

    def _asset_graph(self) -> Graph:
        owner = self if isinstance(self, GraphItem) else self._asset_owner
        if owner is None or owner.graph is None:
            raise ValueError("Asset holder requires a bound graph owner")
        return owner.graph

    @property
    def discrete_wallet(self) -> DiscreteAssetWallet | None:
        if self.discrete_wallet_id is None:
            return None
        wallet = self._asset_graph().get(self.discrete_wallet_id)
        if not isinstance(wallet, DiscreteAssetWallet):
            raise ValueError("Asset holder wallet is missing from its graph")
        return wallet

    def member_sources(self, selector: Selector | None = None) -> Iterator[GraphItem]:
        wallet = self.discrete_wallet
        return wallet.members(selector) if wallet is not None else iter(())

    @property
    def assets(self) -> dict[str, GraphItem]:
        result = {}
        for member in self.member_sources():
            key = next((label for label, uid in self.asset_aliases.items() if uid == member.uid), None)
            key = key or member.get_label()
            if not key and isinstance(member, Token):
                key = member.token_from
            if not key:
                raise ValueError("Held asset requires a label")
            result[key] = member
        return result

    def get_asset(self, label: str) -> GraphItem | None:
        inventory = self.assets
        if label in inventory:
            return inventory[label]
        return next((item for item in inventory.values()
                     if item.get_label() == label or
                     (isinstance(item, Token) and item.token_from == label)), None)

    def get_asset_key(self, asset: GraphItem | str) -> str | None:
        resolved = self.get_asset(asset) if isinstance(asset, str) else asset
        return next((label for label, item in self.assets.items() if item is resolved), None)

    def has_asset(self, asset: GraphItem | str) -> bool:
        if isinstance(asset, str):
            return self.get_asset(asset) is not None
        wallet = self.discrete_wallet
        return wallet is not None and wallet.has_asset(asset)

    def can_add_asset(self, asset: GraphItem, *, label: str | None = None) -> bool:
        owner = self if isinstance(self, GraphItem) else self._asset_owner
        if owner is None or owner.graph is None:
            return False
        graph = owner.graph
        key = label or asset.get_label() or (asset.token_from if isinstance(asset, Token) else None)
        if not key or self.get_asset(key) is not None:
            return False
        wallet = self.discrete_wallet
        if wallet is None and isinstance(graph, StoryGraph) and graph.frozen_shape:
            return False
        return wallet.can_add_asset(asset) if wallet is not None else (
            asset.registry is graph and graph.get(asset.uid) is asset
        )

    def can_remove_asset(self, asset: GraphItem | str) -> bool:
        return self.has_asset(asset)

    def prepare_discrete_wallet(self) -> DiscreteAssetWallet:
        """Create the wallet during accepted setup or materialization."""
        wallet = self.discrete_wallet
        if wallet is None:
            wallet = self._asset_graph().add_subgraph(kind=DiscreteAssetWallet)
            self.discrete_wallet_id = wallet.uid
        return wallet

    def add_asset(self, asset: GraphItem, *, label: str | None = None) -> None:
        if not self.can_add_asset(asset, label=label):
            raise ValueError("Cannot add asset to holder")
        wallet = self.prepare_discrete_wallet()
        wallet.add_asset(asset)
        if label is not None and label != asset.get_label():
            self.asset_aliases[label] = asset.uid

    def remove_asset(self, asset: GraphItem | str) -> GraphItem:
        resolved = self.get_asset(asset) if isinstance(asset, str) else asset
        if resolved is None or not self.can_remove_asset(resolved):
            raise KeyError(f"Unknown asset: {asset!r}")
        self.discrete_wallet.remove_asset(resolved)
        for label, uid in list(self.asset_aliases.items()):
            if uid == resolved.uid:
                del self.asset_aliases[label]
        return resolved

    def can_give_asset(self, asset: GraphItem, receiver: HasDiscreteAssets | None = None) -> bool:
        return self.can_remove_asset(asset)

    def can_receive_asset(self, asset: GraphItem, giver: HasDiscreteAssets | None = None) -> bool:
        return True

    @contribute_ns
    def provide_discrete_symbols(self) -> Mapping[str, object]:
        inventory = self.assets
        return {
            "asset_holder": self,
            "assets": inventory,
            "inv": inventory,
            "asset_sources": tuple(inventory.values()),
        }


class HasAssets(HasFungibleAssets, HasDiscreteAssets):
    """Combined facade over independent counted and discrete holdings."""

    def has_asset(self, asset: GraphItem | Singleton | str, count: int = 1) -> bool:
        if isinstance(asset, Singleton):
            return HasFungibleAssets.has_asset(self, asset, count)
        return HasDiscreteAssets.has_asset(self, asset)

    def can_add_asset(self, asset: GraphItem | Singleton, count: int = 1,
                      *, label: str | None = None) -> bool:
        if isinstance(asset, Singleton):
            return HasFungibleAssets.can_add_asset(self, asset, count)
        return HasDiscreteAssets.can_add_asset(self, asset, label=label)

    def can_remove_asset(self, asset: GraphItem | Singleton | str, count: int = 1) -> bool:
        if isinstance(asset, Singleton):
            return HasFungibleAssets.can_remove_asset(self, asset, count)
        return HasDiscreteAssets.can_remove_asset(self, asset)

    def add_asset(self, asset: GraphItem | Singleton, count: int = 1,
                  *, label: str | None = None) -> None:
        if isinstance(asset, Singleton):
            HasFungibleAssets.add_asset(self, asset, count)
        else:
            HasDiscreteAssets.add_asset(self, asset, label=label)

    def remove_asset(self, asset: GraphItem | Singleton | str, count: int = 1) -> GraphItem | None:
        if isinstance(asset, Singleton):
            HasFungibleAssets.remove_asset(self, asset, count)
            return None
        return HasDiscreteAssets.remove_asset(self, asset)
