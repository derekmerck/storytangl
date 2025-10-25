import pytest
from typing import Any

from tangl.core.singleton import RegistrySingleton

def test_basic_registry():
    """Test basic registry functionality"""
    StringRegistry = RegistrySingleton[str, str]

    registry = StringRegistry(label="test")
    registry["key"] = "value"

    assert registry["key"] == "value"
    assert len(registry) == 1
    assert "key" in registry

#
# def test_type_checking():
#     """Test type enforcement"""
#     IntStrRegistry = RegistrySingleton[int, str]
#     registry = IntStrRegistry(label="test")
#
#     # These should work
#     registry[1] = "one"
#     registry[2] = "two"
#
#     # These should fail type checking
#     with pytest.raises(TypeError):
#         registry["not_an_int"] = "value"
#
#     with pytest.raises(TypeError):
#         registry[1] = 123  # not a string


def test_singleton_behavior():
    """Test that registry maintains singleton behavior"""
    AnyRegistry = RegistrySingleton[str, Any]

    r1 = AnyRegistry(label="test")
    r1["a"] = 1

    r2 = AnyRegistry(label="test")
    r2["b"] = 2

    assert r1 is r2
    assert "a" in r1 and "b" in r1
    assert len(r1) == 2


def test_registry_operations():
    """Test dictionary-like operations"""
    Registry = RegistrySingleton[str, int]
    Registry.clear_instances()
    registry = Registry(label="test")

    # Basic operations
    registry["one"] = 1
    registry["two"] = 2

    # Update
    registry.update({"three": 3, "four": 4})

    # Iteration
    assert set(registry.keys()) == {"one", "two", "three", "four"}
    assert sum(registry.values()) == 10

    # Delete
    del registry["one"]
    assert "one" not in registry

    # Clear
    registry.clear()
    assert len(registry) == 0


def test_different_registries():
    """Test multiple registries remain independent"""
    StrRegistry = RegistrySingleton[str, str]
    IntRegistry = RegistrySingleton[str, int]

    StrRegistry.clear_instances()
    IntRegistry.clear_instances()

    str_reg = StrRegistry(label="str_reg")
    int_reg = IntRegistry(label="int_reg")

    str_reg["key"] = "value"
    int_reg["key"] = 123

    assert str_reg["key"] == "value"
    assert int_reg["key"] == 123


def test_registry_copy():
    """Test copying behavior"""
    Registry = RegistrySingleton[str, list[int]]
    Registry.clear_instances()
    registry = Registry(label="test")

    registry["numbers"] = [1, 2, 3]

    # getter should return a new dict
    copied = registry.data
    assert isinstance(copied, dict)
    assert copied == {"numbers": [1, 2, 3]}

    # Modifying copy shouldn't affect original
    copied["numbers"].append(4)
    assert registry["numbers"] == [1, 2, 3]


def test_nested_types():
    """Test registries with complex value types"""
    ComplexRegistry = RegistrySingleton[str, dict[str, list[int]]]
    registry = ComplexRegistry(label="test")

    registry["data"] = {"nums": [1, 2, 3]}
    assert registry["data"]["nums"] == [1, 2, 3]


def test_registry_inheritance():
    """Test that registries work with inheritance"""

    class SpecialRegistry(RegistrySingleton[str, str]):
        def get_uppercase(self, key: str) -> str:
            return self[key].upper()

    registry = SpecialRegistry(label="test")
    registry["name"] = "value"

    assert registry.get_uppercase("name") == "VALUE"


def test_registry_initialization():
    """Test registry initialization with data"""
    Registry = RegistrySingleton[str, int]
    Registry.clear_instances()

    # Initialize with data
    initial_data = {"one": 1, "two": 2}
    registry = Registry(label="test", data=initial_data)

    assert dict(registry) == initial_data

    # Create another instance - should be same singleton
    registry2 = Registry(label="test", data={"three": 3})  # This data is ignored
    assert registry2 is registry
    assert dict(registry2) == initial_data

    # Verify we can still add new items
    registry["four"] = 4
    assert registry["four"] == 4

