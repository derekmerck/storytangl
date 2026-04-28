from __future__ import annotations

import pytest
from pydantic import Field

from tangl.core import Entity, Token
from tangl.mechanics.presence.wearable import Wearable, WearableType
from tangl.story.concepts.asset import (
    AssetTransactionManager,
    AssetType,
    AssetWallet,
    CountableAsset,
    HasAssets,
)


class WeaponType(AssetType):
    damage: int = 1


class AssetHolder(Entity, HasAssets):
    accepted_assets: set[str] = Field(default_factory=set)
    accepted_counts: set[str] = Field(default_factory=set)
    countable_events: list[str] = Field(default_factory=list)

    def can_receive_asset(self, asset: Token, giver: HasAssets | None = None) -> bool:
        _ = giver
        return not self.accepted_assets or asset.token_from in self.accepted_assets

    def can_receive_countable(
        self,
        asset_label: str,
        amount: int,
        giver: HasAssets | None = None,
    ) -> bool:
        _ = (amount, giver)
        return not self.accepted_counts or asset_label in self.accepted_counts

    def spend_countable(self, asset_label: str, amount: int) -> None:
        super().spend_countable(asset_label, amount)
        self.countable_events.append(f"spent:{amount}:{asset_label}")

    def gain_countable(self, asset_label: str, amount: int) -> None:
        super().gain_countable(asset_label, amount)
        self.countable_events.append(f"gained:{amount}:{asset_label}")


class RejectingGainHolder(AssetHolder):
    def gain_countable(self, asset_label: str, amount: int) -> None:
        _ = (asset_label, amount)
        raise RuntimeError("receiver failed")


class RejectingAssetHolder(AssetHolder):
    def add_asset(self, asset: Token, *, label: str | None = None) -> None:
        _ = (asset, label)
        raise RuntimeError("receiver failed")


@pytest.fixture(autouse=True)
def _clear_asset_singletons() -> None:
    WeaponType.clear_instances()
    CountableAsset.clear_instances()
    WearableType.clear_instances()
    yield
    WeaponType.clear_instances()
    CountableAsset.clear_instances()
    WearableType.clear_instances()
    WearableType.load_defaults()


def test_weapon_asset_type_can_be_tokenized() -> None:
    WeaponType(label="sword", value=12.5, description="a practice sword", damage=3)

    sword = Token[WeaponType](token_from="sword", label="training_sword")

    assert sword.has_kind(WeaponType)
    assert sword.damage == 3
    assert sword.value == 12.5
    assert sword.describe() == "a practice sword"


def test_wearable_type_uses_story_asset_base_and_can_be_tokenized() -> None:
    shirt_type = WearableType(label="shirt", value=4.0, description="a linen shirt")

    shirt = Wearable(token_from=shirt_type.label)

    assert isinstance(shirt_type, AssetType)
    assert shirt.has_kind(WearableType)
    assert shirt.value == 4.0
    assert shirt.describe() == "a linen shirt"


def test_countable_asset_exposes_value_and_description() -> None:
    gold = CountableAsset(label="gold", value=1.5, description="bright coin")

    assert gold.value == 1.5
    assert gold.description == "bright coin"
    assert gold.describe() == "bright coin"
    assert gold.text == "bright coin"


def test_countable_asset_inherits_from_ref_defaults() -> None:
    CountableAsset(label="coin", value=1.0, units="coins")
    gold = CountableAsset(label="gold", from_ref="coin", value=5.0)

    assert gold.value == 5.0
    assert gold.units == "coins"


def test_asset_wallet_can_gain_and_spend_fungibles() -> None:
    wallet = AssetWallet()

    wallet.gain(gold=50, arrows=12)
    wallet.spend(gold=20, arrows=2)

    assert wallet["gold"] == 30
    assert wallet["arrows"] == 10
    assert wallet.can_afford(gold=30)
    assert not wallet.can_afford(arrows=11)


def test_asset_wallet_spend_is_atomic_when_short() -> None:
    wallet = AssetWallet()
    wallet.gain(gold=10, arrows=2)

    with pytest.raises(ValueError, match="gold"):
        wallet.spend(gold=20, arrows=1)

    assert wallet["gold"] == 10
    assert wallet["arrows"] == 2


def test_asset_wallet_spend_rejects_negative_amounts() -> None:
    wallet = AssetWallet()
    wallet.gain(gold=10)

    with pytest.raises(ValueError, match="Cannot spend negative amount"):
        wallet.spend(gold=-1)

    assert wallet["gold"] == 10


