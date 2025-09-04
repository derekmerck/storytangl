from tangl.core.entity import Singleton

import pytest


class MyTestSingleton(Singleton):

    def __init_subclass__(cls, **kwargs):
        print(f"Subclass init {cls.__name__}")
        super().__init_subclass__(**kwargs)

@pytest.fixture(autouse=True)
def clear_my_test_singleton():
    MyTestSingleton.clear_instances()
    yield
    MyTestSingleton.clear_instances()

def test_subclass_shadowing():
    s1 = MyTestSingleton(label="unique")

    class MyTestSingletonSub(MyTestSingleton):
        pass

    s2 = MyTestSingletonSub(label="unique")  # This should pass, unique is unique in subclass registry
    assert MyTestSingletonSub.get_instance("unique") is s2, "Subclass get_instance should shadow parent class registry"

    assert MyTestSingleton.get_instance("unique") is s1, "Subclass registry should _not_ shadow parent class registry"

def test_singleton_creation():

    s1 = MyTestSingleton(label="unique")
    s2 = MyTestSingleton.get_instance("unique")
    assert s1 == s2

    s3 = MyTestSingleton.get_instance("unique")
    assert s1 == s3

    with pytest.raises((KeyError, ValueError)):
        s4 = MyTestSingleton(label="unique")

def test_singleton_hashes():

    u = MyTestSingleton(label="unique")
    { u }

def test_singleton_unstructure_structure():
    s1 = MyTestSingleton(label="unique")
    structured = s1.unstructure()
    restored = MyTestSingleton.structure(structured)
    assert restored == s1

def test_singleton_entity():
    e1 = MyTestSingleton(label='singleton1')

    assert MyTestSingleton._instances.get(e1.uid) is e1
    assert MyTestSingleton.get_instance('singleton1') is e1

def test_singleton_hash():
    e = MyTestSingleton(label='singleton1')
    assert hash(e) == hash((e.__class__, e.label),)

def test_singleton_get_instance():
    label = "another_unique_label"
    singleton = MyTestSingleton(label=label)
    assert singleton is not None
    retrieved_singleton = MyTestSingleton.get_instance(label)
    assert retrieved_singleton is singleton

def test_singleton_distinct_instances():
    singleton1 = MyTestSingleton(label="first_label")
    singleton2 = MyTestSingleton(label="second_label")

    assert singleton1 is not None
    assert singleton1 is not singleton2
    assert singleton1.uid != singleton2.uid

def test_singleton_unstructure():
    label = "singleton_label"
    singleton = MyTestSingleton(label=label)
    dumped = singleton.unstructure()

    assert dumped['obj_cls'] == MyTestSingleton
    assert dumped['label'] == label

def test_singleton_uniqueness():
    """Test that only one instance is created per label."""
    instance1 = MyTestSingleton(label="test_label")
    with pytest.raises((KeyError, ValueError)):
        instance2 = MyTestSingleton(label="test_label")

def test_singleton_entity_reduce():
    """Test that the singleton entity can be pickled by reference."""
    instance = MyTestSingleton(label="pickle_label")
    pickled_data = instance.__reduce__()
    assert pickled_data == (MyTestSingleton.get_instance, ("pickle_label",))

def test_singleton_pickling_support():
    import pickle
    label = "Entity"
    entity = MyTestSingleton(label=label)

    pickled_entity = pickle.dumps(entity)
    unpickled_entity = pickle.loads(pickled_entity)

    assert unpickled_entity is entity

def test_hashing_singletons():
    a = { MyTestSingleton(label="a") }

# def test_search_subclasses():
#
#     class SubclassSingleton(MyTestSingleton):
#         ...
#
#     assert SubclassSingleton in MyTestSingleton.__subclasses__()
#
#     a = SubclassSingleton(label="a")
#
#     assert a is SubclassSingleton.get_instance("a")
#     # assert a is SubclassSingleton("a")
#
#     assert MyTestSingleton.get_instance("a") is None
#
#     assert a is MyTestSingleton.get_instance("a", search_subclasses=True)
