"""Tests for shorthand expansion on scene and block role/setting declarations."""

import pytest

from tangl.ir.story_ir.scene_script_models import BlockScript, SceneScript


@pytest.fixture()
def base_scene_data() -> dict:
    return {
        "label": "village",
        "blocks": {
            "intro": {
                "content": "you arrive",
            }
        },
    }


def test_scene_role_list_shorthand_expands_to_actor_refs(base_scene_data: dict) -> None:
    scene = SceneScript.model_validate(
        {
            **base_scene_data,
            "roles": ["bob", "alice"],
        }
    )

    assert set(scene.roles.keys()) == {"bob", "alice"}
    assert scene.roles["bob"].actor_ref == "bob"
    assert scene.roles["alice"].actor_ref == "alice"


def test_scene_role_dict_shorthands_expand(base_scene_data: dict) -> None:
    scene = SceneScript.model_validate(
        {
            **base_scene_data,
            "roles": {
                "guard": None,
                "merchant": "shopkeep",
            },
        }
    )

    assert scene.roles["guard"].actor_ref == "guard"
    assert scene.roles["merchant"].actor_ref == "shopkeep"


def test_scene_role_dict_without_references_logs_warning(base_scene_data: dict, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING"):
        scene = SceneScript.model_validate(
            {
                **base_scene_data,
                "roles": {
                    "scribe": {
                        "actor_conditions": ["ready"],
                    }
                },
            }
        )

    assert scene.roles["scribe"].actor_ref == "scribe"
    assert any("Role 'scribe'" in message for message in caplog.messages)


def test_scene_setting_shorthands_expand(base_scene_data: dict) -> None:
    scene = SceneScript.model_validate(
        {
            **base_scene_data,
            "settings": {
                "square": None,
                "tavern": "inn",  # string reference
            },
        }
    )

    assert scene.settings["square"].location_ref == "square"
    assert scene.settings["tavern"].location_ref == "inn"


def test_scene_setting_dict_without_refs_logs_warning(base_scene_data: dict, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING"):
        scene = SceneScript.model_validate(
            {
                **base_scene_data,
                "settings": {
                    "library": {
                        "location_conditions": ["open"],
                    }
                },
            }
        )

    assert scene.settings["library"].location_ref == "library"
    assert any("Setting 'library'" in message for message in caplog.messages)


def test_block_role_and_setting_shorthands_expand() -> None:
    block = BlockScript.model_validate(
        {
            "label": "village.intro",
            "roles": ["guard", {"label": "merchant", "actor_ref": "shopkeep"}],
            "settings": {
                "square": None,
                "market": "bazaar",
            },
        }
    )

    assert block.roles["guard"].actor_ref == "guard"
    assert block.roles["merchant"].actor_ref == "shopkeep"
    assert block.settings["square"].location_ref == "square"
    assert block.settings["market"].location_ref == "bazaar"


def test_empty_role_list_becomes_empty_mapping(base_scene_data: dict) -> None:
    scene = SceneScript.model_validate({**base_scene_data, "roles": []})

    assert scene.roles == {}


def test_empty_setting_list_becomes_empty_mapping(base_scene_data: dict) -> None:
    scene = SceneScript.model_validate({**base_scene_data, "settings": []})

    assert scene.settings == {}
