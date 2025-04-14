from tangl.core import Singleton

import pytest


class MyTestSingleton(Singleton):
    pass

@pytest.fixture(autouse=True)
def clear_my_test_singleton():
    MyTestSingleton.clear_instances()
    yield
    MyTestSingleton.clear_instances()

def test_singleton_creation():

    s1 = MyTestSingleton(label="unique")
    s2 = MyTestSingleton.get_instance("unique")
    assert s1 == s2

    s3 = MyTestSingleton.get_instance("unique")
    assert s1 == s3

    s4 = MyTestSingleton("unique")
    assert s1 == s4

@pytest.mark.xfail(reason="currently trusting of label re-use")
def test_singleton_duplicate_prevention():
    # todo: could implement stricter new/init check
    class DataSingleton(Singleton):
        data: int

    DataSingleton(label="unique", data=123)
    with pytest.raises(ValueError):
        DataSingleton(label="unique", data=456)  # Should fail due to duplicate label

def test_singleton_hashes():

    u = MyTestSingleton(label="unique")
    { u }

def test_singleton_unstructure_structure():
    s1 = MyTestSingleton(label="unique")
    structured = s1.unstructure()
    restored = MyTestSingleton.structure(structured)
    assert restored == s1

def test_singleton_idempotency():
    singleton_a = MyTestSingleton(label="example")
    singleton_b = MyTestSingleton(label="example")
    assert singleton_a is singleton_b
    assert len(MyTestSingleton._instances) == 1

def test_singleton_entity():
    e1 = MyTestSingleton(label='singleton1')

    assert MyTestSingleton._instances[e1.uid] is e1
    assert MyTestSingleton.get_instance('singleton1') is e1

def test_singleton_hash():
    e = MyTestSingleton(label='singleton1')
    assert hash(e) == hash((e.__class__, e.label),)

def test_singleton_uniqueness():
    label = "unique_label"
    singleton1 = MyTestSingleton(label=label)
    singleton2 = MyTestSingleton(label=label)

    assert singleton1 is singleton2
    assert singleton1.uid == singleton2.uid

def test_singleton_get_instance():
    label = "another_unique_label"
    singleton = MyTestSingleton(label=label)

    retrieved_singleton = MyTestSingleton.get_instance(label)
    assert retrieved_singleton is singleton


def test_singleton_distinct_instances():
    singleton1 = MyTestSingleton(label="first_label")
    singleton2 = MyTestSingleton(label="second_label")

    assert singleton1 is not singleton2
    assert singleton1.uid != singleton2.uid


def test_singleton_model_dump():
    label = "singleton_label"
    singleton = MyTestSingleton(label=label)
    dumped = singleton.model_dump()

    assert dumped['obj_cls'] == 'MyTestSingleton'
    assert dumped['label'] == label


def test_singleton_entity_creation():
    """Test that only one instance is created per label."""
    instance1 = MyTestSingleton(label="test_label")
    instance2 = MyTestSingleton(label="test_label")
    assert instance1 is instance2

def test_singleton_unique_instances():
    label_a = "EntityA"
    label_b = "EntityB"
    entity_a = MyTestSingleton(label=label_a)
    entity_b = MyTestSingleton(label=label_b)

    assert entity_a is not entity_b

# def test_singleton_initialization():
#     MyTestSingleton.clear_instances()
#     label = "Entity"
#     entity = MyTestSingleton(label)
#     assert entity._initialized

def test_singleton_initialization():
    """Test that the singleton entity is initialized only once."""
    init_counter = 0

    class InitCountingSingleton(MyTestSingleton):

        def __init__(self, *args, **kwargs):
            nonlocal init_counter
            # This is the same skip code in the base class
            if hasattr(self, "__pydantic_private__") and self._initialized:
                return
            init_counter += 1
            super().__init__(*args, **kwargs)

    instance = InitCountingSingleton(label="new_label")
    assert init_counter == 1, "called initialize once"
    InitCountingSingleton(label="new_label")
    assert init_counter == 1, "doesn't re-initialize"
    InitCountingSingleton(label="new_label")
    assert init_counter == 1, "still doesn't re-initialize"

# No longer behaves this way
# def test_singleton_entity_class_getitem():
#     """Test retrieval of instances by label."""
#     MyTestSingleton.clear()
#     instance = MyTestSingleton("retrieve_label")
#     retrieved_instance = MyTestSingleton["retrieve_label"]
#     assert instance is retrieved_instance

# No longer behaves this way, fails silently, returns None
# def test_singleton_entity_error_on_invalid_label():
#     """Test that an error is raised when retrieving an instance with an invalid label."""
#     MyTestSingleton.clear_instances()
#     with pytest.raises(KeyError):
#         MyTestSingleton.get_instance("invalid_label")

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

def test_search_subclasses():

    class SubclassSingleton(MyTestSingleton):
        ...

    assert SubclassSingleton in MyTestSingleton.__subclasses__()

    a = SubclassSingleton(label="a")

    assert a is SubclassSingleton.get_instance("a")
    # assert a is SubclassSingleton("a")

    assert MyTestSingleton.get_instance("a") is None

    assert a is MyTestSingleton.get_instance("a", search_subclasses=True)
