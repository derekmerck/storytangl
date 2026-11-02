"""Graph-owned holder membership, contribution sources, and exchanges."""
from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.core import DispatchLayer, Graph, Node, Priority, Selector, Token, contribute_ns
from tangl.mechanics.transaction import AssetMoveCommitment, CallbackCommitment, CountableTransferCommitment, TransactionOffer
from tangl.mechanics.sandbox import (
    ChargeFacet, LightSourceFacet, SandboxCompiledAssetType, SandboxLocation,
    SandboxScope, SwitchableFacet,
)
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story.concepts.asset import (
    AssetTransactionManager, CountableAsset, HasAssets, HasDiscreteAssets, HasFungibleAssets,
)
from tangl.story import Action, StoryGraph
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm import Ledger, TraversableNode, on_update
from tangl.vm.dispatch import dispatch, do_provision


class Holder(HasAssets, TraversableNode):
    pass


class Inventory(HasDiscreteAssets, Node):
    pass


class Purse(HasFungibleAssets, Node):
    pass


class Donation(Node):
    @contribute_ns
    def donate(self):
        return {"special_signal": "hello"}


def test_optional_holders_sources_and_round_trip_are_pure() -> None:
    graph = Graph()
    holder = Holder(label="host", registry=graph)
    inventory = Inventory(label="bag", registry=graph)
    purse = Purse(label="purse", registry=graph)
    member = Donation(label="amulet", registry=graph)
    other = Donation(label="charm", registry=graph)
    coin = CountableAsset(label=f"coin-{uuid4()}")
    before = graph.value_hash(), len(graph.members)
    assert holder.assets == {} and inventory.assets == {}
    assert not holder.has_asset(member) and holder.can_add_asset(member)
    assert holder.wallet.can_add_asset(coin) and not holder.has_asset(coin)
    assert (graph.value_hash(), len(graph.members)) == before
    holder.add_asset(member, label="treasure")
    holder.add_asset(other)
    purse.add_asset(coin, 3)
    ctx = PhaseCtx(graph=graph, cursor_id=holder.uid)
    namespace = ctx.get_ns(holder)
    sources = namespace["asset_sources"]
    assert sources == (member, other)
    source = sources[0]
    assert source is member and source.get_ns()["special_signal"] == "hello"
    assert namespace["self"] is holder
    restored = Graph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
    restored_holder = restored.get(holder.uid)
    assert restored_holder.get_asset("treasure") is restored.get(member.uid)
    assert restored_holder.get_asset("charm") is restored.get(other.uid)
    assert list(restored_holder.member_sources(Selector(label="amulet"))) == [restored.get(member.uid)]
    assert restored.get(purse.uid).wallet[coin] == 3


def test_exchange_rolls_back_balance_membership_order_and_aliases() -> None:
    graph = Graph()
    seller, buyer = Holder(label="seller", registry=graph), Holder(label="buyer", registry=graph)
    first, second = Node(label="first", registry=graph), Node(label="second", registry=graph)
    seller.add_asset(first, label="display")
    seller.add_asset(second)
    coin = CountableAsset(label=f"coin-{uuid4()}")
    buyer.add_asset(coin, 5)
    before = graph.value_hash(), len(graph.members), list(seller.assets)
    offer = TransactionOffer(commitments=[
        CountableTransferCommitment(buyer, seller, coin, 3),
        AssetMoveCommitment(seller, buyer, first),
        CallbackCommitment(label="fail", apply=lambda: (_ for _ in ()).throw(RuntimeError("fail"))),
    ])
    with pytest.raises(RuntimeError, match="fail"):
        offer.accept()
    assert buyer.wallet[coin] == 5 and seller.wallet[coin] == 0
    assert list(seller.assets) == before[2] and seller.get_asset("display") is first
    assert buyer.assets == {} and (graph.value_hash(), len(graph.members)) == before[:2]


def test_simple_transfer_restores_order_and_alias_after_receive_failure() -> None:
    class RejectingHolder(Holder):
        def add_asset(self, asset, *args, **kwargs):
            raise RuntimeError("receive failed")

    graph = Graph()
    giver = Holder(label="giver", registry=graph)
    receiver = RejectingHolder(label="receiver", registry=graph)
    first = Node(label="first", registry=graph)
    second = Node(label="second", registry=graph)
    giver.add_asset(first, label="alias")
    giver.add_asset(second)
    before = graph.value_hash(), list(giver.assets)

    with pytest.raises(RuntimeError, match="receive failed"):
        AssetTransactionManager().give_asset(giver, receiver, first)

    assert giver.get_asset("alias") is first
    assert (graph.value_hash(), list(giver.assets)) == before


def test_carried_node_remains_a_live_source_in_sandbox_scope() -> None:
    graph = Graph()
    scope = SandboxScope(label="scope", registry=graph)
    room = SandboxLocation(label="room", registry=graph)
    source = Donation(label="amulet", registry=graph)
    scope.add_child(room)
    scope.player_assets.add_asset(source)
    ctx = PhaseCtx(graph=graph, cursor_id=room.uid)
    do_provision(room, ctx=ctx)
    namespace = ctx.get_ns(room)
    held = namespace["player_assets"]
    assert list(held.member_sources(Selector(label="amulet"))) == [source]
    assert source.get_ns()["special_signal"] == "hello"
    assert namespace["self"] is room


def test_frozen_graph_requires_prepared_wallet() -> None:
    graph = StoryGraph(frozen_shape=True)
    holder = Holder(registry=graph)
    member = Node(label="item", registry=graph)
    before = graph.value_hash(), len(graph.members)
    assert not holder.can_add_asset(member)
    with pytest.raises(ValueError):
        holder.add_asset(member)
    assert (graph.value_hash(), len(graph.members)) == before
    holder.prepare_discrete_wallet()
    holder.add_asset(member)
    assert holder.has_asset(member)


def test_refresh_sees_late_author_effect_after_one_clock_tick() -> None:
    graph = Graph()
    scope = SandboxScope(label="scope", registry=graph, locals={"world_turn": 0})
    room = SandboxLocation(label="room", registry=graph)
    scope.add_child(room)
    definition = SandboxCompiledAssetType(
        label=f"late-lamp-{uuid4()}", name="lamp", portable=True,
        switchable=SwitchableFacet(), light_source=LightSourceFacet(),
        charge=ChargeFacet(current=5, maximum=5),
    )
    lamp = Token[SandboxCompiledAssetType](token_from=definition.label, registry=graph)
    edge = Action(registry=graph, predecessor_id=room.uid, successor_id=room.uid,
                  text="Receive lamp", tags={"sandbox"})

    @on_update(wants_caller_kind=SandboxLocation, wants_exact_kind=False,
               dispatch_layer=DispatchLayer.AUTHOR, priority=Priority.LAST)
    def late_effect(*, caller, ctx, **_kw):
        if caller.uid == room.uid and ctx.selected_edge.uid == edge.uid:
            scope.player_assets.add_asset(lamp)
            lamp.lit = True

    try:
        ledger = Ledger.from_graph(graph, entry_id=room.uid)
        ledger.resolve_choice(edge.uid)
        assert scope.locals["world_turn"] == 1
        assert lamp.charge.current == 5
        actions = list(room.edges_out(Selector(has_kind=Action)))
        assert any(action.text == "Turn off lamp" for action in actions)
    finally:
        dispatch.remove(late_effect._behavior.uid)
