from __future__ import annotations

from tangl.compiler.script_manager import ScriptManager


def _script_with_actors(data):
    base = {
        "label": "test_script",
        "metadata": {"title": "Test", "author": "Tester"},
    }
    base.update(data)
    return base


def test_get_unstructured_handles_dict_sections() -> None:
    script = _script_with_actors(
        {
            "actors": {
                "alice": {"name": "Alice"},
                "bob": {"name": "Bob"},
            },
            "scenes": {"intro": {"blocks": {"start": {}}}},
        }
    )

    manager = ScriptManager.from_data(script)

    labels = {entry["label"] for entry in manager.get_unstructured("actors")}
    assert labels == {"alice", "bob"}


def test_get_unstructured_handles_list_sections() -> None:
    script = _script_with_actors(
        {
            "actors": [
                {"label": "alice", "name": "Alice"},
                {"label": "bob", "name": "Bob"},
            ],
            "scenes": {"intro": {"blocks": {"start": {}}}},
        }
    )

    manager = ScriptManager.from_data(script)

    payloads = list(manager.get_unstructured("actors"))
    assert len(payloads) == 2
    assert {entry["label"] for entry in payloads} == {"alice", "bob"}


def test_get_story_globals_defaults_to_empty_dict() -> None:
    script = _script_with_actors({"scenes": {"intro": {"blocks": {"start": {}}}}})

    manager = ScriptManager.from_data(script)

    assert manager.get_story_globals() == {}

    script["globals"] = {"difficulty": "normal"}
    manager = ScriptManager.from_data(script)
    assert manager.get_story_globals() == {"difficulty": "normal"}


def test_get_unstructured_injects_default_obj_classes() -> None:
    script = _script_with_actors(
        {
            "actors": {"alice": {"name": "Alice"}},
            "scenes": {
                "intro": {
                    "blocks": {
                        "start": {
                            "content": "Hello",
                            "actions": [
                                {
                                    "text": "Next",
                                    "successor": "intro.end",
                                }
                            ],
                        },
                        "end": {
                            "content": "The end",
                        },
                    }
                }
            },
        }
    )

    manager = ScriptManager.from_data(script)

    actor_payload = next(manager.get_unstructured("actors"))
    assert actor_payload["obj_cls"] == "tangl.story.fabula.actor.actor.Actor"

    scene_payload = next(manager.get_unstructured("scenes"))
    assert scene_payload["obj_cls"] == "tangl.story.episode.scene.SimpleScene"

    blocks = scene_payload["blocks"]
    assert "start" in blocks
    start_block = blocks["start"]
    assert start_block["obj_cls"] == "tangl.story.episode.block.SimpleBlock"
    assert start_block["block_cls"] == "tangl.story.episode.block.SimpleBlock"

    actions = start_block["actions"]
    assert actions
    assert actions[0]["obj_cls"] == "tangl.vm.frame.ChoiceEdge"
