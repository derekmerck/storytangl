"""Identity-only authority assembly across Core, Story and the phase context."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pydantic import Field

from tangl.core import BehaviorRegistry, DispatchLayer, Graph, Singleton
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.presentation.dispatch import presentation_dispatch
from tangl.story import Block, StoryGraph, World
from tangl.story.dispatch import story_dispatch
from tangl.vm.runtime.frame import PhaseCtx


class AuthorityFactory(Singleton):
    authorities: list[object] = Field(default_factory=list)

    def get_authorities(self) -> list[object]:
        return self.authorities


class AuthorityProvider:
    def __init__(self, authorities: list[object]) -> None:
        self.authorities = authorities

    def get_authorities(self) -> list[object]:
        return self.authorities


@pytest.fixture(autouse=True)
def clear_factory_instances() -> Iterator[None]:
    AuthorityFactory.clear_instances()
    yield
    AuthorityFactory.clear_instances()


def ids(values: list[object]) -> list[int]:
    return [id(value) for value in values]


@pytest.mark.parametrize("producer", ["graph", "world", "story", "phase"])
def test_authority_assembly_retains_equal_objects_without_value_operations(
    producer: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = BehaviorRegistry(label="first")
    equal = first.model_copy()
    second = BehaviorRegistry(label="second")
    last = BehaviorRegistry(label="last")
    local = BehaviorRegistry(label="local")
    marker = object()
    assert first is not equal and first.uid == equal.uid and first == equal
    factory = AuthorityFactory(label="factory", authorities=[first, None, equal, first,
                                                              marker, second, None])
    graph = Graph(factory=factory)
    world = World(label="authority_world", dispatch=first,
                  extra_authorities=[None, equal, first, marker, second, equal])
    story = StoryGraph(factory=world)
    # Exercise the existing non-factory world override as well as the factory chain.
    story.world = AuthorityProvider([second, None, last, first, last])
    ctx = PhaseCtx(graph=story, cursor_id=None,
                   local_authorities=[second, equal, None, marker, local, local])
    if producer == "graph":
        assemble, expected = graph.get_authorities, [first, None, equal, marker, second]
    elif producer == "world":
        assemble, expected = world.get_authorities, [first, equal, marker, second]
    elif producer == "story":
        assemble = story.get_authorities
        expected = [story_dispatch, presentation_dispatch, first, equal, marker, second, None, last]
    else:
        assemble = ctx.get_authorities
        expected = [story_dispatch, presentation_dispatch, first, equal, second, last, local]

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("authority assembly must not compare or serialize registry values")

    # Limit interception to assembly, not setup, dispatch, restoration or replay.
    with monkeypatch.context() as patch:
        for name in ("__eq__", "eq_by_value", "value_hash", "unstructure"):
            patch.setattr(BehaviorRegistry, name, forbidden)
        actual = assemble()
        assert ids(actual) == ids(expected)


def test_authority_lists_follow_live_factory_world_override_and_local_changes() -> None:
    first = BehaviorRegistry(label="first")
    equal = first.model_copy()
    local = BehaviorRegistry(label="local")
    factory = AuthorityFactory(label="factory", authorities=[first, first])
    graph = Graph(factory=factory)
    assert ids(graph.get_authorities()) == ids([first])
    factory.authorities[:] = [equal, first, equal]
    assert ids(graph.get_authorities()) == ids([equal, first])

    world = World(label="live_authorities", dispatch=first, extra_authorities=[equal, first])
    story = StoryGraph(factory=world)
    override = AuthorityProvider([equal, local, equal])
    story.world = override
    ctx = PhaseCtx(graph=story, cursor_id=None, local_authorities=[local, first])
    prefix = [story_dispatch, presentation_dispatch]
    assert ids(ctx.get_authorities()) == ids([*prefix, first, equal, local])
    world.extra_authorities.clear()
    override.authorities[:] = [local]
    ctx.local_authorities[:] = [equal, local]
    assert ids(ctx.get_authorities()) == ids([*prefix, first, local, equal])
    ctx.local_authorities.clear()
    override.authorities.clear()
    assert ids(ctx.get_authorities()) == ids([*prefix, first])


def test_dispatch_reaches_distinct_authorities_but_executes_same_registry_once() -> None:
    events: list[str] = []
    application = BehaviorRegistry(default_dispatch_layer=DispatchLayer.APPLICATION)
    application.register(task="identity_probe", func=lambda **_kw: events.append("application"))
    equal = application.model_copy()
    assert application is not equal and application == equal
    local = BehaviorRegistry(default_dispatch_layer=DispatchLayer.LOCAL)
    local.register(task="identity_probe", func=lambda **_kw: events.append("local"))
    world = World(label="dispatch_identity", dispatch=application,
                  extra_authorities=[equal, application])
    graph = StoryGraph(factory=world)
    caller = Block(label="caller", registry=graph)
    ctx = PhaseCtx(graph=graph, cursor_id=caller.uid,
                   local_authorities=[local, application, local])
    receipts = list(BehaviorRegistry.chain_execute_all(
        application, application, ctx=ctx, task="identity_probe", call_kwargs={"caller": caller},
    ))
    # The two distinct, equal registries each participate under existing Core
    # chain policy. Behavior sorting still puts APPLICATION before LOCAL.
    assert len(receipts) == 3
    assert events == ["application", "application", "local"]


def test_world_singleton_authority_and_registry_identity_survive_graph_json_restore() -> None:
    world = World(label="restored_authority")
    equal = world.dispatch.model_copy()
    world.extra_authorities[:] = [equal, world.dispatch, equal]
    graph = StoryGraph(factory=world)
    for restored in (
        StoryGraph.structure(graph.unstructure()),
        StoryGraph.structure(Json.deserialize(Json.serialize(graph.unstructure()))),
    ):
        assert restored.factory is world
        assert ids(restored.get_authorities()) == ids([
            story_dispatch, presentation_dispatch, world.dispatch, equal,
        ])
