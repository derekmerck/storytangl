"""Shared Actor-owned Scene offers at ordinary and sandbox receivers."""
from __future__ import annotations

import pytest

from tangl.core import Selector
from tangl.journal.fragments import ChoiceFragment
from tangl.mechanics.sandbox import SandboxLocation
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import Action, Actor, InitMode, Scene, World
from tangl.story.concepts import Role
from tangl.story.system_handlers import render_block_choices
from tangl.vm import Affordance, Ledger
from tangl.vm.dispatch import do_provision


def _world() -> World:
    return World.from_script_data(script_data={
        "label": "shared_repair_offer",
        "metadata": {"start_at": "inn.plain"},
        "actors": {"aria": {
            "name": "Aria",
            "episodes": {"repair": {
                "action_name": "Ask Aria to fix your armor",
                "offer": {
                    "source_requirement": {"has_tags": ["repair_scope"]},
                    "availability": [{"expr": "can_pause"}],
                },
                "blocks": {"message": {
                    "content": "Aria tightens the straps.",
                    "locals": {"ready": True},
                    "conditions": ["ready"],
                }},
            }},
        }},
        "scenes": {
            "inn": {
                "tags": ["repair_scope"],
                "roles": {"friend": {"actor_ref": "aria"}, "helper": {"actor_ref": "aria"}},
                "blocks": {
                    "plain": {
                        "content": "The ordinary room.",
                        "locals": {"can_pause": True, "ready": False},
                    },
                    "hub": {
                        "kind": SandboxLocation,
                        "content": "The sandbox room.",
                        "wait_enabled": False,
                        "locals": {"can_pause": True, "ready": False},
                    },
                },
            },
            "outside": {"blocks": {
                "entry": {
                    "content": "Entry.",
                    "actions": [{"text": "Advance", "successor": "current"}],
                },
                "current": {
                    "kind": SandboxLocation,
                    "content": "Outside.",
                    "wait_enabled": False,
                    "actions": [{"text": "Enter", "successor": "inn.hub"}],
                },
            }},
        },
    })


def _offers(node):
    return [edge for edge in node.edges_out(Selector(has_kind=Action)) if edge.offer_id]


@pytest.mark.parametrize("receiver_label", ["plain", "hub"])
def test_shared_repair_offer_scope_gate_and_json_continuation(receiver_label):
    graph = _world().create_story("repair_run", init_mode=InitMode.EAGER).graph
    receiver = graph.find_one(Selector(label=receiver_label))
    outside = graph.find_one(Selector(label="current"))
    scene = graph.find_one(Selector(has_kind=Scene, label="aria.repair"))
    aria = graph.find_one(Selector(has_kind=Actor, label="aria"))
    roles = list(receiver.parent.edges_out(Selector(has_kind=Role)))
    assert len(roles) == 2 and all(role.provider is aria for role in roles)
    ledger = Ledger.from_graph(graph, entry_id=receiver.uid)
    do_provision(receiver, ctx=ledger.get_frame()._make_ctx())
    do_provision(outside, ctx=ledger.get_frame()._make_ctx().derive(cursor_id=outside.uid))
    assert not _offers(outside)
    (action,) = _offers(receiver)
    assert action.successor is scene and scene.owner is aria
    offer = graph.get(action.offer_id)
    assert isinstance(offer, Affordance)
    do_provision(receiver, ctx=ledger.get_frame()._make_ctx())
    assert _offers(receiver)[0].uid == action.uid
    receiver.locals["can_pause"] = False
    ctx = ledger.get_frame()._make_ctx()
    do_provision(receiver, ctx=ctx)
    assert _offers(receiver)[0].uid == action.uid
    choice = next(item for item in render_block_choices(caller=receiver, ctx=ctx)
                  if isinstance(item, ChoiceFragment) and item.edge_id == action.uid)
    assert not choice.available
    with pytest.raises(ValueError):
        ledger.resolve_choice(action.uid)
    receiver.locals["can_pause"] = True
    ctx = ledger.get_frame()._make_ctx()
    choice = next(item for item in render_block_choices(caller=receiver, ctx=ctx)
                  if isinstance(item, ChoiceFragment) and item.edge_id == action.uid)
    assert choice.available  # The entry's ready=True overrides receiver ready=False.
    entry = graph.get(scene.source_id)
    receiver.locals["ready"] = True
    entry.locals["ready"] = False
    choice = next(item for item in render_block_choices(caller=receiver, ctx=ctx)
                  if isinstance(item, ChoiceFragment) and item.edge_id == action.uid)
    assert not choice.available
    with pytest.raises(ValueError):
        ledger.resolve_choice(action.uid)
    entry.locals["ready"] = True
    receiver.locals["ready"] = False
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    assert restored.graph.get(scene.uid).owner is restored.graph.get(aria.uid)
    assert restored.graph.get(offer.uid).successor is restored.graph.get(scene.uid)
    assert all(restored.graph.get(role.uid).provider is restored.graph.get(aria.uid) for role in roles)
    do_provision(restored.cursor, ctx=restored.get_frame()._make_ctx())
    assert _offers(restored.cursor)[0].uid == action.uid
    restored.resolve_choice(action.uid)
    assert restored.cursor_id == receiver.uid and scene.uid in restored.cursor_history
    for role in roles:
        restored.graph.remove(role.uid)
    with pytest.raises(ValueError):
        restored.resolve_choice(action.uid)
    do_provision(restored.cursor, ctx=restored.get_frame()._make_ctx())
    assert not _offers(restored.cursor)


def test_frame_ahead_planning_uses_successors_own_repair_scope():
    graph = _world().create_story("repair_ahead", init_mode=InitMode.EAGER).graph
    entry = graph.find_one(Selector(label="entry"))
    current = graph.find_one(Selector(label="current"))
    hub = graph.find_one(Selector(label="hub"))
    ledger = Ledger.from_graph(graph, entry_id=entry.uid)
    edge = next(edge for edge in entry.edges_out(Selector(has_kind=Action)) if edge.text == "Advance")
    ledger.resolve_choice(edge.uid)
    assert ledger.cursor_id == current.uid
    assert not _offers(current)
    (offered,) = _offers(hub)
    assert offered.successor.label == "aria.repair"
    assert offered.available(ctx=ledger.get_frame()._make_ctx())
