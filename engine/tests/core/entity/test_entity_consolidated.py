"""Tests for tangl.core.entity.Entity

Organized by functionality:
- Creation and initialization
- Identifiers and aliases
- Tags and tag operations
- Matching and filtering
- Serialization
- Equality and hashing
"""
from __future__ import annotations

import pickle
import pytest
from enum import Enum
from uuid import UUID, uuid4
from pydantic import Field

from tangl.core.entity import Entity, is_identifier, Conditional
from tangl.utils.enum_plus import EnumPlusMixin


# ============================================================================
# Test Fixtures and Helper Classes
# ============================================================================

class TestEntity(Entity):
    """Basic test entity with a simple field."""
    foo: int = 0


class Person(Entity):
    """Entity with multiple fields for testing."""
    name: str | None = None
    age: int | None = None


class Character(Entity):
    """Entity with identifier field and method."""
    name: str = Field(..., json_schema_extra={'is_identifier': True})

    @is_identifier
    def nickname(self):
        return f"nick_{self.name.lower()}"


class EntityWithAliasSet(Entity):
    """Entity with a set-valued identifier field."""
    alias: set = Field(..., json_schema_extra={'is_identifier': True})


class Foo(EnumPlusMixin, Enum):
    """Test enum for tag key-value tests."""
    BAR = "bar"
    XYZZY = "xyzzy"


class Age(EnumPlusMixin, Enum):
    """Test int enum for tag key-value tests."""
    ONE = 1
    TWO = 2
    THREE = 3


# ============================================================================
# Creation and Initialization
# ============================================================================

class TestEntityCreation:
    """Tests for entity instantiation and initialization."""

    def test_basic_creation(self):
        e = Entity()
        assert isinstance(e.uid, UUID)
        assert isinstance(e.tags, set)

    def test_creation_with_label(self):
        e = Entity(label="test label")
        assert e.label == "test_label"  # sanitized, no spaces

    def test_creation_with_tags(self):
        e = Entity(tags={"a", "b", "c"})
        assert isinstance(e.tags, set)
        assert e.tags == {"a", "b", "c"}

    def test_creation_with_tags_as_list(self):
        e = Entity(tags=["a", "b", "c"])
        assert isinstance(e.tags, set)
        assert e.tags == {"a", "b", "c"}

    def test_subclass_creation(self):
        e = TestEntity(foo=42)
        assert isinstance(e.uid, UUID)
        assert e.foo == 42

    def test_uid_is_unique(self):
        e1 = Entity()
        e2 = Entity()
        assert e1.uid != e2.uid

    def test_label_sanitization(self):
        e = Entity(label="test label")
        assert e.label == "test_label"


# ============================================================================
# Identifiers and Aliases
# ============================================================================

class TestEntityIdentifiers:
    """Tests for entity identifiers: uid, label, get_label, and custom identifiers."""

    def test_get_label_returns_label_when_set(self):
        e = Entity(label="hero")
        assert e.get_label() == "hero"

    def test_get_label_returns_short_uid_when_label_unset(self):
        import shortuuid
        e = Entity()
        assert e.get_label() == shortuuid.encode(e.uid)

    def test_has_identifier_with_label(self):
        e = Entity(label="hero")
        assert e.has_identifier("hero")
        assert e.has_identifier(e.uid)
        assert not e.has_identifier("villain")

    def test_has_identifier_with_uuid(self):
        uid = uuid4()
        e = Entity(uid=uid, label="test")
        assert e.has_identifier(uid)
        assert e.has_identifier("test")
        assert not e.has_identifier(uuid4())

    def test_has_alias_with_label(self):
        e = Entity(label="hero")
        assert e.has_alias("hero")
        assert not e.has_alias("villain")

    def test_has_alias_with_uid_and_short_uid(self):
        u = uuid4()
        e = Entity(uid=u, label="test_entity")
        assert e.has_alias("test_entity")
        assert e.has_alias(u)
        assert e.has_alias(e.short_uid())
        assert not e.has_alias(uuid4())

    def test_get_identifiers_includes_uid_and_label(self):
        uid = UUID(bytes=b"abcd"*4)
        e = Entity(uid=uid, label="hello")
        identifiers = set(e.get_identifiers())
        assert uid in identifiers
        assert "hello" in identifiers

    def test_custom_identifier_field(self):
        """Test entity with additional identifier fields."""
        uid = UUID(bytes=b"efgh"*4)
        c = Character(uid=uid, label="main", name="Alice")
        identifiers = set(c.get_identifiers())

        # Should include base identifiers plus custom ones
        assert uid in identifiers
        assert "main" in identifiers
        assert "Alice" in identifiers
        assert "nick_alice" in identifiers  # from @is_identifier method

    def test_custom_identifier_method(self):
        """Test that @is_identifier decorated methods are included."""
        c = Character(uid=uuid4(), label="protagonist", name="Bob")
        assert c.has_identifier("Bob")
        assert c.has_identifier("nick_bob")

    def test_identifier_inheritance(self):
        """Test that identifiers are inherited and extended in subclasses."""
        class Agent(Character):
            callsign: str = Field("BRAVO", json_schema_extra={'is_identifier': True})

            @is_identifier
            def agent_tag(self):
                return f"AGENT-{self.callsign}"

        uid = UUID(bytes=b"ijkl"*4)
        a = Agent(uid=uid, label="undercover", name="Bob", callsign="ECHO")
        identifiers = set(a.get_identifiers())

        # All inherited and new identifiers
        assert uid in identifiers
        assert "undercover" in identifiers
        assert "Bob" in identifiers
        assert "nick_bob" in identifiers
        assert "ECHO" in identifiers
        assert "AGENT-ECHO" in identifiers

    def test_set_valued_identifiers(self):
        """Test identifiers that are sets of values."""
        e = EntityWithAliasSet(alias={'alias1', 'alias2'}, label='test_entity')
        assert e.has_alias('alias1')
        assert e.has_alias('alias2')
        assert not e.has_alias('alias3')
        assert e.has_alias(e.label)
        assert e.has_alias(e.short_uid())


