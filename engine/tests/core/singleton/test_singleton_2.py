from __future__ import annotations
from uuid import UUID
import pickle

from pydantic import BaseModel, Field, ValidationError
import pytest

from tangl.core.singleton import Singleton

# Test fixtures
# 
# class Singleton(Singleton):
#     """Basic singleton for testing core functionality"""
# 
#     def __init__(self, value: str, **kwargs):
#         self.value = value
#         super().__init__(**kwargs)
# 
#     @classmethod
#     def compute_digest(cls, *, value, **kwargs) -> bytes:
#         return cls.hash_value(value)
# 
#     @staticmethod
#     def _filter_by_value(inst: Singleton, value: str) -> bool:
#         # handles "find_instance" value criterion
#         return inst.value == value


# class Singleton(Singleton, BaseModel):
#     """Test Pydantic integration"""
#     value: str = Field(...)
#     optional: str | None = None
# 
#     @classmethod
#     def compute_digest(cls, *, value, **kwargs) -> bytes:
#         return cls.hash_value(value)

    # @staticmethod
    # def _filter_by_value(inst: Singleton, value: str) -> bool:
    #     return inst.value == value

# Basic functionality tests

@pytest.fixture(autouse=True, scope="function")
def clear_singletons():
    Singleton.clear_instances()
    yield
    Singleton.clear_instances()

def test_singleton_uniqueness():
    """Test that instances with same value share identity"""
    s1 = Singleton(label="test")
    with pytest.raises((KeyError, ValueError)):
        s2 = Singleton(label="test")
    s2 = Singleton.get_instance("test")
    assert s1.uid == s2.uid
    assert s1 is s2
    assert len(Singleton._instances) == 1


def test_different_values_different_instances():
    """Test that different values create different instances"""
    s1 = Singleton(label="test1")
    s2 = Singleton(label="test2")
    assert s1.uid != s2.uid
    assert s1 is not s2
    assert len(Singleton._instances) == 2


# Instance management tests

def test_get_instance():
    s1 = Singleton(label="test")
    s2 = Singleton.get_instance(s1.uid)
    assert s1 is s2


def test_get_instance_missing():
    assert Singleton.get_instance(UUID(int=0)) is None

# Inheritance tests

class ChildSingleton(Singleton):
    pass

@pytest.fixture(autouse=True, scope="function")
def clear_child_singletons():
    ChildSingleton.clear_instances()
    yield
    ChildSingleton.clear_instances()


def test_subclass_instances():
    """Test that subclasses maintain separate instance registries"""
    parent = Singleton(label="test")
    child = ChildSingleton(label="test")

    assert parent.uid != child.uid
    assert parent is not child  # Different registries
    assert len(Singleton._instances) == 1
    assert len(ChildSingleton._instances) == 1


# def test_search_subclasses():
#     child = ChildSingleton(label="test")
#     found = Singleton.get_instance(child.uid, search_subclasses=True)
#     assert found is child


# Pydantic integration tests

def test_pydantic_singleton():
    """Test basic Pydantic integration"""
    s1 = Singleton(label="test")
    assert s1.unstructure() == {"obj_cls": Singleton, "label": "test"}


def test_pydantic_validation():
    """Test that Pydantic validation still works"""
    with pytest.raises((ValueError, TypeError)):
        Singleton()  # Missing required field


# def test_pydantic_optional_fields():
#     """Test optional fields behave correctly"""
#     s1 = Singleton(label="test", optional="opt")
#     s2 = Singleton(label="test")  # Same identity even with different optional
#     assert s1 is s2
#     assert s1.optional == "opt"


def test_pydantic_immutability():
    """Test that instances are immutable"""
    s = Singleton(label="test")
    with pytest.raises((AttributeError, ValidationError),):
        s.value = "new value"


# Serialization tests

def test_pickle_singleton():
    """Test pickle serialization/deserialization"""
    original = Singleton(label="test")
    pickled = pickle.dumps(original)
    unpickled = pickle.loads(pickled)
    assert original is unpickled


def test_clear_instances():
    """Test instance clearing"""
    Singleton(label="test1")
    Singleton(label="test2")
    ChildSingleton(label="test3")

    Singleton.clear_instances()
    assert len(Singleton._instances) == 0
    ChildSingleton.clear_instances()
    assert len(ChildSingleton._instances) == 0


# Error handling tests

def test_duplicate_registration_error():
    """Test error on duplicate registration attempt"""
    s = Singleton(label="test")

    # Try to register same instance again
    with pytest.raises((AttributeError, KeyError)):
        Singleton.register_instance(s)


def test_missing_digest_error():
    """Test error when digest computation fails"""

    class BadSingleton(Singleton):
        def compute_digest(self) -> bytes:
            return None

    with pytest.raises((ValueError, TypeError),):
        BadSingleton()


# Filter tests

def test_find_instances():
    """Test instance filtering"""
    s1 = Singleton(label="test1")
    s2 = Singleton(label="test2")

    found = Singleton.find_instance(label="test1")
    assert found is s1

    found = Singleton.find_instance(label="test2")
    assert found is s2

