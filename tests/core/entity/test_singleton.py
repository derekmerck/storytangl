from tangl.core.entity.singleton import Singleton

import pytest

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

