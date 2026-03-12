"""Contract tests for story38 concept namespace publication."""

from __future__ import annotations

import pytest

from tangl.story.concepts import Actor, Location, Role, Setting
from tangl.story.episode import Block, Scene
from tangl.story.story_graph import StoryGraph
from tangl.vm import Requirement
from tangl.vm.runtime.frame import PhaseCtx


def _build_scene_with_block() -> tuple[StoryGraph, Scene, Block]:
    graph = StoryGraph(label="ns_story")
    scene = Scene(label="scene")
    block = Block(label="block")
    graph.add(scene)
    graph.add(block)
    scene.add_child(block)
    return graph, scene, block


def test_role_and_setting_publish_provider_symbols_into_namespace() -> None:
    graph, scene, block = _build_scene_with_block()

    actor = Actor(label="guard", name="Joe")
    location = Location(label="castle", name="Castle")
    graph.add(actor)
    graph.add(location)

    role = Role(
        label="host",
        predecessor_id=scene.uid,
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
    )
    setting = Setting(
        label="place",
        predecessor_id=scene.uid,
        requirement=Requirement(has_kind=Location, hard_requirement=False),
    )
    graph.add(role)
    graph.add(setting)
    role.set_provider(actor)
    setting.set_provider(location)

    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)
    ns = ctx.get_ns(block)

    assert ns["host"] is actor
    assert ns["host_role"] is role
    assert ns["host_name"] == "Joe"
    assert ns["host_label"] == "guard"
    assert ns["roles"]["host"] is actor
    assert ns["role_edges"]["host"] is role

    assert ns["place"] is location
    assert ns["place_setting"] is setting
    assert ns["place_name"] == "Castle"
    assert ns["place_label"] == "castle"
    assert ns["settings"]["place"] is location
    assert ns["setting_edges"]["place"] is setting


def test_role_and_provider_keep_distinct_narrator_knowledge() -> None:
    graph, scene, block = _build_scene_with_block()

    actor = Actor(label="katya", name="Katya")
    graph.add(actor)

    role = Role(
        label="villain",
        predecessor_id=scene.uid,
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
    )
    graph.add(role)
    role.set_provider(actor)

    actor.get_knowledge("player").state = "IDENTIFIED"
    role.get_knowledge("player").state = "FAMILIAR"

    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)
    ns = ctx.get_ns(block)

    assert ns["villain"] is actor
    assert ns["villain_role"] is role
    assert ns["villain"].get_knowledge("player").state == "IDENTIFIED"
    assert ns["villain_role"].get_knowledge("player").state == "FAMILIAR"


def test_role_publication_order_is_deterministic() -> None:
    graph, scene, block = _build_scene_with_block()

    actor_b = Actor(label="beta_actor", name="B")
    actor_a = Actor(label="alpha_actor", name="A")
    graph.add(actor_b)
    graph.add(actor_a)

    role_b = Role(
        label="beta",
        predecessor_id=scene.uid,
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
    )
    role_a = Role(
        label="alpha",
        predecessor_id=scene.uid,
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
    )
    graph.add(role_b)
    graph.add(role_a)
    role_b.set_provider(actor_b)
    role_a.set_provider(actor_a)

    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)
    ns = ctx.get_ns(block)

    assert list(ns["roles"].keys()) == ["alpha", "beta"]
    assert list(ns["role_edges"].keys()) == ["alpha", "beta"]


def test_nearer_scope_role_symbols_override_parent_scope() -> None:
    graph, scene, block = _build_scene_with_block()

    scene_actor = Actor(label="scene_guide", name="Scene Guide")
    block_actor = Actor(label="block_guide", name="Block Guide")
    graph.add(scene_actor)
    graph.add(block_actor)

    scene_role = Role(
        label="guide",
        predecessor_id=scene.uid,
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
    )
    block_role = Role(
        label="guide",
        predecessor_id=block.uid,
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
    )
    graph.add(scene_role)
    graph.add(block_role)
    scene_role.set_provider(scene_actor)
    block_role.set_provider(block_actor)

    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)
    ns_1 = ctx.get_ns(block)
    ns_2 = ctx.get_ns(block)

    assert ns_1 is ns_2
    assert ns_1["guide"] is block_actor
    assert ns_1["guide_name"] == "Block Guide"


def test_role_provider_hook_type_errors_are_not_swallowed() -> None:
    graph, scene, block = _build_scene_with_block()

    class ExplodingActor(Actor):
        def get_ns(self):
            raise TypeError("provider boom")

    actor = ExplodingActor(label="guard", name="Joe")
    role = Role(
        label="host",
        predecessor_id=scene.uid,
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
    )
    graph.add(actor)
    graph.add(role)
    role.set_provider(actor)

    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)
    with pytest.raises(TypeError, match="provider boom"):
        ctx.get_ns(block)


def test_setting_provider_hook_requires_mapping_or_none() -> None:
    graph, scene, block = _build_scene_with_block()

    class BadLocation(Location):
        def get_ns(self) -> list[str]:
            return ["bad"]

    location = BadLocation(label="castle", name="Castle")
    setting = Setting(
        label="place",
        predecessor_id=scene.uid,
        requirement=Requirement(has_kind=Location, hard_requirement=False),
    )
    graph.add(location)
    graph.add(setting)
    setting.set_provider(location)

    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)
    with pytest.raises(TypeError, match="get_ns must return Mapping \\| None"):
        ctx.get_ns(block)
