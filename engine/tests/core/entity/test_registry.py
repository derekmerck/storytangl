from tangl.core import Entity, Registry

import pytest


def test_registry_add_find():
    r = Registry()
    e = Entity(label="hero")
    r.add(e)
    assert r.find_one(label="hero") == e
    assert r.find(label="hero") == [e]
    assert r['hero'] == e

    with pytest.raises(KeyError):
        r['dog']

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

