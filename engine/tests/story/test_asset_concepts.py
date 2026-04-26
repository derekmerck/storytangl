from __future__ import annotations

import pytest

from tangl.core import Token
from tangl.mechanics.presence.wearable import Wearable, WearableType
from tangl.story.concepts.asset import AssetType, AssetWallet, CountableAsset


class WeaponType(AssetType):
    damage: int = 1


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


def test_asset_wallet_total_value_and_description() -> None:
    CountableAsset(label="gold", value=1.0)
    CountableAsset(label="gems", value=10.0)
    wallet = AssetWallet()

    wallet.gain(gold=5, gems=2)

    assert wallet.total_value() == 25.0
    assert wallet.describe() == "5 gold, 2 gems"
