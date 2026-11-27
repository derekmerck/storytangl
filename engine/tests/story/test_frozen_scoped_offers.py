"""Frozen EAGER setup closes scoped Action bindings for each playthrough."""
from __future__ import annotations

import pytest
from uuid import UUID

from tangl.core import EntityTemplate, Selector
from tangl.journal.fragments import ChoiceFragment, ContentFragment
from tangl.persistence import PersistenceManagerFactory
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.service import ServiceManager
from tangl.service.response import DirectEdgeRequest
from tangl.story import Action, Block, InitMode, World
from tangl.story.concepts import Role
from tangl.story.fabula.materializer import action_template_from_spec
from tangl.story.scoped_offers import add_local_action_offer
from tangl.vm import Ledger
from tangl.vm.dispatch import do_provision


def _script(label: str) -> dict:
    return {
        "label": label, "metadata": {"start_at": "inn.start"},
        "actors": {"aria": {"name": "Aria", "episodes": {"chat": {
            "action_name": "Talk", "offer": {
                "source_requirement": {"has_tags": ["tavern"]},
                "availability": [{"expr": "ready"}],
            },
            "blocks": {"message": {"content": "Hello."}},
        }}}},
        "scenes": {"inn": {
            "tags": ["tavern"], "roles": {"bard": "aria"},
            "blocks": {
                "start": {"content": "Start", "locals": {"ready": True},
                          "actions": [{"text": "Next", "successor": "middle"}]},
                "middle": {"content": "Middle", "locals": {"ready": True},
                           "actions": [{"text": "Far", "successor": "far"}]},
                "far": {"content": "Far", "locals": {"ready": False, "lit": False},
                        "offered_actions": [{"text": "Light", "successor": "current",
                                             "effects": ["lit = True"],
                                             "journal_text": "The lamp glows."}]},
            },
        }},
    }


def _node(graph, label):
    return graph.find_one(Selector(has_kind=Block, label=label))


def _offered(node):
    return [edge for edge in node.edges_out(Selector(has_kind=Action)) if edge.offer_id]


def test_frozen_setup_closes_realized_scope_and_preserves_replay(monkeypatch):
    graph = World.from_script_data(script_data=_script("frozen_scope")).create_story(
        "run", init_mode=InitMode.EAGER, freeze_shape=True,
    ).graph
    start, middle, far = (_node(graph, label) for label in ("start", "middle", "far"))
    assert graph.frozen_shape
    assert len(_offered(start)) == len(_offered(middle)) == 1
    assert {edge.text for edge in _offered(far)} == {"", "Light"}
    talk = next(edge for edge in _offered(far) if edge.text == "")
    light = next(edge for edge in _offered(far) if edge.text == "Light")
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    ctx = ledger.get_frame()._make_ctx().derive(cursor_id=far.uid)
    gate_state = graph.unstructure()
    assert not talk.available(ctx=ctx)
    assert graph.unstructure() == gate_state
    far.locals["ready"] = True
    gate_state = graph.unstructure()
    assert talk.available(ctx=ledger.get_frame()._make_ctx().derive(cursor_id=far.uid))
    assert graph.unstructure() == gate_state
    ledger.save_snapshot(force=True)
    ids = [edge.uid for edge in _offered(far)]
    before = graph.unstructure()
    def no_materialization(*_args, **_kwargs):
        pytest.fail("unchanged frozen assembly materialized a new Action")
    monkeypatch.setattr(EntityTemplate, "materialize", no_materialization)
    for _ in range(3):
        do_provision(far, ctx=ledger.get_frame()._make_ctx().derive(cursor_id=far.uid))
    assert graph.unstructure() == before
    assert [edge.uid for edge in _offered(far)] == ids
    monkeypatch.undo()
    ledger.resolve_choice(next(e.uid for e in start.edges_out(Selector(has_kind=Action)) if e.text == "Next"))
    ledger.resolve_choice(next(e.uid for e in middle.edges_out(Selector(has_kind=Action)) if e.text == "Far"))
    ledger.save_snapshot()
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    restored.resolve_choice(light.uid)
    assert restored.cursor.locals["lit"] is True
    assert any(isinstance(f, ContentFragment) and f.content == "The lamp glows."
               for f in restored.get_journal())
    restored.rollback_to_step(2, reason="repeat")
    assert restored.graph.get(light.uid) is not None
    restored.resolve_choice(light.uid)
    assert restored.cursor.locals["lit"] is True


def test_frozen_reconciliation_rejects_changed_or_new_binding():
    graph = World.from_script_data(script_data=_script("frozen_refusal")).create_story(
        "run", freeze_shape=True,
    ).graph
    far = _node(graph, "far")
    ledger = Ledger.from_graph(graph, entry_id=far.uid)
    action = next(edge for edge in _offered(far) if edge.text == "Light")
    offer = graph.get(action.offer_id)
    offer.action_template.payload.text = "A different action"
    with pytest.raises(ValueError, match="Frozen story cannot bind scoped Action offer"):
        do_provision(far, ctx=ledger.get_frame()._make_ctx())
    with pytest.raises(ValueError):
        ledger.resolve_choice(action.uid)
    graph.remove(action.uid)
    with pytest.raises(ValueError, match="Frozen story cannot bind scoped Action offer"):
        do_provision(far, ctx=ledger.get_frame()._make_ctx())


