"""Wait uses the shared scoped Action lifecycle and sandbox clock."""
from __future__ import annotations

import pytest

from tangl.core import EntityTemplate, Graph, Selector
from tangl.mechanics.sandbox import SandboxLocation, SandboxScope, current_world_time
from tangl.journal.fragments import ChoiceFragment, ContentFragment
from tangl.mechanics.sandbox.handlers import compose_sandbox_wait_order
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.service import ServiceManager
from tangl.story import Action, World
from tangl.vm import Ledger
from tangl.vm.dispatch import do_provision


def _wait(location: SandboxLocation) -> Action:
    return next(location.edges_out(Selector(has_kind=Action, has_tags={"wait"})))


def test_wait_keeps_its_menu_position_after_selection():
    world = World.from_script_data(script_data={
        "label": "wait_menu_order", "metadata": {"start_at": "hub.road"},
        "scenes": {"hub": {"kind": SandboxScope, "blocks": {
            "road": {"kind": SandboxLocation, "links": {"east": "east", "west": "west"}},
            "east": {"kind": SandboxLocation}, "west": {"kind": SandboxLocation},
        }}},
    })
    graph = world.create_story("run").graph
    road = graph.find_one(Selector(has_kind=SandboxLocation, label="road"))
    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    ServiceManager._prime_initial_update(ledger)
    before = [f for f in ledger.get_current_update() if isinstance(f, ChoiceFragment)]
    assert [f.text for f in before] == ["Go east to east", "Go west to west", "Wait"]
    wait_uid = before[-1].edge_id
    ledger.resolve_choice(wait_uid)
    after = [f for f in ledger.get_current_update() if isinstance(f, ChoiceFragment)]
    assert [f.text for f in after] == ["Go east to east", "Go west to west", "Wait"]
    assert after[-1].edge_id == wait_uid


def test_wait_order_preserves_other_choices_and_fragment_slots():
    graph = Graph()
    road = SandboxLocation(label="road", registry=graph)
    actions = [
        Action(registry=graph, predecessor_id=road.uid, successor_id=road.uid,
               text=text, tags=tags)
        for text, tags in [
            ("Wait", {"sandbox", "wait"}), ("Inspect", set()),
            ("East", {"sandbox", "movement"}), ("Listen", set()),
            ("West", {"sandbox", "movement"}),
        ]
    ]
    content = ContentFragment(content="Scene text")
    choices = [ChoiceFragment(edge_id=action.uid, text=action.text) for action in actions]
    fragments = [choices[0], content, *choices[1:]]
    before_ids = list(graph.members)
    result = compose_sandbox_wait_order(caller=road, ctx=None, fragments=fragments)
    assert [f.text for f in result if isinstance(f, ChoiceFragment)] == [
        "Inspect", "East", "Listen", "West", "Wait",
    ]
    assert result[1] is content
    assert list(graph.members) == before_ids


def test_wait_retains_replaces_and_retires_via_shared_offers(monkeypatch):
    graph = Graph()
    scope = SandboxScope(label="scope", wait_text="Pass time", wait_turn_delta=2, registry=graph)
    road = SandboxLocation(label="road", registry=graph)
    scope.add_child(road)
    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    do_provision(road, ctx=ledger.get_frame()._make_ctx())
    first = _wait(road)
    assert first.offer_id is not None
    offer = graph.get(first.offer_id)
    template_uid = offer.action_template.uid
    assert first.text == "Pass time"
    assert first.payload["sandbox_time_cost"] == {"kind": "wait", "duration": 2}
    before = graph.unstructure()
    with monkeypatch.context() as patch:
        def no_materialization(*args, **kwargs):
            pytest.fail("unchanged Wait declaration was materialized again")
        patch.setattr(EntityTemplate, "materialize", no_materialization)
        for _ in range(3):
            do_provision(road, ctx=ledger.get_frame()._make_ctx())
    assert _wait(road).uid == first.uid
    assert graph.unstructure() == before

    road.wait_text = "Pause here"
    road.wait_turn_delta = 3
    with pytest.raises(ValueError):
        ledger.resolve_choice(first.uid)
    do_provision(road, ctx=ledger.get_frame()._make_ctx())
    replacement = _wait(road)
    assert replacement.uid != first.uid
    assert replacement.offer_id == offer.uid
    assert offer.action_template.uid == template_uid
    assert replacement.text == "Pause here"
    assert replacement.payload["sandbox_time_cost"]["duration"] == 3
    with pytest.raises(ValueError):
        ledger.resolve_choice(first.uid)
    road.wait_enabled = False
    with pytest.raises(ValueError):
        ledger.resolve_choice(replacement.uid)
    do_provision(road, ctx=ledger.get_frame()._make_ctx())
    assert not list(road.edges_out(Selector(has_kind=Action, has_tags={"wait"})))
    with pytest.raises(ValueError):
        ledger.resolve_choice(replacement.uid)


def test_wait_json_restore_charges_once_and_replays():
    graph = Graph()
    scope = SandboxScope(label="scope", wait_turn_delta=2, locals={"world_turn": 0}, registry=graph)
    road = SandboxLocation(label="road", registry=graph)
    scope.add_child(road)
    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    do_provision(road, ctx=ledger.get_frame()._make_ctx())
    wait_uid = _wait(road).uid
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    restored.resolve_choice(wait_uid)
    assert current_world_time(restored.graph.get(scope.uid)).turn == 2
    first_step = restored.cursor_steps
    first_hash = restored.graph.value_hash()
    assert _wait(restored.cursor).uid == wait_uid
    restored.resolve_choice(wait_uid)
    assert current_world_time(restored.graph.get(scope.uid)).turn == 4
    restored.rollback_to_step(first_step)
    assert restored.graph.value_hash() == first_hash
    assert current_world_time(restored.graph.get(scope.uid)).turn == 2
    restored.resolve_choice(wait_uid)
    assert current_world_time(restored.graph.get(scope.uid)).turn == 4


def test_frozen_setup_does_not_create_dynamic_wait():
    world = World.from_script_data(script_data={
        "label": "frozen_wait", "metadata": {"start_at": "hub.road"},
        "scenes": {"hub": {"kind": SandboxScope, "blocks": {
            "road": {"kind": SandboxLocation},
        }}},
    })
    graph = world.create_story("run", freeze_shape=True).graph
    road = graph.find_one(Selector(has_kind=SandboxLocation, label="road"))
    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    do_provision(road, ctx=ledger.get_frame()._make_ctx())
    assert not list(road.edges_out(Selector(has_kind=Action, has_tags={"wait"})))


def test_same_checkpoint_creates_same_wait_declaration_and_action():
    graph = Graph()
    road = SandboxLocation(label="road", registry=graph)
    ledger = Ledger.from_graph(graph, entry_id=road.uid)
    checkpoint = Json.serialize(ledger.unstructure())
    identities = []
    for _ in range(2):
        restored = Ledger.structure(Json.deserialize(checkpoint))
        do_provision(restored.cursor, ctx=restored.get_frame()._make_ctx())
        action = _wait(restored.cursor)
        offer = restored.graph.get(action.offer_id)
        identities.append((action.uid, action.templ_hash, offer.uid, offer.action_template.uid))
    assert identities[0] == identities[1]
