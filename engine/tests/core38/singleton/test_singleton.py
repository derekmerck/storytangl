"""Contract tests for ``tangl.core38.singleton``."""

from __future__ import annotations

import pickle

import pytest
from pydantic import Field, ValidationError

from tangl.core38.singleton import InstanceInheritance, Singleton


class SimpleSingleton(Singleton):
    pass


class ValueSingleton(Singleton):
    value: int = 0


class ChildSingleton(SimpleSingleton):
    pass


class InheritableItem(InstanceInheritance):
    value: int = 0
    name: str = "default"
    items: list[int] = Field(default_factory=list)


@pytest.fixture(autouse=True)
def clear_singletons() -> None:
    for cls in [SimpleSingleton, ValueSingleton, ChildSingleton, InheritableItem]:
        cls.clear_instances()
    yield
    for cls in [SimpleSingleton, ValueSingleton, ChildSingleton, InheritableItem]:
        cls.clear_instances()


class TestSingletonCreation:
    def test_create_with_label(self) -> None:
        instance = SimpleSingleton(label="hero")
        assert instance.label == "hero"

    def test_label_required(self) -> None:
        with pytest.raises(TypeError):
            SimpleSingleton()

    def test_duplicate_label_raises(self) -> None:
        SimpleSingleton(label="hero")
        with pytest.raises(ValidationError):
            SimpleSingleton(label="hero")

    def test_none_label_raises(self) -> None:
        with pytest.raises(ValidationError):
            SimpleSingleton(label=None)


class TestSingletonRegistry:
    def test_get_and_has_instance(self) -> None:
        instance = SimpleSingleton(label="hero")
        assert SimpleSingleton.has_instance("hero")
        assert SimpleSingleton.get_instance("hero") is instance

    def test_subclass_registry_isolated(self) -> None:
        base = SimpleSingleton(label="hero")
        child = ChildSingleton(label="hero")
        assert SimpleSingleton.get_instance("hero") is base
        assert ChildSingleton.get_instance("hero") is child
        assert base is not child

    def test_clear_instances(self) -> None:
        SimpleSingleton(label="hero")
        SimpleSingleton.clear_instances()
        assert not SimpleSingleton.has_instance("hero")


class TestSingletonIdentityAndSerialization:
    def test_hashable_and_hash_contract(self) -> None:
        instance = ValueSingleton(label="x", value=1)
        assert hash(instance) == hash((ValueSingleton, "x"))
        assert instance in {instance}

    def test_frozen_rejects_mutation(self) -> None:
        instance = ValueSingleton(label="x", value=1)
        with pytest.raises(ValidationError):
            instance.label = "y"

    def test_unstructure_roundtrip_reference(self) -> None:
        instance = ValueSingleton(label="x", value=3)
        data = instance.unstructure()
        restored = ValueSingleton.structure(dict(data))
        assert restored is instance
        assert data == {"kind": ValueSingleton, "label": "x"}

    def test_pickle_returns_same_instance(self) -> None:
        instance = ValueSingleton(label="x", value=3)
        restored = pickle.loads(pickle.dumps(instance))
        assert restored is instance


class TestInstanceInheritance:
    def test_inherit_and_override(self) -> None:
        parent = InheritableItem(label="base", value=7, name="base-name")
        child = InheritableItem(label="child", inherit_from="base", name="child-name")
        assert child.value == parent.value
        assert child.name == "child-name"

    def test_missing_parent_raises(self) -> None:
        with pytest.raises(ValueError):
            InheritableItem(label="child", inherit_from="missing")

    def test_mutable_fields_copied_not_shared(self) -> None:
        parent = InheritableItem(label="base", items=[1, 2])
        child = InheritableItem(label="child", inherit_from="base")
        child.items.append(3)
        assert parent.items == [1, 2]
        assert child.items == [1, 2, 3]
