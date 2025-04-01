import pytest

from tangl.core import Entity, PipelineStrategy, TaskPipeline, HandlerPriority, TaskHandler

@pytest.fixture(autouse=True)
def renderable_pipeline_and_classes():

    on_render = TaskPipeline[Entity, dict](label="on_render", pipeline_strategy=PipelineStrategy.GATHER)

    class RenderableTestEntity(Entity):

        @on_render.register(HandlerPriority.NORMAL)
        def _rendering_handler(self, **context) -> dict:
            return {'hello': 'world', 'foo': 'bar'}

        def render(self):
            return on_render.execute(self)

    class MyRenderableTestEntity(RenderableTestEntity):

        @on_render.register(HandlerPriority.FIRST)
        def _my_rendering_handler(self, **context) -> dict:
            return {'hello': 'world2'}

    yield on_render, RenderableTestEntity, MyRenderableTestEntity

    TaskPipeline.clear_instances()


def test_renderable_pipeline(renderable_pipeline_and_classes):

    on_render, RenderableTestEntity, MyRenderableTestEntity = renderable_pipeline_and_classes

    renderable_test_handler = on_render.handler_registry.find_one(func_name="_rendering_handler")
    assert renderable_test_handler.caller_cls is RenderableTestEntity
    my_renderable_test_handler = on_render.handler_registry.find_one(func_name="_my_rendering_handler")
    assert my_renderable_test_handler.caller_cls is MyRenderableTestEntity

    result = on_render.execute(RenderableTestEntity())
    assert result == {'hello': 'world', 'foo': 'bar'}
    result = on_render.execute(MyRenderableTestEntity())
    assert result == {'hello': 'world2', 'foo': 'bar'}

    result = RenderableTestEntity().render()
    assert result == {'hello': 'world', 'foo': 'bar'}
    result = MyRenderableTestEntity().render()
    assert result == {'hello': 'world2', 'foo': 'bar'}


def test_extra_handlers_with_priority():
    """Test that extra handlers respect priority ordering"""
    on_process = TaskPipeline[Entity, list](
        label="test_pipeline",
        pipeline_strategy=PipelineStrategy.GATHER
    )

    entity = Entity()

    # Register a normal priority handler
    @on_process.register(HandlerPriority.NORMAL)
    def base_handler(e, **ctx):
        return "base"

    # Create handlers with different priorities
    early_handler = TaskHandler(
        func=lambda e, **ctx: "early",
        priority=HandlerPriority.EARLY
    )

    late_handler = TaskHandler(
        func=lambda e, **ctx: "late",
        priority=HandlerPriority.LATE
    )

    result = on_process.execute(
        entity,
        extra_handlers=[late_handler, early_handler]
    )

    # Check order of merged results
    assert result == ["early", "base", "late"]


def test_extra_handlers_with_class_restrictions():
    """Test that extra handlers respect class constraints"""

    class SpecialEntity(Entity):
        pass

    on_render = TaskPipeline[Entity, dict](
        label="test_pipeline",
        pipeline_strategy=PipelineStrategy.GATHER
    )

    # Register base handler
    @on_render.register()
    def base_handler(e: Entity, **ctx):
        return {"base": "value"}

    # Create class-specific handler
    special_handler = TaskHandler(
        func=lambda e, **ctx: {"special": "value"},
        caller_cls=SpecialEntity
    )

    # Should only get base handler
    regular_entity = Entity()
    result = on_render.execute(
        regular_entity,
        extra_handlers=[special_handler]
    )
    assert result == {"base": "value"}

    # Should get both handlers
    special_entity = SpecialEntity()
    result = on_render.execute(
        special_entity,
        extra_handlers=[special_handler]
    )
    assert result == {"base": "value", "special": "value"}


def test_pipeline_strategy_with_extra_handlers():
    """Test that pipeline strategy works with injected handlers"""

    on_process = TaskPipeline[Entity, int](
        label="test_pipeline",
        pipeline_strategy=PipelineStrategy.PIPELINE
    )

    entity = Entity()

    # Register base handler
    @on_process.register(priority=HandlerPriority.FIRST)
    def base_handler(e: Entity, value: int = None, **ctx):
        return (value or 0) + 1

    # Create increment handlers
    plus_two = TaskHandler(
        func=lambda e, value, **ctx: value + 2
    )

    times_two = TaskHandler(
        func=lambda e, value, **ctx: value * 2
    )

    # Test different handler combinations
    result = on_process.execute(entity)
    assert result == 1  # Just base handler

    result = on_process.execute(entity, extra_handlers=[plus_two])
    assert result == 3, "Processes extra handler 1 + 2 = 3"

    result = on_process.execute(entity, extra_handlers=[plus_two, times_two])
    assert result == 6, "Multiple extra handlers (1 + 2) * 2 = 6"

    result = on_process.execute(entity, extra_handlers=[times_two, plus_two])
    assert result == 4, "Order should be respected (1 * 2) + 2 = 4"


def test_temporary_handler_caching():
    """Test that caching works correctly with temporary handlers"""

    on_render = TaskPipeline[Entity, dict](
        label="test_pipeline",
        pipeline_strategy=PipelineStrategy.GATHER
    )

    entity = Entity()

    # Register permanent handler
    @on_render.register()
    def base_handler(e, **ctx):
        return {"base": "value"}

    # First execution with extra handler
    result1 = on_render.execute(
        entity,
        extra_handlers=[lambda e, **ctx: {"extra": "value"}]
    )
    assert result1 == {"base": "value", "extra": "value"}

    # Second execution without extra handler should use cache
    result2 = on_render.execute(entity)
    assert result2 == {"base": "value"}

    # Third execution with different extra handler
    result3 = on_render.execute(
        entity,
        extra_handlers=[lambda e, **ctx: {"different": "value"}]
    )
    assert result3 == {"base": "value", "different": "value"}