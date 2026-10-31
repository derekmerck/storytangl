from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

from pydantic import Field

from tangl.core import GraphItem, Selector, Subgraph


class DiscreteAssetWallet(Subgraph):
    """A graph-owned, ordered group of discrete graph members.

    Membership is not hierarchical or exclusive. Hosts refer to this wallet by
    UID; the graph owns both the wallet and each member.
    """

    member_ids: list[UUID] = Field(
        default_factory=list, json_schema_extra={"include": True},
    )

    def has_asset(self, asset: GraphItem) -> bool:
        return self.graph.get(asset.uid) is asset and asset.uid in self.member_ids

    def can_add_asset(self, asset: GraphItem) -> bool:
        return (
            asset is not self
            and asset.registry is self.graph
            and self.graph.get(asset.uid) is asset
            and asset.uid not in self.member_ids
        )

    def can_remove_asset(self, asset: GraphItem) -> bool:
        return asset.registry is self.graph and self.has_asset(asset)

    def add_member(self, item: GraphItem, _ctx=None) -> None:
        if not self.can_add_asset(item):
            raise ValueError("Asset must be a new member of the same graph")
        super().add_member(item, _ctx=_ctx)

    def remove_member(self, item: GraphItem, _ctx=None) -> None:
        if not self.can_remove_asset(item):
            raise ValueError("Asset must be a member of this wallet and graph")
        super().remove_member(item, _ctx=_ctx)

    def add_asset(self, asset: GraphItem) -> None:
        self.add_member(asset)

    def remove_asset(self, asset: GraphItem) -> None:
        self.remove_member(asset)

    def members(self, selector: Selector | None = None, sort_key=None) -> Iterator[GraphItem]:
        for uid in self.member_ids:
            if self.graph.get(uid) is None:
                raise KeyError(f"Wallet member {uid} is missing from its graph")
        return super().members(selector=selector, sort_key=sort_key)
