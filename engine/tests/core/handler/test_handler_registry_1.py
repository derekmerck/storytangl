import pytest

from tangl.core.entity import Entity
from tangl.core.handler import HandlerRegistry, HandlerPriority, BaseHandler
from tangl.utils.dereference_obj_cls import dereference_obj_cls


@pytest.fixture(autouse=True)
def renderable_pipeline_and_classes():

    on_render = HandlerRegistry(label="on_render", default_aggregation_strategy="merge")

    class RenderableTestEntity(Entity):

        @on_render.register(priority=HandlerPriority.FIRST,)
        def _rendering_handler(self, ctx) -> dict:
            return {'hello': 'world', 'foo': 'bar'}

        def render(self):
            return on_render.execute_all(self, ctx=None)

    class MyRenderableTestEntity(RenderableTestEntity):

        @on_render.register(priority=HandlerPriority.LAST)
        def _my_rendering_handler(self, ctx) -> dict:
            return {'hello': 'world2'}

    yield on_render, RenderableTestEntity, MyRenderableTestEntity


def test_renderable_pipeline(renderable_pipeline_and_classes):

    on_render, RenderableTestEntity, MyRenderableTestEntity = renderable_pipeline_and_classes

    assert dereference_obj_cls(Entity, "RenderableTestEntity") is RenderableTestEntity

    renderable_test_handler = on_render.find_one(has_func_name="_rendering_handler")
    assert renderable_test_handler.owner_cls is RenderableTestEntity
    my_renderable_test_handler = on_render.find_one(has_func_name="_my_rendering_handler")
    assert my_renderable_test_handler.owner_cls is MyRenderableTestEntity

    result = on_render.execute_all(RenderableTestEntity(), ctx=None)
    assert dict(result) == {'hello': 'world', 'foo': 'bar'}
    result = on_render.execute_all(MyRenderableTestEntity(), ctx=None)
    assert dict(result) == {'hello': 'world2', 'foo': 'bar'}

    result = RenderableTestEntity().render()
    assert dict(result) == {'hello': 'world', 'foo': 'bar'}
    result = MyRenderableTestEntity().render()
    assert dict(result) == {'hello': 'world2', 'foo': 'bar'}


def test_extra_handlers_with_priority():
    """Test that extra handlers respect priority ordering"""
    on_process = HandlerRegistry(
        label="test_pipeline",
        default_aggregation_strategy="gather"
    )

    entity = Entity()

    # Register a normal priority handler
    @on_process.register(priority=HandlerPriority.NORMAL)
    def base_handler(e, ctx):
        return "base"

    # Create handlers with different priorities
    early_handler = BaseHandler(
        func=lambda e, ctx: "early",
        priority=HandlerPriority.EARLY
    )

    late_handler = BaseHandler(
        func=lambda e, ctx: "late",
        priority=HandlerPriority.LATE
    )

    result = on_process.execute_all(
        entity,
        ctx=None,
        extra_handlers=[late_handler, early_handler]
    )

    # Check order of merged results
    assert result == ["early", "base", "late"]


def test_extra_handlers_with_class_restrictions():
    """Test that extra handlers respect class constraints"""

    class SpecialEntity(Entity):
        pass

    on_render = HandlerRegistry(
        label="test_pipeline",
        default_aggregation_strategy="merge"
    )

    # Register base handler
    @on_render.register()
    def base_handler(e: Entity, ctx):
        return {"base": "value"}

    # Create class-specific handler
    special_handler = BaseHandler(
        func=lambda e, ctx: {"special": "value"},
        owner_cls=SpecialEntity
    )

    # Should only get base handler
    regular_entity = Entity()
    result = on_render.execute_all(
        regular_entity,
        ctx=None,
        extra_handlers=[special_handler]
    )
    assert result == {"base": "value"}

    # Should get both handlers
    special_entity = SpecialEntity()
    result = on_render.execute_all(
        special_entity,
        ctx=None,
        extra_handlers=[special_handler]
    )
    assert result == {"base": "value", "special": "value"}


def test_pipeline_strategy_with_extra_handlers():
    """Test that pipeline strategy works with injected handlers"""

    on_process = HandlerRegistry(
        label="test_pipeline",
        default_aggregation_strategy="pipeline"
    )

    entity = Entity()

    # Register base handler
    @on_process.register(priority=HandlerPriority.FIRST)
    def base_handler(e: Entity, ctx):
        return {'value': 1}

    # Create increment handlers
    plus_two = BaseHandler(
        func=lambda e, ctx: {'value': ctx["value"] + 2}
    )

    times_two = BaseHandler(
        func=lambda e, ctx: {'value': ctx["value"] * 2}
    )

    # Test different handler combinations
    ctx = on_process.execute_all(entity, ctx={})
    assert ctx["value"] == 1  # Just base handler

    ctx = on_process.execute_all(entity, ctx={}, extra_handlers=[plus_two])
    assert ctx["value"] == 3, "Processes extra handler 1 + 2 = 3"

    ctx = on_process.execute_all(entity, ctx={}, extra_handlers=[plus_two, times_two])
    assert ctx["value"] == 6, "Multiple extra handlers (1 + 2) * 2 = 6"

    ctx = on_process.execute_all(entity, ctx={}, extra_handlers=[times_two, plus_two])
    assert ctx["value"] == 4, "Order should be respected (1 * 2) + 2 = 4"


@pytest.mark.skip(reason="Not implemented yet")
def test_temporary_handler_caching():
    """Test that caching works correctly with temporary handlers"""

    on_render = HandlerPipeline[Entity, dict](
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