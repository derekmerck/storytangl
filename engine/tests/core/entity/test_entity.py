import pytest
from uuid import UUID

from tangl.core import Entity


class TestEntity:

    def test_entity_creation(self):
        e = Entity()
        assert isinstance(e.uid, UUID)
        assert isinstance(e.tags, set)

    def test_label_default(self):
        e = Entity()
        assert isinstance(e.label, str)

    def test_has_tags(self):
        e = Entity(tags={"magic", "fire"})
        assert e.has_tags("magic")
        assert not e.has_tags("water")

    def test_has_alias(self):
        e = Entity(label="hero")
        assert e.has_alias("hero")
        assert not e.has_alias("villain")

    def test_get_identifiers(self):
        e = Entity(label="hero")
        identifiers = e.get_identifiers()
        assert "hero" in identifiers
        assert e.uid in identifiers

    def test_matches_criteria(self):
        e = Entity(label="hero", tags={"magic"})
        assert e.matches_criteria(label="hero")
        assert e.matches_criteria(tags={"magic"})
        assert not e.matches_criteria(label="villain")

    def test_filter_by_criteria(self):
        e1 = Entity(label="hero", tags={"magic"})
        e2 = Entity(label="villain", tags={"dark"})
        results = Entity.filter_by_criteria([e1, e2], label="hero")
        assert len(results) == 1 and results[0] == e1

    def test_model_dump(self):
        e = Entity(label="hero")
        dump = e.model_dump()
        assert "obj_cls" in dump
        assert dump["obj_cls"].__name__ == "Entity"

    def test_unstructure_structure(self):
        e = Entity(label="hero")
        structured = e.unstructure()
        restored = Entity.structure(structured)
        assert restored.label == e.label
        assert restored.uid == e.uid
        assert restored == e

    def test_entity_unhashable(self):
        e = Entity()
        with pytest.raises(TypeError):
            { e }

    def test_entity_roundtrip(self):

        e = Entity(tags=["a", "b", "c"])
        assert isinstance(e.tags, set)
        unstructured = e.unstructure()
        print(unstructured)
        assert isinstance(unstructured['tags'], list)
        ee = Entity.structure(unstructured)
        assert isinstance(ee.tags, set)

    def test_entity_equality(self):

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


