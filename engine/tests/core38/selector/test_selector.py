"""Contract tests for ``tangl.core38.selector.Selector``."""

from __future__ import annotations

from typing import Any

from tangl.core38.behavior import Behavior
from tangl.core38.entity import Entity
from tangl.core38.selector import Selector


class ReversibleEntity(Entity):
    """Entity with a property for callable-vs-property selector tests."""

    @property
    def label_rev(self) -> str:
        if self.label is None:
            return ""
        return self.label[::-1]


class Person(Entity):
    name: str = "anonymous"
    age: int = 0


class Weapon(Entity):
    damage: int = 0
    magic: bool = False


class MagicSword(Weapon):
    element: str = "fire"


class TestSelectorConstruction:
    def test_empty_selector_matches_anything(self) -> None:
        assert Selector().matches(Entity())

    def test_selector_stores_criteria_in_extra(self) -> None:
        selector = Selector(label="x")
        assert selector.__pydantic_extra__["label"] == "x"

    def test_selector_with_predicate_not_in_extra(self) -> None:
        selector = Selector(predicate=lambda e: e.label == "x", label="x")
        assert callable(selector.predicate)
        assert "predicate" not in (selector.__pydantic_extra__ or {})

    def test_from_identifier(self) -> None:
        selector = Selector.from_identifier("hero")
        assert selector.__pydantic_extra__["has_identifier"] == "hero"

    def test_from_kind(self) -> None:
        selector = Selector.from_kind(Entity)
        assert selector.__pydantic_extra__["has_kind"] is Entity

    def test_from_id_alias(self) -> None:
        assert Selector.from_id("hero") == Selector.from_identifier("hero")


class TestSelectorMatching:
    def test_match_by_label(self) -> None:
        assert Selector(label="hero").matches(Entity(label="hero"))

    def test_match_by_label_negative(self) -> None:
        assert not Selector(label="hero").matches(Entity(label="villain"))

    def test_match_by_multiple_fields(self) -> None:
        assert Selector(name="Alice", age=30).matches(Person(name="Alice", age=30))

    def test_match_by_multiple_fields_one_fails(self) -> None:
        assert not Selector(name="Alice", age=31).matches(Person(name="Alice", age=30))

    def test_match_tags_by_equality(self) -> None:
        entity = Entity(tags={"a", "b"})
        assert Selector(tags={"a", "b"}).matches(entity)

    def test_match_tags_by_equality_subset_fails(self) -> None:
        entity = Entity(tags={"a", "b"})
        assert not Selector(tags={"a"}).matches(entity)

    def test_match_has_tags_subset(self) -> None:
        entity = Entity(tags={"a", "b"})
        assert Selector(has_tags={"a"}).matches(entity)

    def test_match_has_tags_passes_set_to_variadic(self) -> None:
        entity = Entity(tags={"a", "b"})
        assert Selector(has_tags={"a", "b"}).matches(entity)

    def test_match_has_kind_subclass(self) -> None:
        assert Selector(has_kind=Entity).matches(MagicSword())

    def test_match_has_kind_wrong_class(self) -> None:
        assert not Selector(has_kind=ReversibleEntity).matches(Weapon())

    def test_match_has_identifier(self) -> None:
        entity = Entity(label="hero")
        assert Selector(has_identifier="hero").matches(entity)

    def test_match_has_identifier_by_uid(self) -> None:
        entity = Entity()
        assert Selector(has_identifier=entity.uid).matches(entity)

    def test_match_caller_kind(self) -> None:
        behavior = Behavior(func=lambda **_: True, wants_caller_kind=Entity)
        assert Selector(caller_kind=Entity).matches(behavior)
        assert not Selector(caller_kind=dict).matches(behavior)

    def test_match_with_predicate_function(self) -> None:
        selector = Selector(predicate=lambda e: e.age > 25)
        assert selector.matches(Person(age=30))

    def test_match_predicate_and_criteria_both_required(self) -> None:
        selector = Selector(predicate=lambda e: e.age > 25, name="Bob")
        assert not selector.matches(Person(name="Alice", age=30))

    def test_match_predicate_fails_short_circuits(self) -> None:
        class Trap(Entity):
            @property
            def explode(self) -> str:
                raise RuntimeError("should not be reached")

        selector = Selector(predicate=lambda _: False, explode="x")
        assert not selector.matches(Trap(label="t"))

    def test_match_missing_attribute_is_non_match(self) -> None:
        assert not Selector(missing="x").matches(Entity())

    def test_match_any_sentinel_is_wildcard(self) -> None:
        entity = Entity(label="hero")
        assert Selector(label=Any, has_identifier="hero").matches(entity)

    def test_match_none_is_not_wildcard(self) -> None:
        assert not Selector(label=None).matches(Entity(label="hero"))

    def test_match_property_uses_equality(self) -> None:
        entity = ReversibleEntity(label="abc")
        assert Selector(label_rev="cba").matches(entity)

    def test_match_property_none_safe(self) -> None:
        entity = ReversibleEntity()
        assert entity.label_rev == ""
        assert Selector(label_rev="").matches(entity)


