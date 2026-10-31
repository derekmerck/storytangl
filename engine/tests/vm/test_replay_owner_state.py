"""Replay registry constructor state without replacing the live owner."""
from __future__ import annotations

from uuid import UUID

import pytest

from tangl.core import Graph, Node
from tangl.core.bases import HasState
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.core import Selector
from tangl.vm import Ledger, TraversableEdge, TraversableNode
from tangl.vm.dispatch import on_update
from tangl.vm.replay import CheckpointRecord, OpEnum, Patch, get_replay_engine


class StatefulGraph(Graph, HasState):
    score: int = 0


def _copy(graph: StatefulGraph) -> StatefulGraph:
    return StatefulGraph.structure(graph.unstructure())


def test_owner_changes_and_default_resets_keep_live_graph_and_members() -> None:
    engine = get_replay_engine("diff_v1")
    before = StatefulGraph(label="owner")
    member = Node(label="member", registry=before)
    after = _copy(before)
    after.locals["marker"] = "set"
    after.score = 7
    delta = engine.build_delta(before_graph=before, after_graph=after)
    assert delta is not None and delta.events == []
    assert delta.registry_state["locals"] == {"marker": "set"}
    assert delta.registry_state["score"] == 7
    assert "members" not in delta.registry_state
    identity = id(before)
    assert engine.apply_delta(graph=before, delta=delta) is before
    assert id(before) == identity and before.uid == after.uid
    assert before.get(member.uid) is member and member.registry is before
    assert before.value_hash() == after.value_hash()
    empty = _copy(after)
    empty.locals.clear()
    empty.score = 0
    reset = engine.build_delta(before_graph=after, after_graph=empty)
    assert reset is not None and "locals" not in reset.registry_state
    engine.apply_delta(graph=before, delta=reset)
    assert before.locals == {} and before.score == 0
    assert before.value_hash() == empty.value_hash()
    assert engine.build_delta(before_graph=before, after_graph=empty) is None


def test_mixed_changes_preserve_member_order_and_hash_guards() -> None:
    engine = get_replay_engine("diff_v1")
    before = StatefulGraph()
    first = Node(uid=UUID(int=4), label="first", registry=before)
    removed = Node(uid=UUID(int=3), label="remove", registry=before)
    after = _copy(before)
    after.locals["marker"] = "mixed"
    after.score = 2
    after.remove(removed.uid)
    after.add(after.get(first.uid).evolve(label="updated"))
    Node(uid=UUID(int=2), label="new first", registry=after)
    Node(uid=UUID(int=1), label="new second", registry=after)
    delta = engine.build_delta(before_graph=before, after_graph=after)
    assert [event.operation for event in delta.events] == [
        OpEnum.DELETE, OpEnum.CREATE, OpEnum.CREATE, OpEnum.UPDATE,
    ]
    wrong = _copy(before)
    wrong.score = 99
    with pytest.raises(ValueError, match="initial registry state"):
        engine.apply_delta(graph=wrong, delta=delta)
    target = _copy(before)
    engine.apply_delta(graph=target, delta=delta)
    assert list(target.members) == list(after.members)
    assert target.locals == after.locals and target.score == after.score
    assert target.value_hash() == after.value_hash()
    assert all(item.registry is target for item in target.values())


def test_incompatible_owner_identity_is_rejected() -> None:
    engine = get_replay_engine("diff_v1")
    before, other = StatefulGraph(), StatefulGraph()
    with pytest.raises(ValueError, match="identities or kinds"):
        engine.build_delta(before_graph=before, after_graph=other)
    different_kind = Graph(uid=before.uid)
    with pytest.raises(ValueError, match="identities or kinds"):
        engine.build_delta(before_graph=before, after_graph=different_kind)

    after = _copy(before)
    after.score = 1
    patch = engine.build_delta(before_graph=before, after_graph=after)
    patch.registry_state["uid"] = other.uid
    with pytest.raises(ValueError, match="incompatible identity or kind"):
        patch.apply_to(before)
    assert before.score == 0
    patch.registry_state["uid"] = before.uid
    patch.registry_state["kind"] = Graph
    with pytest.raises(ValueError, match="incompatible identity or kind"):
        patch.apply_to(before)
    assert before.score == 0


def test_owner_header_does_not_walk_members(monkeypatch: pytest.MonkeyPatch) -> None:
    graph = StatefulGraph()
    Node(label="member", registry=graph)
    def forbidden(_self):
        pytest.fail("owner header must not unstructure members")
    monkeypatch.setattr(Node, "unstructure", forbidden)
    assert "members" not in graph.unstructure(include_members=False)


def test_json_patch_restores_owner_state() -> None:
    engine = get_replay_engine("diff_v1")
    before = StatefulGraph()
    after = _copy(before)
    after.locals["marker"] = "json"
    patch = engine.build_delta(before_graph=before, after_graph=after)
    data = Json.deserialize(Json.serialize(patch.unstructure()))
    data["kind"] = Patch
    restored = Patch.structure(data)
    engine.apply_delta(graph=before, delta=restored)
    assert before.locals == {"marker": "json"}


def test_ledger_json_rollback_replays_owner_and_node_state_between_checkpoints() -> None:
    graph = StatefulGraph()
    nodes = [TraversableNode(label=label, registry=graph) for label in ("start", "one", "two", "three")]
    edges = [TraversableEdge(predecessor_id=left.uid, successor_id=right.uid, registry=graph)
             for left, right in zip(nodes, nodes[1:])]

    @on_update
    def update_state(*, caller, ctx, **_kw):
        if caller.label == "one":
            ctx.graph.locals["marker"] = "one"
            caller.locals["marker"] = "node-one"
        elif caller.label == "two":
            ctx.graph.locals.clear()
            caller.locals["marker"] = "node-two"
        elif caller.label == "three":
            ctx.graph.locals["marker"] = "three"

    ledger = Ledger.from_graph(graph=graph, entry_id=nodes[0].uid)
    ledger.checkpoint_cadence = 100
    for edge in edges:
        ledger.resolve_choice(edge.uid)
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    checkpoints = list(Selector(has_kind=CheckpointRecord).filter(restored.output_stream))
    assert [checkpoint.step for checkpoint in checkpoints] == [0]
    restored.rollback_to_step(2)
    assert restored.cursor_id == nodes[2].uid
    assert restored.graph.locals == {}
    assert restored.graph.get(nodes[1].uid).locals["marker"] == "node-one"
    assert restored.graph.get(nodes[2].uid).locals["marker"] == "node-two"
    restored.rollback_to_step(1)
    assert restored.cursor_id == nodes[1].uid
    assert restored.graph.locals == {"marker": "one"}
    assert restored.graph.get(nodes[1].uid).locals["marker"] == "node-one"
    assert restored.graph.get(nodes[2].uid).locals == {}
