"""A known source-side refusal precedes lazy destination construction."""
from __future__ import annotations

import pytest

from tangl.core import Edge, Graph, Selector
from tangl.mechanics.sandbox import SandboxLocation
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import Action, Actor, Block, InitMode, World
from tangl.story.system_handlers import _preview_destination_viability
from tangl.vm import Dependency, Ledger, Requirement, Resolver
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.dispatch import do_provision
from tangl.vm.system_handlers import validate_successor_exists


def test_bound_choice_evaluates_random_source_guard_once():
    graph = Graph()
    source = Block(label="source", registry=graph)
    target = Block(label="target", registry=graph)
    action = Action(
        registry=graph, predecessor_id=source.uid, successor_id=target.uid,
        availability=[{"expr": "rand.random() < 0.5"}],
    )
    frame = Ledger.from_graph(graph, entry_id=source.uid).get_frame()
    frame._random.seed(1)
    frame.resolve_choice(action)
    assert frame.cursor is target


def test_lazy_choice_evaluates_random_source_guard_once(monkeypatch):
    world = World.from_script_data(script_data={
        "label": "lazy_random_guard", "metadata": {"start_at": "intro.start"},
        "scenes": {"intro": {"blocks": {
            "start": {"actions": [{"text": "Enter", "successor": "later",
                                   "conditions": ["rand.random() < 0.5"]}]},
            "later": {"content": "Here."},
        }}},
    })
    graph = world.create_story("run", init_mode=InitMode.LAZY).graph
    frame = Ledger.from_graph(graph).get_frame()
    action = next(frame.cursor.edges_out(Selector(has_kind=Action, text="Enter")))
    calls = []
    original = Action.source_available

    def count_source(self, *, ctx=None, ns=None):
        calls.append(self.uid)
        return original(self, ctx=ctx, ns=ns)

    monkeypatch.setattr(Action, "source_available", count_source)
    frame._random.seed(1)
    frame.resolve_choice(action)
    assert frame.cursor.label == "later"
    assert calls.count(action.uid) == 1


@pytest.mark.parametrize("remove_offer", [False, True])
def test_readiness_rechecks_scoped_attachment(monkeypatch, remove_offer):
    world = World.from_script_data(script_data={
        "label": "lazy_stale_offer", "metadata": {"start_at": "intro.start"},
        "scenes": {"intro": {"blocks": {
            "start": {"offered_actions": [{"text": "Enter", "successor": "later"}]},
            "later": {"content": "Here."},
        }}},
    })
    graph = world.create_story("run", init_mode=InitMode.LAZY).graph
    frame = Ledger.from_graph(graph).get_frame()
    do_provision(frame.cursor, ctx=frame._make_ctx())
    action = next(frame.cursor.edges_out(Selector(has_kind=Action, text="Enter")))
    original = type(frame)._ready_destinations

    def detach_after_readiness(self, edges, *, ctx):
        original(self, edges, ctx=ctx)
        graph.remove(action.offer_id if remove_offer else action.uid)

    monkeypatch.setattr(type(frame), "_ready_destinations", detach_after_readiness)
    with pytest.raises(ValueError, match="Edge validation failed"):
        frame.resolve_choice(action)
    assert frame.cursor.label == "start"
    assert not frame.return_stack


@pytest.mark.parametrize("through_selection", [False, True])
def test_readiness_uses_destination_provider_scope(through_selection):
    graph = Graph()
    source = Block(label="source", registry=graph)
    target = Block(label="target", registry=graph)
    source_actor = Actor(label="source_actor", registry=graph)
    target_actor = Actor(label="target_actor", registry=graph)
    Edge(registry=graph, predecessor_id=source.uid, successor_id=source_actor.uid)
    Edge(registry=graph, predecessor_id=target.uid, successor_id=target_actor.uid)
    dependency = Dependency(
        registry=graph, predecessor_id=target.uid, requirement=Requirement(has_kind=Actor),
    )
    ctx = PhaseCtx(graph=graph, cursor_id=source.uid)
    resolver = Resolver.from_ctx(ctx)
    if through_selection:
        action = Action(registry=graph, predecessor_id=source.uid, successor_id=target.uid)
        ledger = Ledger.from_graph(graph, entry_id=source.uid)
        ledger.resolve_choice(action.uid)
        assert ledger.cursor is target
    else:
        resolver.provision_readiness(target, _ctx=ctx)
    assert dependency.provider is target_actor
    before = graph.unstructure()
    resolver.provision_readiness(target, _ctx=ctx)
    assert dependency.provider is target_actor
    assert dependency.provider is not source_actor
    assert graph.unstructure() == before


