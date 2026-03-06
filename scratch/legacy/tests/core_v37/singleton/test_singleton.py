"""Tests for tangl.core.singleton.Singleton and InheritingSingleton

Organized by functionality:
- Basic singleton behavior
- Instance registry and retrieval
- Inheritance and subclass isolation
- Hashing and identity
- Serialization
- InheritingSingleton with from_ref
"""
from __future__ import annotations

import pickle
import pytest
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ValidationError

from tangl.core.singleton import Singleton, InheritingSingleton


# ============================================================================
# Test Fixtures and Helper Classes
# ============================================================================

class SingletonSubclass(Singleton):
    """Basic test singleton."""
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)


class SimpleLabelSingleton(Singleton):
    """Test singleton with additional field."""
    value: int = Field(default=0)


class ChildSingleton(SingletonSubclass):
    """Child singleton for testing subclass isolation."""
    pass


class InheritingSingletonSubclass(InheritingSingleton):
    """Test class for InheritingSingleton."""
    value: int = 0
    nested: dict = Field(default_factory=dict)
    items: list = Field(default_factory=list)
    optional: Optional[str] = None


class Character(InheritingSingleton):
    """Complex test class for inheritance scenarios."""
    name: str
    level: int = 1
    hp: int = 100
    mp: int = 50
    traits: set[str] = Field(default_factory=set)


@pytest.fixture(autouse=True)
def clear_all_singletons():
    """Clear all singleton registries before and after each test."""
    SingletonSubclass.clear_instances()
    SimpleLabelSingleton.clear_instances()
    ChildSingleton.clear_instances()
    Singleton.clear_instances()
    InheritingSingletonSubclass.clear_instances()
    Character.clear_instances()
    yield
    SingletonSubclass.clear_instances()
    SimpleLabelSingleton.clear_instances()
    ChildSingleton.clear_instances()
    Singleton.clear_instances()
    InheritingSingletonSubclass.clear_instances()
    Character.clear_instances()


# ============================================================================
# Basic Singleton Behavior
# ============================================================================

class TestSingletonBasics:
    """Tests for basic singleton behavior and uniqueness."""

    def test_singleton_creation_and_retrieval(self):
        """Test that singleton can be created and retrieved."""
        s1 = SingletonSubclass(label="unique")
        s2 = SingletonSubclass.get_instance("unique")
        assert s1 == s2
        assert s1 is s2

    def test_singleton_uniqueness_by_label(self):
        """Test that only one instance per label is allowed."""
        s1 = SingletonSubclass(label="unique")
        with pytest.raises((KeyError, ValueError)):
            s2 = SingletonSubclass(label="unique")

    def test_different_labels_create_different_instances(self):
        """Test that different labels create distinct instances."""
        s1 = SimpleLabelSingleton(label="test1")
        s2 = SimpleLabelSingleton(label="test2")
        assert s1.uid != s2.uid
        assert s1 is not s2
        assert len(SimpleLabelSingleton._instances) == 2

    def test_singleton_requires_label(self):
        """Test that label is required."""
        with pytest.raises((TypeError, ValueError, ValidationError)):
            Singleton()

    def test_singleton_rejects_empty_label(self):
        """Test that empty labels are rejected."""
        with pytest.raises((ValueError, ValidationError)):
            SimpleLabelSingleton(label="")

    def test_label_must_be_string(self):
        """Test that label type is validated."""
        with pytest.raises((ValueError, ValidationError)):
            SimpleLabelSingleton(label=123)


# ============================================================================
# Instance Registry and Retrieval
# ============================================================================

