import pytest
from uuid import UUID, uuid4
import pickle

from tangl.core import Entity


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

def test_has_alias():
    e = Entity(label="hero")
    assert e.has_alias("hero")
    assert not e.has_alias("villain")

def test_get_identifiers():
    e = Entity(label="hero")
    identifiers = e.get_identifiers()
    assert "hero" in identifiers
    assert e.uid in identifiers

def test_matches_criteria():
    e = Entity(label="hero", tags={"magic"})
    assert e.matches_criteria(label="hero")
    assert e.matches_criteria(tags={"magic"})
    assert not e.matches_criteria(label="villain")

def test_filter_by_criteria():
    e1 = Entity(label="hero", tags={"magic"})
    e2 = Entity(label="villain", tags={"dark"})
    results = Entity.filter_by_criteria([e1, e2], label="hero")
    assert len(results) == 1 and results[0] == e1

def test_model_dump():
    e = Entity(label="hero")
    dump = e.model_dump()
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

    kwargs = {'uid': uuid4(),
              'label': "test label"}

    e = Entity(**kwargs)
    print( e )

    assert e.label == "test label"

    d = e.model_dump()
    print( d )

    # does not hash
    with pytest.raises(TypeError):
        { e }


def test_entity_instantiation2():
    import shortuuid
    entity = Entity()
    assert isinstance(entity.uid, UUID)
    # assert entity.tags == set()
    # Testing label generation based on UID
    # assert entity.label == key_for_secret(str(entity.uid))[0:6]
    assert shortuuid.encode(entity.uid).startswith(entity.label)  # label is only first few chars

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
    dumped = entity.model_dump()
    # assert dumped['obj_cls'] == 'Entity'
    assert dumped['label'] == "TestLabel"
    assert 'uid' in dumped

def test_entity_tags():

    a = Entity()
    assert a.tags == set()

    assert 'tags' not in a.model_dump()  # b/c it's unset

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


def test_has_aliases():
    class MyEntity(Entity):
        alias: set

    e = MyEntity(alias={'alias1', 'alias2'}, label='test_entity')
    assert e.has_alias('alias1')
    assert e.has_alias('alias2')
    assert not e.has_alias('alias3')

    identifiers = e.get_identifiers()
    assert 'alias1' in identifiers
    assert 'alias2' in identifiers
    assert e.label in identifiers
    assert e.short_uid[0:6] in identifiers


def test_identifiers():
    class MyEntity(Entity):
        alias: set

    e = MyEntity(alias={'alias1'}, label='test_label')
    identifiers = e.get_identifiers()
    assert 'alias1' in identifiers
    assert 'test_label' in identifiers
    assert e.short_uid in identifiers


def test_entity_does_not_hash():
    e = Entity()
    print(e.uid, e.label)

    with pytest.raises(TypeError):
        {e}  # mutable, doesn't hash


def test_filtering():
    class MyEntity(Entity):
        alias: set = None

    e0 = MyEntity(alias={'alias1'})
    e1 = MyEntity(alias={'alias1'}, tags={'tag1'})
    e2 = MyEntity(alias={'alias2'}, tags={'tag2'})
    e3 = MyEntity(tags={'tag1', 'tag3', 'tag4'})

    instances = [e0, e1, e2, e3]
    filtered = Entity.filter_by_criteria(instances, alias='alias1')
    assert filtered == [e0, e1], "e0 and e1 both use that alias"
    filtered = Entity.filter_by_criteria(instances, alias='alias1', tags=None)
    assert filtered == [e0], "None query should fail on e1"

    filtered = Entity.filter_by_criteria(instances, tags={'tag2'})
    assert filtered == [e2]
    # checking alias = None doesn't make any sense, just leave it blank
    # filtered = Entity.filter_by_criteria(instances, alias=None, tags={'tag2'})
    # assert filtered == [e2]

    filtered = Entity.filter_by_criteria(instances, tags={'tag1', 'tag2'})
    assert filtered == []

    filtered = Entity.filter_by_criteria(instances, tags={'tag1', 'tag3'})
    assert filtered == [e3]

