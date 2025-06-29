from __future__ import annotations
from typing import Mapping, Any
import logging

logger = logging.getLogger(__name__)

import pytest
import jinja2
from pydantic import BaseModel

from tangl.core.entity import Entity
from tangl.core.dispatch import HandlerPriority
from tangl.core.services import on_render_content, Renderable, on_gather_context, HasContext

MyRenderableEntity = type('MyRenderableEntity', (Renderable, Entity), {} )

@pytest.fixture
def renderable_entity():
    yield Renderable(locals={'msg': 'hello entity'}, content="msg: {{ msg }}")


def test_renderable_entity(renderable_entity):

    context = on_gather_context.execute_all_for(renderable_entity, ctx=None)
    assert context['msg'] == 'hello entity'

    context = renderable_entity.gather_context()
    assert context['msg'] == 'hello entity'

    result = on_render_content.execute_all_for(renderable_entity, ctx=context)
    assert result['content'] == "msg: hello entity"

    result = renderable_entity.render_content()
    assert result['content'] == "msg: hello entity"

class ContextRenderableEntity(Renderable, HasContext, Entity):
    title: str = None
    icon: str = None

    @on_render_content.register()
    def _include_extras(self, ctx) -> Mapping[str, Any]:
        return {'title': self.title,
                'icon': self.icon}

@pytest.fixture
def renderable():
    return ContextRenderableEntity(
        title="dog",
        content = "Hello, {{ name }}!",
        locals = {"name": "World"}
    )

def test_renderable1(renderable):
    result = Renderable.render_str( renderable.content, ctx=renderable.locals )
    assert result == "Hello, World!"
    result = renderable.render_content()
    assert result.get('content') == "Hello, World!"


def test_renderable2():
    n = ContextRenderableEntity( locals={'abc': 'foo'}, content='this should say foo: {{abc}}' )
    output = n.render_content()
    assert output['content'] == 'this should say foo: foo'


def test_renderable_fields():
    test_entity = ContextRenderableEntity(content="Hello {{ var1 }}", title="Title", icon="icon.png", locals={'var1': 'World'})
    rendered = test_entity.render_content()
    assert rendered['content'] == "Hello World"
    assert rendered['title'] == "Title"
    assert rendered['icon'] == "icon.png"

def test_rendering_with_multiple_fields():
    n = ContextRenderableEntity(locals={'abc': 'foo', 'dog': 'cat'}, content='{{abc}} {{dog}}')
    output = n.render_content()
    assert output['content'] == f'foo cat'


def test_rendering_with_missing_variable():
    n = ContextRenderableEntity(content='Missing variable: {{missing_var}}')
    output = n.render_content()
    assert 'missing_var' not in output['content']

def test_template_error_handling():
    node = ContextRenderableEntity(
        content="Hello, {{ name }!",  # Missing closing brace
        locals={"name": "World"}
    )

    with pytest.raises(jinja2.exceptions.TemplateSyntaxError):
        node.render_content()


def test_complex_template():
    node = ContextRenderableEntity(
        content="{{ a + b }} {{ c * d }} {{ e.upper() }} {{ 'x' if f else 'y' }}",
        locals={"a": 1, "b": 2, "c": 3, "d": 4, "e": "test", "f": False}
    )

    result = node.render_content()
    assert result.get('content') == "3 12 TEST y"


def test_custom_render_handler():

    class CustomRenderableEntity(ContextRenderableEntity):

        @on_render_content.register()
        def _custom_content(self, ctx):
            return {'custom_content': "dog"}

    node = CustomRenderableEntity()
    print( node.render_content() )
    assert node.render_content().get('custom_content') == "dog"

def test_accumulate_rendering():

    class CustomRenderableNode(ContextRenderableEntity):

        @on_render_content.register(priority=HandlerPriority.LATE)
        def _render_content(self, ctx):
            return {'icon': 'bar', 'text': ctx.get('abc')}

    node = CustomRenderableNode()
    r = node.render_content()
    assert r.get("icon") == "bar"
    assert r.get('text') is None

    rr = on_render_content.execute_all_for(node, ctx={"abc": 123})
    assert rr.get("icon") == "bar"
    assert rr.get('text') == 123


@pytest.mark.xfail(reason="not sure")
def test_accumulate_rendering_order():

    class CustomRenderableNode(ContextRenderableEntity):

        @on_render_content.register(priority=HandlerPriority.LATE)
        def _render_content(self, ctx):
            return {'text': 'bar'}
        # this should override the text field from the base renderer

    node = CustomRenderableNode()
    assert node.render_content()['text'] == "bar"


def test_multiple_renderable_mixins():

    class Renderable1(Entity):
        # This _has_ to inherit from entity, or else the task decorator
        # won't properly restrict the task to a subclass of this one.

        @on_render_content.register(priority=HandlerPriority.LATE)
        def _render1(self, ctx):
            return {'icon': 'bar'}

    class Renderable2(Entity):

        @on_render_content.register(priority=HandlerPriority.LATE)
        def _render2(self, ctx):
            return {'content': 'foo1'}

    DoubleRenderableNode = type('DoubleRenderableNode',
                                (Renderable1, Renderable2, ContextRenderableEntity),
                                {})

    node = DoubleRenderableNode(title="cat")
    res = node.render_content()
    logger.debug( res )

    assert res == { 'title': 'cat',
                    'label': node.label,
                    'icon': 'bar',
                    'content': 'foo1' }