class TestSingletonRegistry:
    """Tests for singleton instance registry management."""

    def test_get_instance_by_label(self):
        """Test retrieving instance by label."""
        s1 = SingletonSubclass(label="test")
        s2 = SingletonSubclass.get_instance("test")
        assert s1 is s2

    def test_get_instance_by_uuid(self):
        """Test retrieving instance by UUID."""
        s1 = SimpleLabelSingleton(label="test")
        s2 = SimpleLabelSingleton.get_instance(s1.uid)
        assert s1 is s2

    def test_get_instance_returns_none_for_missing(self):
        """Test that get_instance returns None for missing instances."""
        assert Singleton.get_instance(UUID(int=0)) is None

    def test_has_instance_by_label(self):
        """Test checking instance existence by label."""
        s = SimpleLabelSingleton(label="test")
        assert SimpleLabelSingleton.has_instance("test")
        assert not SimpleLabelSingleton.has_instance("nonexistent")

    def test_has_instance_by_uuid(self):
        """Test checking instance existence by UUID."""
        s = SimpleLabelSingleton(label="test")
        assert SimpleLabelSingleton.has_instance(s.uid)
        assert not SimpleLabelSingleton.has_instance(UUID(int=0))

    def test_find_instance_by_label(self):
        """Test finding instances by criteria."""
        s1 = SimpleLabelSingleton(label="test1")
        s2 = SimpleLabelSingleton(label="test2")

        found = SimpleLabelSingleton.find_instance(label="test1")
        assert found is s1

        found = SimpleLabelSingleton.find_instance(label="test2")
        assert found is s2

    def test_all_instance_labels(self):
        """Test getting all instance labels."""
        s1 = SimpleLabelSingleton(label="test1")
        s2 = SimpleLabelSingleton(label="test2")

        labels = SimpleLabelSingleton.all_instance_labels()
        assert len(labels) == 2
        assert "test1" in labels
        assert "test2" in labels

    def test_clear_instances(self):
        """Test clearing instance registry."""
        SimpleLabelSingleton(label="test1")
        SimpleLabelSingleton(label="test2")
        assert len(SimpleLabelSingleton.all_instance_labels()) == 2

        SimpleLabelSingleton.clear_instances()
        assert len(SimpleLabelSingleton.all_instance_labels()) == 0

    def test_registry_operations(self):
        """Test singleton is properly registered."""
        s = SingletonSubclass(label="test")
        assert SingletonSubclass._instances.get(s.uid) is s
        assert SingletonSubclass.get_instance('test') is s

    def test_duplicate_registration_error(self):
        """Test error on duplicate registration attempt."""
        s = Singleton(label="test")
        with pytest.raises((AttributeError, KeyError)):
            Singleton.register_instance(s)


# ============================================================================
# Inheritance and Subclass Isolation
# ============================================================================

class TestSingletonInheritance:
    """Tests for singleton inheritance and registry isolation."""

    def test_subclass_has_separate_registry(self):
        """Test that subclasses maintain separate instance registries."""
        parent = SingletonSubclass(label="test")
        child = ChildSingleton(label="test")

        assert parent.uid != child.uid
        assert parent is not child
        assert len(SingletonSubclass._instances) == 1
        assert len(ChildSingleton._instances) == 1

    def test_subclass_shadowing(self):
        """Test that subclass registries shadow parent registries appropriately."""
        s1 = SingletonSubclass(label="unique")
        s2 = ChildSingleton(label="unique")

        # Subclass get_instance should find subclass instance
        assert ChildSingleton.get_instance("unique") is s2

        # Parent class get_instance should not be shadowed
        assert SingletonSubclass.get_instance("unique") is s1

    def test_label_inheritance_separate_registries(self):
        """Test label singletons with inheritance."""
        class ChildLabelSingleton(SimpleLabelSingleton):
            pass

        parent = SimpleLabelSingleton(label="test")
        child = ChildLabelSingleton(label="test")

        assert parent is not child
        assert parent.label == child.label
        assert len(SimpleLabelSingleton._instances) == 1
        assert len(ChildLabelSingleton._instances) == 1

    def test_clear_instances_per_class(self):
        """Test that clear_instances only affects specific class."""
        class ChildLabelSingleton(SimpleLabelSingleton):
            pass

        SimpleLabelSingleton(label="test1")
        SimpleLabelSingleton(label="test2")
        ChildLabelSingleton(label="test3")

        assert len(SimpleLabelSingleton.all_instance_labels()) == 2
        assert len(ChildLabelSingleton.all_instance_labels()) == 1

        SimpleLabelSingleton.clear_instances()

        assert len(SimpleLabelSingleton.all_instance_labels()) == 0
        assert len(ChildLabelSingleton.all_instance_labels()) == 1


# ============================================================================
# Hashing and Identity
# ============================================================================

class TestSingletonHashing:
    """Tests for singleton hashing and identity."""

    def test_singleton_is_hashable(self):
        """Test that singletons are hashable (unlike regular entities)."""
        s = SingletonSubclass(label="unique")
        {s}  # Should not raise

    def test_singleton_hash_value(self):
        """Test singleton hash computation."""
        e = SingletonSubclass(label='singleton1')
        assert hash(e) == hash((e.__class__, e.label))

    def test_different_labels_different_hashes(self):
        """Test that different labels produce different hashes."""
        s1 = SimpleLabelSingleton(label="beta")
        s2 = SimpleLabelSingleton(label="gamma")
        assert hash(s1) != hash(s2)

    def test_id_hash_uses_label_not_uid(self):
        """Test that _id_hash uses label, not uid."""
        s1 = SimpleLabelSingleton(label="beta")
        s2 = SimpleLabelSingleton(label="gamma")
        assert s1._id_hash() != s2._id_hash()


# ============================================================================
# Serialization
# ============================================================================

