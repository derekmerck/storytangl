"""Tests for template declarations on scene and block scripts."""

from tangl.ir.story_ir.scene_script_models import BlockScript, SceneScript


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

    assert scene.templates is None
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

    assert scene.templates == {"villager.greeting": {"text": "Hello there"}}
    dumped = scene.model_dump()

    assert dumped["templates"] == {"villager.greeting": {"text": "Hello there"}}


def test_block_script_template_map_round_trips() -> None:
    block = BlockScript.model_validate(
        {
            "label": "village.intro",
            "templates": {
                "local_only": {"obj_cls": "example.Template"},
            },
        }
    )

    assert block.templates == {"local_only": {"obj_cls": "example.Template"}}
    dumped = block.model_dump()

    assert dumped["templates"] == {"local_only": {"obj_cls": "example.Template"}}
