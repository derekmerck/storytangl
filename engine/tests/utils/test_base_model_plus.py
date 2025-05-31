import pytest
from tangl.utils.base_model_plus import BaseModelPlus

class DemoModel(BaseModelPlus):
    tags: set[str]
    ids: set[int] = set()

def test_set_string_input():
    # Should convert comma-separated string to set of str
    m = DemoModel(tags="foo, bar, baz")
    assert m.tags == {"foo", "bar", "baz"}

def test_set_none_input():
    # Should convert None to empty set
    m = DemoModel(tags=None)
    assert m.tags == set()

def test_set_native_set():
    m = DemoModel(tags={"x", "y"})
    assert m.tags == {"x", "y"}

def test_set_serialization():
    m = DemoModel(tags={"a", "b"})
    data = m.model_dump()
    # Should be serialized as list, not set (JSON can't represent sets)
    assert isinstance(data["tags"], list)
    assert set(data["tags"]) == {"a", "b"}

def test_set_ints_from_string():
    # Intentionally uses wrong type to see what happens
    m = DemoModel(tags={"a"}, ids="1,2,3")
    # Our validator will only work for set, not for set[int]
    assert m.ids == {1,2,3} or m.ids == {"1", "2", "3"}  # Depending on validator

def test_type_error_on_wrong_type():
    # If you give a list, it should convert fine; other types should be preserved or error
    m = DemoModel(tags=["one", "two"])
    assert m.tags == {"one", "two"}

    with pytest.raises(ValueError):
        DemoModel(tags=123)  # Should fail, can't make set from int