class TestSingletonSerialization:
    """Tests for singleton serialization and deserialization."""

    def test_unstructure_includes_class_and_label(self):
        """Test that unstructure includes obj_cls and label."""
        s = SingletonSubclass(label="unique")
        data = s.unstructure()
        assert data == {"obj_cls": SingletonSubclass, "label": "unique"}

    def test_structure_returns_same_instance(self):
        """Test that structure returns the existing singleton instance."""
        s = SingletonSubclass(label="unique")
        data = s.unstructure()
        restored = SingletonSubclass.structure(dict(data))
        assert restored is s

    def test_roundtrip_unstructure_structure(self):
        """Test full roundtrip serialization."""
        s1 = SingletonSubclass(label="unique")
        structured = s1.unstructure()
        restored = SingletonSubclass.structure(structured)
        assert restored == s1
        assert restored is s1

    def test_pickle_singleton(self):
        """Test pickle serialization returns same instance."""
        original = SingletonSubclass(label="test")
        pickled = pickle.dumps(original)
        unpickled = pickle.loads(pickled)
        assert original is unpickled

    def test_reduce_pickling_contract(self):
        """Test __reduce__ returns correct pickling contract."""
        s = SingletonSubclass(label="epsilon")
        func, args = s.__reduce__()
        assert callable(func)
        rebuilt = func(*args)
        assert rebuilt is s

    def test_pickling_support(self):
        """Test comprehensive pickling support."""
        label = "Entity"
        entity = SingletonSubclass(label=label)

        pickled_entity = pickle.dumps(entity)
        unpickled_entity = pickle.loads(pickled_entity)

        assert unpickled_entity is entity


# ============================================================================
# InheritingSingleton - Basic Inheritance
# ============================================================================

class TestInheritingSingletonBasics:
    """Tests for InheritingSingleton basic inheritance functionality."""

    def test_basic_inheritance(self):
        """Test basic attribute inheritance from another instance."""
        base = InheritingSingletonSubclass(
            label="base",
            value=1,
            nested={"key": "value"},
            items=[1, 2, 3],
            optional="test"
        )

        child = InheritingSingletonSubclass(
            label="child",
            from_ref="base"
        )

        assert child.value == base.value
        assert child.nested == base.nested
        assert child.items == base.items
        assert child.optional == base.optional
        assert child is not base

    def test_inheritance_from_existing_instance(self):
        """Test creating instance with from_ref."""
        base = InheritingSingletonSubclass(label="base_entity", value=42)
        new_instance = InheritingSingletonSubclass(label="new_label", from_ref="base_entity")

        assert new_instance.value == 42
        assert new_instance.label == "new_label"

    def test_override_inheritance(self):
        """Test overriding inherited values."""
        base = InheritingSingletonSubclass(
            label="base",
            value=1,
            nested={"key": "value"}
        )

        child = InheritingSingletonSubclass(
            label="child",
            from_ref="base",
            value=2,
            nested={"new": "data"}
        )

        assert child.value == 2
        assert child.nested == {"key": "value", "new": "data"}  # Merged
        assert child is not base

    def test_data_overriding(self):
        """Test that explicit values override inherited ones."""
        base = InheritingSingletonSubclass(label="base_entity", value=10)
        overriding = InheritingSingletonSubclass(
            label="overriding",
            from_ref="base_entity",
            value=20
        )
        assert overriding.value == 20

    def test_label_not_inherited(self):
        """Test that label is not inherited."""
        base = InheritingSingletonSubclass(label="base_entity", value=5)
        derived = InheritingSingletonSubclass(label="unique_label", from_ref="base_entity")
        assert derived.label == "unique_label"

    def test_error_on_nonexistent_ref(self):
        """Test proper error when referencing non-existent instance."""
        with pytest.raises(KeyError) as exc_info:
            InheritingSingletonSubclass(label="faulty", from_ref="nonexistent")
        assert "nonexistent" in str(exc_info.value) or "Cannot inherit" in str(exc_info.value)

    def test_missing_reference(self):
        """Test handling of missing reference instances."""
        with pytest.raises(KeyError) as exc_info:
            InheritingSingletonSubclass(label="test", from_ref="nonexistent")
        assert "Cannot inherit from non-existent instance" in str(exc_info.value) or "nonexistent" in str(exc_info.value)


# ============================================================================
# InheritingSingleton - Complex Scenarios
# ============================================================================

