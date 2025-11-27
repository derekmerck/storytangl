import pytest
from tangl.ir.media_ir.media_script_model import MediaItemScript
from tangl.ir.story_ir.scene_script_models import BlockScript
from tangl.media.media_role import MediaRole


def test_block_script_parses_media_list() -> None:
    script = BlockScript.model_validate(
        {
            "label": "intro",
            "media": [
                {
                    "name": "dragon.svg",
                    "media_role": MediaRole.NARRATIVE_IM,
                }
            ],
        }
    )

    assert script.media is not None
    assert script.media[0].name == "dragon.svg"
    assert script.media[0].media_role == MediaRole.NARRATIVE_IM


def test_media_item_script_validates_single_source() -> None:
    item = MediaItemScript(name="foo.png", media_role=MediaRole.NARRATIVE_IM)

    assert item.model_dump(exclude_none=True)["name"] == "foo.png"

    with pytest.raises(ValueError):
        MediaItemScript(name="foo.png", url="https://example.invalid/foo.png")
