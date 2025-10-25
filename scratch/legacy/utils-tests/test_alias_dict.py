
import pytest
from legacy.utils.alias_dict import AliasDict, HasAliases
from uuid import uuid4

class TestObject(HasAliases):
    def __init__(self, uid, aliases):
        self.uid = uid
        self._aliases = aliases

    def get_aliases(self):
        return self._aliases

@pytest.fixture
def alias_dict():
    return AliasDict()

def test_add_and_retrieve(alias_dict):
    obj_uid = uuid4()
    obj = TestObject(obj_uid, ["alias1", "alias2"])
    alias_dict.add(obj)

    # Test retrieval by UID
    assert alias_dict[obj_uid] is obj

    # Test retrieval by aliases
    assert alias_dict["alias1"] is obj
    assert alias_dict["alias2"] is obj


def test_update_aliases(alias_dict):
    obj_uid = uuid4()
    obj = TestObject(obj_uid, ["alias1", "alias2"])
    alias_dict.add(obj)

    # Update aliases
    obj._aliases = ["alias3", "alias4"]
    alias_dict.add(obj)

    # Old aliases should not work
    with pytest.raises(KeyError):
        _ = alias_dict["alias1"]

    # New aliases should work
    assert alias_dict["alias3"] is obj
    assert alias_dict["alias4"] is obj


class TestObjectNoUID:
    pass

def test_add_without_uid_or_aliases(alias_dict):
    obj = TestObjectNoUID()

    with pytest.raises(TypeError):
        alias_dict.add(obj)


def test_find_item(alias_dict):
    obj_uid = uuid4()
    obj = TestObject(obj_uid, ["alias1", "alias2"])
    alias_dict.add(obj)

    # Test find_item
    found_obj = alias_dict.find_item("alias1")
    assert found_obj is obj

    # Test find_item with non-existing alias
    assert alias_dict.find_item("non_existing") is None

    # Test find_item with filter
    assert alias_dict.find_item("alias1", filt=lambda x: x.uid == obj_uid) is obj
    assert alias_dict.find_item("alias1", filt=lambda x: x.uid != obj_uid) is None
