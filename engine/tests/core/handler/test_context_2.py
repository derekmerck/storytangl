from typing import Mapping

import pytest

from tangl.core.entity import Entity
from tangl.core.handler import on_gather_context, HasContext

MyContextEntity = type('MyContext', (HasContext, Entity), {} )

@pytest.fixture
def context_entity():
    yield MyContextEntity(locals={'entity': 'hello entity'})

def test_context_entity(context_entity):

    result = on_gather_context.execute_all(context_entity, ctx=None)
    assert result['entity'] == "hello entity"


# def test_namespace_inclusion():
#
#     test_entity = MyContextEntity(locals={'var1': 'value1', 'var2': 2})
#     namespace = test_entity.gather_context()
#     assert namespace == {'var1': 'value1', 'var2': 2}


def test_post_facto_namespace():
    node = MyContextEntity()
    node.locals = {"x": 5}
    namespace = node.gather_context()
    assert "x" in namespace
    assert namespace["x"] == 5


def test_has_ns():
    n = MyContextEntity( locals={'abc': 'foo'} )
    ns = n.gather_context()
    assert ns['abc'] == 'foo'


def test_namespace_with_no_locals():
    node = MyContextEntity()
    ns = node.gather_context()
    assert isinstance(ns, Mapping)
    # assert not ns  # Should be empty -- now it has 'self' defined by default
