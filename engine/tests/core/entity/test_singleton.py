from tangl.business.core import Singleton

import pytest

class TestSingleton:

    def test_singleton_creation(self):
        class TestSingleton(Singleton):
            pass

        s1 = TestSingleton(label="unique")
        s2 = TestSingleton.get_instance("unique")
        assert s1 == s2

        s3 = TestSingleton.get_instance("unique")
        assert s1 == s3

        s4 = TestSingleton("unique")
        assert s1 == s4

    # def test_singleton_duplicate_prevention(self):
    #     class TestSingleton(Singleton):
    #         data: int
    #
    #     TestSingleton(label="unique", data=123)
    #     with pytest.raises(ValueError):
    #         TestSingleton(label="unique", data=456)  # Should fail due to duplicate label

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