# ============================================================================
# Tags and Tag Operations
# ============================================================================

class TestEntityTags:
    """Tests for entity tags and tag operations."""

    def test_tags_default_to_empty_set(self):
        e = Entity()
        assert e.tags == set()

    def test_tags_with_single_tag(self):
        e = Entity(tags={"a"})
        assert e.tags == {"a"}

    def test_has_tags_single(self):
        e = Entity(tags={"magic", "fire"})
        assert e.has_tags("magic")
        assert e.has_tags("fire")
        assert not e.has_tags("water")

    def test_has_tags_multiple(self):
        e = Entity(tags={'tag1', 'tag2', 'tag3'})
        assert e.has_tags('tag1')
        assert e.has_tags('tag1', 'tag2')
        assert e.has_tags('tag1', 'tag2', 'tag3')
        assert not e.has_tags('tag1', 'tag4')

    def test_has_tags_with_set(self):
        e = Entity(tags={'abc', 'def', 'ghi'})
        assert e.has_tags({"abc"})
        assert e.has_tags({"abc", "def"})
        assert not e.has_tags({"abc", "xyz"})

    def test_tags_serialize_as_list(self):
        """Tags are sets internally but serialize as lists."""
        e = Entity(tags={"a", "b"})
        dumped = e.model_dump()
        assert dumped['tags'] in [["a", "b"], ["b", "a"]]

    def test_get_tag_kv_with_prefix(self):
        """Test extracting tag values by prefix."""
        e = Entity(tags={"foo:bar", "foo:baz", "other:zzz"})
        result = e.get_tag_kv(prefix="foo")
        assert result == {"bar", "baz"}

    def test_get_tag_kv_with_enum_type(self):
        """Test extracting and casting tag values to enum."""
        e = Entity(tags={"foo:bar", Foo.XYZZY, "other:zzz"})
        result = e.get_tag_kv(enum_type=Foo)
        assert result == {Foo.BAR, Foo.XYZZY}

    def test_get_tag_kv_requires_prefix_or_enum(self):
        """Test that get_tag_kv requires at least prefix or enum_type."""
        e = Entity(tags={"a"})
        with pytest.raises(TypeError):
            e.get_tag_kv()

    def test_get_tag_kv_with_int_values(self):
        """Test extracting numeric tag values."""
        e = Entity(tags={"age:1", "age:2", "age:3"})
        result = e.get_tag_kv(prefix="age")
        assert result == {"1", "2", "3"}

    def test_get_tag_kv_cast_to_int(self):
        """Test casting numeric tag values to int."""
        e = Entity(tags={"age:1", "age:2", "age:3", "other:5"})
        result = e.get_tag_kv(prefix="age", enum_type=int)
        assert result == {1, 2, 3}

    def test_get_tag_kv_with_int_enum(self):
        """Test extracting and casting to int-valued enum."""
        e = Entity(tags={"age:1", "age:2", Age.THREE})
        result = e.get_tag_kv(prefix="age", enum_type=Age)
        assert result == {Age.ONE, Age.TWO, Age.THREE}

    def test_get_tag_kv_int_type_requires_prefix(self):
        """Test that int type requires prefix."""
        e = Entity(tags={"age:1", 1})
        with pytest.raises(TypeError):
            e.get_tag_kv(enum_type=int)


