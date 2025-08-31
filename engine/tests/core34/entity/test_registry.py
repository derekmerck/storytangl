import pytest

from tangl.core.entity import Entity, Registry

class TestEntity(Entity):
    foo: int = 0

def test_registry_add_get_find_remove():
    reg = Registry[TestEntity]()
    e1 = TestEntity(foo=1, tags="abc")
    e2 = TestEntity(foo=2, tags="def")
    reg.add(e1)
    reg.add(e2)
    assert reg.get(e1.uid) is e1
    assert reg.find_one(foo=2) is e2
    assert list(reg.find_all(foo=1)) == [e1]

    print( reg.all_tags() )
    assert reg.all_tags() == {"abc", "def"}
    print( reg.all_labels() )
    assert len(reg.all_labels()) == 2

    reg.remove(e1)
    assert reg.get(e1.uid) is None
    assert len(reg) == 1


def test_registry_add_find():
    r = Registry()
    e = Entity(label="hero")
    r.add(e)
    assert r.find_one(label="hero") == e
    assert next(r.find_all(label="hero")) == e

@pytest.mark.xfail(reason="allow_overwrite not implemented yet in current rev")
def test_registry_prevent_duplicate():
    r = Registry()
    e = Entity(label="hero")
    r.add(e)
    with pytest.raises(ValueError):
        r.add(e)  # Should raise because allow_overwrite=False by default

def test_registry_unstructure_structure():
    r = Registry()
    e = Entity(label="hero")
    r.add(e)
    structured = r.unstructure()
    restored = Registry.structure(structured)
    assert restored.find_one(label="hero") == e

class P(Entity):
    data: str = None

def test_find_by_feature():
    g = Registry()
    g.add(P(label="h1", data="123"))
    assert g.find_one(data="123").label == "h1"

def test_find_all_by_feature():
    g = Registry()
    g.add(P(label="h1", data="123"))
    g.add(P(label="h2", data="123"))
    assert 'h1' in [ x.label for x in g.find_all(data="123") ]
    assert 'h2' in [ x.label for x in g.find_all(data="123") ]
