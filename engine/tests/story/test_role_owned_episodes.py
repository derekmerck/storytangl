"""A scene-local Role owns its episode independently of its current provider."""
from __future__ import annotations

import pytest

from tangl.core import Selector
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import Action, Actor, InitMode, Scene, World
from tangl.story.concepts import Role
from tangl.story.fabula import StoryCompiler
from tangl.vm import Affordance, Ledger, ResolutionPhase
from tangl.vm.dispatch import do_provision


def _script():
    return {
        "label": "role_owned", "metadata": {"start_at": "inn.hearth"},
        "actors": {"aria": {"name": "Aria"}, "bram": {"name": "Bram"}},
        "scenes": {
            "inn": {"tags": ["tavern"], "roles": {
                "bard": {"hard": False, "grants": {"title": "Host", "tags": ["host"]}},
            }, "blocks": {
                "hearth": {"content": "At the hearth.", "actions": [
                    {"text": "Go to table", "successor": "table"},
                    {"text": "Leave inn", "successor": "other.outside"},
                ]},
                "table": {"content": "At the table."},
            }},
            "other": {"tags": ["tavern"], "roles": {"visitor": {"actor_ref": "aria"}},
                      "blocks": {"outside": {"content": "Outside."}}},
            "conversation": {"owner_ref": "inn.roles.bard", "action_name": "Hear the news",
                "offer": {"source_requirement": {"has_tags": ["tavern"]}, "once": True},
                "blocks": {"message": {"content": "The road is open."}}},
        },
    }


def _offers(block):
    return [edge for edge in block.edges_out(Selector(has_kind=Action)) if edge.offer_id]


def test_role_owner_survives_provider_swap_and_json_restore():
    world = World.from_script_data(script_data=_script())
    graph = world.create_story("role_owned_run", init_mode=InitMode.EAGER).graph
    inn = graph.find_one(Selector(has_kind=Scene, label="inn"))
    role = next(inn.edges_out(Selector(has_kind=Role, label="bard")))
    aria = graph.find_one(Selector(has_kind=Actor, label="aria"))
    bram = graph.find_one(Selector(has_kind=Actor, label="bram"))
    assert role.requirement.satisfied_by(aria) and role.requirement.satisfied_by(bram)
    role.set_provider(aria)
    scene = graph.find_one(Selector(has_kind=Scene, label="conversation"))
    assert scene.owner is role and role.provider is aria
    assert scene.parent is None
    offer = graph.find_one(Selector(has_kind=Affordance, predecessor_id=role.uid))
    assert offer.successor is scene
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    frame._run_planning_phase(ctx=frame._make_ctx(), entry_phase=ResolutionPhase.PLANNING)
    hearth = ledger.cursor
    table = graph.find_one(Selector(label="table"))
    outside = graph.find_one(Selector(label="outside"))
    visitor = next(outside.parent.edges_out(Selector(has_kind=Role, label="visitor")))
    assert visitor.provider is aria and visitor.uid != role.uid
    do_provision(outside, ctx=frame._make_ctx().derive(cursor_id=outside.uid))
    assert not _offers(outside)
    (first,), (second,) = _offers(hearth), _offers(table)
    original = first.uid, second.uid, offer.uid, scene.uid, role.uid
    ns = frame._make_ctx().get_ns(hearth)
    assert ns["bard"] is aria and ns["bard_role"] is role
    assert ns["bard_title"] == "Host" and ns["bard_tags"] == {"host"}
    aria_before = aria.unstructure()
    bram_before = bram.unstructure()
    role.set_provider(bram)
    do_provision(hearth, ctx=frame._make_ctx())
    do_provision(table, ctx=frame._make_ctx().derive(cursor_id=table.uid))
    ns = frame._make_ctx().get_ns(hearth)
    assert ns["bard"] is bram and ns["bard_role"] is role
    assert ns["bard_title"] == "Host" and ns["bard_tags"] == {"host"}
    assert aria.unstructure() == aria_before
    assert bram.unstructure() == bram_before
    assert (_offers(hearth)[0].uid, _offers(table)[0].uid, offer.uid, scene.uid, role.uid) == original
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    restored_role = restored.graph.get(role.uid)
    restored_scene = restored.graph.get(scene.uid)
    assert restored_scene.owner is restored_role
    assert restored_role.provider is restored.graph.get(bram.uid)
    assert restored.graph.get(offer.uid).predecessor is restored_role
    assert restored.graph.get(offer.uid).source_ids == [hearth.uid, table.uid]
    assert restored.graph.get(first.uid).successor is restored_scene
    restored_ns = restored.get_frame()._make_ctx().get_ns(restored.cursor)
    assert restored_ns["bard"] is restored.graph.get(bram.uid)
    assert restored_ns["bard_role"] is restored_role and restored_ns["bard_title"] == "Host"
    do_provision(restored.cursor, ctx=restored.get_frame()._make_ctx())
    assert _offers(restored.cursor)[0].uid == first.uid
    restored.resolve_choice(first.uid)
    assert restored.cursor_id == hearth.uid
    assert scene.uid in restored.cursor_history
    assert not restored.graph.get(second.uid).available(ctx=restored.get_frame()._make_ctx())


@pytest.mark.parametrize("role_names", [[], ["bard", "bard"]])
def test_invalid_role_owner_has_authored_diagnostic(role_names):
    script = _script()
    script["scenes"]["inn"]["roles"] = [{"label": name} for name in role_names]
    bundle = StoryCompiler().compile(script)
    issue = next(issue for issue in bundle.issues if issue.code == "compile:invalid_episode_owner")
    assert issue.subject_label == "conversation"
    assert issue.source_ref.authored_path.endswith("conversation.owner_ref")


def test_role_address_conflicting_with_template_owner_is_ambiguous():
    script = _script()
    script["actors"]["inn.roles.bard"] = {"name": "Another owner"}
    bundle = StoryCompiler().compile(script)
    issue = next(issue for issue in bundle.issues if issue.code == "compile:invalid_episode_owner")
    assert "resolves to 2" in issue.message
    assert issue.source_ref.authored_path.endswith("conversation.owner_ref")


def test_removed_owning_role_cannot_authorize_recorded_site():
    graph = World.from_script_data(script_data=_script()).create_story(
        "removed_role", init_mode=InitMode.EAGER,
    ).graph
    role = next(graph.find_all(Selector(has_kind=Role, label="bard")))
    role.set_provider(graph.find_one(Selector(has_kind=Actor, label="aria")))
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    frame._run_planning_phase(ctx=frame._make_ctx(), entry_phase=ResolutionPhase.PLANNING)
    (action,) = _offers(ledger.cursor)
    offer = graph.get(action.offer_id)
    graph.remove(role.uid)
    with pytest.raises(ValueError):
        ledger.resolve_choice(action.uid)
    do_provision(ledger.cursor, ctx=ledger.get_frame()._make_ctx())
    assert not _offers(ledger.cursor)
    assert ledger.cursor_id in offer.source_ids