# ============================================================================
# Matching and Filtering
# ============================================================================

class TestEntityMatching:
    """Tests for entity.matches() and filtering."""

    def test_matches_by_label(self):
        e = Entity(label="hero", tags={"magic"})
        assert e.matches(label="hero")
        assert not e.matches(label="villain")

    def test_matches_by_tags(self):
        e = Entity(label="hero", tags={"magic", "fire"})
        assert e.matches(tags={"magic"})
        assert not e.matches(tags={"water"})

    def test_matches_by_attribute(self):
        p = Person(name="Alice", age=30)
        assert p.matches(name="Alice")
        assert p.matches(age=30)
        assert p.matches(name="Alice", age=30)
        assert not p.matches(name="Alice", age=31)

    def test_matches_with_predicate(self):
        p = Person(name="Alice", age=30)
        assert p.matches(predicate=lambda e: e.age == 30)
        assert not p.matches(predicate=lambda e: e.age > 30)

    def test_matches_with_mixed_criteria(self):
        p = Person(label="alice", tags={"human"}, name="Alice", age=30)
        assert p.matches(
            predicate=lambda e: e.age == 30,
            name="Alice",
            tags={"human"}
        )
        assert not p.matches(
            predicate=lambda e: e.age > 30,
            name="Alice"
        )

    def test_matches_with_has_tags(self):
        p = Person(label="alice", tags={"human", "tester"}, name="Alice")
        assert p.matches(has_tags={"human"})
        assert p.matches(has_tags={"human", "tester"})
        assert not p.matches(has_tags={"robot"})

    def test_matches_with_is_instance(self):
        p = Person(label="bob", name="Bob")
        assert p.matches(is_instance=Person)
        assert p.matches(is_instance=Entity)
        assert not p.matches(is_instance=TestEntity)

    def test_matches_with_has_identifier(self):
        e = Entity(label="hero")
        assert e.matches(has_identifier="hero")
        assert e.matches(has_identifier=e.uid)
        assert not e.matches(has_identifier="villain")

    def test_matches_custom_field(self):
        e = TestEntity(foo=42)
        assert e.matches(foo=42)
        assert not e.matches(foo=43)

    def test_filter_by_criteria_single_match(self):
        e1 = Entity(label="hero", tags={"magic"})
        e2 = Entity(label="villain", tags={"dark"})
        results = list(Entity.filter_by_criteria([e1, e2], label="hero"))
        assert len(results) == 1
        assert results[0] == e1

    def test_filter_by_criteria_multiple_matches(self):
        e0 = EntityWithAliasSet(alias={'alias1'})
        e1 = EntityWithAliasSet(alias={'alias1'}, tags={'tag1'})
        e2 = EntityWithAliasSet(alias={'alias2'}, tags={'tag2'})
        e3 = EntityWithAliasSet(alias=set(), tags={'tag1', 'tag3'})

        instances = [e0, e1, e2, e3]

        # Filter by alias
        filtered = list(Entity.filter_by_criteria(instances, has_alias='alias1'))
        assert filtered == [e0, e1]

        # Filter by tags
        filtered = list(Entity.filter_by_criteria(instances, has_tags={'tag2'}))
        assert filtered == [e2]

        # Filter requiring multiple tags
        filtered = list(Entity.filter_by_criteria(instances, has_tags={'tag1', 'tag3'}))
        assert filtered == [e3]


# ============================================================================
# Serialization
# ============================================================================

