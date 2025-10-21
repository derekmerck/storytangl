from __future__ import annotations
import dataclasses
import pytest
from uuid import UUID

from tangl.core import Entity, Singleton, Registry


# --- Helper subclasses used in tests -------------------------------------------------

class Person(Entity):
    name: str | None = None
    age: int | None = None

class Service(Singleton):
    description: str | None = None


class OtherService(Singleton):
    description: str | None = None

@pytest.fixture(autouse=True)
def clear_singletons():
    Service.clear_instances()
    OtherService.clear_instances()
    yield
    Service.clear_instances()
    OtherService.clear_instances()


# --- Entity tests --------------------------------------------------------------------

def test_entity_has_tags_and_matches_simple_attrs():
    p = Person(label="alice", tags={"human", "tester"}, name="Alice", age=30)

    # has_tags
    assert p.has_tags({"human"})
    assert p.has_tags({"human", "tester"})
    assert not p.has_tags({"robot"})

    # matches by attribute equality
    assert p.matches(name="Alice", age=30)
    assert not p.matches(name="Alice", age=31)

    # callable predicate(s) and mixed criteria
    assert p.matches(predicate=lambda e: e.age == 30, name="Alice")
    assert not p.matches(predicate=lambda e: e.age > 30)


def test_entity_matches_predicate_attribute_is_instance():
    p = Person(label="bob", name="Bob")

    # matches will treat 'is_instance' as an attribute that is callable
    # and pass the provided value (a class) into the bound method.
    assert p.matches(is_instance=Person)
    assert not p.matches(is_instance=Service)  # not a Singleton subclass instance

# Removed for now, unnecessary extra complexity
# def test_entity_fields_selector_respects_metadata_defaults():
#     # DEFAULT_FIELD_ANNOTATIONS says 'unique' defaults to False; we haven't
#     # annotated any fields as unique in this test class, so none should match.
#     unique_fields = list(Person._fields(unique=True))
#     assert unique_fields == []
#
#     # And with unique=False we should see all dataclass fields of the class
#     non_unique_fields = {f.name for f in Person._fields(unique=False)}
#     # uid, label, tags, name, age
#     assert {"uid", "label", "tags", "name", "age"} <= non_unique_fields


def test_entity_id_and_state_hash_are_bytes_and_state_changes_hash():
    p = Person(label="carol", name="Carol", age=20)

    id_hash = p._id_hash()
    assert isinstance(id_hash, (bytes, bytearray))

    s0 = p._state_hash()
    p.age = 21
    s1 = p._state_hash()
    assert s0 != s1  # state hash changes when data changes


def test_entity_unstructure_and_structure_roundtrip_with_class_obj():
    p = Person(label="dave", tags={"x"}, name="Dave", age=40)
    data = p.unstructure()
    # entity.unstructure() stores obj_cls as the CLASS OBJECT (not a string)
    assert data["obj_cls"] is Person

    q = Entity.structure(dict(data))  # copy in case structure mutates dict
    assert isinstance(q, Person)
    assert q.label == "dave"
    assert q.name == "Dave"
    assert q.age == 40
    assert q.tags == {"x"}


def test_entity_structure_with_qualname_string_resolves_subclass():
    p = Person(label="eve", name="Eve", age=22)
    data = p.unstructure()

    # Simulate a serializer that flattened the class to its qualname (no module)
    data["obj_cls"] = Person.__qualname__

    q = Entity.structure(dict(data))
    assert isinstance(q, Person)
    assert q.name == "Eve" and q.age == 22 and q.label == "eve"


# --- Registry tests ------------------------------------------------------------------

def test_registry_add_get_remove_and_contains():
    reg: Registry[Person] = Registry(label="people")
    alice = Person(label="alice", name="Alice", age=30)
    bob = Person(label="bob", name="Bob", age=31)

    reg.add(alice)
    reg.add(bob)

    # get by UUID
    assert reg.get(alice.uid) is alice
    assert reg.get(UUID(int=0)) is None

    # contains by UUID, by Entity, and by label (string)
    assert alice.uid in reg
    assert alice in reg
    assert "alice" in reg
    assert "charlie" not in reg

    # remove
    reg.remove(bob.uid)
    assert bob.uid not in reg
    assert bob not in reg
    assert "bob" not in reg