def test_destination_preview_uses_destination_candidates():
    graph = Graph()
    source = Block(label="source", registry=graph)
    target = Block(label="target", registry=graph)
    actor = Actor(label="target_actor", registry=graph)
    Edge(registry=graph, predecessor_id=target.uid, successor_id=actor.uid)
    Dependency(
        registry=graph, predecessor_id=target.uid, label="person",
        requirement=Requirement(has_kind=Actor, uid=actor.uid),
    )
    action = Action(registry=graph, predecessor_id=source.uid, successor_id=target.uid)
    ctx = PhaseCtx(graph=graph, cursor_id=source.uid)
    assert validate_successor_exists(caller=action, ctx=ctx)


def test_nested_destination_assembles_closed_intermediate_scope():
    world = World.from_script_data(script_data={
        "label": "closed_intermediate", "metadata": {"start_at": "intro.start"},
        "scenes": {
            "intro": {"blocks": {"start": {"actions": [
                {"text": "Enter", "successor": "other.entry"},
            ]}}},
            "other": {"conditions": ["False"], "blocks": {"entry": {"content": "Here."}}},
        },
    })
    ledger = Ledger.from_graph(world.create_story("run", init_mode=InitMode.LAZY).graph)
    action = next(ledger.cursor.edges_out(Selector(has_kind=Action, text="Enter")))
    ledger.resolve_choice(action.uid)
    assert ledger.cursor.label == "entry"


@pytest.mark.parametrize("field", ["actions", "offered_actions"])
def test_rejected_lazy_call_keeps_graph_and_call_stack_unchanged(field):
    world = World.from_script_data(script_data={
        "label": "lazy_preflight_guard", "metadata": {"start_at": "intro.start"},
        "scenes": {"intro": {"blocks": {
            "start": {"locals": {"ready": False}, field: [
                {"text": "Enter", "successor": "later", "return": True,
                 "conditions": ["ready"]},
            ]},
            "later": {"locals": {"ready": True}, "conditions": ["ready"],
                      "content": "Arrived."},
        }}},
    })
    graph = world.create_story("run", init_mode=InitMode.LAZY).graph
    ledger = Ledger.from_graph(graph)
    frame = ledger.get_frame()
    do_provision(frame.cursor, ctx=frame._make_ctx())
    action = next(frame.cursor.edges_out(Selector(has_kind=Action, text="Enter")))
    before = graph.unstructure()
    random_state = frame._random.getstate()
    with pytest.raises(ValueError, match="Edge validation failed"):
        frame.resolve_choice(action)
    assert graph.unstructure() == before
    assert frame._random.getstate() == random_state
    assert not frame.return_stack
    assert graph.find_one(Selector(has_kind=Block, label="later")) is None


def test_invalid_payload_does_not_prepare_destination():
    world = World.from_script_data(script_data={
        "label": "lazy_payload_guard", "metadata": {"start_at": "intro.start"},
        "scenes": {"intro": {"blocks": {
            "start": {"actions": [{
                "text": "Enter", "successor": "later", "return": True,
                "accepts": {"kind": "text", "required": True},
            }]},
            "later": {"content": "Here."},
        }}},
    })
    graph = world.create_story("run", init_mode=InitMode.LAZY).graph
    frame = Ledger.from_graph(graph).get_frame()
    action = next(frame.cursor.edges_out(Selector(has_kind=Action, text="Enter")))
    before = graph.unstructure()
    random_state = frame._random.getstate()
    with pytest.raises(ValueError, match="Text input"):
        frame.resolve_choice(action)
    assert graph.unstructure() == before
    assert frame._random.getstate() == random_state
    assert not frame.return_stack


