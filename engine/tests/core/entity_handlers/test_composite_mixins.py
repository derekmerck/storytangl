from __future__ import annotations
import logging

import pytest

from tangl.core import Entity, Node
from tangl.core.entity_handlers import *
from tangl.persistence import PersistenceManager
from tangl.persistence.structuring import StructuringHandler

logging.basicConfig(level=logging.DEBUG)

class TestCompositeEntity(Renderable, HasConditions, HasEffects, Entity):
    ...

class TestCompositeNode(Renderable, HasConditions, HasEffects, Node):
    ...

@pytest.fixture
def kwargs():
    return {
        'content': 'hello {{animals[0]}}',
        'locals': {'animals': ['cat']},
        'effects': ['animals[0] = "dog"'],
        'conditions': ['animals[0] == "dog"']
    }

@pytest.mark.parametrize('entity_cls', [TestCompositeEntity, TestCompositeNode])
def test_composite_entity(entity_cls, kwargs):

    e = entity_cls(**kwargs)
    print( e )
    assert not e.check_conditions()
    res = e.render()
    assert( res['content'] == "hello cat" )
    e.apply_effects()
    assert e.locals['animals'][0] == "dog"
    assert e.check_conditions()
    res = e.render()
    assert( res['content'] == "hello dog" )


@pytest.mark.parametrize('entity_cls', [TestCompositeEntity, TestCompositeNode])
def test_composite_entity_structuring(entity_cls, kwargs):

    e = entity_cls(**kwargs)
    print( e )

    unstructured_data = StructuringHandler.unstructure( e )
    print( unstructured_data )
    obj = StructuringHandler.structure( unstructured_data )
    print( obj.__class__ )
    assert obj == e

    serialized_data = PersistenceManager(
        structuring=StructuringHandler
    ).save( e )
    print( serialized_data )
    obj = PersistenceManager(
        structuring=StructuringHandler
    ).load( None, data=serialized_data )
    assert obj == e
