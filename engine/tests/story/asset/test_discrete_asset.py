from __future__ import annotations

from tangl.core import Graph
from tangl.core.graph.token import Token
from tangl.story.concepts.asset import AssetType, DiscreteAsset


class TestDiscreteAssetGenericTyping:
    """Test that DiscreteAsset[T] generic typing works correctly."""

    def test_can_create_typed_wrapper(self) -> None:
        """DiscreteAsset[AssetType] creates proper wrapper class."""

        class Weapon(AssetType):
            damage: int = 10

        Weapon(label="sword", damage=15)

        SwordToken = DiscreteAsset[Weapon]
        assert issubclass(SwordToken, DiscreteAsset)
        assert issubclass(SwordToken, Token)

    def test_token_delegates_to_singleton(self) -> None:
        """Token attributes delegate to singleton definition."""

        class Weapon(AssetType):
            damage: int = 10
            weight: float = 3.5

        Weapon(label="sword", damage=15, weight=4.0)

        graph = Graph(label="test")
        token = DiscreteAsset[Weapon](label="sword", graph=graph)

        assert token.damage == 15
        assert token.weight == 4.0

    def test_token_has_instance_state(self) -> None:
        """Token has instance variables separate from singleton."""

        class Item(AssetType):
            value: int = 10

        Item(label="coin", value=5)

        graph = Graph(label="test")
        token1 = DiscreteAsset[Item](label="coin", graph=graph)
        token2 = DiscreteAsset[Item](label="coin", graph=graph)

        assert token1.uid != token2.uid

        token1.owner_id = "alice"
        token2.owner_id = "bob"
        assert token1.owner_id != token2.owner_id

        assert token1.value == token2.value == 5

    def test_token_in_graph(self) -> None:
        """Token is a proper graph node."""

        class Item(AssetType):
            pass

        Item(label="key")

        graph = Graph(label="test")
        token = DiscreteAsset[Item](label="key", graph=graph)

        assert token in graph
        assert token.graph is graph

    def test_multiple_asset_types(self) -> None:
        """Different asset types create different token classes."""

        class Weapon(AssetType):
            damage: int = 10

        class Armor(AssetType):
            defense: int = 5

        Weapon(label="sword")
        Armor(label="shield")

        WeaponToken = DiscreteAsset[Weapon]
        ArmorToken = DiscreteAsset[Armor]

        assert WeaponToken is not ArmorToken

