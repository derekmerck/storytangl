import logging

import pytest

from tangl.core.entity import Registry, Graph, Entity
from tangl.core.entity.entity import match_logger
from tangl.core.solver.provisioner import EntityTemplate, TemplateProvider, HasRequirement

match_logger.setLevel(logging.DEBUG)

class MockEntity(Entity):
    name: str
    type: str = None

@pytest.fixture
def entity_template() -> EntityTemplate:
    return EntityTemplate(data={"obj_cls": MockEntity, "type": "npc", "name": "Bob"})

def test_entity_template_matching(entity_template: EntityTemplate):
    assert entity_template.matches(type="npc")
    assert not entity_template.matches(type="item")
    assert entity_template.matches(name=lambda n: n.startswith("Bo"))

def test_entity_template_build(entity_template: EntityTemplate):
    entity = entity_template.build()
    assert entity.type == "npc"
    assert entity.name == "Bob"

    # test overrides
    entity_override = entity_template.build(name="Alice")
    assert entity_override.name == "Alice"

def test_template_provider_provision(entity_template: EntityTemplate):
    registry = Registry[EntityTemplate]()
    provider = TemplateProvider(template_registry=registry)
    registry.add(entity_template)

    provided_entity = provider.provision(criteria={"type": "npc"})
    assert provided_entity is not None
    assert provided_entity.name == "Bob"

    provided_entity = provider.provision(criteria={"type": "npc"}, build_overrides={"name": "Charlie"})
    assert provided_entity is not None
    assert provided_entity.name == "Charlie"
