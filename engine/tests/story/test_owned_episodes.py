"""Story-side lowering and persistence of referentially owned episodes."""
from __future__ import annotations

from copy import deepcopy

import pytest

from tangl.core import Selector
from tangl.ir.story_ir import StoryScript
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import Actor, InitMode, Location, Scene, World
from tangl.story.fabula import StoryCompiler
from tangl.vm import Ledger


def _script() -> dict:
    return {
        "label": "owned_episode_world",
        "metadata": {"title": "Owned episodes", "author": "Tests", "start_at": "inn.start"},
        "actors": {
            "aria": {"name": "Aria", "episodes": {
                "chat": {"blocks": {"message": {"content": "Hello."}}},
                "later": {"blocks": {"message": {"content": "Later."}}},
            }},
            "bram": {"name": "Bram", "episodes": {
                "chat": {"blocks": {"message": {"content": "Good day."}}},
            }},
        },
        "locations": {"hall": {"name": "Hall"}},
        "scenes": {
            "inn": {"blocks": {
                "start": {"content": "Inn", "actions": [
                    {"text": "Talk", "successor": "aria.chat"},
                ]},
                "other": {"content": "Other", "actions": [
                    {"text": "Talk too", "successor": "aria.chat"},
                ]},
            }},
            "hall.meeting": {"owner_ref": "hall", "blocks": {"message": {"content": "Hall."}}},
        },
    }


def test_nested_owned_scenes_use_graph_references_and_restore() -> None:
    script = _script()
    before = deepcopy(script)
    ir = StoryScript.model_validate(script)
    assert ir.actors["aria"].episodes["chat"].blocks["message"].content == "Hello."
    bundle = StoryCompiler().compile(script)
    assert script == before
    assert not [issue for issue in bundle.issues if issue.severity.value == "error"]
    world = World.from_script_data(script_data=script)
    graph = world.create_story("owned_run", init_mode=InitMode.EAGER).graph
    aria = graph.find_one(Selector(has_kind=Actor, label="aria"))
    hall = graph.find_one(Selector(has_kind=Location, label="hall"))
    scenes = {name: graph.find_one(Selector(has_kind=Scene, label=name)) for name in (
        "aria.chat", "aria.later", "bram.chat", "hall.meeting",
    )}
    assert scenes["aria.chat"].owner is aria
    declaration = world.templates.find_one(Selector(label="aria.chat"))
    assert scenes["aria.chat"].templ_hash == declaration.content_hash()
    assert scenes["aria.later"].owner is aria
    assert scenes["bram.chat"].owner.label == "bram"
    assert scenes["hall.meeting"].owner is hall
    assert scenes["aria.chat"].parent is None
    assert len(list(graph.find_all(Selector(has_kind=Actor, label="aria")))) == 1
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    assert ledger.cursor.label == "start"
    (action,) = ledger.cursor.edges_out()
    assert action.successor_id == scenes["aria.chat"].uid
    other = graph.find_one(Selector(label="other"))
    assert next(other.edges_out()).successor_id == action.successor_id
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    restored_scene = restored.graph.get(scenes["aria.chat"].uid)
    assert restored_scene.owner_id == aria.uid
    assert restored_scene.owner is restored.graph.get(aria.uid)
    assert restored_scene.templ_hash == scenes["aria.chat"].templ_hash
    assert restored_scene.templ_hash == declaration.content_hash()
    assert len(list(restored.graph.find_all(Selector(has_kind=Scene, label="aria.chat")))) == 1
    restored.resolve_choice(action.uid)
    assert restored.cursor.content == "Hello."


def test_owned_scene_is_not_implicit_default_entry() -> None:
    script = _script()
    script["metadata"] = {}
    script["scenes"]["inn"]["blocks"] = {"entrance": {"content": "Inn"}}
    script["actors"]["aria"]["episodes"]["chat"]["blocks"] = {"start": {"content": "Chat"}}
    graph = World.from_script_data(script_data=script).create_story("default_entry").graph
    assert graph.get(graph.initial_cursor_id).label == "entrance"
    assert list(graph.get(graph.initial_cursor_id).edges_out()) == []


def test_explicit_and_nested_declarations_lower_equivalently() -> None:
    nested = _script()
    explicit = deepcopy(nested)
    chat = explicit["actors"]["aria"]["episodes"].pop("chat")
    explicit["scenes"]["aria.chat"] = {**chat, "owner_ref": "aria"}
    for script in (nested, explicit):
        bundle = StoryCompiler().compile(script)
        scene = bundle.template_registry.find_one(Selector(label="aria.chat"))
        assert scene.payload.owner_ref == "aria"
        block = bundle.template_registry.find_one(Selector(label="aria.chat.message"))
        assert block.payload.content == "Hello."
        assert block.parent is scene


def test_owner_reference_uses_template_identity_when_runtime_label_differs() -> None:
    script = _script()
    script["actors"]["aria"]["label"] = "aria_instance"
    graph = World.from_script_data(script_data=script).create_story("renamed_owner").graph
    scene = graph.find_one(Selector(has_kind=Scene, label="aria.chat"))
    assert scene.owner_ref == "aria"
    assert scene.owner.label == "aria_instance"


def test_frozen_eager_construction_keeps_owner_reference() -> None:
    graph = World.from_script_data(script_data=_script()).create_story(
        "frozen_owned", init_mode=InitMode.EAGER, freeze_shape=True,
    ).graph
    scene = graph.find_one(Selector(has_kind=Scene, label="aria.chat"))
    assert graph.frozen_shape
    assert scene.owner is graph.find_one(Selector(has_kind=Actor, label="aria"))


def test_nested_episode_diagnostics_keep_original_source_path() -> None:
    script = _script()
    block = script["actors"]["aria"]["episodes"]["chat"]["blocks"]["message"]
    block["actions"] = [{"text": "Missing", "successor": "absent"}]
    bundle = StoryCompiler().compile(script)
    issue = next(issue for issue in bundle.issues if issue.code == "compile:dangling_successor_ref")
    assert issue.source_ref.authored_path == "actors[0].aria.episodes[0].chat.blocks[0].message.actions[0]"


def test_ambiguous_owner_is_diagnosed_and_rejected() -> None:
    script = _script()
    script["locations"]["aria"] = {"name": "Another Aria"}
    bundle = StoryCompiler().compile(script)
    assert any(issue.code == "compile:invalid_episode_owner"
               and issue.subject_label == "aria.chat" for issue in bundle.issues)
    with pytest.raises(ValueError, match="owner 'aria'.*2 graph items"):
        World.from_script_data(script_data=script).create_story("ambiguous")


def test_missing_owner_reference_has_source_diagnostic() -> None:
    script = _script()
    script["scenes"]["hall.meeting"]["owner_ref"] = "missing"
    bundle = StoryCompiler().compile(script)
    assert any(issue.code == "compile:invalid_episode_owner"
               and "owner_ref" in issue.source_ref.authored_path for issue in bundle.issues)
    with pytest.raises(ValueError, match="owner 'missing'.*0 graph items"):
        World.from_script_data(script_data=script).create_story("missing_owner")


def test_wrong_shaped_owner_reference_fails_with_authored_path() -> None:
    script = _script()
    script["scenes"]["hall.meeting"]["owner_ref"] = 123
    with pytest.raises(ValueError, match=r"scenes\[1\]\.hall.meeting\.owner_ref"):
        StoryCompiler().compile(script)