def test_asset_wallet_total_value_and_description() -> None:
    CountableAsset(label="gold", value=1.0)
    CountableAsset(label="gems", value=10.0)
    wallet = AssetWallet()

    wallet.gain(gold=5, gems=2)

    assert wallet.total_value() == 25.0
    assert wallet.total_value({}) == 0.0
    assert wallet.describe() == "5 gold, 2 gems"


def test_has_assets_nominates_inventory_into_namespace() -> None:
    WeaponType(label="sword", value=12.5)
    sword = Token[WeaponType](token_from="sword", label="training_sword")
    holder = AssetHolder(label="hero")

    holder.add_asset(sword, label="primary")
    holder.wallet.gain(gold=10)
    ns = holder.get_ns()

    assert ns["asset_holder"] is holder
    assert ns["asset_wallet"] is holder.wallet
    assert ns["wallet"] is holder.wallet
    assert ns["inv"]["primary"] is sword
    assert ns["assets"]["primary"] is sword


def test_transaction_manager_moves_discrete_asset_after_preflight() -> None:
    WeaponType(label="sword")
    sword = Token[WeaponType](token_from="sword", label="training_sword")
    giver = AssetHolder(label="giver")
    receiver = AssetHolder(label="receiver", accepted_assets={"sword"})
    manager = AssetTransactionManager()
    giver.add_asset(sword)

    result = manager.can_give_asset(giver, receiver, "sword")
    moved = manager.give_asset(giver, receiver, "sword")

    assert result.accepted
    assert moved is sword
    assert not giver.has_asset("sword")
    assert receiver.has_asset("sword")


def test_transaction_manager_rejects_discrete_asset_without_mutation() -> None:
    WeaponType(label="sword")
    sword = Token[WeaponType](token_from="sword")
    giver = AssetHolder(label="giver")
    receiver = AssetHolder(label="receiver", accepted_assets={"shield"})
    manager = AssetTransactionManager()
    giver.add_asset(sword)

    result = manager.can_give_asset(giver, receiver, "sword")

    assert not result.accepted
    assert result.reason == "receiver cannot receive asset"
    assert giver.has_asset("sword")
    assert not receiver.has_asset("sword")


def test_transaction_manager_rolls_back_discrete_asset_if_receive_fails() -> None:
    WeaponType(label="sword")
    sword = Token[WeaponType](token_from="sword")
    giver = AssetHolder(label="giver")
    receiver = RejectingAssetHolder(label="receiver")
    manager = AssetTransactionManager()
    giver.add_asset(sword)

    with pytest.raises(RuntimeError, match="receiver failed"):
        manager.give_asset(giver, receiver, "sword")

    assert giver.has_asset("sword")
    assert not receiver.has_asset("sword")


def test_transaction_manager_moves_countable_assets_after_preflight() -> None:
    giver = AssetHolder(label="giver")
    receiver = AssetHolder(label="receiver", accepted_counts={"gold"})
    manager = AssetTransactionManager()
    giver.wallet.gain(gold=20)

    result = manager.can_transfer_countable(giver, receiver, "gold", 7)
    manager.transfer_countable(giver, receiver, "gold", 7)

    assert result.accepted
    assert giver.wallet["gold"] == 13
    assert receiver.wallet["gold"] == 7
    assert giver.countable_events == ["spent:7:gold"]
    assert receiver.countable_events == ["gained:7:gold"]


def test_transaction_manager_rejects_countable_assets_without_mutation() -> None:
    giver = AssetHolder(label="giver")
    receiver = AssetHolder(label="receiver", accepted_counts={"gems"})
    manager = AssetTransactionManager()
    giver.wallet.gain(gold=20)

    result = manager.can_transfer_countable(giver, receiver, "gold", 7)

    assert not result.accepted
    assert result.reason == "receiver cannot receive countable asset"
    assert giver.wallet["gold"] == 20
    assert receiver.wallet["gold"] == 0


def test_transaction_manager_rolls_back_countable_spend_if_receive_fails() -> None:
    giver = AssetHolder(label="giver")
    receiver = RejectingGainHolder(label="receiver", accepted_counts={"gold"})
    manager = AssetTransactionManager()
    giver.wallet.gain(gold=20)

    with pytest.raises(RuntimeError, match="receiver failed"):
        manager.transfer_countable(giver, receiver, "gold", 7)

    assert giver.wallet["gold"] == 20
    assert receiver.wallet["gold"] == 0