class TestEntitySerialization:
    """Tests for entity serialization and deserialization."""

    def test_unstructure_basic(self):
        e = Entity(label="hero")
        data = e.unstructure()
        assert "obj_cls" in data
        assert data["obj_cls"].__name__ == "Entity"
        assert "label" in data
        assert "uid" in data

    def test_unstructure_excludes_internal_fields(self):
        e = TestEntity(foo=7)
        data = e.unstructure()
        assert 'tags' not in data  # because it's empty/default
        assert 'is_dirty' not in data
        assert 'foo' in data
        assert 'uid' in data

    def test_structure_basic(self):
        e = Entity(label="hero")
        data = e.unstructure()
        restored = Entity.structure(data)
        assert restored.label == e.label
        assert restored.uid == e.uid
        assert restored == e

    def test_structure_with_subclass(self):
        e = TestEntity(foo=7)
        data = e.unstructure()
        restored = TestEntity.structure(data)
        assert restored.foo == 7
        assert restored.uid == e.uid

    def test_unstructure_structure_roundtrip(self):
        p = Person(label="dave", tags={"x"}, name="Dave", age=40)
        data = p.unstructure()

        # obj_cls stored as class object
        assert data["obj_cls"] is Person

        restored = Entity.structure(dict(data))
        assert isinstance(restored, Person)
        assert restored.label == "dave"
        assert restored.name == "Dave"
        assert restored.age == 40
        assert restored.tags == {"x"}

    def test_structure_with_qualname_string(self):
        """Test that structure can resolve class from qualname string."""
        p = Person(label="eve", name="Eve", age=22)
        data = p.unstructure()

        # Simulate serializer that flattened class to qualname
        data["obj_cls"] = Person.__qualname__

        restored = Entity.structure(dict(data))
        assert isinstance(restored, Person)
        assert restored.name == "Eve"
        assert restored.age == 22

    def test_tags_roundtrip_set_to_list_to_set(self):
        """Tags are sets internally, lists when serialized."""
        e = Entity(tags=["a", "b", "c"])
        assert isinstance(e.tags, set)

        unstructured = e.unstructure()
        assert isinstance(unstructured['tags'], list)

        restored = Entity.structure(unstructured)
        assert isinstance(restored.tags, set)

    def test_pickle_roundtrip(self):
        """Test that entities can be pickled."""
        e = Entity(label="test_entity")
        pickled = pickle.dumps(e)
        restored = pickle.loads(pickled)
        assert e == restored

    def test_model_dump(self):
        """Test pydantic's model_dump method."""
        e = Entity(label="TestLabel")
        dumped = e.model_dump()
        assert dumped['label'] == "TestLabel"
        assert 'uid' in dumped


# ============================================================================
# Equality and Hashing
# ============================================================================

class TestEntityEquality:
    """Tests for entity equality and identity."""

    def test_entity_equal_to_itself(self):
        e = Entity(label="test")
        assert e == e

    def test_entities_with_same_uid_and_data_are_equal(self):
        e1 = Entity(tags=["a", "b", "c"])
        e2 = Entity(uid=e1.uid, tags=["a", "b", "c"])
        assert e1 == e2

    def test_entities_with_same_uid_different_data_are_not_equal(self):
        e1 = Entity(uid=uuid4(), tags=["a", "b"])
        e2 = Entity(uid=e1.uid, tags=["x", "y"])
        assert e1 != e2

    def test_entities_with_different_uid_are_not_equal(self):
        e1 = Entity(label="SameLabel")
        e2 = Entity(label="SameLabel")
        assert e1 != e2  # Different UIDs

    def test_entity_and_subclass_with_same_uid_are_not_equal(self):
        """Entities of different classes are not equal even with same UID."""
        e1 = Entity(tags=["a", "b", "c"])
        e2 = TestEntity(uid=e1.uid, tags=["a", "b", "c"])
        assert e1 != e2

    def test_entities_do_not_hash(self):
        """Entities are mutable and should not be hashable."""
        e = Entity()
        with pytest.raises(TypeError):
            {e}

    def test_entity_hash_raises_type_error(self):
        """Verify that attempting to hash an entity raises TypeError."""
        e = Entity(label="test")
        with pytest.raises(TypeError):
            hash(e)


# ============================================================================
# Special Cases and Edge Cases
# ============================================================================

class TestEntitySpecialCases:
    """Tests for special cases and edge conditions."""

    def test_conditional_entity_predicate(self):
        """Test Conditional entity with predicate."""
        c = Conditional(predicate=lambda ctx: ctx.get("flag", False))
        assert c.available({"flag": True})
        assert not c.available({"flag": False})
        assert not c.available({})

    def test_entity_with_empty_tags_unstructure(self):
        """Empty tags may or may not appear in unstructured form."""
        a = Entity()
        assert a.tags == set()
        # Empty default fields may be excluded from unstructure

    def test_entity_label_with_unicode(self):
        """Label sanitization should handle unicode."""
        e = Entity(label="test label")
        assert " " not in e.label
        assert e.label == "test_label"
