import pytest
from uuid import UUID

from tangl.core.entity import Entity, Registry, Singleton


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
        assert dump["obj_cls"] == "Entity"

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


class TestRegistry:

    def test_registry_add_find(self):
        r = Registry()
        e = Entity(label="hero")
        r.add(e)
        assert r.find_one(label="hero") == e
        assert r.find(label="hero") == [e]
        assert r['hero'] == e

        with pytest.raises(KeyError):
            r['dog']

    def test_registry_prevent_duplicate(self):
        r = Registry()
        e = Entity(label="hero")
        r.add(e)
        with pytest.raises(ValueError):
            r.add(e)  # Should raise because allow_overwrite=False by default

    def test_registry_unstructure_structure(self):
        r = Registry()
        e = Entity(label="hero")
        r.add(e)
        structured = r.unstructure()
        restored = Registry.structure(structured)
        assert restored.find_one(label="hero") == e


class TestSingleton:

    def test_singleton_creation(self):
        class TestSingleton(Singleton):
            pass

        s1 = TestSingleton(label="unique")
        s2 = TestSingleton.get_instance("unique")
        assert s1 == s2

    def test_singleton_duplicate_prevention(self):
        class TestSingleton(Singleton):
            pass

        TestSingleton(label="unique")
        with pytest.raises(ValueError):
            TestSingleton(label="unique")  # Should fail due to duplicate label

    def test_singleton_hashes(self):

        class TestSingleton(Singleton):
            pass

        u = TestSingleton(label="unique")
        { u }

    def test_singleton_unstructure_structure(self):
        class TestSingleton(Singleton):
            pass
        s1 = TestSingleton(label="unique")
        structured = s1.unstructure()
        restored = TestSingleton.structure(structured)
        assert restored == s1

