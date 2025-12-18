from __future__ import annotations

from collections.abc import Iterable

import pytest

from tangl.core import Entity
from tangl.core.graph import GraphItem, Node
from tangl.ir.story_ir import BlockScript, StoryScript
from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World
from tangl.story.fabula import materialize_handlers
from tangl.story.story_graph import StoryGraph
from tangl.vm.context import MaterializationContext
from tangl.vm.dispatch import vm_dispatch
from tangl.vm.dispatch.materialize_task import MaterializePhase, MaterializeTask


@pytest.fixture(autouse=True)
def clear_world_singleton():
    World.clear_instances()
    yield
    World.clear_instances()


def _suspend_default_handlers() -> list:
    suspended: list = []
    for handler in (
        materialize_handlers.instantiation_handler,
        materialize_handlers.standard_wiring_handler,
    ):
        behavior = getattr(handler, "_behavior", None)
        if behavior is not None:
            vm_dispatch.remove(behavior)
            suspended.append(behavior)
    return suspended


def _restore_handlers(behaviors: Iterable) -> None:
    for behavior in behaviors:
        vm_dispatch.add_behavior(behavior)


def _make_world() -> World:
    script = StoryScript.model_validate(
        {"label": "test", "metadata": {"title": "Test", "author": "Tests"}, "scenes": {}}
    )
    manager = ScriptManager(master_script=script)
    return World(
        label="test",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )


def test_materialize_creates_context():
    world = _make_world()
    graph = StoryGraph(label="test", world=world)
    template = BlockScript(label="start", content="Start block")

    contexts: list[MaterializationContext] = []

    @vm_dispatch.register(task=MaterializeTask.MATERIALIZE, priority=MaterializePhase.EARLY)
    def capture_context(caller: Entity, *, ctx: MaterializationContext, **_):
        contexts.append(ctx)

    try:
        node = world._materialize_from_template(template, graph, None)

        assert node is not None
        assert len(contexts) == 1
        ctx = contexts[0]
        assert isinstance(ctx, MaterializationContext)
        assert ctx.template is template
        assert ctx.graph is graph
        assert ctx.parent_container is None
        assert "content" in ctx.payload
    finally:
        vm_dispatch.remove(capture_context._behavior)


def test_materialize_runs_all_phases_in_order():
    world = _make_world()
    graph = StoryGraph(label="test", world=world)
    template = BlockScript(label="start", content="Start")

    suspended = _suspend_default_handlers()

    phases: list[str] = []

    @vm_dispatch.register(task=MaterializeTask.MATERIALIZE, priority=MaterializePhase.EARLY)
    def early_handler(caller: Entity, *, ctx: MaterializationContext, **_):
        phases.append("EARLY")
        ctx.payload["early"] = True

    @vm_dispatch.register(task=MaterializeTask.MATERIALIZE, priority=MaterializePhase.NORMAL)
    def normal_handler(caller: Entity, *, ctx: MaterializationContext, **_):
        phases.append("NORMAL")
        ctx.node = Node(label=ctx.payload["label"], graph=ctx.graph)

    @vm_dispatch.register(task=MaterializeTask.MATERIALIZE, priority=MaterializePhase.LATE)
    def late_handler(caller: Entity, *, ctx: MaterializationContext, **_):
        phases.append("LATE")
        assert ctx.node is not None

    @vm_dispatch.register(task=MaterializeTask.MATERIALIZE, priority=MaterializePhase.LAST)
    def last_handler(caller: Entity, *, ctx: MaterializationContext, **_):
        phases.append("LAST")
        assert ctx.node is not None

    try:
        node = world._materialize_from_template(template, graph, None)
        assert node is not None
        assert phases == ["EARLY", "NORMAL", "LATE", "LAST"]
    finally:
        for handler in (early_handler, normal_handler, late_handler, last_handler):
            vm_dispatch.remove(handler._behavior)
        _restore_handlers(suspended)


def test_materialize_requires_normal_phase_to_set_node():
    world = _make_world()
    graph = StoryGraph(label="test", world=world)
    template = BlockScript(label="start", content="Start")

    suspended = _suspend_default_handlers()

    @vm_dispatch.register(task=MaterializeTask.MATERIALIZE, priority=MaterializePhase.NORMAL)
    def broken_handler(caller: Entity, *, ctx: MaterializationContext, **_):
        return None

    try:
        with pytest.raises(RuntimeError, match="no handler set ctx.node"):
            world._materialize_from_template(template, graph, None)
    finally:
        vm_dispatch.remove(broken_handler._behavior)
        _restore_handlers(suspended)


def test_materialize_early_phase_can_modify_payload():
    world = _make_world()
    graph = StoryGraph(label="test", world=world)
    template = BlockScript(label="start", content="Original")

    suspended = _suspend_default_handlers()

    @vm_dispatch.register(task=MaterializeTask.MATERIALIZE, priority=MaterializePhase.EARLY)
    def modify_payload(caller: Entity, *, ctx: MaterializationContext, **_):
        ctx.payload["content"] = "Modified"
        ctx.payload["computed"] = "value"

    @vm_dispatch.register(task=MaterializeTask.MATERIALIZE, priority=MaterializePhase.NORMAL)
    def create_node(caller: Entity, *, ctx: MaterializationContext, **_):
        ctx.node = Node(label=ctx.payload["label"], graph=ctx.graph)
        assert ctx.payload["content"] == "Modified"
        assert ctx.payload["computed"] == "value"

    try:
        node = world._materialize_from_template(template, graph, None)
        assert node is not None
    finally:
        for handler in (modify_payload, create_node):
            vm_dispatch.remove(handler._behavior)
        _restore_handlers(suspended)


def test_materialize_with_parent_container_passes_through():
    world = _make_world()
    graph = StoryGraph(label="test", world=world)
    scene = graph.add_subgraph(label="scene")
    template = BlockScript(label="start", content="Start")

    suspended = _suspend_default_handlers()

    @vm_dispatch.register(task=MaterializeTask.MATERIALIZE, priority=MaterializePhase.NORMAL)
    def normal_handler(caller: Entity, *, ctx: MaterializationContext, **_):
        assert ctx.parent_container is scene
        ctx.node = Node(label=ctx.payload["label"], graph=ctx.graph)
        scene.add_member(ctx.node)

    try:
        node = world._materialize_from_template(template, graph, scene)
        assert node.parent is scene
    finally:
        vm_dispatch.remove(normal_handler._behavior)
        _restore_handlers(suspended)
