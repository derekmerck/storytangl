from uuid import uuid4, UUID
import pytest
import pydantic

from tangl.persistence.factory import PersistenceManagerFactory, PersistenceManagerName
from tangl.persistence.storage.mongo_storage import HAS_MONGO
from tangl.persistence.storage.redis_storage import HAS_REDIS


class TestModel1(pydantic.BaseModel):
    # Needs a different name to avoid collision
    uid: UUID
    data: str


@pytest.fixture
def test_obj():
    data = {'uid': uuid4(), 'data': 'test data'}
    return TestModel1(**data)

from tangl.config import settings
import logging

def _manager_name():
    all_names = PersistenceManagerName.__args__

    for name in all_names:

        if 'redis' in name and (not settings or not settings.service.apis.redis.enabled):
            logging.debug("Marking redis xfail")
            yield pytest.param(name, marks=[pytest.mark.xfail(raises=ImportError, reason="No Redis")])

        elif ('mongo' in name or 'bson' in name) and (not settings or not settings.service.apis.mongo.enabled):
            logging.debug("Marking mongo xfail")
            yield pytest.param(name, marks=[pytest.mark.xfail(raises=ImportError, reason="No Mongo/BSON")])

        else:
            yield pytest.param(name)


@pytest.mark.parametrize('manager_name', _manager_name())
def test_factory(manager_name, test_obj, tmpdir):
    print( manager_name )

    manager = PersistenceManagerFactory.create_persistence_manager(
        manager_name = manager_name, user_data_path=tmpdir)

    manager.save(test_obj)
    uid = test_obj.uid
    loaded_obj = manager.load(uid)
    assert loaded_obj == test_obj, "Loaded object should match the saved object"
