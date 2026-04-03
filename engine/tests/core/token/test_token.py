"""Contract tests for ``tangl.core.token``."""

from __future__ import annotations

from typing import TypeVar

import pytest
from pydantic import ValidationError

from tangl.core.entity import Entity
from tangl.core.graph import Graph, GraphItem, HierarchicalNode, Node
from tangl.core.selector import Selector
from tangl.core.singleton import Singleton
from tangl.core.token import Token, TokenCatalog

from ..conftest import ArmorType, NPCType, WeaponType

WST = TypeVar("WST", bound=Singleton)


class TestTokenClassGeneration:
    def test_class_getitem_returns_class(self) -> None:
        assert isinstance(Token[WeaponType], type)

    def test_class_getitem_cached(self) -> None:
        assert Token[WeaponType] is Token[WeaponType]

    def test_different_singletons_different_classes(self) -> None:
        assert Token[WeaponType] is not Token[ArmorType]

    def test_wrapper_has_instance_var_fields(self) -> None:
        assert "sharpness" in Token[WeaponType].model_fields

    def test_wrapper_excludes_non_instance_vars(self) -> None:
        assert "damage" not in Token[WeaponType].model_fields

    def test_wrapper_wrapped_cls_set(self) -> None:
        assert Token[WeaponType].wrapped_cls is WeaponType

    def test_wrapper_is_subclass_of_token(self) -> None:
        assert issubclass(Token[WeaponType], Token)

    def test_wrapper_is_subclass_of_node(self) -> None:
        assert issubclass(Token[WeaponType], Node)

    def test_typevar_resolves_to_bound(self) -> None:
        assert Token[WST] is Token[Singleton]

    def test_wrapper_registered_in_module(self) -> None:
        wrapper = Token[WeaponType]
        assert getattr(__import__("tangl.core.token", fromlist=[wrapper.__name__]), wrapper.__name__) is wrapper