class TestInheritingSingletonComplex:
    """Tests for complex inheritance scenarios."""

    def test_mutable_independence(self):
        """Test that mutable attributes are independent copies."""
        base = InheritingSingletonSubclass(
            label="base",
            nested={"key": "value"},
            items=[1, 2, 3]
        )

        child = InheritingSingletonSubclass(
            label="child",
            from_ref="base"
        )

        # Modify child's mutable attributes
        child.nested["new"] = "data"
        child.items.append(4)

        # Base should be unchanged
        assert base.nested == {"key": "value"}
        assert base.items == [1, 2, 3]

        # Child should have modified copies
        assert child.nested == {"key": "value", "new": "data"}
        assert child.items == [1, 2, 3, 4]

    def test_character_inheritance(self):
        """Test inheritance with complex Character class."""
        warrior = Character(
            label="warrior",
            name="Generic Warrior",
            hp=150,
            traits={"strong", "brave"}
        )

        elite = Character(
            label="elite",
            from_ref="warrior",
            name="Elite Warrior"
        )

        assert elite.hp == 150  # Inherited
        assert elite.mp == 50  # Default
        assert elite.level == 1  # Default
        assert elite.traits == {"strong", "brave"}  # Inherited
        assert elite.name == "Elite Warrior"  # Overridden
        assert elite.uid != warrior.uid

    def test_chained_inheritance(self):
        """Test inheritance through multiple levels."""
        base = Character(
            label="base",
            name="Base",
            hp=100
        )

        improved = Character(
            label="improved",
            from_ref="base",
            hp=150,
            traits={"tough"}
        )

        elite = Character(
            label="elite",
            from_ref="improved",
            name="Elite",
            traits={"tough", "skilled"}
        )

        assert elite.hp == 150
        assert elite.traits == {"tough", "skilled"}
        assert elite.name == "Elite"
        assert elite.mp == 50

    def test_partial_updates(self):
        """Test minimal overrides with inheritance."""
        base = Character(
            label="base",
            name="Base",
            hp=100,
            traits={"tough"}
        )

        partial = Character(
            label="partial",
            from_ref="base",
            traits={"tough", "quick"}
        )

        assert partial.name == "Base"
        assert partial.hp == 100
        assert partial.traits == {"tough", "quick"}
        assert partial.mp == 50

    def test_complex_data_inheritance(self):
        """Test inheritance of complex data structures."""
        class ComplexCharacter(InheritingSingleton):
            name: str
            stats: dict[str, int] = Field(default_factory=dict)
            buffs: list[str] = Field(default_factory=list)

        base = ComplexCharacter(
            label="base",
            name="Base",
            stats={"str": 10, "dex": 8},
            buffs=["haste"]
        )

        derived = ComplexCharacter(
            label="derived",
            from_ref="base",
            stats={"str": 12}
        )

        assert derived.stats == {"str": 12, "dex": 8}
        assert derived.buffs == ["haste"]
        assert derived.name == "Base"

    def test_inheriting_singleton_hashes(self):
        """Test that InheritingSingleton instances are hashable."""
        base = InheritingSingletonSubclass(label="base", value=1)
        {base}  # Should not raise

        child = InheritingSingletonSubclass(label="child", from_ref="base")
        {child}  # Should not raise

    @pytest.mark.parametrize("field_name,base_value,child_value", [
        ("value", 1, 2),
        ("nested", {"a": 1}, {"b": 2}),
        ("items", [1, 2], [3, 4]),
        ("optional", "base", "child"),
        ("optional", "base", None),
        ("optional", None, "child"),
    ])
    def test_field_inheritance_cases(self, field_name, base_value, child_value):
        """Test various field inheritance scenarios."""
        base = InheritingSingletonSubclass(
            label="base",
            **{field_name: base_value}
        )

        child = InheritingSingletonSubclass(
            label="child",
            from_ref="base",
            **{field_name: child_value}
        )

        # Field should be overridden (or merged for nested)
        if field_name != "nested":
            assert getattr(child, field_name) == child_value
        else:
            assert getattr(child, field_name) == child_value | base_value

        # Base should be unchanged
        assert getattr(base, field_name) == base_value


# ============================================================================
# Edge Cases and Validation
# ============================================================================

class TestSingletonEdgeCases:
    """Tests for edge cases and validation."""

    def test_pydantic_validation_still_works(self):
        """Test that Pydantic validation is enforced."""
        with pytest.raises((ValueError, TypeError)):
            Singleton()  # Missing required label

    def test_pydantic_immutability(self):
        """Test that singleton instances are immutable."""
        s = SimpleLabelSingleton(label="test")
        with pytest.raises(ValidationError):
            s.value = "new value"  # type: ignore

    def test_inheritance_with_missing_ref_keyerror(self):
        """Test KeyError for missing from_ref."""
        with pytest.raises(KeyError):
            Character(
                label="invalid",
                from_ref="nonexistent",
                name="Invalid"
            )
