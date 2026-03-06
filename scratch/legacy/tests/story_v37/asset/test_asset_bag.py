from __future__ import annotations

from typing import ClassVar

import pytest

from tangl.core import Graph, Node
from tangl.story.concepts.asset import AssetBag, AssetType, DiscreteAsset, HasAssetBag


@pytest.fixture(autouse=True)
def _clear_asset_types() -> None:
    """Ensure singleton registries are reset between tests."""

    def _clear() -> None:
        AssetType.clear_instances()
        for subclass in list(AssetType.__subclasses__()):
            if hasattr(subclass, "clear_instances"):
                subclass.clear_instances()

    _clear()
    yield
    _clear()


class TestAssetBag:
    """Test bag operations for discrete assets."""

    @pytest.fixture
    def graph(self) -> Graph:
        return Graph(label="test")

    @pytest.fixture
    def owner(self, graph: Graph) -> Node:
        return Node(label="owner", graph=graph)

    @pytest.fixture
    def item_type(self) -> type[AssetType]:
        class Item(AssetType):
            weight: float = 1.0

        return Item

    def test_create_unlimited_bag(self, owner: Node) -> None:
        bag = AssetBag(owner)

        assert bag.owner is owner
        assert bag.max_items is None
        assert bag.max_weight is None

    def test_create_limited_bag(self, owner: Node) -> None:
        bag = AssetBag(owner, max_items=10, max_weight=50.0)

        assert bag.max_items == 10
        assert bag.max_weight == 50.0

    def test_empty_bag_properties(self, owner: Node) -> None:
        bag = AssetBag(owner)

        assert bag.count() == 0
        assert bag.total_weight() == 0.0
        assert bag.items == []
        assert bag.describe() == "empty bag"

    def test_add_item_to_bag(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        item_type(label="sword", weight=3.5)
        bag = AssetBag(owner)

        token = DiscreteAsset[item_type](label="sword", graph=graph)
        bag.add(token)

        assert token in bag.items
        assert bag.count() == 1
        assert token.owner_id == owner.uid

    def test_add_multiple_items(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        item_type(label="sword", weight=3.0)
        item_type(label="potion", weight=0.5)

        bag = AssetBag(owner)

        sword = DiscreteAsset[item_type](label="sword", graph=graph)
        potion = DiscreteAsset[item_type](label="potion", graph=graph)

        bag.add(sword)
        bag.add(potion)

        assert bag.count() == 2
        assert sword in bag.items
        assert potion in bag.items

    def test_total_weight_calculation(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        item_type(label="sword", weight=3.5)
        item_type(label="potion", weight=0.5)

        bag = AssetBag(owner)

        sword = DiscreteAsset[item_type](label="sword", graph=graph)
        potion = DiscreteAsset[item_type](label="potion", graph=graph)

        bag.add(sword)
        bag.add(potion)

        assert bag.total_weight() == pytest.approx(4.0)

    def test_get_item_by_label(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        item_type(label="key")

        bag = AssetBag(owner)
        token = DiscreteAsset[item_type](label="key", graph=graph)
        bag.add(token)

        found = bag.get_item("key")
        assert found is token

    def test_get_missing_item_returns_none(self, owner: Node) -> None:
        bag = AssetBag(owner)

        assert bag.get_item("missing") is None

    def test_contains_check(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        item_type(label="key")

        bag = AssetBag(owner)
        token = DiscreteAsset[item_type](label="key", graph=graph)

        assert not bag.contains("key")

        bag.add(token)
        assert bag.contains("key")

    def test_items_of_type_filter(
        self, owner: Node, graph: Graph
    ) -> None:
        class Weapon(AssetType):
            pass

        class Potion(AssetType):
            pass

        Weapon(label="sword")
        Potion(label="health")

        bag = AssetBag(owner)

        sword = DiscreteAsset[Weapon](label="sword", graph=graph)
        potion = DiscreteAsset[Potion](label="health", graph=graph)

        bag.add(sword)
        bag.add(potion)

        WeaponToken = DiscreteAsset[Weapon]
        weapons = bag.items_of_type(WeaponToken)

        assert weapons == [sword]
        assert potion not in weapons

    def test_remove_item(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        item_type(label="sword")

        bag = AssetBag(owner)
        token = DiscreteAsset[item_type](label="sword", graph=graph)

        bag.add(token)
        assert bag.count() == 1

        bag.remove(token)
        assert bag.count() == 0
        assert token not in bag.items
        assert token.owner_id is None

    def test_remove_missing_item_raises(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        item_type(label="sword")

        bag = AssetBag(owner)
        token = DiscreteAsset[item_type](label="sword", graph=graph)

        with pytest.raises(ValueError, match="not in bag"):
            bag.remove(token)

    def test_clear_bag(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        item_type(label="item1")
        item_type(label="item2")

        bag = AssetBag(owner)

        token1 = DiscreteAsset[item_type](label="item1", graph=graph)
        token2 = DiscreteAsset[item_type](label="item2", graph=graph)

        bag.add(token1)
        bag.add(token2)
        assert bag.count() == 2

        bag.clear()
        assert bag.count() == 0
        assert bag.items == []

    def test_max_items_constraint(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        item_type(label="coin", weight=0.1)

        bag = AssetBag(owner, max_items=2)

        coin1 = DiscreteAsset[item_type](label="coin", graph=graph)
        coin2 = DiscreteAsset[item_type](label="coin", graph=graph)
        coin3 = DiscreteAsset[item_type](label="coin", graph=graph)

        bag.add(coin1)
        bag.add(coin2)

        with pytest.raises(ValueError, match="Bag full"):
            bag.add(coin3)

        assert bag.count() == 2

    def test_max_weight_constraint(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        item_type(label="heavy", weight=30.0)
        item_type(label="light", weight=10.0)

        bag = AssetBag(owner, max_weight=50.0)

        heavy = DiscreteAsset[item_type](label="heavy", graph=graph)
        light = DiscreteAsset[item_type](label="light", graph=graph)

        bag.add(heavy)
        bag.add(light)

        heavy2 = DiscreteAsset[item_type](label="heavy", graph=graph)

        with pytest.raises(ValueError, match="Too heavy"):
            bag.add(heavy2)

    def test_validate_empty_bag(self, owner: Node) -> None:
        bag = AssetBag(owner)

        assert bag.validate() == []

    def test_validate_within_limits(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        item_type(label="item", weight=5.0)

        bag = AssetBag(owner, max_items=10, max_weight=50.0)

        token = DiscreteAsset[item_type](label="item", graph=graph)
        bag.add(token)

        assert bag.validate() == []

    def test_validate_over_item_limit(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        for i in range(3):
            item_type(label=f"item-{i}")

        bag = AssetBag(owner, max_items=3)

        tokens = [
            DiscreteAsset[item_type](label=f"item-{i}", graph=graph)
            for i in range(3)
        ]
        for token in tokens:
            bag.add(token)

        bag.max_items = 2

        errors = bag.validate()
        assert len(errors) == 1
        assert "Too many items" in errors[0]

    def test_validate_over_weight_limit(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        for i in range(2):
            item_type(label=f"heavy-{i}", weight=30.0)

        bag = AssetBag(owner, max_weight=100.0)

        tokens = [
            DiscreteAsset[item_type](label=f"heavy-{i}", graph=graph)
            for i in range(2)
        ]
        for token in tokens:
            bag.add(token)

        bag.max_weight = 50.0

        errors = bag.validate()
        assert len(errors) == 1
        assert "Overweight" in errors[0]

    def test_can_accept_checks_capacity(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        for label in ("item-1", "item-2"):
            item_type(label=label)

        bag = AssetBag(owner, max_items=1)

        token1 = DiscreteAsset[item_type](label="item-1", graph=graph)
        token2 = DiscreteAsset[item_type](label="item-2", graph=graph)

        can_add, errors = bag.can_accept(token1)
        assert can_add is True
        assert errors == []

        bag.add(token1)

        can_add, errors = bag.can_accept(token2)
        assert can_add is False
        assert any("full" in error.lower() for error in errors)

    def test_describe_with_limits(
        self, owner: Node, item_type: type[AssetType], graph: Graph
    ) -> None:
        for label in ("item-1", "item-2"):
            item_type(label=label, weight=5.0)

        bag = AssetBag(owner, max_items=10, max_weight=50.0)

        token1 = DiscreteAsset[item_type](label="item-1", graph=graph)
        token2 = DiscreteAsset[item_type](label="item-2", graph=graph)

        bag.add(token1)
        bag.add(token2)

        desc = bag.describe()
        assert "2 items" in desc
        assert "max 10" in desc
        assert "10.0/50.0" in desc


class TestHasAssetBag:
    """Tests for the :class:`HasAssetBag` mixin."""

    def test_mixin_provides_bag(self) -> None:
        class Container(Node, HasAssetBag):
            pass

        graph = Graph(label="test")
        container = Container(label="chest", graph=graph)

        assert hasattr(container, "bag")
        assert isinstance(container.bag, AssetBag)

    def test_bag_persists(self) -> None:
        class Container(Node, HasAssetBag):
            pass

        graph = Graph(label="test")
        container = Container(label="chest", graph=graph)

        assert container.bag is container.bag

    def test_bag_with_limits(self) -> None:
        class Container(Node, HasAssetBag):
            _bag_max_items: ClassVar[int] = 5
            _bag_max_weight: ClassVar[float] = 20.0

        graph = Graph(label="test")
        container = Container(label="chest", graph=graph)

        assert container.bag.max_items == 5
        assert container.bag.max_weight == 20.0
