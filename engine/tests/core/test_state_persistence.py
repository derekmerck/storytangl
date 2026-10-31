"""Persistent owners retain default-created mutable state."""
from __future__ import annotations

import pytest

from tangl.core import Entity, Graph
from tangl.core.bases import HasState
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.persistence.structuring import StructuringHandler
from tangl.story.episode import Block, Scene
from tangl.story.story_graph import StoryGraph
from tangl.vm import TraversableNode
from tangl.vm.replay import OpEnum, get_replay_engine


class StatefulEntity(Entity, HasState):
    pass


@pytest.mark.parametrize("kind", [StatefulEntity, TraversableNode, Block, Scene, StoryGraph])
@pytest.mark.parametrize("explicit", [False, True])
def test_state_round_trips_after_in_place_mutation(kind, explicit: bool) -> None:
    owner = kind(label="witness", **({"locals": {}} if explicit else {}))
    uid, identifiers = owner.uid, owner.get_identifiers()
    value_before = owner.value_hash()
    before = owner.unstructure()
    owner.locals["marker"] = {"count": 1}
    after = owner.unstructure()
    assert before.get("locals", {}) == {}
    assert after["locals"] == {"marker": {"count": 1}}
    assert owner.value_hash() != value_before
    assert owner.uid == uid and owner.get_identifiers() == identifiers
    assert kind.structure(after).locals == owner.locals
    restored = StructuringHandler.structure(
        Json.deserialize(Json.serialize(after)), kind_map={kind.__fqn__(): kind},
    )
    assert type(restored) is kind and restored.uid == uid and restored.locals == owner.locals
    owner.locals.clear()
    assert owner.unstructure().get("locals", {}) == {}
    cleared = StructuringHandler.structure(
        Json.deserialize(Json.serialize(owner.unstructure())), kind_map={kind.__fqn__(): kind},
    )
    assert cleared.locals == {}


def test_default_node_state_is_visible_in_graph_delta() -> None:
    before = Graph()
    node = TraversableNode(label="entry", registry=before)
    after = Graph.structure(before.unstructure())
    after.get(node.uid).locals["marker"] = "changed"
    engine = get_replay_engine("diff_v1")
    delta = engine.build_delta(before_graph=before, after_graph=after)
    assert len(delta.events) == 1
    event = delta.events[0]
    assert event.operation is OpEnum.UPDATE and event.item_id == node.uid
    assert event.value["locals"] == {"marker": "changed"}
    restored = engine.apply_delta(graph=Graph.structure(before.unstructure()), delta=delta)
    assert restored.get(node.uid).locals == {"marker": "changed"}
