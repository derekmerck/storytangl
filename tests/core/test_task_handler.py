import pytest

from tangl.core.entity import Entity
from tangl.core.task_handler import PipelineStrategy, TaskPipeline, HandlerPriority

@pytest.fixture(autouse=True)
def renderable_pipeline_and_classes():
    on_render = TaskPipeline[Entity, dict](label="on_render", pipeline_strategy=PipelineStrategy.GATHER)

    class RenderableTestEntity(Entity):

        @on_render.register(HandlerPriority.NORMAL)
        def my_rendering_handler(self, **context) -> dict:
            return {'hello': 'world', 'foo': 'bar'}

        def render(self):
            return on_render.execute(self)

    class MyRenderableTestEntity(RenderableTestEntity):

        @on_render.register(HandlerPriority.FIRST)
        def my_rendering_handler(self, **context) -> dict:
            return {'hello': 'world2'}

    yield on_render, RenderableTestEntity, MyRenderableTestEntity

    TaskPipeline.clear_instances()


def test_renderable_pipeline(renderable_pipeline_and_classes):

    on_render, RenderableTestEntity, MyRenderableTestEntity = renderable_pipeline_and_classes
    result = on_render.execute(RenderableTestEntity())
    assert result == {'hello': 'world', 'foo': 'bar'}
    result = on_render.execute(MyRenderableTestEntity())
    assert result == {'hello': 'world2', 'foo': 'bar'}

    result = RenderableTestEntity().render()
    assert result == {'hello': 'world', 'foo': 'bar'}
    result = MyRenderableTestEntity().render()
    assert result == {'hello': 'world2', 'foo': 'bar'}
