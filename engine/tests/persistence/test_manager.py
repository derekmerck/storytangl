import json
from uuid import uuid4, UUID

import pydantic
import pytest

from tangl.core import Entity
from tangl.persistence import PersistenceManager, PersistenceManagerFactory
from tangl.persistence.serializers import JsonSerializationHandler
from tangl.persistence.storage import FileStorage
from tangl.persistence.structuring import StructuringHandler


class ManagerModel(pydantic.BaseModel):
    uid: UUID
    data: str

@pytest.fixture
def test_obj():
    data = {'uid': uuid4(), 'data': 'test data'}
    return ManagerModel(**data)

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


def test_json_persistence_round_trip_preserves_entity_templ_hash_bytes(tmp_path) -> None:
    entity = Entity(label="persisted", templ_hash=b"\x12\x34\xab\xcd")
    manager = PersistenceManager(
        serializer=JsonSerializationHandler,
        structuring=StructuringHandler,
        storage=FileStorage(base_path=tmp_path),
    )

    manager.save(entity)
    raw = manager.storage[entity.uid]
    loaded = manager.load(entity.uid)
    payload = json.loads(raw)

    assert payload["templ_hash"]["__tangl_type__"] == "bytes"
    assert payload["templ_hash"]["hex"] == "1234abcd"
    assert isinstance(loaded, Entity)
    assert loaded.templ_hash == entity.templ_hash
    assert isinstance(loaded.templ_hash, bytes)


def test_reopened_json_file_manager_values_use_logical_storage_keys(tmp_path) -> None:
    manager = PersistenceManagerFactory.json_file(base_path=tmp_path)
    saved = ManagerModel(uid=uuid4(), data="persisted")
    manager.save(saved)

    reopened = PersistenceManagerFactory.json_file(base_path=tmp_path)
    assert "ManagerModel" not in reopened.kind_map
    with pytest.raises(KeyError, match="ManagerModel"):
        list(reopened.values())
    reopened.register_kind(ManagerModel)

    assert list(reopened.values()) == [saved]