def test_registry_find_and_find_one_with_predicates_and_criteria():
    reg: Registry[Person] = Registry(label="people")
    reg.add(Person(label="a", name="Ann", age=20, tags={"t1"}))
    reg.add(Person(label="b", name="Ben", age=30, tags={"t2"}))
    reg.add(Person(label="c", name="Cal", age=30, tags={"t1", "t3"}))

    # Find by callable predicate (age == 30)
    got = list(reg.find_all(predicate=lambda e: e.age == 30))
    labels = {x.label for x in got}
    assert labels == {"b", "c"}

    # Find by attribute equality (name)
    assert reg.find_one(name="Ann").label == "a"
    assert reg.find_one(name="Zoe") is None

    # Mixed: callable + criteria
    got2 = list(reg.find_all(predicate=lambda e: "t1" in e.tags, age=30))
    assert {x.label for x in got2} == {"c"}


def test_registry_all_labels_and_all_tags():
    reg: Registry[Person] = Registry(label="people")
    reg.add(Person(label="a", tags={"x"}))
    reg.add(Person(label=None, tags={"y"}))  # None labels are skipped
    reg.add(Person(label="b", tags={"x", "z"}))

    assert {"a", "b"}.issubset(reg.all_labels())
    assert reg.all_tags() == {"x", "y", "z"}


def test_registry_get_with_string_raises_use_find_one_message():
    reg: Registry[Person] = Registry(label="people")
    with pytest.raises(ValueError) as ei:
        reg.get("alice")  # type: ignore[arg-type]
    assert "find_one(label='alice')" in str(ei.value)


def test_registry_unstructure_structure_roundtrip_plain():
    reg: Registry[Person] = Registry(label="people")
    a = Person(label="alice", name="Alice", age=30)
    b = Person(label="bob",   name="Bob",   age=31)

    reg.add(a)
    reg.add(b)

    # Unstructure to a string-keyed dict
    payload = reg.unstructure()

    # Expect obj_cls and an internal _data map of items
    assert "obj_cls" in payload
    assert "_data" in payload
    assert isinstance(payload["_data"], list)
    assert len(payload["_data"]) == 2

    # Each entry should itself be an unstructured entity map
    for item in payload["_data"]:
        assert isinstance(item, dict)
        assert "obj_cls" in item
        assert "label" in item

    # Structure: build a new registry from the payload
    new_reg = Registry.structure(dict(payload))  # structure may mutate input; pass a copy

    # After structuring, it should be a Registry[Person] with two items
    assert isinstance(new_reg, Registry)
    persons = list(new_reg.values())
    assert len(persons) == 2

    # Labels survived round-trip
    labels = {p.label for p in persons}
    assert labels == {"alice", "bob"}

    # Optional: ensure the items are of the right subclass and data preserved
    by_label = {p.label: p for p in persons}
    assert isinstance(by_label["alice"], Person)
    assert by_label["alice"].name == "Alice"
    assert by_label["bob"].age == 31

# --- Singleton tests -----------------------------------------------------------------

def test_singleton_unique_by_label_and_instance_registry_per_subclass():
    # Create a Service singleton
    s1 = Service(label="alpha")
    assert Service.get_instance("alpha") is s1

    # Same label in different subclass is allowed and distinct
    o1 = OtherService(label="alpha")
    assert OtherService.get_instance("alpha") is o1
    assert o1 is not s1

    # Duplicate label within same subclass is forbidden
    with pytest.raises(ValueError):
        Service(label="alpha")


def test_singleton_hash_and_id_hash_use_label_not_uid():
    s1 = Service(label="beta")
    s2 = Service(label="gamma")

    # Python __hash__ combines class and label
    assert hash(s1) != hash(s2)

    # _id_hash uses (label, class); different labels => different id hashes
    assert s1._id_hash() != s2._id_hash()


def test_singleton_unstructure_and_structure_roundtrip_returns_same_instance():
    s = Service(label="delta")
    data = s.unstructure()
    # { 'obj_cls': Service, 'label': 'delta' }
    x = Service.structure(dict(data))
    assert x is s  # exact same instance looked up via get_instance


def test_singleton_reduce_pickling_contract_like_get_instance():
    s = Service(label="epsilon")
    func, args = s.__reduce__()
    # The reduce contract returns (callable, args) that should
    # reconstruct the same logical instance.
    assert callable(func)
    rebuilt = func(*args)
    assert rebuilt is s