@pytest.mark.parametrize("field", ["actions", "offered_actions"])
@pytest.mark.parametrize("receiver_kind", [Block, SandboxLocation])
def test_destination_refusal_leaves_dormant_target_without_call(field, receiver_kind):
    world = World.from_script_data(script_data={
        "label": "lazy_destination_guard", "metadata": {"start_at": "intro.start"},
        "scenes": {"intro": {"blocks": {
            "start": {"kind": receiver_kind, "locals": {"ready": True}, field: [
                {"text": "Enter", "successor": "later", "return": True},
            ]},
            "later": {"locals": {"ready": False, "arrivals": 0},
                      "conditions": ["ready"], "effects": ["arrivals += 1"]},
        }}},
    })
    graph = world.create_story("run", init_mode=InitMode.LAZY).graph
    ledger = Ledger.from_graph(graph)
    frame = ledger.get_frame()
    do_provision(frame.cursor, ctx=frame._make_ctx())
    action = next(frame.cursor.edges_out(Selector(has_kind=Action, text="Enter")))
    start = frame.cursor.uid
    trace = list(frame.cursor_trace)
    output = frame.output_stream.unstructure()
    before_preview = graph.unstructure()
    random_state = frame._random.getstate()
    for _ in range(2):
        preview = _preview_destination_viability(edge=action, ctx=frame._make_ctx())
        assert preview is not None and preview.viable and preview.requires_readiness
    assert graph.unstructure() == before_preview
    assert frame._random.getstate() == random_state
    assert graph.find_one(Selector(has_kind=Block, label="later")) is None
    with pytest.raises(ValueError):
        frame.resolve_choice(action)
    target = graph.find_one(Selector(has_kind=Block, label="later"))
    assert target is not None
    assert frame.cursor.uid == start
    assert frame.cursor_trace == trace
    assert frame.output_stream.unstructure() == output
    assert not frame.return_stack
    assert action.successor_id == target.uid
    assert target.locals["arrivals"] == 0
    before = graph.unstructure()
    frame._ready_destinations([action], ctx=frame._make_ctx())
    assert graph.unstructure() == before
    if field == "offered_actions" and receiver_kind is Block:
        do_provision(frame.cursor, ctx=frame._make_ctx())
        assert graph.get(action.uid) is action
        assert action.successor_id == target.uid
    target.locals["ready"] = True
    frame.resolve_choice(action)
    assert target.uid in frame.cursor_trace
    assert target.locals["arrivals"] == 1


@pytest.mark.parametrize("field", ["actions", "offered_actions"])
def test_restored_checkpoint_repeats_destination_allocation(field):
    world = World.from_script_data(script_data={
        "label": "lazy_destination_restore", "metadata": {"start_at": "intro.start"},
        "scenes": {"intro": {"blocks": {
            "start": {field: [{"text": "Enter", "successor": "later"}]},
            "later": {"content": "Here."},
        }}},
    })
    ledger = Ledger.from_graph(world.create_story("run", init_mode=InitMode.LAZY).graph)
    do_provision(ledger.cursor, ctx=ledger.get_frame()._make_ctx())
    checkpoint = Json.serialize(ledger.unstructure())
    results = []
    for _ in range(2):
        restored = Ledger.structure(Json.deserialize(checkpoint))
        frame = restored.get_frame()
        frame._random.seed(12345)
        action = next(frame.cursor.edges_out(Selector(has_kind=Action)))
        frame.resolve_choice(action)
        results.append((action.uid, action.templ_hash, action.successor_id))
    assert results[0] == results[1]


