"""Action declarations on generic Block templates use the normal compiler path."""
from __future__ import annotations

import pytest

from tangl.core import EntityTemplate, Selector
from tangl.journal.fragments import ContentFragment
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import Action, Block, InitMode, Scene, World
from tangl.vm import Ledger
from tangl.vm.dispatch import do_provision


def _script(*, nested: bool) -> dict:
    extra = {
        "kind": Block, "content": "A dark room.", "locals": {"lit": False},
        "offered_actions": [{"text": "Light", "successor": "current",
                             "effects": ["lit = True"], "journal_text": "The lamp glows."}],
        "actions": [{"text": "Wait", "successor": "current"},
                    {"text": "Leave", "successor": "intro.start"}],
    }
    return {
        "label": f"generic_action_{nested}", "metadata": {"start_at": "intro.start"},
        "templates": ({"pack": {"kind": Scene, "templates": {"extra": extra}}}
                      if nested else {"extra": extra}),
        "scenes": {"intro": {"blocks": {"start": {"content": "Start."}}}},
    }


@pytest.mark.parametrize("nested", [False, True])
def test_generic_block_actions_materialize_and_play(nested: bool) -> None:
    world = World.from_script_data(script_data=_script(nested=nested))
    graph = world.create_story("generic_actions", init_mode=InitMode.EAGER).graph
    block = graph.find_one(Selector(has_kind=Block, label="extra"))
    ledger = Ledger.from_graph(graph, entry_id=block.uid)
    do_provision(block, ctx=ledger.get_frame()._make_ctx())
    actions = {edge.text: edge for edge in block.edges_out(Selector(has_kind=Action))}
    assert set(actions) == {"Light", "Wait", "Leave"}
    assert actions["Light"].successor is block and actions["Wait"].successor is block
    template = world.find_template("pack.extra" if nested else "extra")
    assert graph.get(actions["Light"].offer_id).action_template.uid == (
        template.action_templates["offered_actions"][0].uid
    )
    ledger.resolve_choice(actions["Light"].uid)
    assert block.locals["lit"] is True
    assert any(isinstance(f, ContentFragment) and f.content == "The lamp glows."
               for f in ledger.get_journal())
    ledger.resolve_choice(actions["Leave"].uid)
    assert ledger.cursor.label == "start"


def test_lazy_generic_block_offer_is_stable_after_checkpoint_restore() -> None:
    script = _script(nested=False)
    script["scenes"]["intro"]["templates"] = {"extra": script.pop("templates")["extra"]}
    script["scenes"]["intro"]["blocks"]["start"]["actions"] = [
        {"text": "Enter", "successor": "intro.extra"},
    ]
    world = World.from_script_data(script_data=script)
    graph = world.create_story("lazy_generic_actions", init_mode=InitMode.LAZY).graph
    start = graph.find_one(Selector(has_kind=Block, label="start"))
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    data = Json.serialize(ledger.unstructure())
    outcomes = []
    for _ in range(2):
        restored = Ledger.structure(Json.deserialize(data))
        enter = next(edge for edge in restored.cursor.edges_out(Selector(has_kind=Action))
                     if edge.text == "Enter")
        restored.resolve_choice(enter.uid)
        action = next(edge for edge in restored.cursor.edges_out(Selector(has_kind=Action))
                      if edge.text == "Light")
        offer = restored.graph.get(action.offer_id)
        outcomes.append((action.uid, action.templ_hash, offer.uid, list(offer.source_ids),
                         action.unstructure(), offer.unstructure()))
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("mode", [InitMode.EAGER, InitMode.LAZY])
def test_block_declarations_belong_to_their_world_template(mode: InitMode) -> None:
    shared_payload_uid = "00000000-0000-4000-8000-000000000123"
    script = {
        "label": f"block_declaration_{mode}", "metadata": {"start_at": "intro.start"},
        "scenes": {
            "intro": {"blocks": {"start": {"actions": [
                {"text": "First", "successor": "one.room"},
                {"text": "Second", "successor": "two.room"},
            ]}}},
            "one": {"blocks": {"room": {"uid": shared_payload_uid, "content": "Room", "actions": [
                {"text": "Ordinary one", "successor": "current"}],
                "offered_actions": [{"text": "Offer one", "successor": "current"}]}}},
            "two": {"blocks": {"room": {"uid": shared_payload_uid, "content": "Room", "actions": [
                {"text": "Ordinary two", "successor": "current"}],
                "offered_actions": [{"text": "Offer two", "successor": "current"}]}}},
        },
    }
    world = World.from_script_data(script_data=script)
    assert world.find_template("one.room").payload.unstructure() == (
        world.find_template("two.room").payload.unstructure()
    )
    declaration = world.find_template("one.room")
    restored_declaration = type(declaration).structure(declaration.unstructure())
    assert restored_declaration.action_templates["actions"][0].uid == (
        declaration.action_templates["actions"][0].uid
    )
    ledger = Ledger.from_graph(world.create_story("block_owners", init_mode=mode).graph)
    checkpoint = Json.serialize(ledger.unstructure())
    for choice, expected in (("First", "one"), ("Second", "two")):
        restored = Ledger.structure(Json.deserialize(checkpoint))
        entry = next(edge for edge in restored.cursor.edges_out(Selector(has_kind=Action))
                     if edge.text == choice)
        restored.resolve_choice(entry.uid)
        block = restored.cursor
        assert {edge.text for edge in block.edges_out(Selector(has_kind=Action))} == {
            f"Ordinary {expected}", f"Offer {expected}"
        }
        assert not {"actions", "continues", "redirects", "offered_actions", "action_templates"} & set(
            block.unstructure()
        )


def test_reentry_uses_existing_action_without_materialization(monkeypatch: pytest.MonkeyPatch) -> None:
    script = {"label": "block_reentry", "metadata": {"start_at": "s.start"},
              "scenes": {"s": {"blocks": {"start": {"actions": [
                  {"text": "Stay", "successor": "current"}]}}}}}
    graph = World.from_script_data(script_data=script).create_story("reentry").graph
    ledger = Ledger.from_graph(graph)
    action = next(ledger.cursor.edges_out(Selector(has_kind=Action)))

    def no_materialization(*_args, **_kwargs):
        pytest.fail("reentry constructed an Action candidate")

    monkeypatch.setattr(EntityTemplate, "materialize", no_materialization)
    ledger.resolve_choice(action.uid)
    ledger.resolve_choice(action.uid)
    assert next(ledger.cursor.edges_out(Selector(has_kind=Action))).uid == action.uid