class TestSelectorFilter:
    def test_filter_returns_matching(self) -> None:
        items = [Entity(label="a"), Entity(label="b"), Entity(label="a")]
        results = list(Selector(label="a").filter(items))
        assert [item.label for item in results] == ["a", "a"]

    def test_filter_empty_result(self) -> None:
        items = [Entity(label="a")]
        assert list(Selector(label="x").filter(items)) == []

    def test_filter_is_lazy(self) -> None:
        result = Selector(label="a").filter([Entity(label="a")])
        assert result.__class__.__name__ == "filter"

    def test_filter_preserves_order(self) -> None:
        first = Entity(label="x")
        second = Entity(label="x")
        results = list(Selector(label="x").filter([first, second]))
        assert results == [first, second]


class TestSelectorComposition:
    def test_with_defaults_adds_new_criteria(self) -> None:
        selector = Selector(label="a").with_defaults(has_kind=Entity)
        assert selector.label == "a"
        assert selector.has_kind is Entity

    def test_with_defaults_does_not_override_existing(self) -> None:
        selector = Selector(label="a").with_defaults(label="b")
        assert selector.label == "a"

    def test_with_defaults_returns_new_selector(self) -> None:
        selector = Selector(label="a")
        changed = selector.with_defaults(has_kind=Entity)
        assert selector is not changed
        assert not hasattr(selector, "has_kind")

    def test_with_criteria_overrides_existing(self) -> None:
        selector = Selector(label="a").with_criteria(label="b")
        assert selector.label == "b"

    def test_with_criteria_narrows_has_kind(self) -> None:
        class Base(Entity):
            pass

        class Child(Base):
            pass

        selector = Selector(has_kind=Base).with_criteria(has_kind=Child)
        assert selector.has_kind is Child
        assert selector.matches(Child())
        assert not selector.matches(Base())

    def test_with_criteria_does_not_widen_has_kind(self) -> None:
        class Base(Entity):
            pass

        class Child(Base):
            pass

        selector = Selector(has_kind=Child).with_criteria(has_kind=Base)
        assert selector.has_kind is Child

    def test_composition_with_predicate(self) -> None:
        selector = Selector(predicate=lambda e: e.label == "a")
        updated = selector.with_criteria(label="a")
        assert updated.matches(Entity(label="a"))


class TestSelectorInteropWithEntity:
    def test_selector_with_has_tags_calls_entity_method(self) -> None:
        entity = Entity(tags={"x", "y"})
        assert Selector(has_tags={"x"}).matches(entity)

    def test_selector_with_has_identifier_calls_entity_method(self) -> None:
        entity = Entity(label="hero")
        assert Selector(has_identifier="hero").matches(entity)

    def test_selector_with_has_kind_calls_entity_method(self) -> None:
        assert Selector(has_kind=Entity).matches(Entity())

    def test_selector_from_identifier_roundtrip(self) -> None:
        entity = Entity()
        assert Selector.from_identifier(entity.uid).matches(entity)
