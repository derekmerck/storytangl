from __future__ import annotations

import pytest

from tangl.story.concepts.asset import CountableAsset, Fungible


@pytest.fixture(autouse=True)
def _clear_countable_assets() -> None:
    """Ensure the singleton registry is empty for each test."""
    CountableAsset.clear_instances()
    yield
    CountableAsset.clear_instances()


class TestCountableAsset:
    """Tests for :class:`CountableAsset`."""

    def test_create_simple_currency(self) -> None:
        """Can define a simple currency asset."""
        gold = CountableAsset(label="gold", value=1.0, symbol="🪙")

        assert gold.label == "gold"
        assert gold.value == 1.0
        assert gold.symbol == "🪙"

    def test_instance_inheritance(self) -> None:
        """Instances inherit defaults through ``from_ref``."""
        CountableAsset(label="coin", value=1.0)
        CountableAsset(label="gold_coin", from_ref="coin", value=5.0)

        gold_coin = CountableAsset.get_instance("gold_coin")
        assert gold_coin.value == 5.0
        assert gold_coin.units == "units"

    def test_fungible_alias_works(self) -> None:
        """The historical ``Fungible`` alias resolves to ``CountableAsset``."""
        assert Fungible is CountableAsset

        gold = Fungible(label="gold")
        assert isinstance(gold, CountableAsset)

    def test_default_values(self) -> None:
        """Default values are retained when unspecified."""
        token = CountableAsset(label="token")

        assert token.value == 1.0
        assert token.units == "units"
        assert token.symbol is None