def test_frozen_reconciliation_rejects_newly_matching_scope_without_mutation():
    script = _script("frozen_new_match")
    script["actors"]["aria"]["episodes"]["chat"]["offer"]["source_requirement"] = {
        "has_tags": ["chosen"],
    }
    graph = World.from_script_data(script_data=script).create_story("run", freeze_shape=True).graph
    far = _node(graph, "far")
    assert {edge.text for edge in _offered(far)} == {"Light"}
    far.tags = far.tags | {"chosen"}
    before = graph.unstructure()
    ledger = Ledger.from_graph(graph, entry_id=far.uid)
    with pytest.raises(ValueError, match="Frozen story cannot bind scoped Action offer"):
        do_provision(far, ctx=ledger.get_frame()._make_ctx())
    assert graph.unstructure() == before


def test_frozen_reconciliation_rejects_new_latent_destination():
    graph = World.from_script_data(script_data=_script("frozen_latent")).create_story(
        "run", freeze_shape=True,
    ).graph
    far = _node(graph, "far")
    graph.remove(_node(graph, "middle").uid)
    template = action_template_from_spec(
        {"text": "Hidden", "successor_ref": "inn.middle"}, label="hidden",
    )
    add_local_action_offer(far, template)
    before = graph.unstructure()
    ledger = Ledger.from_graph(graph, entry_id=far.uid)
    with pytest.raises(ValueError, match="Frozen story cannot bind scoped Action offer"):
        do_provision(far, ctx=ledger.get_frame()._make_ctx())
    assert graph.unstructure() == before


def test_frozen_scope_loss_preserves_active_bookmark_through_restore():
    script = _script("frozen_active_call")
    blocks = script["actors"]["aria"]["episodes"]["chat"]["blocks"]
    blocks["message"]["actions"] = [{"text": "Finish", "successor": "finish"}]
    blocks["finish"] = {"content": "Done."}
    graph = World.from_script_data(script_data=script).create_story("run", freeze_shape=True).graph
    start = _node(graph, "start")
    call = _offered(start)[0]
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    ledger.resolve_choice(call.uid)
    assert call.uid in ledger.call_stack_ids
    role = next(start.parent.edges_out(Selector(has_kind=Role)))
    graph.remove(role.uid)
    do_provision(start, ctx=ledger.get_frame()._make_ctx().derive(cursor_id=start.uid))
    assert graph.get(call.uid) is call
    assert not call.available(ctx=ledger.get_frame()._make_ctx())
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    finish = next(edge for edge in restored.cursor.edges_out(Selector(has_kind=Action))
                  if edge.text == "Finish")
    restored.resolve_choice(finish.uid)
    assert restored.cursor_id == start.uid


class EntryChoiceWorld(World):
    def _resolve_entry_override(self, graph, namespace):
        chosen = _node(graph, namespace["start"])
        return chosen.uid


def test_each_start_closes_its_own_setup_context_without_catalog_mutation():
    script = _script("frozen_two_starts")
    script["actors"]["aria"]["episodes"]["chat"]["offer"]["source_requirement"] = {
        "has_tags": ["chosen"],
    }
    world = EntryChoiceWorld.from_script_data(script_data=script)
    @world.dispatch.register(task="story_ready")
    def configure(*, ctx, **_kwargs):
        ctx.cursor.tags = ctx.cursor.tags | {"chosen"}

    catalog = world.templates.unstructure()
    first = world.create_story("first", freeze_shape=True, namespace={"start": "start"}).graph
    second = world.create_story("second", freeze_shape=True, namespace={"start": "far"}).graph
    assert first.initial_cursor_id == _node(first, "start").uid
    assert second.initial_cursor_id == _node(second, "far").uid
    assert len(_offered(_node(first, "start"))) == 1
    assert {a.text for a in _offered(_node(first, "far"))} == {"Light"}
    assert not _offered(_node(second, "start"))
    assert {a.text for a in _offered(_node(second, "far"))} == {"", "Light"}
    assert world.templates.unstructure() == catalog


def test_frozen_offer_through_service_json(tmp_path):
    world = World.from_script_data(script_data=_script("frozen_service"))
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path))
    user = UUID(service.create_user(secret="frozen-offer").details["user_id"])
    envelope = service.create_story(user_id=user, world_id=world.label, world=world, freeze_shape=True)
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment) and f.text == "Talk")
    assert choice.available
    envelope = service.resolve_choice(user_id=user, request=DirectEdgeRequest(edge_id=choice.edge_id))
    assert any(isinstance(f, ContentFragment) and f.content == "Hello."
               for f in envelope.fragments)
    with service.open_session(user_id=user) as session:
        assert session.ledger.graph.frozen_shape
        assert session.ledger.graph.get(choice.edge_id) is not None
