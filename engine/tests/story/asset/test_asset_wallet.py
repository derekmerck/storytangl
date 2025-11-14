from __future__ import annotations

import pytest

from tangl.story.concepts.asset import AssetWallet, CountableAsset, HasAssetWallet


@pytest.fixture(autouse=True)
def _clear_countable_assets() -> None:
    """Reset singleton registry between tests."""
    CountableAsset.clear_instances()
    yield
    CountableAsset.clear_instances()


class TestAssetWallet:
    """Tests for :class:`AssetWallet`."""

    def test_create_empty_wallet(self) -> None:
        wallet = AssetWallet()
        assert len(wallet) == 0
        assert wallet.describe() == "empty"

    def test_gain_assets(self) -> None:
        wallet = AssetWallet()
        wallet.gain(gold=50)

        assert wallet["gold"] == 50
        assert "gold" in wallet

    def test_gain_multiple_assets(self) -> None:
        wallet = AssetWallet()
        wallet.gain(gold=50, gems=3, tokens=100)

        assert wallet["gold"] == 50
        assert wallet["gems"] == 3
        assert wallet["tokens"] == 100

    def test_gain_accumulates(self) -> None:
        wallet = AssetWallet()
        wallet.gain(gold=30)
        wallet.gain(gold=20)

        assert wallet["gold"] == 50

    def test_cannot_gain_negative(self) -> None:
        wallet = AssetWallet()

        with pytest.raises(ValueError, match="negative amount"):
            wallet.gain(gold=-10)

    def test_can_afford_checks(self) -> None:
        wallet = AssetWallet()
        wallet.gain(gold=50, gems=5)

        assert wallet.can_afford(gold=30)
        assert wallet.can_afford(gold=50)
        assert not wallet.can_afford(gold=51)

        assert wallet.can_afford(gold=20, gems=3)
        assert not wallet.can_afford(gold=20, gems=6)

    def test_can_afford_missing_asset(self) -> None:
        wallet = AssetWallet()
        wallet.gain(gold=50)

        assert not wallet.can_afford(gems=1)

    def test_spend_reduces_amount(self) -> None:
        wallet = AssetWallet()
        wallet.gain(gold=50)
        wallet.spend(gold=30)

        assert wallet["gold"] == 20

    def test_spend_removes_zero_entries(self) -> None:
        wallet = AssetWallet()
        wallet.gain(gold=50)
        wallet.spend(gold=50)

        assert "gold" not in wallet
        assert len(wallet) == 0

    def test_spend_insufficient_raises(self) -> None:
        wallet = AssetWallet()
        wallet.gain(gold=30)

        with pytest.raises(ValueError, match="Insufficient assets"):
            wallet.spend(gold=40)

        assert wallet["gold"] == 30

    def test_spend_multiple_insufficient_raises(self) -> None:
        wallet = AssetWallet()
        wallet.gain(gold=10, gems=2)

        with pytest.raises(ValueError) as exc_info:
            wallet.spend(gold=20, gems=5)

        error = str(exc_info.value)
        assert "gold" in error
        assert "gems" in error

        assert wallet["gold"] == 10
        assert wallet["gems"] == 2

    def test_total_value_calculation(self) -> None:
        CountableAsset(label="gold", value=1.0)
        CountableAsset(label="gems", value=10.0)

        asset_types = {
            "gold": CountableAsset.get_instance("gold"),
            "gems": CountableAsset.get_instance("gems"),
        }

        wallet = AssetWallet()
        wallet.gain(gold=50, gems=3)

        total = wallet.total_value(asset_types)
        assert total == 50 * 1.0 + 3 * 10.0

    def test_total_value_ignores_unknown(self) -> None:
        asset_types = {
            "gold": CountableAsset(label="gold", value=1.0)
        }

        wallet = AssetWallet()
        wallet.gain(gold=50, unknown=100)

        total = wallet.total_value(asset_types)
        assert total == 50.0

    def test_describe_empty(self) -> None:
        wallet = AssetWallet()
        assert wallet.describe() == "empty"

    def test_describe_contents(self) -> None:
        wallet = AssetWallet()
        wallet.gain(gold=50, gems=3)

        desc = wallet.describe()
        assert "gold" in desc
        assert "50" in desc
        assert "gems" in desc
        assert "3" in desc

    def test_describe_sorts_by_count(self) -> None:
        wallet = AssetWallet()
        wallet.gain(gold=5, gems=100, tokens=20)

        desc = wallet.describe()
        assert desc.index("gems") < desc.index("tokens")
        assert desc.index("tokens") < desc.index("gold")


class TestHasAssetWallet:
    """Tests for :class:`HasAssetWallet`."""

    def test_mixin_provides_wallet(self) -> None:
        from tangl.core import Graph, Node

        class Player(Node, HasAssetWallet):
            pass

        graph = Graph(label="test")
        player = Player(label="alice", graph=graph)

        assert hasattr(player, "wallet")
        assert isinstance(player.wallet, AssetWallet)

    def test_wallet_persists(self) -> None:
        from tangl.core import Graph, Node

        class Player(Node, HasAssetWallet):
            pass

        graph = Graph(label="test")
        player = Player(label="alice", graph=graph)

        wallet1 = player.wallet
        wallet2 = player.wallet
        assert wallet1 is wallet2

    def test_wallet_operations_work(self) -> None:
        from tangl.core import Graph, Node

        class Player(Node, HasAssetWallet):
            pass

        graph = Graph(label="test")
        player = Player(label="alice", graph=graph)

        player.wallet.gain(gold=100)
        assert player.wallet["gold"] == 100

        player.wallet.spend(gold=30)
        assert player.wallet["gold"] == 70
