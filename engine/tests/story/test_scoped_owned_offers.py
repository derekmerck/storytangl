"""Scoped owned-scene offers through the ordinary planning and ledger paths."""
from tangl.core import Selector
from tangl.core.runtime_op import Predicate
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.journal.fragments import ChoiceFragment, ContentFragment
import pytest

from tangl.story import Action, Actor, InitMode, Scene, World
from tangl.story.concepts import Role
from tangl.story.system_handlers import is_action_selectable, render_choice_text
from tangl.vm import Affordance, Ledger, ResolutionPhase, Resolver
from tangl.vm.dispatch import do_journal, do_provision
from tangl.vm.traversable import HasAvailability, TraversableEffect


def _world():
    return World.from_script_data(script_data={
        "label": "scoped_owned", "metadata": {"start_at": "inn.start"},
        "actors": {"aria": {"name": "Aria", "episodes": {"chat": {
            "action_name": "Talk to Aria",
            "offer": {"source_requirement": {"has_tags": ["tavern"]}, "once": True},
            "blocks": {"message": {"content": "Hello."}},
        }}}},
        "scenes": {
            "inn": {"tags": ["tavern"], "roles": {"bard": "aria", "friend": "aria"},
                    "blocks": {"start": {"content": "Inn", "actions": [
                        {"text": "Next", "successor": "other"}]},
                               "other": {"content": "Other"}}},
            "outside": {"blocks": {"alone": {"content": "Outside"}}},
        },
    })


def _actions(node):
    return [edge for edge in node.edges_out(Selector(has_kind=Action)) if edge.offer_id]


