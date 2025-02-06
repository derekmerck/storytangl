from uuid import uuid4, UUID

import pydantic
import pytest

class TestModel(pydantic.BaseModel):
    uid: UUID
    data: str

@pytest.fixture
def test_obj():
    data = {'uid': uuid4(), 'data': 'test data'}
    return TestModel(**data)

def test_save_and_load(manager, test_obj):
    manager.save(test_obj)
    uid = test_obj.uid
    loaded_obj = manager.load(uid)
    assert loaded_obj == test_obj, "Loaded object should match the saved object"

def test_remove(manager, test_obj):
    manager.save(test_obj)
    uid = test_obj.uid
    manager.remove(uid)
    with pytest.raises((KeyError, FileNotFoundError, TypeError),):
        manager.load(uid)

def test_context_manager(manager, test_obj):
    manager.save(test_obj)
    uid = test_obj.uid

    with manager.open(uid, write_back=True) as loaded_obj:
        loaded_obj.data = 'updated data'

    updated_obj = manager.load(uid)
    assert updated_obj.data == 'updated data', "Object should be updated after context manager"
