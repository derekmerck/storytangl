import pytest
from typing import Optional
from pydantic import Field

from tangl.core.singleton import InheritingSingleton


class TestInheritingSingleton(InheritingSingleton):
    """Test fixture class"""
    value: int = 0
    nested: dict = Field(default_factory=dict)
    items: list = Field(default_factory=list)
    optional: Optional[str] = None


def test_basic_inheritance():
    """Test basic attribute inheritance"""
    base = TestInheritingSingleton(
        label="base",
        value=1,
        nested={"key": "value"},
        items=[1, 2, 3],
        optional="test"
    )

    child = TestInheritingSingleton(
        label="child",
        from_ref="base"
    )

    assert child.value == base.value
    assert child.nested == base.nested
    assert child.items == base.items
    assert child.optional == base.optional
    assert child is not base


def test_override_inheritance():
    """Test overriding inherited values"""
    base = TestInheritingSingleton(
        label="base",
        value=1,
        nested={"key": "value"}
    )

    child = TestInheritingSingleton(
        label="child",
        from_ref="base",
        value=2,  # Override
        nested={"new": "data"}  # Override
    )

    assert child.value == 2
    assert child.nested == {"key": "value", "new": "data"}
    assert child is not base


def test_mutable_independence():
    """Test that mutable attributes are independent"""
    base = TestInheritingSingleton(
        label="base",
        nested={"key": "value"},
        items=[1, 2, 3]
    )

    child = TestInheritingSingleton(
        label="child",
        from_ref="base"
    )

    # Modify child's mutable attributes
    child.nested["new"] = "data"
    child.items.append(4)

    # Base should be unchanged
    assert base.nested == {"key": "value"}
    assert base.items == [1, 2, 3]

    # Child should have modified copies
    assert child.nested == {"key": "value", "new": "data"}
    assert child.items == [1, 2, 3, 4]


# def test_chain_inheritance():
#     """Test chained inheritance"""
#     base = TestInheritingSingleton(
#         label="base",
#         value=1,
#         optional="base"
#     )
#
#     middle = TestInheritingSingleton(
#         label="middle",
#         from_ref="base",
#         value=2
#     )
#
#     child = TestInheritingSingleton(
#         label="child",
#         from_ref="middle",
#         optional="child"
#     )
#
#     assert child.value == 2  # From middle
#     assert child.optional == "child"  # Overridden
#
#     # Check inheritance chain
#     assert child.get_inheritance_chain() == ["base", "middle"]


# def test_circular_inheritance():
#     """Test detection of circular inheritance"""
#     base = TestInheritingSingleton(label="base")
#
#     middle = TestInheritingSingleton(
#         label="middle",
#         from_ref="base"
#     )
#
#     # Attempting to create circular reference
#     with pytest.raises(ValueError) as exc_info:
#         circular = TestInheritingSingleton(
#             label="circular",
#             from_ref="middle",
#         )
#         setattr(base, "from_ref", circular)
#         # base.from_ref = "circular"  # This would create a circle
#
#     assert "Circular inheritance" in str(exc_info.value)


def test_missing_reference():
    """Test handling of missing reference instances"""
    with pytest.raises(KeyError) as exc_info:
        instance = TestInheritingSingleton(
            label="test",
            from_ref="nonexistent"
        )

    assert "Cannot inherit from non-existent instance" in str(exc_info.value)


# def test_alias_compatibility():
#     """Test both from_ref and from alias work"""
#     base = TestInheritingSingleton(
#         label="base",
#         value=1
#     )
#
#     # Test both forms
#     child1 = TestInheritingSingleton(label="child1", from_ref="base")
#     child2 = TestInheritingSingleton(label="child2", **{'from': "base"})
#
#     assert child1.value == child2.value == 1


# def test_inheritance_chain_isolation():
#     """Test that inheritance chains are properly isolated"""
#     base = TestInheritingSingleton(label="base")
#
#     child1 = TestInheritingSingleton(
#         label="child1",
#         from_ref="base"
#     )
#
#     child2 = TestInheritingSingleton(
#         label="child2",
#         from_ref="base"
#     )
#
#     # Each should have independent chains
#     assert child1.get_inheritance_chain() == ["base"]
#     assert child2.get_inheritance_chain() == ["base"]
#
#     # Modifying one chain shouldn't affect others
#     child1.inheritance_chain_.append("test")
#     assert "test" not in child2.get_inheritance_chain()


@pytest.mark.parametrize("field_name,base_value,child_value", [
    ("value", 1, 2),
    ("nested", {"a": 1}, {"b": 2}),
    ("items", [1, 2], [3, 4]),
    ("optional", "base", "child"),
    ("optional", "base", None),
    ("optional", None, "child"),
])
def test_field_inheritance_cases(field_name, base_value, child_value):
    """Test various field inheritance scenarios"""
    # Create base with the field set
    base = TestInheritingSingleton(
        label="base",
        **{field_name: base_value}
    )

    # Create child with field override
    child = TestInheritingSingleton(
        label="child",
        from_ref="base",
        **{field_name: child_value}
    )

    # Field should be overridden
    if field_name != "nested":
        assert getattr(child, field_name) == child_value
    else:
        assert getattr(child, field_name) == child_value | base_value

    # Base should be unchanged
    assert getattr(base, field_name) == base_value


@pytest.fixture(autouse=True)
def cleanup():
    TestInheritingSingleton.clear_instances()
    yield
    TestInheritingSingleton.clear_instances()