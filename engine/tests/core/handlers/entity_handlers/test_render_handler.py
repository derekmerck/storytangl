from __future__ import annotations
from typing import Mapping, Any

import pytest
import jinja2
from pydantic import BaseModel

from tangl.core.entity import Entity
from tangl.core.handlers import on_render, Renderable, on_gather_context, HasContext
from tangl.core.handlers.task_handler import HandlerPriority

MyRenderableEntity = type('MyRenderableEntity', (Renderable, Entity), {} )

@pytest.fixture
def renderable_entity():
    yield Renderable(locals={'msg': 'hello entity'}, text="msg: {{ msg }}")


def test_renderable_entity(renderable_entity):

    context = on_gather_context.execute(renderable_entity)
    assert context == {'msg': 'hello entity'}

    context = renderable_entity.gather_context()
    assert context == {'msg': 'hello entity'}

    result = on_render.execute(renderable_entity, **context)
    assert result['text'] == "msg: hello entity"

    result = renderable_entity.render()
    assert result['text'] == "msg: hello entity"

class ContextRenderableEntity(Renderable, HasContext, Entity):
    title: str = None
    icon: str = None

    @on_render.register()
    def _include_extras(self, **kwargs) -> Mapping[str, Any]:
        return {'title': self.title,
                'icon': self.icon}

@pytest.fixture
def renderable():
    return ContextRenderableEntity(
        title="dog",
        text = "Hello, {{ name }}!",
        locals = {"name": "World"}
    )

def test_renderable1(renderable):
    result = Renderable.render_str( renderable.text, **renderable.locals )
    assert result == "Hello, World!"
    result = renderable.render()
    assert result.get('text') == "Hello, World!"


def test_renderable2():
    n = ContextRenderableEntity( locals={'abc': 'foo'}, text='this should say foo: {{abc}}' )
    output = n.render()
    assert output['text'] == 'this should say foo: foo'


def test_renderable_fields():
    test_entity = ContextRenderableEntity(text="Hello {{ var1 }}", title="Title", icon="icon.png", locals={'var1': 'World'})
    rendered = test_entity.render()
    assert rendered['text'] == "Hello World"
    assert rendered['title'] == "Title"
    assert rendered['icon'] == "icon.png"

def test_rendering_with_multiple_fields():
    n = ContextRenderableEntity(locals={'abc': 'foo', 'dog': 'cat'}, text='{{abc}} {{dog}}')
    output = n.render()
    assert output['text'] == f'foo cat'


def test_rendering_with_missing_variable():
    n = ContextRenderableEntity(text='Missing variable: {{missing_var}}')
    output = n.render()
    assert 'missing_var' not in output['text']

def test_template_error_handling():
    node = ContextRenderableEntity(
        text="Hello, {{ name }!",  # Missing closing brace
        locals={"name": "World"}
    )

    with pytest.raises(jinja2.exceptions.TemplateSyntaxError):
        node.render()


def test_complex_template():
    node = ContextRenderableEntity(
        text="{{ a + b }} {{ c * d }} {{ e.upper() }} {{ 'x' if f else 'y' }}",
        locals={"a": 1, "b": 2, "c": 3, "d": 4, "e": "test", "f": False}
    )

    result = node.render()
    assert result.get('text') == "3 12 TEST y"


def test_custom_render_handler():

    class CustomRenderableEntity(ContextRenderableEntity):

        @on_render.register()
        def _custom_content(self, **kwargs):
            return {'custom_content': "dog"}

    node = CustomRenderableEntity()
    print( node.render() )
    assert node.render().get('custom_content') == "dog"

def test_accumulate_rendering():

    class CustomRenderableNode(ContextRenderableEntity):

        @on_render.register(priority=HandlerPriority.LATE)
        def _render(self, abc=None, **kwargs):
            return {'icon': 'bar', 'text': abc}

    node = CustomRenderableNode()
    r = node.render()
    assert r.get("icon") == "bar"
    assert r.get('text') is None

    rr = on_render.execute(node, abc=123)
    assert rr.get("icon") == "bar"
    assert rr.get('text') == 123


@pytest.mark.xfail(reason="not sure")
def test_accumulate_rendering_order():

    class CustomRenderableNode(ContextRenderableEntity):

        @on_render.register(priority=HandlerPriority.LATE)
        def _render(self, **kwargs):
            return {'text': 'bar'}
        # this should override the text field from the base renderer

    node = CustomRenderableNode()
    assert node.render()['text'] == "bar"


def test_multiple_renderable_mixins():

    class Renderable1(BaseModel):

        @on_render.register(priority=HandlerPriority.LATE)
        def _render1(self, **kwargs):
            return {'icon': 'bar'}

    class Renderable2(BaseModel):

        @on_render.register(priority=HandlerPriority.LATE)
        def _render2(self, **kwargs):
            return {'text': 'foo'}

    DoubleRenderableNode = type('DoubleRenderableNode', (Renderable1, Renderable2, ContextRenderableEntity), {})

    node = DoubleRenderableNode(title="cat")
    res = node.render()
    print( res )

    assert res == { 'title': 'cat',
                    'label': node.label,
                    'icon': 'bar',
                    'text': 'foo' }
