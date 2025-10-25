from uuid import uuid4
import pytest
from tangl.core.entity import Entity
from tangl.persistence import PersistenceManager
from tangl.persistence.structuring import StructuringHandler
from tangl.persistence.serializers import YamlSerializationHandler
from tangl.utils.dereference_obj_cls import dereference_obj_cls

# Assuming an example subclass of Entity for testing
class TestStructuringEntity(Entity):
    name: str

@pytest.fixture
def entity_instance():
    return TestStructuringEntity(name="TestName")


def test_subclass_lookup():
    class TestSubClass(Entity):
        pass

    class TestSubSubClass(TestSubClass):
        pass

    assert TestSubSubClass is dereference_obj_cls(Entity, "TestSubSubClass")

    created_instance = dereference_obj_cls(Entity, "TestSubSubClass")(name="hello")
    assert isinstance(created_instance, TestSubSubClass)


def test_unstructure_entity(entity_instance):
    unstructured = StructuringHandler.unstructure(entity_instance)
    assert unstructured['obj_cls'] == TestStructuringEntity
    assert unstructured['name'] == "TestName"

def test_structure_entity():
    unstructured_data = {'obj_cls': TestStructuringEntity, 'name': 'TestName', 'uid': uuid4()}
    entity = Entity.structure(unstructured_data)
    assert isinstance(entity, TestStructuringEntity)
    assert entity.name == "TestName"

@pytest.mark.xfail(reason="doesn't require a map for cold loading currently")
def test_persistence_cold_load(entity_instance):
    PersistenceManager.obj_cls_map.clear()
    persistence_manager = PersistenceManager(
        structuring=StructuringHandler
    )

    # haven't seen TestStructuringEntity yet, so should raise
    with pytest.raises(KeyError):
        structured = persistence_manager.load(None, data={'obj_cls': 'TestStructuringEntity', 'name': 'dog'})

    PersistenceManager.obj_cls_map.clear()
    persistence_manager = PersistenceManager(
        structuring=Entity,
    )
    # Using the graph structuring handler should let us cold-load any entity-derived subclass
    structured = persistence_manager.load(None, data={'obj_cls': 'TestStructuringEntity', 'name': 'dog'})
    assert structured.name == "dog"
    assert isinstance(structured, TestStructuringEntity)


def test_persistence_round_trip(entity_instance):
    # Setup persistence manager with YAML handler
    persistence_manager = PersistenceManager(
        structuring=StructuringHandler,
        serializer=YamlSerializationHandler
    )

    # Serialize (dump) the entity
    serialized_data = persistence_manager.save(entity_instance)
    assert 'TestName' in serialized_data  # Check for inst name in serialized output

    # Deserialize (load) the entity
    loaded_entity = persistence_manager.load( None, data=serialized_data )
    assert isinstance(loaded_entity, TestStructuringEntity)
    assert loaded_entity.name == "TestName"
