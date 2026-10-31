"""Graph-owned discrete asset membership and replay."""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import Field

from tangl.core import Graph, HierarchicalNode, Node, Selector, Token
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story.concepts.asset import AssetType, DiscreteAssetWallet
from tangl.vm.replay import get_replay_engine


class WalletHost(Node):
    wallet_id: UUID


class LampType(AssetType):
    lit: bool = Field(default=False, json_schema_extra={"instance_var": True})


def _fixture() -> tuple[Graph, WalletHost, DiscreteAssetWallet, Node, Token]:
    graph = Graph()
    parent = HierarchicalNode(label="room", registry=graph)
    item = Node(label="item", registry=graph)
    parent.add_child(item)
    definition = LampType(label=f"wallet-test-lamp-{uuid4()}")
    lamp = Token[LampType](label="lamp", token_from=definition.label, registry=graph)
    wallet = DiscreteAssetWallet(label="wallet", registry=graph)
    host = WalletHost(label="host", wallet_id=wallet.uid, registry=graph)
    return graph, host, wallet, item, lamp


def _json_copy(graph: Graph) -> Graph:
    return Graph.structure(Json.deserialize(Json.serialize(graph.unstructure())))


def test_membership_identity_order_and_json_roundtrip() -> None:
    graph, host, wallet, item, lamp = _fixture()
    parent = item.parent
    wallet.add_asset(item)
    wallet.add_asset(lamp)
    lamp.lit = True
    assert item.parent is parent
    assert list(wallet.members()) == [item, lamp]
    assert wallet.member(Selector(label="lamp")) is lamp

    restored = _json_copy(graph)
    restored_host = restored.get(host.uid)
    restored_wallet = restored.get(restored_host.wallet_id)
    assert isinstance(restored_wallet, DiscreteAssetWallet)
    assert list(restored_wallet.members()) == [restored.get(item.uid), restored.get(lamp.uid)]
    assert restored_wallet.member(Selector(label="lamp")) is restored.get(lamp.uid)
    assert restored.get(lamp.uid).lit is True
    assert restored.get(item.uid).parent is restored.get(parent.uid)
    assert len(restored.members) == len(graph.members)
    assert len({member.uid for member in restored.values()}) == len(graph.members)


def test_checks_are_pure_and_reject_duplicates_foreign_and_stale_objects() -> None:
    graph, _, wallet, item, lamp = _fixture()
    wallet.add_asset(item)
    other = Graph()
    foreign = Node(registry=other)
    stale = item.model_copy()
    assert stale.registry is graph and stale is not item
    before = graph.value_hash(), len(graph.members), list(wallet.member_ids)
    assert wallet.has_asset(item) and wallet.can_remove_asset(item)
    assert not wallet.can_add_asset(item) and wallet.can_add_asset(lamp)
    assert not wallet.can_add_asset(foreign) and not wallet.can_remove_asset(foreign)
    assert not wallet.has_asset(stale) and not wallet.can_add_asset(stale)
    assert list(wallet.members()) == [item]
    for candidate in (item, foreign, stale, wallet):
        with pytest.raises(ValueError):
            wallet.add_asset(candidate)
    with pytest.raises(ValueError):
        wallet.remove_asset(foreign)
    assert (graph.value_hash(), len(graph.members), wallet.member_ids) == before
    # Separate groups can describe possession and equipment simultaneously.
    equipped = DiscreteAssetWallet(registry=graph)
    equipped.add_asset(item)
    assert wallet.has_asset(item) and equipped.has_asset(item)


def test_missing_reference_fails_visibly() -> None:
    graph, _, wallet, item, _ = _fixture()
    wallet.add_asset(item)
    graph.remove(item.uid)
    with pytest.raises(KeyError, match="missing"):
        list(wallet.members())
    wallet.member_ids.append(uuid4())
    with pytest.raises(KeyError, match="missing"):
        wallet.member(Selector(label="not-there"))


def test_removal_to_empty_survives_json_and_replay() -> None:
    graph, host, wallet, item, lamp = _fixture()
    wallet.add_asset(item)
    wallet.add_asset(lamp)
    wallet.remove_asset(item)
    assert list(wallet.members()) == [lamp]
    before = _json_copy(graph)
    wallet.remove_asset(lamp)
    after = _json_copy(graph)
    assert after.get(host.wallet_id).member_ids == []
    engine = get_replay_engine("diff_v1")
    delta = engine.build_delta(before_graph=before, after_graph=after)
    assert delta is not None
    engine.apply_delta(graph=before, delta=delta)
    assert before.get(host.wallet_id).member_ids == []
    assert before.value_hash() == after.value_hash()
