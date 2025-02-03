import pytest

from tangl.core import Entity
from tangl.core.handler import TaskHandler, TaskPipeline, PipelineStrategy, HandlerPriority

@pytest.fixture(autouse=True)
def renderable_pipeline_and_classes():
    on_render = TaskPipeline[Entity, dict](label="on_render", pipeline_strategy=PipelineStrategy.GATHER)

    class RenderableEntity(Entity):

        @on_render.register(HandlerPriority.NORMAL)
        def my_rendering_handler(self, **context) -> dict:
            return {'hello': 'world', 'foo': 'bar'}

        def render(self):
            return on_render.execute(self)

    class MyRenderableEntity(RenderableEntity):

        @on_render.register(HandlerPriority.FIRST)
        def my_rendering_handler(self, **context) -> dict:
            return {'hello': 'world2'}

    yield on_render, RenderableEntity, MyRenderableEntity

    TaskPipeline.clear_instances()


def test_renderable_pipeline(renderable_pipeline_and_classes):

    on_render, RenderableEntity, MyRenderableEntity = renderable_pipeline_and_classes
    result = on_render.execute(RenderableEntity())
    assert result == {'hello': 'world', 'foo': 'bar'}
    result = on_render.execute(MyRenderableEntity())
    assert result == {'hello': 'world2', 'foo': 'bar'}

    result = RenderableEntity().render()
    assert result == {'hello': 'world', 'foo': 'bar'}
    result = MyRenderableEntity().render()
    assert result == {'hello': 'world2', 'foo': 'bar'}
