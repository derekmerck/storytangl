"""Contract tests for ``tangl.core38.bases`` traits."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ConfigDict, Field
from shortuuid import ShortUUID

from tangl.core38.bases import (
    BaseModelPlus,
    HasAvailability,
    HasContent,
    HasEffects,
    HasIdentity,
    HasOrder,
    HasState,
    Unstructurable,
    is_identifier,
)
from tangl.core38.runtime_op import Effect, Predicate
from tangl.utils.hashing import hashing_func


class TestBaseModelPlus:
    """Tests for schema introspection and force-set behavior."""

    def test_match_fields_by_schema_extra(self) -> None:
        class Demo(BaseModelPlus):
            ident: int = Field(1, json_schema_extra={"is_identifier": True})
            value: int = 2

        assert list(Demo._match_fields(is_identifier=True)) == ["ident"]

    def test_match_methods_by_attribute(self) -> None:
        class Demo(BaseModelPlus):
            @property
            def prop(self) -> int:
                return 1

            def meth(self) -> int:
                return 2

        setattr(Demo.meth, "magic", True)
        assert list(Demo._match_methods(magic=True)) == ["meth"]

    def test_schema_matches_combines_fields_and_methods(self) -> None:
        class Demo(BaseModelPlus):
            ident: int = Field(3, json_schema_extra={"is_identifier": True})

            @is_identifier
            def code(self) -> str:
                return "abc"

        data = Demo()._schema_matches(is_identifier=True)
        assert data["ident"] == 3
        assert data["code()"] == "abc"

    def test_force_set_on_frozen_model(self) -> None:
        class Frozen(BaseModelPlus):
            model_config = ConfigDict(frozen=True)
            x: int = 0

        model = Frozen(x=1)
        model.force_set("x", 7)
        assert model.x == 7


class TestIdentifierDecorator:
    """Tests for the ``is_identifier`` decorator."""

    def test_sets_attribute_and_preserves_callable(self) -> None:
        @is_identifier
        def ident() -> str:
            return "id"

        assert ident.is_identifier is True
        assert ident() == "id"


class TestHasIdentity:
    """Identity trait tests."""

    def test_get_identifiers_includes_field_and_method_sources(self) -> None:
        entity = HasIdentity(label="hero")
        ids = entity.get_identifiers()
        assert entity.uid in ids
        assert entity.label in ids
        assert entity.shortcode() in ids
        assert entity.id_hash() in ids
        assert entity.get_label() in ids

    def test_not_hashable(self) -> None:
        with pytest.raises(TypeError):
            hash(HasIdentity())

    def test_label_stored_as_given(self) -> None:
        entity = HasIdentity(label="Hero Name")
        assert entity.label == "Hero Name"

    def test_eq_by_id_same_uid_different_data(self) -> None:
        uid = uuid4()
        left = HasIdentity(uid=uid, label="a")
        right = HasIdentity(uid=uid, label="b")
        assert left == right

    def test_shortcode_matches_shortuuid(self) -> None:
        entity = HasIdentity()
        assert entity.shortcode() == ShortUUID().encode(entity.uid)

    def test_has_identifier_with_aliases(self) -> None:
        entity = HasIdentity(label="hero")
        assert entity.has_identifier(entity.uid)
        assert entity.has_identifier("hero")
        assert entity.has_identifier(entity.shortcode())
        assert entity.has_identifier(entity.id_hash())

    def test_has_tags_edge_cases(self) -> None:
        entity = HasIdentity(tags={"a", "b"})
        assert entity.has_tags()
        assert entity.has_tags(None)
        assert entity.has_tags({"a", "b"})
        assert entity.has_tags(("a", "b"))
        assert not entity.has_tags("ab")


class TestUnstructurable:
    """Un/structure and value-equality tests."""

    def test_unstructure_includes_kind_and_uid(self) -> None:
        class Demo(Unstructurable, HasIdentity):
            pass

        entity = Demo(label="x")
        data = entity.unstructure()
        assert data["kind"] is Demo
        assert data["uid"] == entity.uid

    def test_unstructure_excludes_marked_fields(self) -> None:
        class Demo(Unstructurable):
            kept: int = 1
            dropped: int = Field(2, json_schema_extra={"exclude": True})

        data = Demo().unstructure()
        assert "kept" not in data
        assert "dropped" not in data

        updated = Demo(kept=9).unstructure()
        assert updated["kept"] == 9
        assert "dropped" not in updated

    def test_structure_uses_kind(self) -> None:
        class Demo(Unstructurable, HasIdentity):
            name: str

        entity = Demo(name="alice")
        restored = Unstructurable.structure(entity.unstructure())
        assert isinstance(restored, Demo)
        assert restored == entity

    def test_guard_unstructure_raises(self) -> None:
        class Guarded(Unstructurable):
            guard_unstructure = True

        with pytest.raises(TypeError):
            Guarded().unstructure()

    def test_evolve_preserves_uid_by_default(self) -> None:
        class Demo(Unstructurable, HasIdentity):
            pass

        entity = Demo(label="v1")
        evolved = entity.evolve(label="v2")
        assert evolved.uid == entity.uid
        assert evolved.label == "v2"

    def test_value_hash_changes_with_data(self) -> None:
        class Demo(Unstructurable, HasIdentity):
            value: int = 0

        left = Demo(value=1)
        right = Demo(value=2)
        assert left.value_hash() != right.value_hash()


class TestHasContent:
    """Content-hash trait tests."""

    def test_eq_by_content_same_content(self) -> None:
        class Demo(HasContent):
            content: str

            def get_hashable_content(self) -> str:
                return self.content

        assert Demo(content="x") == Demo(content="x")
        assert Demo(content="x") != Demo(content="y")

    def test_abstract_enforcement(self) -> None:
        with pytest.raises(TypeError):
            HasContent()


class TestHasOrder:
    """Ordering trait tests."""

    def test_explicit_and_auto_seq(self) -> None:
        explicit = HasOrder(seq=5)
        first = HasOrder()
        second = HasOrder()
        assert explicit.seq == 5
        assert first.seq < second.seq

    def test_has_seq_in_range_and_tuple(self) -> None:
        item = HasOrder(seq=5)
        assert item.has_seq_in(1, 10)
        assert not item.has_seq_in(6, 10)
        assert item.has_seq_in((1, 10))


class TestHasAvailability:
    def test_available_true_when_empty(self) -> None:
        item = HasAvailability()
        assert item.available() is True

    def test_all_predicates_must_pass(self) -> None:
        item = HasAvailability(availability=[
            Predicate(expr="has_key"),
            Predicate(expr="level > 2"),
        ])
        assert item.available({"has_key": True, "level": 3}) is True
        assert item.available({"has_key": True, "level": 1}) is False


class TestHasEffects:
    def test_apply_effects_mutates_namespace(self) -> None:
        item = HasEffects(effects=[Effect(expr="count = count + 1")])
        ns = {"count": 2}
        result = item.apply_effects(ns)
        assert ns["count"] == 3
        assert result is ns


class TestTraitComposition:
    """Composition/MRO behavior tests."""

    def test_left_most_eq_wins(self) -> None:
        class ContentFirst(HasContent, HasIdentity):
            content: str

            def get_hashable_content(self) -> str:
                return self.content

        uid = uuid4()
        left = ContentFirst(uid=uid, content="a")
        right = ContentFirst(uid=uid, content="b")
        assert left != right

    def test_identity_over_value_when_left_most(self) -> None:
        class IdentityFirst(HasIdentity, Unstructurable):
            value: int = 0

        uid = uuid4()
        left = IdentityFirst(uid=uid, value=1)
        right = IdentityFirst(uid=uid, value=2)
        assert left == right

    def test_unstructurable_default_entity_style(self) -> None:
        class ValueFirst(Unstructurable, HasIdentity):
            value: int = 0

        uid = uuid4()
        left = ValueFirst(uid=uid, value=1)
        right = ValueFirst(uid=uid, value=2)
        assert left != right

    def test_composed_identifiers_include_id_and_content_hashes(self) -> None:
        class Full(HasState, HasContent, HasOrder, Unstructurable, HasIdentity):
            content: str = "base"

            def get_hashable_content(self) -> str:
                return self.content

        entity = Full(content="hello")
        ids = entity.get_identifiers()
        assert entity.id_hash() in ids
        assert entity.content_hash() in ids
        assert entity.value_hash() not in ids

    def test_force_set_through_composition(self) -> None:
        class Demo(Unstructurable, HasIdentity):
            value: int = 0

        entity = Demo(value=1)
        entity.force_set("value", 9)
        assert entity.value == 9
        assert entity.id_hash() == hashing_func(entity.__class__, entity.uid)
