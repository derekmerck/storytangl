"""Authored template occurrences remain addressable after story restoration."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tangl.core import Selector
from tangl.journal.fragments import ChoiceFragment
from tangl.persistence import PersistenceManagerFactory
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.service import ServiceManager
from tangl.service.response import DirectEdgeRequest
from tangl.story import Action, Block, InitMode, World
from tangl.story.fabula.block_template import BlockTemplate
from tangl.story.fabula.compiler import StoryCompiler
from tangl.vm import Ledger


def test_restored_occurrence_resolves_against_recompiled_world(monkeypatch) -> None:
    script = {
        "label": "occurrence_world", "metadata": {"start_at": "intro.start"},
        "actors": {"shared": {}},
        "scenes": {
            "intro": {"blocks": {
                "start": {"actions": [
                    {"text": "Pass", "successor": "current"},
                    {"text": "Enter", "successor": "middle"}]},
                "middle": {"actions": [{"text": "Go", "successor": "shared.room"}]},
            }},
            "shared": {"blocks": {"room": {"actions": [
                {"text": "Stay", "successor": "current"}]}}},
        },
    }
    world = World.from_script_data(script_data=script)
    graph = world.create_story("occurrence_story", init_mode=InitMode.LAZY).graph
    ledger = Ledger.from_graph(graph)
    passing = next(edge for edge in ledger.cursor.edges_out(Selector(has_kind=Action))
                   if edge.text == "Pass")
    ledger.resolve_choice(passing.uid)
    assert graph.find_one(Selector(has_kind=Block, label="room")) is None
    saved = Json.serialize(ledger.unstructure())
    changed = deepcopy(script)
    changed["actors"] = {"someone": {}, **changed["actors"]}
    changed["scenes"]["shared"]["blocks"] = {
        "other": {"content": "Other"}, **changed["scenes"]["shared"]["blocks"],
    }
    recompiled = StoryCompiler().compile(changed).template_registry
    monkeypatch.setitem(world.__dict__, "templates", recompiled)

    restored = Ledger.structure(Json.deserialize(saved))
    assert restored.graph.value_hash() == graph.value_hash()
    enter = next(edge for edge in restored.cursor.edges_out(Selector(has_kind=Action))
                 if edge.text == "Enter")
    restored.resolve_choice(enter.uid)
    onward = next(edge for edge in restored.cursor.edges_out(Selector(has_kind=Action))
                  if edge.text == "Go")
    restored.resolve_choice(onward.uid)
    action = next(restored.cursor.edges_out(Selector(has_kind=Action)))
    assert action.text == "Stay"
    assert action.declaration_ref == ("actions", 0)
    action_uid = action.uid
    restored = Ledger.structure(Json.deserialize(Json.serialize(restored.unstructure())))
    action = restored.graph.get(action_uid)
    assert action.declaration_ref == ("actions", 0)
    graph = restored.graph
    before = graph.value_hash()
    groups = graph.get_template_scope_groups(restored.cursor)
    source = groups[0][0]
    assert isinstance(source, BlockTemplate)
    field, occurrence = action.declaration_ref
    assert source.action_templates[field][occurrence].payload.text == "Stay"
    assert graph.value_hash() == before
    settled_step = restored.step
    restored.resolve_choice(action.uid)
    restored.rollback_to_step(settled_step, reason="provenance")
    assert restored.graph.value_hash() == before


def test_unchanged_service_choices_do_not_hash_block_catalog(tmp_path: Path, monkeypatch) -> None:
    script = {
        "label": "provenance_service", "metadata": {"start_at": "scene.block_0"},
        "scenes": {"scene": {"blocks": {
            f"block_{i}": {"content": "Room", "actions": [{"text": "Next",
                "successor": f"block_{(i + 1) % 20}"}]}
            for i in range(20)
        }}},
    }
    world = World.from_script_data(script_data=script)
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path))
    user = service.create_user(secret="provenance").details["user_id"]
    envelope = service.create_story(user_id=user, world_id=world.label, world=world)
    original_hash = BlockTemplate.get_hashable_content
    original_choice = ServiceManager.resolve_choice
    calls = 0
    counts = []

    def counted_hash(self):
        nonlocal calls
        calls += 1
        return original_hash(self)

    def counted_choice(self, *args, **kwargs):
        nonlocal calls
        calls = 0
        result = original_choice(self, *args, **kwargs)
        counts.append(calls)
        return result

    monkeypatch.setattr(BlockTemplate, "get_hashable_content", counted_hash)
    monkeypatch.setattr(ServiceManager, "resolve_choice", counted_choice)
    for _ in range(2):
        choice = next(fragment for fragment in envelope.fragments
                      if isinstance(fragment, ChoiceFragment) and fragment.available)
        envelope = service.resolve_choice(user_id=user, request=DirectEdgeRequest(edge_id=choice.edge_id))
    assert counts == [0, 0]
