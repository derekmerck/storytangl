import pytest
from uuid import UUID

from tangl34.core.entity import Entity, Registry

class TestEntity(Entity):
    foo: int = 0

def test_entity_creation_and_label():
    e = TestEntity(foo=42)
    assert isinstance(e.uid, UUID)
    assert e.label is not None
    assert e.foo == 42
    assert e.match(foo=42)
    assert not e.match(foo=43)
    # label defaults to a 6-character slice of uid if not provided
    assert len(e.label) > 0

def test_entity_structure_unstructure():
    e = TestEntity(foo=7)
    data = e.unstructure()
    restored = TestEntity.structure(data)
    assert restored.foo == 7
    assert restored.uid == e.uid

def test_predicate_satisfied():
    e = TestEntity(foo=1, predicate=lambda ctx: ctx.get("flag", False))
    assert e.is_satisfied(ctx={"flag": True})
    assert not e.is_satisfied(ctx={"flag": False})

def test_registry_add_get_find_remove():
    reg = Registry[TestEntity]()
    e1 = TestEntity(foo=1)
    e2 = TestEntity(foo=2)
    reg.add(e1)
    reg.add(e2)
    assert reg.get(e1.uid) is e1
    assert reg.find_one(foo=2) is e2
    assert reg.find_all(foo=1) == [e1]
    reg.remove(e1)
    assert reg.get(e1.uid) is None
    assert len(reg) == 1