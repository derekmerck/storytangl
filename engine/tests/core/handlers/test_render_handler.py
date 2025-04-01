import pytest

from tangl.core.handlers import on_render, Renderable, on_gather_context

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

