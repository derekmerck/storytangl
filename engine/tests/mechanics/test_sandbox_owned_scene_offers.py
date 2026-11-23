"""Shared Actor-owned Scene offers at ordinary and sandbox receivers."""
from __future__ import annotations

import pytest

from tangl.core import EntityTemplate, Selector
from tangl.journal.fragments import ChoiceFragment
from tangl.mechanics.sandbox import SandboxLocation
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import Action, Actor, InitMode, Scene, World
from tangl.story.concepts import Role
from tangl.story.system_handlers import render_block_choices
from tangl.vm import Affordance, Ledger, Requirement
from tangl.vm.dispatch import do_provision


def _world(*, stay_open: bool = False) -> World:
    script = {
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
                    "actions": [{"text": "Advance", "successor": "outside_hub"}],
                },
                "outside_hub": {
                    "kind": SandboxLocation,
                    "content": "Outside.",
                    "wait_enabled": False,
                    "actions": [{"text": "Enter", "successor": "inn.hub"}],
                },
            }},
        },
    }
    if stay_open:
        blocks = script["actors"]["aria"]["episodes"]["repair"]["blocks"]
        blocks["message"]["actions"] = [{"text": "Finish", "successor": "finish"}]
        blocks["finish"] = {"content": "The repair is finished."}
    return World.from_script_data(script_data=script)


def _offers(node):
    return [edge for edge in node.edges_out(Selector(has_kind=Action)) if edge.offer_id]


@pytest.mark.parametrize("receiver_label", ["plain", "hub"])
def test_shared_repair_offer_scope_gate_and_json_continuation(receiver_label):
    graph = _world().create_story("repair_run", init_mode=InitMode.EAGER).graph
    receiver = graph.find_one(Selector(label=receiver_label))
    outside = graph.find_one(Selector(label="outside_hub"))
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
    assert graph.get(offer.action_template.payload.uid) is None
    do_provision(receiver, ctx=ledger.get_frame()._make_ctx())
    assert _offers(receiver)[0].uid == action.uid
    receiver.locals["can_pause"] = False
    ctx = ledger.get_frame()._make_ctx()
    do_provision(receiver, ctx=ctx)
    assert _offers(receiver)[0].uid == action.uid
    before_gate = graph.unstructure()
    assert not action.available(ctx=ctx)
    assert graph.unstructure() == before_gate
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
    current = graph.find_one(Selector(label="outside_hub"))
    hub = graph.find_one(Selector(label="hub"))
    ledger = Ledger.from_graph(graph, entry_id=entry.uid)
    edge = next(edge for edge in entry.edges_out(Selector(has_kind=Action)) if edge.text == "Advance")
    ledger.resolve_choice(edge.uid)
    assert ledger.cursor_id == current.uid
    assert not _offers(current)
    (offered,) = _offers(hub)
    assert offered.successor.label == "aria.repair"
    assert offered.available(ctx=ledger.get_frame()._make_ctx())


def test_changed_declaration_replaces_binding_and_refuses_stale_choice():
    graph = _world().create_story("repair_changed", init_mode=InitMode.EAGER).graph
    receiver = graph.find_one(Selector(label="plain"))
    ledger = Ledger.from_graph(graph, entry_id=receiver.uid)
    ctx = ledger.get_frame()._make_ctx()
    do_provision(receiver, ctx=ctx)
    (original,) = _offers(receiver)
    offer = graph.get(original.offer_id)
    offer.action_template = EntityTemplate.from_entity(
        offer.action_template.payload.evolve(text="Ask Aria to adjust your armor")
    )
    with pytest.raises(ValueError):
        ledger.resolve_choice(original.uid)
    do_provision(receiver, ctx=ledger.get_frame()._make_ctx())
    (replacement,) = _offers(receiver)
    assert replacement.uid != original.uid
    assert replacement.text == "Ask Aria to adjust your armor"