def test_destination_role_is_established_before_admission():
    world = World.from_script_data(script_data={
        "label": "lazy_destination_role", "metadata": {"start_at": "intro.start"},
        "actors": {"guard": {"name": "Joe"}},
        "scenes": {"intro": {"blocks": {
            "start": {"actions": [{"text": "Enter", "successor": "later"}]},
            "later": {
                "roles": [{"label": "host", "actor_ref": "guard", "hard": True}],
                "conditions": ["host.name == 'Joe'"],
                "content": "Hello.",
            },
        }}},
    })
    ledger = Ledger.from_graph(world.create_story("run", init_mode=InitMode.LAZY).graph)
    frame = ledger.get_frame()
    action = next(frame.cursor.edges_out(Selector(has_kind=Action)))
    frame.resolve_choice(action)
    assert frame.cursor.label == "later"


def test_container_entry_role_is_established_before_admission():
    world = World.from_script_data(script_data={
        "label": "lazy_entry_role", "metadata": {"start_at": "intro.start"},
        "actors": {"guard": {"name": "Joe"}},
        "scenes": {
            "intro": {"blocks": {"start": {"actions": [
                {"text": "Enter", "successor": "other"},
            ]}}},
            "other": {"blocks": {"entry": {
                "roles": [{"label": "host", "actor_ref": "guard", "hard": True}],
                "conditions": ["host.name == 'Joe'"], "content": "Here.",
            }}},
        },
    })
    ledger = Ledger.from_graph(world.create_story("run", init_mode=InitMode.LAZY).graph)
    frame = ledger.get_frame()
    action = next(frame.cursor.edges_out(Selector(has_kind=Action, text="Enter")))
    frame.resolve_choice(action)
    assert frame.cursor.label == "entry"


def test_refused_lazy_entry_roundtrips_before_replay():
    world = World.from_script_data(script_data={
        "label": "refused_entry_replay", "metadata": {"start_at": "intro.start"},
        "scenes": {"intro": {"blocks": {
            "start": {"actions": [
                {"text": "Enter", "successor": "later", "return": True},
                {"text": "Stay", "successor": "current"},
            ]},
            "later": {"conditions": ["False"]},
        }}},
    })
    ledger = Ledger.from_graph(world.create_story("run", init_mode=InitMode.LAZY).graph)
    actions = {edge.text: edge.uid for edge in ledger.cursor.edges_out(Selector(has_kind=Action))}
    with pytest.raises(ValueError):
        ledger.resolve_choice(actions["Enter"])
    assert ledger.graph.find_one(Selector(has_kind=Block, label="later")) is not None
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    restored.resolve_choice(actions["Stay"])
    settled_step = restored.cursor_steps
    expected_hash = restored.graph.value_hash()
    expected_history = list(restored.cursor_history)
    expected_stack = list(restored.call_stack_ids)
    expected_journal = [fragment.unstructure() for fragment in restored.get_journal()]
    restored.resolve_choice(actions["Stay"])
    restored.rollback_to_step(settled_step)
    assert restored.graph.value_hash() == expected_hash
    assert restored.cursor_history == expected_history
    assert restored.call_stack_ids == expected_stack
    assert [fragment.unstructure() for fragment in restored.get_journal()] == expected_journal


def test_closed_container_remains_bound_without_pushing_return():
    world = World.from_script_data(script_data={
        "label": "lazy_closed_entry", "metadata": {"start_at": "intro.start"},
        "scenes": {
            "intro": {"blocks": {"start": {"actions": [
                {"text": "Enter", "successor": "other", "return": True},
            ]}}},
            "other": {"blocks": {"entry": {
                "locals": {"ready": False}, "conditions": ["ready"], "content": "Here.",
            }}},
        },
    })
    ledger = Ledger.from_graph(world.create_story("run", init_mode=InitMode.LAZY).graph)
    frame = ledger.get_frame()
    action = next(frame.cursor.edges_out(Selector(has_kind=Action, text="Enter")))
    with pytest.raises(ValueError, match="Edge validation failed"):
        frame.resolve_choice(action)
    target = action.successor
    assert target is not None
    assert not frame.return_stack
    target.resolve_entry(ctx=frame._make_ctx()).locals["ready"] = True
    frame.resolve_choice(action)
    assert target.uid in frame.cursor_trace
