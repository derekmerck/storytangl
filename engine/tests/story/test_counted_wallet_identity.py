"""Singleton and named balances through owner-graph constructor form."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import ClassVar
from uuid import uuid4

import pytest
from pydantic import Field

from tangl.core import Graph, Node
from tangl.core.bases import Unstructurable
from tangl.loaders.compilers import AssetCompiler
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story.concepts.asset import AssetWallet, CountableAsset, HasAssets


class Coin(CountableAsset):
    catalog_id: str = ""


class OtherCoin(CountableAsset):
    pass


class Holder(HasAssets, Node):
    pass


class WalletSettings(Unstructurable):
    message: str = "default"


class CappedWallet(AssetWallet):
    limit: int = 100
    notes: list[str] = Field(default_factory=list, json_schema_extra={"include": True})
    settings: WalletSettings = Field(
        default_factory=WalletSettings,
        json_schema_extra={"include": True, "unstructurable": True},
    )
    transient: str = Field(default="default", exclude=True)
    category: ClassVar[str] = "wallet-policy"

    def can_add_asset(self, asset, count=1):
        return super().can_add_asset(asset, count) and self[asset] + count <= self.limit


class CappedHost(Node):
    wallet: CappedWallet = Field(
        default_factory=CappedWallet,
        json_schema_extra={"include": True, "unstructurable": True},
    )


@pytest.mark.parametrize("through_json", [False, True])
def test_declared_wallet_subclass_state_survives_graph_restore(through_json: bool) -> None:
    graph = Graph()
    host = CappedHost(registry=graph, wallet=CappedWallet(limit=2, transient="temporary"))
    host.wallet.notes.append("kept")
    host.wallet.settings.message = "kept too"
    host.wallet.add_asset("gold", 2)
    payload = graph.unstructure()
    wallet_data = next(item for item in payload["members"] if item["uid"] == host.uid)["wallet"]
    assert "amounts" not in wallet_data and "category" not in wallet_data
    assert "transient" not in wallet_data
    if through_json:
        payload = Json.deserialize(Json.serialize(payload))
    wallet = Graph.structure(payload).get(host.uid).wallet
    assert isinstance(wallet, CappedWallet) and wallet.limit == 2
    assert wallet.notes == ["kept"] and wallet.settings.message == "kept too"
    assert wallet.transient == "default" and wallet.category == "wallet-policy"
    assert wallet["gold"] == 2 and not wallet.can_add_asset("gold")
    with pytest.raises(ValueError):
        wallet.add_asset("gold")


def test_owner_json_identity_canonical_order_and_empty() -> None:
    label = str(uuid4())
    first = Coin(label=label)
    second = OtherCoin(label=label)
    graph = Graph()
    host = Holder(registry=graph)
    host.wallet.gain({first: 3, second: 4, label: 5})
    before_hash = graph.value_hash()
    assert host.wallet.has_asset(first, 3) and host.wallet.can_remove_asset(second, 4)
    assert host.wallet.can_add_asset(first, 1) and not host.wallet.can_remove_asset(first, 4)
    assert graph.value_hash() == before_hash
    reversed_wallet = AssetWallet(amounts={label: 5, second: 4, first: 3})
    assert reversed_wallet.unstructure() == host.wallet.unstructure()
    host.wallet.amounts.clear()
    host.wallet.gain({label: 5, second: 4, first: 3})
    assert graph.value_hash() == before_hash
    native = Graph.structure(graph.unstructure()).get(host.uid).wallet
    assert any(key is first for key in native.amounts)
    assert any(key is second for key in native.amounts)
    restored = Graph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
    wallet = restored.get(host.uid).wallet
    assert wallet[first] == 3 and wallet[second] == 4 and wallet[label] == 5
    keys = list(wallet.amounts)
    assert any(key is first for key in keys) and any(key is second for key in keys)
    for key in (first, second, label):
        wallet.remove_asset(key, wallet[key])
    restored_again = Graph.structure(Json.deserialize(Json.serialize(restored.unstructure())))
    assert restored_again.get(host.uid).wallet.amounts == {}


def test_batch_policy_refusal_and_invalid_counts_are_atomic() -> None:
    class PolicyWallet(AssetWallet):
        def can_add_asset(self, asset, count=1):
            return asset != "blocked" and super().can_add_asset(asset, count)

        def can_remove_asset(self, asset, count=1):
            return asset != "locked" and super().can_remove_asset(asset, count)

    wallet = PolicyWallet(amounts={"good": 3, "locked": 1})
    before = dict(wallet.amounts)
    for operation, values in (
        (wallet.gain, {"good": 2, "blocked": 1}),
        (wallet.gain, {"good": 2, "bad": -1}),
        (wallet.gain, {"good": 2, "bad": 0.5}),
        (wallet.spend, {"good": 1, "locked": 1}),
        (wallet.spend, {"good": 1, "missing": 1}),
        (wallet.spend, {"good": 1, "bad": -1}),
    ):
        with pytest.raises(ValueError):
            operation(values)
        assert wallet.amounts == before
    with pytest.raises(ValueError):
        wallet.add_asset("blocked")
    with pytest.raises(ValueError):
        wallet.remove_asset("locked")
    assert wallet.amounts == before

    class PermissiveWallet(AssetWallet):
        def can_add_asset(self, asset, count=1):
            return True

        def can_remove_asset(self, asset, count=1):
            return True

    permissive = PermissiveWallet()
    with pytest.raises(ValueError):
        permissive.gain({"valid": 2, "invalid": -1})
    with pytest.raises(ValueError):
        permissive.spend({"missing": 1})
    assert permissive.amounts == {}


def _cold(root: Path, mode: str) -> None:
    source = root / "coins.yaml"
    source.write_text("coin:\n  value: 2\n", encoding="utf-8")
    catalogs = [AssetCompiler._load_catalog(source_path=source, definition_type=Coin,
                world_label=world, catalog_label="money") for world in ("east", "west")]
    east, west = (next(c.find_all()) for c in catalogs)
    if mode == "write":
        graph = Graph()
        holder = Holder(registry=graph)
        holder.wallet.gain({east: 2, west: 7, "coin": 4})
        (root / "graph.json").write_text(Json.serialize(graph.unstructure()), encoding="utf-8")
    else:
        graph = Graph.structure(Json.deserialize((root / "graph.json").read_text(encoding="utf-8")))
        holder = next(item for item in graph.values() if isinstance(item, Holder))
        assert holder.wallet[east] == 2 and holder.wallet[west] == 7 and holder.wallet["coin"] == 4
        assert any(key is east for key in holder.wallet.amounts)
        assert any(key is west for key in holder.wallet.amounts)
        assert len(list(Coin.all_instances())) == 2


def test_cold_catalog_bootstrap_and_json_restore(tmp_path: Path) -> None:
    for mode in ("write", "read"):
        subprocess.run(
            [sys.executable, "-c", "from engine.tests.story.test_counted_wallet_identity import _cold;"
             "from pathlib import Path; import sys; _cold(Path(sys.argv[1]), sys.argv[2])",
             str(tmp_path), mode],
            check=True, env=os.environ.copy(), timeout=30,
        )
