from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pydantic import Field

from tangl.core import Graph
from tangl.core.graph import Token
from tangl.story.concepts.asset import AssetType, CountableAsset
from tangl.story.fabula.asset_manager import AssetManager


class TestAssetManagerRegistration:
    """Test asset type registration."""

    def test_register_discrete_class(self) -> None:
        """Can register discrete asset class."""

        class Weapon(AssetType):
            pass

        manager = AssetManager()
        manager.register_discrete_class("weapons", Weapon)

        assert "weapons" in manager.discrete_classes
        assert manager.discrete_classes["weapons"] is Weapon
        assert manager.token_factory.has_type(Weapon)

    def test_register_countable_class(self) -> None:
        """Can register countable asset class."""

        class Currency(CountableAsset):
            pass

        manager = AssetManager()
        manager.register_countable_class("currency", Currency)

        assert "currency" in manager.countable_classes
        assert manager.countable_classes["currency"] is Currency

    def test_register_multiple_types(self) -> None:
        """Can register multiple types."""

        class Weapon(AssetType):
            pass

        class Armor(AssetType):
            pass

        manager = AssetManager()
        manager.register_discrete_class("weapons", Weapon)
        manager.register_discrete_class("armor", Armor)

        assert len(manager.discrete_classes) == 2


class TestAssetManagerLoading:
    """Test loading assets from YAML and data."""

    @pytest.fixture
    def manager(self) -> AssetManager:
        return AssetManager()

    @pytest.fixture
    def weapon_class(self) -> type[AssetType]:
        class Weapon(AssetType):
            damage: int = 10
            weight: float = 1.0

        return Weapon

    @pytest.fixture
    def currency_class(self) -> type[CountableAsset]:
        class Currency(CountableAsset):
            value: float = 1.0

        return Currency

    def test_load_discrete_from_data(
        self, manager: AssetManager, weapon_class: type[AssetType]
    ) -> None:
        """Can load discrete assets from data dicts."""

        manager.register_discrete_class("weapons", weapon_class)

        data = [
            {"label": "sword", "damage": 15, "weight": 3.5},
            {"label": "dagger", "damage": 8, "weight": 1.0},
        ]

        count = manager.load_discrete_from_data("weapons", data)

        assert count == 2
        assert weapon_class.get_instance("sword") is not None
        assert weapon_class.get_instance("dagger") is not None

    def test_load_countable_from_data(
        self, manager: AssetManager, currency_class: type[CountableAsset]
    ) -> None:
        """Can load countable assets from data dicts."""

        manager.register_countable_class("currency", currency_class)

        data = [
            {"label": "gold", "value": 1.0},
            {"label": "gems", "value": 10.0},
        ]

        count = manager.load_countable_from_data("currency", data)

        assert count == 2
        assert currency_class.get_instance("gold") is not None
        assert currency_class.get_instance("gems") is not None

    def test_load_discrete_from_yaml(
        self, manager: AssetManager, weapon_class: type[AssetType]
    ) -> None:
        """Can load discrete assets from YAML file."""

        manager.register_discrete_class("weapons", weapon_class)

        yaml_content = """
- label: sword
  damage: 15
  weight: 3.5
- label: axe
  damage: 20
  weight: 5.0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = Path(f.name)

        try:
            count = manager.load_discrete_from_yaml("weapons", yaml_path)

            assert count == 2
            assert weapon_class.get_instance("sword") is not None
            assert weapon_class.get_instance("axe") is not None
        finally:
            yaml_path.unlink()

    def test_load_unregistered_type_raises(self, manager: AssetManager) -> None:
        """Loading unregistered type raises error."""

        with pytest.raises(KeyError, match="No discrete asset class"):
            manager.load_discrete_from_data("unknown", [])


class TestAssetManagerTokenFactory:
    """Test creating discrete asset tokens."""

    @pytest.fixture
    def manager(self) -> AssetManager:
        return AssetManager()

    @pytest.fixture
    def weapon_class(self) -> type[AssetType]:
        class Weapon(AssetType):
            damage: int = 10
            owner_id: str | None = Field(default=None, json_schema_extra={"instance_var": True})

        return Weapon

    @pytest.fixture
    def graph(self) -> Graph:
        return Graph(label="test")

    def test_create_token(
        self, manager: AssetManager, weapon_class: type[AssetType], graph: Graph
    ) -> None:
        """Can create discrete asset token."""

        manager.register_discrete_class("weapons", weapon_class)
        weapon_class(label="sword", damage=15)

        token = manager.create_token("weapons", "sword", graph)

        assert isinstance(token, Token)
        assert token.label == "sword"
        assert token.graph is graph
        assert token.damage == 15

    def test_create_token_with_instance_vars(
        self, manager: AssetManager, weapon_class: type[AssetType], graph: Graph
    ) -> None:
        """Can create token with instance variables."""

        manager.register_discrete_class("weapons", weapon_class)
        weapon_class(label="sword")

        token = manager.create_token(
            "weapons",
            "sword",
            graph,
            overlay={"owner_id": "player_123"},
        )

        assert token.owner_id == "player_123"

    def test_create_token_missing_singleton_raises(
        self, manager: AssetManager, weapon_class: type[AssetType], graph: Graph
    ) -> None:
        """Creating token for missing singleton raises error."""

        manager.register_discrete_class("weapons", weapon_class)

        with pytest.raises(ValueError, match="No Weapon base named"):
            manager.create_token("weapons", "missing", graph)

    def test_create_token_shows_available(
        self, manager: AssetManager, weapon_class: type[AssetType], graph: Graph
    ) -> None:
        """Error message shows available assets."""

        manager.register_discrete_class("weapons", weapon_class)
        weapon_class(label="sword")
        weapon_class(label="axe")

        with pytest.raises(ValueError) as exc_info:
            manager.create_token("weapons", "missing", graph)

        error = str(exc_info.value)
        assert "sword" in error
        assert "axe" in error


class TestAssetManagerLookup:
    """Test looking up asset definitions."""

    @pytest.fixture
    def manager(self) -> AssetManager:
        return AssetManager()

    @pytest.fixture
    def weapon_class(self) -> type[AssetType]:
        class Weapon(AssetType):
            damage: int = 10

        return Weapon

    @pytest.fixture
    def currency_class(self) -> type[CountableAsset]:
        class Currency(CountableAsset):
            value: float = 1.0

        return Currency

    def test_get_discrete_type(
        self, manager: AssetManager, weapon_class: type[AssetType]
    ) -> None:
        """Can get discrete asset definition."""

        manager.register_discrete_class("weapons", weapon_class)
        weapon_class(label="sword", damage=15)

        asset = manager.get_discrete_type("weapons", "sword")

        assert asset.label == "sword"
        assert asset.damage == 15

    def test_get_missing_discrete_raises(
        self, manager: AssetManager, weapon_class: type[AssetType]
    ) -> None:
        """Getting missing discrete asset raises error."""

        manager.register_discrete_class("weapons", weapon_class)

        with pytest.raises(KeyError, match="No weapons instance"):
            manager.get_discrete_type("weapons", "missing")

    def test_list_discrete(
        self, manager: AssetManager, weapon_class: type[AssetType]
    ) -> None:
        """Can list all discrete asset labels."""

        manager.register_discrete_class("weapons", weapon_class)
        weapon_class(label="sword")
        weapon_class(label="axe")
        weapon_class(label="bow")

        labels = manager.list_discrete("weapons")

        assert set(labels) == {"sword", "axe", "bow"}

    def test_list_empty_type(
        self, manager: AssetManager, weapon_class: type[AssetType]
    ) -> None:
        """Listing empty type returns empty list."""

        manager.register_discrete_class("weapons", weapon_class)

        labels = manager.list_discrete("weapons")

        assert labels == []

    def test_get_countable_type(
        self, manager: AssetManager, currency_class: type[CountableAsset]
    ) -> None:
        """Can get countable asset definition."""

        manager.register_countable_class("currency", currency_class)
        currency_class(label="gold", value=2.0)

        asset = manager.get_countable_type("currency", "gold")

        assert asset.label == "gold"
        assert asset.value == 2.0

    def test_list_countable(
        self, manager: AssetManager, currency_class: type[CountableAsset]
    ) -> None:
        """Can list all countable asset labels."""

        manager.register_countable_class("currency", currency_class)
        currency_class(label="gold")
        currency_class(label="gems")

        labels = manager.list_countable("currency")

        assert set(labels) == {"gold", "gems"}


class TestAssetManagerIntegration:
    """Integration tests for full workflow."""

    def test_full_workflow(self) -> None:
        """Test complete workflow: register → load → create → use."""

        class Weapon(AssetType):
            damage: int = 10
            weight: float = 1.0
            owner_id: str | None = Field(default=None, json_schema_extra={"instance_var": True})

        manager = AssetManager()
        manager.register_discrete_class("weapons", Weapon)

        data = [
            {"label": "sword", "damage": 15, "weight": 3.5},
            {"label": "dagger", "damage": 8, "weight": 1.0},
        ]
        count = manager.load_discrete_from_data("weapons", data)
        assert count == 2

        graph = Graph(label="game")

        sword = manager.create_token("weapons", "sword", graph)
        dagger = manager.create_token("weapons", "dagger", graph)

        assert sword.damage == 15
        assert dagger.damage == 8

        sword.owner_id = "player_1"
        dagger.owner_id = "player_2"

        assert sword.owner_id != dagger.owner_id
