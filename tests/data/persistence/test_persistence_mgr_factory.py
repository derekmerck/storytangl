from uuid import uuid4, UUID
import pytest
import pydantic

from tangl.data.persistence.factory import PersistenceManagerFactory, PersistenceManagerName

class TestModel1(pydantic.BaseModel):
    # Needs a different name to avoid collision
    uid: UUID
    data: str


@pytest.fixture
def test_obj():

    data = {'uid': uuid4(), 'data': 'test data'}
    return TestModel1(**data)


@pytest.mark.xfail(raises=ImportError)
@pytest.mark.parametrize('manager_name', PersistenceManagerName.__args__)
def test_factory(manager_name, test_obj, tmpdir):
    print( manager_name )
    manager = PersistenceManagerFactory.create_persistence_manager(
        manager_name = manager_name, user_data_path=tmpdir)

    manager.save(test_obj)
    uid = test_obj.uid
    loaded_obj = manager.load(uid)
    assert loaded_obj == test_obj, "Loaded object should match the saved object"
