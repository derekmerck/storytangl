from tangl.core import Singleton

import pytest


class MyTestSingleton(Singleton):
    pass

@pytest.fixture(autouse=True)
def clear_my_test_singleton():
    MyTestSingleton.clear_instances()

class TestSingleton:

    def test_singleton_creation(self):

        s1 = MyTestSingleton(label="unique")
        s2 = MyTestSingleton.get_instance("unique")
        assert s1 == s2

        s3 = MyTestSingleton.get_instance("unique")
        assert s1 == s3

        s4 = MyTestSingleton("unique")
        assert s1 == s4

    @pytest.mark.xfail(reason="currently trusting of label re-use")
    def test_singleton_duplicate_prevention(self):
        # todo: could implement stricter new/init check
        class DataSingleton(Singleton):
            data: int

        DataSingleton(label="unique", data=123)
        with pytest.raises(ValueError):
            DataSingleton(label="unique", data=456)  # Should fail due to duplicate label

    def test_singleton_hashes(self):

        u = MyTestSingleton(label="unique")
        { u }

    def test_singleton_unstructure_structure(self):
        s1 = MyTestSingleton(label="unique")
        structured = s1.unstructure()
        restored = MyTestSingleton.structure(structured)
        assert restored == s1

    def test_singleton_idempotency(self):
        singleton_a = MyTestSingleton(label="example")
        singleton_b = MyTestSingleton(label="example")
        assert singleton_a is singleton_b
        assert len(MyTestSingleton._instances) == 1
