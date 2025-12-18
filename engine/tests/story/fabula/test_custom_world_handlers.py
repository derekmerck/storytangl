from __future__ import annotations

from uuid import UUID

import pytest

from tangl.ir.story_ir import BlockScript, StoryScript
from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World
from tangl.story.story_graph import StoryGraph
from tangl.vm.dispatch import vm_dispatch
from tangl.vm.dispatch.materialize_task import MaterializePhase, MaterializeTask


@pytest.fixture(autouse=True)
def clear_world():
    World.clear_instances()
    yield
    World.clear_instances()


def _make_world(label: str = "custom") -> World:
    script = StoryScript.model_validate(
        {"label": label, "metadata": {"title": label.title(), "author": "Tests"}, "scenes": {}}
    )
    manager = ScriptManager(master_script=script)
    return World(
        label=label,
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )


def test_custom_early_handler_injects_payload_fields():
    world = _make_world()
    graph = StoryGraph(label="test", world=world)
    template = BlockScript(label="start", content="Hello world")

    payload_snapshots: list[dict[str, object]] = []

    @vm_dispatch.register(
        task=MaterializeTask.MATERIALIZE,
        priority=MaterializePhase.EARLY,
        layer="custom_world",
    )
    def inject_fields(caller, *, ctx, **_):
        ctx.payload["computed_length"] = len(ctx.payload.get("content", ""))
        payload_snapshots.append(dict(ctx.payload))

    @vm_dispatch.register(
        task=MaterializeTask.MATERIALIZE,
        priority=MaterializePhase.LAST,
        layer="custom_world",
    )
    def capture_payload(caller, *, ctx, **_):
        payload_snapshots.append(dict(ctx.payload))

    try:
        node = world._materialize_from_template(template, graph)
        assert node is not None
        assert any("computed_length" in snapshot for snapshot in payload_snapshots)
    finally:
        vm_dispatch.remove(inject_fields._behavior)
        vm_dispatch.remove(capture_payload._behavior)


def test_custom_last_handler_records_nodes():
    world = _make_world("procedural")
    graph = StoryGraph(label="test", world=world)
    template = BlockScript(label="start", content="Start", tags={"procedural"})

    touched: list[UUID] = []

    @vm_dispatch.register(
        task=MaterializeTask.MATERIALIZE,
        priority=MaterializePhase.LAST,
        layer="custom_world",
    )
    def record_node(caller, *, ctx, **_):
        if ctx.node is not None:
            touched.append(ctx.node.uid)

    try:
        node = world._materialize_from_template(template, graph)
        assert node.uid in touched
    finally:
        vm_dispatch.remove(record_node._behavior)


def test_custom_last_handler_can_add_edges():
    from tangl.core.graph import Edge

    world = _make_world("custom_edges")
    graph = StoryGraph(label="test", world=world)
    template = BlockScript(label="start", content="Start", tags={"linked"})

    created: list[Edge] = []

    @vm_dispatch.register(
        task=MaterializeTask.MATERIALIZE,
        priority=MaterializePhase.LAST,
        layer="custom_world",
    )
    def wire_custom(caller, *, ctx, **_):
        if ctx.node is None or not ctx.node.has_tags("linked"):
            return
        edge = Edge(graph=ctx.graph, source_id=ctx.node.uid, destination=None, label="custom_link")
        created.append(edge)

    try:
        node = world._materialize_from_template(template, graph)
        assert node is not None
        assert len(created) == 1
        assert created[0].label == "custom_link"
    finally:
        vm_dispatch.remove(wire_custom._behavior)


def test_multiple_custom_handlers_compose():
    world = _make_world("compose")
    graph = StoryGraph(label="test", world=world)
    template = BlockScript(label="start", content="Start")

    markers: list[str] = []

    @vm_dispatch.register(
        task=MaterializeTask.MATERIALIZE,
        priority=MaterializePhase.LAST,
        layer="custom1",
    )
    def handler_one(caller, *, ctx, **_):
        markers.append("handler1")

    @vm_dispatch.register(
        task=MaterializeTask.MATERIALIZE,
        priority=MaterializePhase.LAST,
        layer="custom2",
    )
    def handler_two(caller, *, ctx, **_):
        markers.append("handler2")

    try:
        world._materialize_from_template(template, graph)
        assert "handler1" in markers and "handler2" in markers
    finally:
        vm_dispatch.remove(handler_one._behavior)
        vm_dispatch.remove(handler_two._behavior)

