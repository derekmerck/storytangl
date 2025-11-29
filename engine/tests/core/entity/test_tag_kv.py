import pytest
from enum import Enum

from tangl.core.entity import Entity


class DummyEntity(Entity):
    """Minimal concrete entity for tests."""
    pass

from tangl.utils.enum_plus import EnumPlusMixin

class Foo(EnumPlusMixin, Enum):
    BAR = "bar"
    XYZZY = "xyzzy"

class Age(EnumPlusMixin, Enum):
    ONE = 1
    TWO = 2
    THREE = 3


def test_get_tag_kv_with_prefix_strings_only():
    """When only prefix is provided, return matching string tags."""
    e = DummyEntity(
        tags={"foo:bar", "foo:baz", "other:zzz"},
    )

    result = e.get_tag_kv(prefix="foo")

    # Current implementation returns the full matched strings (group(0))
    assert result == {"bar", "baz"}


def test_get_tag_kv_with_enum_type_mixes_str_and_enum_tags():
    """
    When enum_type is provided:
    - string tags that match the prefix and enum value are cast to the enum
    - existing enum tags of that type are included directly
    """
    e = DummyEntity(
        tags={
            "foo:bar",        # should map to Foo.BAR
            Foo.XYZZY,        # already an enum member
            "other:zzz",      # ignored
        },
    )

    result = e.get_tag_kv(enum_type=Foo)
    assert result == {Foo.BAR, Foo.XYZZY}


def test_get_tag_kv_raises_if_no_prefix_and_no_enum():
    e = DummyEntity(tags=set())
    with pytest.raises(TypeError):
        e.get_tag_kv()


def test_get_tag_kv_prefix_int_values_as_str_by_default():
    """With only prefix, numeric suffixes are returned as strings."""
    e = DummyEntity(
        tags={"age:1", "age:2", "age:3"},
    )

    result = e.get_tag_kv(prefix="age")

    assert result == {"1", "2", "3"}


def test_get_tag_kv_prefix_int_values_cast_to_int():
    """When enum_type=int, suffixes are parsed as ints."""
    e = DummyEntity(
        tags={"age:1", "age:2", "age:3", "other:5"},
    )

    result = e.get_tag_kv(prefix="age", enum_type=int)

    assert result == {1, 2, 3}


def test_get_tag_kv_prefix_int_values_cast_to_int_enum_and_existing_members():
    """
    When enum_type is an IntEnum-like enum, string tags are cast to that enum and
    existing enum members are included.
    """
    e = DummyEntity(
        tags={
            "age:1",
            "age:2",
            Age.THREE,   # already an enum member
        },
    )

    result = e.get_tag_kv(prefix="age", enum_type=Age)

    assert result == {Age.ONE, Age.TWO, Age.THREE}


def test_get_tag_kv_int_type_requires_prefix():
    """enum_type=int without prefix is ambiguous and should raise."""
    e = DummyEntity(tags={"age:1", 1})

    with pytest.raises(TypeError):
        e.get_tag_kv(enum_type=int)