class TestTokenCreation:
    def test_create_with_valid_ref(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.token_from == "sword"

    def test_from_ref_no_longer_aliases_token_from(self) -> None:
        WeaponType(label="sword", damage="1d6")
        with pytest.raises(ValidationError):
            Token[WeaponType](from_ref="sword", label="Glamdring")

    def test_label_does_not_infer_token_from(self) -> None:
        WeaponType(label="sword", damage="1d6")
        with pytest.raises(ValidationError):
            Token[WeaponType](label="sword")

    def test_invalid_ref_raises(self) -> None:
        with pytest.raises(ValidationError):
            Token[WeaponType](token_from="missing", label="x")

    def test_token_from_and_label_separate(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.token_from == "sword"
        assert token.label == "Glamdring"

    def test_instance_var_default_from_singleton(self) -> None:
        WeaponType(label="sword", damage="1d6", sharpness=1.4)
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.sharpness == 1.4

    def test_instance_var_override_on_creation(self) -> None:
        WeaponType(label="sword", damage="1d6", sharpness=1.4)
        token = Token[WeaponType](token_from="sword", label="Glamdring", sharpness=2.0)
        assert token.sharpness == 2.0

    def test_is_node(self) -> None:
        WeaponType(label="sword", damage="1d6")
        assert isinstance(Token[WeaponType](token_from="sword", label="Glamdring"), Node)

    def test_is_graph_item(self) -> None:
        WeaponType(label="sword", damage="1d6")
        assert isinstance(Token[WeaponType](token_from="sword", label="Glamdring"), GraphItem)


class TestTokenDelegation:
    def test_read_delegated_field(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.damage == "1d6"

    def test_read_instance_var_field(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring", sharpness=2.0)
        assert token.sharpness == 2.0

    def test_write_instance_var(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring", sharpness=2.0)
        token.sharpness = 0.5
        assert token.sharpness == 0.5

    def test_write_delegated_field_raises(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        with pytest.raises((ValidationError, ValueError)):
            token.damage = "2d6"

    def test_instance_var_independent_of_singleton(self) -> None:
        base = WeaponType(label="sword", damage="1d6", sharpness=1.0)
        token = Token[WeaponType](token_from="sword", label="Glamdring", sharpness=2.0)
        token.sharpness -= 0.5
        assert token.sharpness == 1.5
        assert base.sharpness == 1.0

    def test_multiple_tokens_independent(self) -> None:
        WeaponType(label="sword", damage="1d6", sharpness=1.0)
        a = Token[WeaponType](token_from="sword", label="A")
        b = Token[WeaponType](token_from="sword", label="B")
        a.sharpness = 1.2
        b.sharpness = 0.7
        assert a.sharpness == 1.2
        assert b.sharpness == 0.7

    def test_method_delegation(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.describe() == "A Glamdring dealing 1d6 damage"

    def test_method_rebinding_self(self) -> None:
        NPCType(label="guard", name="default")
        token = Token[NPCType](token_from="guard", label="Citizen", name="Aragorn")
        assert token.greet() == "I am Aragorn"

    def test_missing_attribute_raises(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        with pytest.raises(AttributeError):
            _ = token.nonexistent

    def test_reference_singleton_property(self) -> None:
        base = WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.reference_singleton is base

    def test_reference_singleton_cleared_raises(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        WeaponType.clear_instances()
        with pytest.raises(ValueError):
            _ = token.reference_singleton

    def test_repr_delegates(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring", sharpness=2.0)
        assert "Glamdring" in repr(token)
        assert "sharpness=2.0" in repr(token)


class TestTokenKindMatching:
    def test_has_kind_matches_wrapped_type(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.has_kind(WeaponType)

    def test_has_kind_matches_singleton_base(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.has_kind(Singleton)

    def test_has_kind_matches_node(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.has_kind(Node)

    def test_has_kind_matches_entity(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.has_kind(Entity)

    def test_has_kind_rejects_wrong_type(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert not token.has_kind(ArmorType)

    def test_has_kind_non_class_returns_false(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert not token.has_kind("string")

    def test_has_kind_tuple(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.has_kind((WeaponType, ArmorType))

    def test_has_identifier_matches_referent_label(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.has_identifier("sword")

    def test_has_identifier_matches_token_label_and_referent_label(self) -> None:
        WeaponType(label="sword", damage="1d6")
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        assert token.has_identifier("Glamdring")
        assert token.has_identifier("sword")

    def test_has_identifier_propagates_unexpected_referent_errors(self) -> None:
        class BrokenIdType(Singleton):
            def has_identifier(self, identifier):  # pragma: no cover - exercised through Token
                raise RuntimeError("broken identifier logic")

        BrokenIdType(label="broken")
        token = Token[BrokenIdType](token_from="broken", label="broken_token")
        with pytest.raises(RuntimeError, match="broken identifier logic"):
            token.has_identifier("not_local_match")

    def test_graph_find_by_wrapped_type(self) -> None:
        WeaponType(label="sword", damage="1d6")
        graph = Graph()
        token = Token[WeaponType](token_from="sword", label="Glamdring", registry=graph)
        assert list(graph.find_nodes(Selector(has_kind=WeaponType))) == [token]


class TestTokenGraphIntegration:
    def test_add_to_graph(self) -> None:
        WeaponType(label="sword", damage="1d6")
        graph = Graph()
        token = Token[WeaponType](token_from="sword", label="Glamdring")
        graph.add(token)
        assert graph.get(token.uid) is token

    def test_find_in_graph_by_label(self) -> None:
        WeaponType(label="sword", damage="1d6")
        graph = Graph()
        token = Token[WeaponType](token_from="sword", label="Glamdring", registry=graph)
        assert graph.find_one(Selector(label="Glamdring")) is token

    def test_find_in_graph_by_wrapped_type(self) -> None:
        WeaponType(label="sword", damage="1d6")
        graph = Graph()
        token = Token[WeaponType](token_from="sword", label="Glamdring", registry=graph)
        assert graph.find_node(Selector(has_kind=WeaponType)) is token

    def test_multiple_tokens_in_graph(self) -> None:
        WeaponType(label="sword", damage="1d6")
        ArmorType(label="shield", defense=4)
        graph = Graph()
        a = Token[WeaponType](token_from="sword", label="Glamdring", registry=graph)
        b = Token[ArmorType](token_from="shield", label="Aegis", registry=graph)
        assert graph.nodes == [a, b]

    def test_edge_between_tokens(self) -> None:
        WeaponType(label="sword", damage="1d6")
        ArmorType(label="shield", defense=4)
        graph = Graph()
        a = Token[WeaponType](token_from="sword", label="Glamdring", registry=graph)
        b = Token[ArmorType](token_from="shield", label="Aegis", registry=graph)
        edge = graph.add_edge(a, b, label="blocks")
        assert edge.predecessor is a
        assert edge.successor is b

    def test_token_as_hierarchical_node(self) -> None:
        class HierToken(Token[WeaponType], HierarchicalNode):
            pass

        WeaponType(label="sword", damage="1d6")
        graph = Graph()
        root = HierarchicalNode(label="root", registry=graph)
        child = HierToken(token_from="sword", label="Glamdring", registry=graph)
        root.add_child(child)
        assert child.parent is root

class TestTokenCatalog:
    def test_find_all_uses_singleton_registry(self) -> None:
        WeaponType(label="sword", damage="1d6")
        WeaponType(label="dagger", damage="1d4")
        catalog = TokenCatalog[WeaponType](wst=WeaponType)

        found = list(catalog.find_all(Selector(has_identifier="sword")))
        assert len(found) == 1
        assert found[0].label == "sword"

    def test_materialize_one_uses_instance_label_as_token_from(self) -> None:
        base = WeaponType(label="sword", damage="1d6")
        catalog = TokenCatalog[WeaponType](wst=WeaponType)

        token = catalog.materialize_one(base)
        assert token.token_from == "sword"
        assert token.label == "sword"

    def test_materialize_one_accepts_label_override(self) -> None:
        base = WeaponType(label="sword", damage="1d6")
        catalog = TokenCatalog[WeaponType](wst=WeaponType)

        token = catalog.materialize_one(base, label="Glamdring")
        assert token.token_from == "sword"
        assert token.label == "Glamdring"
