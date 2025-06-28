from __future__ import annotations
import logging

import pytest

from tangl.core.entity import Entity
from tangl.core.handlers import *

logging.basicConfig(level=logging.DEBUG)

TestCompositeEntity = type('TestNamespaceEntity', (Renderable, Satisfiable, HasEffects, Entity), {} )
TestCompositeNode = type('TestNamespaceNode', (Renderable, Satisfiable, HasEffects, Entity), {} )


@pytest.fixture
def kwargs():
    return {
        'content': 'hello {{animals[0]}}',
        'locals': {'animals': ['cat']},
        'effects': ['animals[0] = "dog"'],
        'predicates': ['animals[0] == "dog"']
    }

@pytest.mark.parametrize('entity_cls', [TestCompositeEntity, TestCompositeNode])
def test_composite_entity(entity_cls, kwargs):

    e = entity_cls(**kwargs)
    print( e )
    assert not e.is_satisfied()
    res = e.render_content()
    assert( res['content'] == "hello cat" )
    e.apply_effects()
    assert e.locals['animals'][0] == "dog"
    assert e.is_satisfied()
    res = e.render_content()
    assert( res['content'] == "hello dog" )


@pytest.mark.parametrize('entity_cls', [TestCompositeEntity, TestCompositeNode])
def test_composite_entity_structuring(entity_cls, kwargs):

    e = entity_cls(**kwargs)
    print( e )

    unstructured_data = Entity.unstructure( e )
    print( unstructured_data )
    obj = Entity.structure( unstructured_data )
    print( obj.__class__ )
    assert obj == e

    unstructured_data = Entity.unstructure( e )
    print( unstructured_data )
    obj = Entity.structure( data=unstructured_data )
    assert obj == e