# def test_singleton_reinitialization():
#     """Test that the singleton entity is initialized only once."""
#
#     new_counter = 0
#     init_counter = 0
#
#     class InitCounting:
#
#         def __new__(cls, *args, **kwargs):
#             nonlocal new_counter
#             new_counter += 1
#             return super().__new__(cls, **kwargs)
#
#         def __init__(self, **kwargs):
#             nonlocal init_counter
#             init_counter += 1
#             super().__init__(**kwargs)
#
#     class InitCountingSingleton(Singleton, InitCounting):
#         @classmethod
#         def compute_digest(cls, **kwargs) -> bytes:
#             return cls.hash_value("fixed")  # Same identity for all instances
#
#     instance = InitCountingSingleton()
#     # called initialize
#     assert init_counter == 1
#     assert new_counter == 1
#     # doesn't re-init
#     InitCountingSingleton()
#     assert init_counter == 1
#     assert new_counter == 1
#     InitCountingSingleton()
#     assert init_counter == 1
#     assert new_counter == 1


# def test_singleton_inheritance_initialization():
#     """Test initialization counting with inheritance"""
#     new_counter = 0
#     init_counter = 0
#
#     class InitCounting:
#         def __new__(cls, *args, **kwargs):
#             nonlocal new_counter
#             new_counter += 1
#             return super().__new__(cls)
#
#         def __init__(self, **kwargs):
#             nonlocal init_counter
#             init_counter += 1
#             super().__init__(**kwargs)
#
#     class BaseSingleton(Singleton, InitCounting):
#         @classmethod
#         def compute_digest(cls, **kwargs) -> bytes:
#             return cls.hash_value("base")
#
#     class ChildSingleton(BaseSingleton):
#         @classmethod
#         def compute_digest(cls, **kwargs) -> bytes:
#             return cls.hash_value("child")
#
#     # Base singleton init
#     base = BaseSingleton()
#     assert new_counter == 1
#     assert init_counter == 1
#
#     # Second base instance - no new init
#     base2 = BaseSingleton()
#     assert new_counter == 1
#     assert init_counter == 1
#
#     # Child singleton gets own init
#     child = ChildSingleton()
#     assert new_counter == 2
#     assert init_counter == 2
#
#     # Second child instance - no new init
#     child2 = ChildSingleton()
#     assert new_counter == 2
#     assert init_counter == 2


# def test_singleton_failed_creation():
#     """Test initialization counting when creation fails"""
#     new_counter = 0
#     init_counter = 0
#
#     class InitCounting:
#         def __new__(cls, *args, **kwargs):
#             nonlocal new_counter
#             new_counter += 1
#             return super().__new__(cls)
#
#         def __init__(self, **kwargs):
#             nonlocal init_counter
#             init_counter += 1
#             super().__init__(**kwargs)
#
#     class FailingSingleton(Singleton, InitCounting):
#         @classmethod
#         def compute_digest(cls, **kwargs) -> bytes:
#             if kwargs.get('fail'):
#                 raise ValueError("Failed to compute digest")
#             return cls.hash_value("fixed")
#
#     # Successful creation
#     success = FailingSingleton()
#     assert new_counter == 1
#     assert init_counter == 1
#
#     # Failed creation shouldn't complete initialization
#     with pytest.raises(ValueError):
#         FailingSingleton(fail=True)
#     assert new_counter == 2  # __new__ still called
#     assert init_counter == 1  # but __init__ wasn't
#
#
# def test_singleton_pydantic_initialization():
#     """Test initialization counting with Pydantic"""
#     new_counter = 0
#     init_counter = 0
#
#     class InitCounting:
#         def __new__(cls, *args, **kwargs):
#             nonlocal new_counter
#             new_counter += 1
#             return super().__new__(cls)
#
#         def __init__(self, **kwargs):
#             nonlocal init_counter
#             init_counter += 1
#             super().__init__(**kwargs)
#
#     class Singleton_(Singleton, InitCounting, BaseModel):
#         value: str
#
#         @classmethod
#         def compute_digest(cls, *, value: str, **kwargs) -> bytes:
#             return cls.hash_value(value)
#
#     # First creation with validation
#     s1 = Singleton(label="test")
#     assert new_counter == 1
#     assert init_counter == 1
#
#     # Same value - no new init
#     s2 = Singleton(label="test")
#     assert new_counter == 1
#     assert init_counter == 1
#
#     # # Failed validation shouldn't complete initialization
#     # with pytest.raises(ValidationError):
#     #     Singleton(label=123)  # wrong type
#     # assert new_counter == 2  # __new__ still called
#     # assert init_counter == 1  # but __init__ wasn't
#
# # Cleanup after tests
# @pytest.fixture(autouse=True, scope="function")
# def cleanup():
#     Singleton.clear_instances()
#     Singleton.clear_instances()
#     yield
#     Singleton.clear_instances()
