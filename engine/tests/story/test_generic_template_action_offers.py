"""Action declarations on generic Block templates use the normal compiler path."""
from __future__ import annotations

import pytest

from tangl.core import Selector
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
        template.payload.action_templates["offered_actions"][0].uid
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