def test_detachment_preserves_active_call_through_json_restore():
    graph = _world(stay_open=True).create_story("repair_active", init_mode=InitMode.EAGER).graph
    receiver = graph.find_one(Selector(label="plain"))
    roles = list(receiver.parent.edges_out(Selector(has_kind=Role)))
    ledger = Ledger.from_graph(graph, entry_id=receiver.uid)
    do_provision(receiver, ctx=ledger.get_frame()._make_ctx())
    (call,) = _offers(receiver)
    ledger.resolve_choice(call.uid)
    assert call.uid in ledger.call_stack_ids
    for role in roles:
        graph.remove(role.uid)
    ctx = ledger.get_frame()._make_ctx()
    choices = render_block_choices(caller=receiver, ctx=ctx.derive(cursor_id=receiver.uid))
    assert all(choice.edge_id != call.uid for choice in choices or ())
    do_provision(receiver, ctx=ctx.derive(cursor_id=receiver.uid))
    assert graph.get(call.uid) is call
    assert not call.available(ctx=ctx)
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    assert restored.graph.get(call.uid) is not None
    finish = next(edge for edge in restored.cursor.edges_out(Selector(has_kind=Action))
                  if edge.text == "Finish")
    restored.resolve_choice(finish.uid)
    assert restored.cursor_id == receiver.uid
    do_provision(restored.cursor, ctx=restored.get_frame()._make_ctx())
    assert restored.graph.get(call.uid) is None


def test_restored_new_binding_uses_context_randomness():
    graph = _world().create_story("repair_seeded", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    data = Json.serialize(ledger.unstructure())
    ids = []
    for _ in range(2):
        restored = Ledger.structure(Json.deserialize(data))
        receiver = restored.graph.find_one(Selector(label="hub"))
        assert not _offers(receiver)
        ctx = restored.get_frame()._make_ctx().derive(cursor_id=receiver.uid)
        ctx.get_random().seed(12345)
        do_provision(receiver, ctx=ctx)
        ids.append(_offers(receiver)[0].uid)
    assert ids[0] == ids[1]


def test_replanning_retains_binding_without_materialization(monkeypatch):
    graph = _world().create_story("repair_replanning", init_mode=InitMode.EAGER).graph
    receiver = graph.find_one(Selector(label="plain"))
    ledger = Ledger.from_graph(graph, entry_id=receiver.uid)
    calls = []
    original = EntityTemplate.materialize

    def counted(template, *args, **kwargs):
        calls.append(template.uid)
        return original(template, *args, **kwargs)

    monkeypatch.setattr(EntityTemplate, "materialize", counted)
    do_provision(receiver, ctx=ledger.get_frame()._make_ctx())
    action = _offers(receiver)[0]
    assert len(calls) == 1
    for _ in range(20):
        do_provision(receiver, ctx=ledger.get_frame()._make_ctx())
    assert _offers(receiver)[0].uid == action.uid
    assert len(calls) == 1


def test_one_owned_local_verb_serves_ordinary_and_sandbox_receivers():
    from tangl.story.fabula.materializer import action_template_from_spec
    from tangl.story.scoped_offers import ScopedActionOffer

    graph = _world().create_story("shared_verb", init_mode=InitMode.EAGER).graph
    aria = graph.find_one(Selector(has_kind=Actor, label="aria"))
    offer = ScopedActionOffer(
        registry=graph, predecessor_id=aria.uid, requirement=Requirement(),
        source_requirement=Requirement(has_tags=["repair_scope"]),
        action_template=action_template_from_spec({
            "text": "Check the armor", "successor": "current",
            "effects": ["checked = True"],
        }, label="check_armor"),
    )
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    actions = []
    for label in ("plain", "hub"):
        receiver = graph.find_one(Selector(label=label))
        do_provision(receiver, ctx=ledger.get_frame()._make_ctx().derive(cursor_id=receiver.uid))
        (action,) = [edge for edge in _offers(receiver) if edge.offer_id == offer.uid]
        assert action.successor is receiver
        actions.append(action)
    assert actions[0].uid != actions[1].uid
