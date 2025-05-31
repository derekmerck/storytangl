import pytest
from uuid import UUID
import pickle

from tangl.core.entity import Entity, Registry

class TestEntity(Entity):
    foo: int = 0

def test_entity_creation_and_label():
    e = TestEntity(foo=42)
    assert isinstance(e.uid, UUID)
    # assert e.label is not None
    assert e.foo == 42
    assert e.matches(foo=42)
    assert not e.matches(foo=43)
    # label defaults to a 6-character slice of uid if not provided
    # assert len(e.label) > 0

def test_entity_structure_unstructure():
    e = TestEntity(foo=7)
    data = e.unstructure()
    restored = TestEntity.structure(data)
    assert restored.foo == 7
    assert restored.uid == e.uid

@pytest.mark.xfail(raises=AttributeError)
def test_predicate_satisfied():
    e = TestEntity(foo=1, predicate=lambda ctx: ctx.get("flag", False))
    assert e.is_satisfied(ctx={"flag": True})
    assert not e.is_satisfied(ctx={"flag": False})


def test_entity_creation():
    e = Entity()
    assert isinstance(e.uid, UUID)
    assert isinstance(e.tags, set)

def test_label_default():
    e = Entity()
    assert isinstance(e.label, str)

def test_has_tags():
    e = Entity(tags={"magic", "fire"})
    assert e.has_tags("magic")
    assert not e.has_tags("water")

def test_has_tags2():

    e = Entity(tags={'tag1', 'tag2'})
    assert e.has_tags('tag1')
    assert e.has_tags('tag1', 'tag2')
    assert not e.has_tags('tag1', 'tag3')

def test_matches():
    e = Entity(label="hero", tags={"magic"})
    assert e.matches(label="hero")
    assert e.matches(tags={"magic"})
    assert not e.matches(label="villain")

def test_filter_by_criteria():
    e1 = Entity(label="hero", tags={"magic"})
    e2 = Entity(label="villain", tags={"dark"})
    results = list(Entity.filter_by_criteria([e1, e2], label="hero"))
    assert len(results) == 1 and results[0] == e1

def test_model_dump():
    e = Entity(label="hero")
    dump = e.unstructure()
    assert "obj_cls" in dump
    assert dump["obj_cls"].__name__ == "Entity"

def test_unstructure_structure():
    e = Entity(label="hero")
    structured = e.unstructure()
    restored = Entity.structure(structured)
    assert restored.label == e.label
    assert restored.uid == e.uid
    assert restored == e

def test_entity_unhashable():
    e = Entity()
    with pytest.raises(TypeError):
        { e }

def test_entity_roundtrip():

    e = Entity(tags=["a", "b", "c"])
    assert isinstance(e.tags, set)
    unstructured = e.unstructure()
    print(unstructured)
    assert isinstance(unstructured['tags'], list)
    ee = Entity.structure(unstructured)
    assert isinstance(ee.tags, set)

def test_entity_equality():

    e = Entity(tags=["a", "b", "c"])
    f = Entity(uid=e.uid, tags=["a", "b", "c"])
    g = Entity(uid=e.uid, tags=["d", "e", "f"])

    assert e == f,     "identical data should be equal"
    assert not e == g, "different data should be unequal"

    class EntitySubclass(Entity): pass

    e1 = EntitySubclass(uid=e.uid, tags=["a", "b", "c"])
    e2 = EntitySubclass(uid=e.uid, tags=["d", "e", "f"])

    assert e != e1, "identical data but different classes should be unequal"
    assert e != e2
    assert g != e2


def test_entity_equality2():
    entity1 = Entity(label="SameLabel")
    assert entity1 == entity1

    entity2 = Entity(label="SameLabel")
    assert entity1 != entity2  # They should have different UIDs

    entity3 = Entity(uid=entity1.uid, label=entity1.label)
    assert entity1 == entity3  # Now they should be equal since UIDs and labels match

    class TestEntity(Entity):
        ...

    entity4 = TestEntity(uid=entity1.uid, label=entity1.label)
    assert entity1 != entity4  # They should have different classes


def test_entity_instantiation1():

    kwargs = {'label': "test label"}

    e = Entity(**kwargs)
    print( e )

    assert e.label == "test label"

    d = e.unstructure()
    print( d )
    assert d['label'] == "test label"

    # does not hash
    with pytest.raises(TypeError):
        { e }

def test_entity_instantiation2():
    import shortuuid
    entity = Entity()
    assert isinstance(entity.uid, UUID)
    assert entity.label == shortuuid.encode(entity.uid)  # label is only first few chars

def test_entity_uid_generation():
    node1 = Entity()
    node2 = Entity()
    assert isinstance(node1.uid, UUID)
    assert isinstance(node2.uid, UUID)
    assert node1.uid != node2.uid

def test_entity_custom_label():
    custom_label = "CustomLabel"
    entity = Entity(label=custom_label)
    assert entity.label == custom_label

def test_entity_model_dump():
    entity = Entity(label="TestLabel")
    dumped = entity.unstructure()
    # assert dumped['obj_cls'] == 'Entity'
    assert dumped['label'] == "TestLabel"
    assert 'uid' in dumped

def test_entity_tags():

    a = Entity()
    assert a.tags == set()

    assert 'tags' not in a.unstructure()  # b/c it's unset

    a = Entity(tags={"a"})
    assert a.tags == {"a"}

    assert a.model_dump()['tags'] == ["a"]

    a = Entity(tags={"a", "b"})
    assert a.tags == {"a", "b"}

    assert a.model_dump()['tags'] in [ ["a", "b"], ["b", "a"] ]

    a = Entity(tags=["a", "b"])
    assert a.tags == {"a", "b"}

    assert a.model_dump()['tags'] in [ ["a", "b"], ["b", "a"] ]

def test_entity_pickles():

    a = Entity(label="test_entity")

    s = pickle.dumps( a )
    print( s )
    res = pickle.loads( s )
    print( res )
    assert a == res

def test_entity_does_not_hash():
    e = Entity()
    print(e.uid, e.label)

    with pytest.raises(TypeError):
        {e}  # mutable, doesn't hash
