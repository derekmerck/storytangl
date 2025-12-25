"""Tests for template declarations on scene and block scripts."""

from tangl.ir.core_ir import BaseScriptItem
from tangl.ir.story_ir.scene_script_models import BlockScript, SceneScript

def test_base_script_valid():
    data = { 'label': 'foo', 'text': 'bar' }
    assert BaseScriptItem.model_validate(data)

def test_block_script_valid():
    data = { 'label': 'foo', 'text': 'bar' }
    assert BlockScript.model_validate(data)


def test_scene_script_templates_default_to_none() -> None:
    scene = SceneScript.model_validate(
        {
            "label": "village",
            "blocks": {
                "village.intro": {
                    "label": "village.intro",
                }
            },
        }
    )

    assert scene.templates == {}
    assert "templates" not in scene.model_dump()


def test_scene_script_accepts_template_mapping() -> None:
    scene = SceneScript.model_validate(
        {
            "label": "village",
            "blocks": {
                "village.intro": {
                    "label": "village.intro",
                }
            },
            "templates": {
                "villager.greeting": {"text": "Hello there"},
            },
        }
    )

    assert scene.templates is not None
    assert scene.templates["villager.greeting"].text == "Hello there"
    dumped = scene.model_dump()

    assert dumped["templates"]["villager.greeting"]["label"] == "villager.greeting"
    assert dumped["templates"]["villager.greeting"]["text"] == "Hello there"


def test_block_script_template_map_round_trips() -> None:
    block = BlockScript.model_validate(
        {
            "label": "village.intro",
            "templates": {
                "local_only": {"obj_cls": "example.Template"},
            },
        }
    )

    assert block.templates is not None
    assert block.templates["local_only"].obj_cls_ == "example.Template"
    dumped = block.model_dump()

    assert dumped["templates"]["local_only"]["label"] == "local_only"
    assert dumped["templates"]["local_only"]["obj_cls"] == "example.Template"