def test_shared_offer_projection_and_json_restore():
    graph = _world().create_story("scoped", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    frame._run_planning_phase(ctx=frame._make_ctx(), entry_phase=ResolutionPhase.PLANNING)
    start = ledger.cursor
    other = graph.find_one(Selector(label="other"))
    alone = graph.find_one(Selector(label="alone"))
    scene = graph.find_one(Selector(has_kind=Scene, label="aria.chat"))
    offer = graph.find_one(Selector(has_kind=Affordance, successor=scene))
    assert len(_actions(start)) == len(_actions(other)) == 1
    assert not _actions(alone)
    first, second = _actions(start)[0], _actions(other)[0]
    assert first.successor is second.successor is scene
    assert render_choice_text(first, ctx=frame._make_ctx()) == "Talk to Aria"
    assert offer.source_ids == [start.uid, other.uid]
    assert any(edge.text == "Next" for edge in start.edges_out(Selector(has_kind=Action)))
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    restored_offer = restored.graph.get(offer.uid)
    assert restored_offer.source_ids == [start.uid, other.uid]
    do_provision(restored.graph.get(start.uid), ctx=restored.get_frame()._make_ctx())
    assert _actions(restored.graph.get(start.uid))[0].uid == first.uid
    restored.resolve_choice(first.uid)
    assert restored.cursor_id == start.uid
    assert scene.uid in restored.cursor_history
    restored_first = restored.graph.get(first.uid)
    restored_second = restored.graph.get(second.uid)
    ctx = restored.get_frame()._make_ctx()
    assert not restored_first.available(ctx=ctx)
    assert not restored_second.available(ctx=ctx)
    assert _actions(restored.graph.get(other.uid))[0].uid == second.uid


def test_replanning_and_binding_loss_revalidate_stale_actions():
    graph = _world().create_story("scope", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    frame._run_planning_phase(ctx=frame._make_ctx(), entry_phase=ResolutionPhase.PLANNING)
    start = ledger.cursor
    (action,) = _actions(start)
    offer = graph.get(action.offer_id)
    for _ in range(2):
        do_provision(start, ctx=ledger.get_frame()._make_ctx())
    assert _actions(start)[0].uid == action.uid
    before = list(offer.source_ids)
    roles = list(graph.find_all(Selector(has_kind=Role)))
    graph.remove(roles[0].uid)
    do_provision(start, ctx=ledger.get_frame()._make_ctx())
    assert _actions(start)[0].uid == action.uid
    graph.remove(roles[1].uid)
    with pytest.raises(ValueError):
        ledger.resolve_choice(action.uid)
    do_provision(start, ctx=ledger.get_frame()._make_ctx())
    assert not _actions(start)
    assert offer.source_ids == before
    assert graph.get(offer.uid) is offer


def test_structural_mismatch_removes_only_projection_and_can_reattach():
    graph = _world().create_story("mismatch", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    frame._run_planning_phase(ctx=frame._make_ctx(), entry_phase=ResolutionPhase.PLANNING)
    start = ledger.cursor
    other = graph.find_one(Selector(label="other"))
    (action,) = _actions(start)
    offer = graph.get(action.offer_id)
    start.parent.tags.remove("tavern")
    with pytest.raises(ValueError):
        ledger.resolve_choice(action.uid)
    do_provision(start, ctx=ledger.get_frame()._make_ctx())
    assert not _actions(start)
    assert any(edge.text == "Next" for edge in start.edges_out(Selector(has_kind=Action)))
    assert offer.source_ids == [start.uid, other.uid]
    start.parent.tags.add("tavern")
    do_provision(start, ctx=ledger.get_frame()._make_ctx())
    assert len(_actions(start)) == 1
    assert offer.source_ids == [other.uid, start.uid]


@pytest.mark.parametrize("gate", ["offer", "sponsor"])
def test_availability_uses_each_receivers_namespace(gate):
    graph = _world().create_story("gates", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    frame._run_planning_phase(ctx=frame._make_ctx(), entry_phase=ResolutionPhase.PLANNING)
    start = ledger.cursor
    other = graph.find_one(Selector(label="other"))
    first, second = _actions(start)[0], _actions(other)[0]
    offer = graph.get(first.offer_id)
    if gate == "sponsor":
        class AvailableActor(HasAvailability, Actor):
            pass

        sponsor = AvailableActor(label="available_bard", name="Aria", registry=graph)
        for role in graph.find_all(Selector(has_kind=Role)):
            role.set_provider(sponsor)
        offer.set_predecessor(sponsor)
        first.successor.owner_id = sponsor.uid
    else:
        sponsor = offer
    start.locals["allow_offer"] = True
    other.locals["allow_offer"] = False
    sponsor.availability = [Predicate(expr="allow_offer")]
    ctx = ledger.get_frame()._make_ctx()
    assert first.available(ctx=ctx)
    assert not second.available(ctx=ctx)
    assert offer.source_ids[-1] == other.uid
    start.locals["allow_offer"] = False
    with pytest.raises(ValueError):
        ledger.resolve_choice(first.uid)
    do_provision(start, ctx=ledger.get_frame()._make_ctx())
    assert _actions(start)[0].uid == first.uid


@pytest.mark.parametrize(
    ("receiver_ready", "scene_ready", "entry_ready", "gate", "expected"),
    [
        (False, False, True, "entry", True),
        (True, True, False, "entry", False),
        (False, True, False, "scene", True),
        (True, False, True, "scene", False),
    ],
)
def test_destination_gates_use_destination_context(
    receiver_ready, scene_ready, entry_ready, gate, expected,
):
    graph = _world().create_story("destination_scopes", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    frame._run_planning_phase(ctx=frame._make_ctx(), entry_phase=ResolutionPhase.PLANNING)
    receiver = ledger.cursor
    (action,) = _actions(receiver)
    scene = action.successor
    entry = graph.get(scene.source_id)
    receiver.locals["ready"] = receiver_ready
    receiver.locals["source_open"] = True
    scene.locals["ready"] = scene_ready
    entry.locals["ready"] = entry_ready
    graph.get(action.offer_id).availability = [Predicate(expr="source_open")]
    action.availability = [Predicate(expr="source_open")]
    target = scene if gate == "scene" else entry
    target.availability = [Predicate(expr="ready")]
    entry.effects = [TraversableEffect(expr="graph.locals['entered'] = True")]
    ctx = ledger.get_frame()._make_ctx()
    assert action.available(ctx=ctx) is expected
    assert Resolver.from_ctx(ctx).preview_frontier_node(scene, _ctx=ctx).viable is expected
    assert is_action_selectable(edge=action, ctx=ctx) is expected
    choice = next(f for f in do_journal(receiver, ctx=ctx)
                  if isinstance(f, ChoiceFragment) and f.edge_id == action.uid)
    assert choice.available is expected
    history = list(ledger.cursor_history)
    if expected:
        ledger.resolve_choice(action.uid)
        assert ledger.cursor_id == receiver.uid
        assert scene.uid in ledger.cursor_history
        assert graph.locals["entered"] is True
    else:
        with pytest.raises(ValueError):
            ledger.resolve_choice(action.uid)
        assert ledger.cursor_id == receiver.uid
        assert ledger.cursor_history == history
        assert "entered" not in graph.locals


def test_location_owner_uses_setting_scope():
    world = World.from_script_data(script_data={
        "label": "location_offer", "metadata": {"start_at": "inn.start"},
        "locations": {"hall": {"name": "Hall"}},
        "scenes": {
            "inn": {"tags": ["tavern"], "settings": {"place": "hall"},
                    "blocks": {"start": {"content": "Inn"}}},
            "hall.meeting": {"owner_ref": "hall", "action_name": "Explore",
                "offer": {"source_requirement": {"has_tags": ["tavern"]}},
                "blocks": {"message": {"content": "Hall."}}},
        },
    })
    graph = world.create_story("place", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    do_provision(ledger.cursor, ctx=ledger.get_frame()._make_ctx())
    (action,) = _actions(ledger.cursor)
    assert action.successor.label == "hall.meeting"
    assert not action.once


def test_call_from_second_receiver_returns_to_second_receiver():
    graph = _world().create_story("return_other", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    next_action = next(edge for edge in ledger.cursor.edges_out(Selector(has_kind=Action))
                       if edge.text == "Next")
    ledger.resolve_choice(next_action.uid)
    other = ledger.cursor
    assert other.label == "other"
    (action,) = _actions(other)
    ledger.resolve_choice(action.uid)
    assert ledger.cursor_id == other.uid
    assert action.successor_id in ledger.cursor_history


def test_successor_scope_is_isolated_and_planning_does_not_run_effects():
    graph = _world().create_story("ahead", init_mode=InitMode.EAGER).graph
    start = graph.get(graph.initial_cursor_id)
    alone = graph.find_one(Selector(label="alone"))
    outside = alone.parent
    outside.tags.add("tavern")
    for role in list(graph.find_all(Selector(has_kind=Role))):
        role.set_predecessor(outside)
    Action(registry=graph, predecessor_id=start.uid, successor_id=alone.uid, text="Outside")
    alone.effects = [TraversableEffect(expr="graph.locals['future'] = True")]
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    frame = ledger.get_frame()
    frame._run_planning_phase(ctx=frame._make_ctx(), entry_phase=ResolutionPhase.PLANNING)
    assert not _actions(start)
    assert len(_actions(alone)) == 1
    assert "future" not in graph.locals
    assert not list(frame.output_stream.find_all(Selector(has_kind=ContentFragment)))
