from pathlib import Path
from uuid import uuid4

from tangl.journal.media import MediaFragment
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from tangl.service.controllers.runtime_controller import RuntimeController


def test_dereference_media_fragment_to_url():
    asset_path = (
        Path(__file__).resolve().parents[4]
        / "engine"
        / "tests"
        / "resources"
        / "worlds"
        / "media_mvp"
        / "media"
        / "test_image.svg"
    )

    rit = MediaRIT(
        path=asset_path,
        data_type=MediaDataType.IMAGE,
        label="test_image.svg",
    )

    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        content_type=MediaDataType.IMAGE,
        media_role="narrative_im",
        text="A fierce dragon",
        source_id=uuid4(),
    )

    controller = RuntimeController()
    result = controller._dereference_media(fragment, world_id="test_world")

    assert result["fragment_type"] == "media"
    assert result["url"] == "/media/world/test_world/test_image.svg"
    assert result["media_role"] == "narrative_im"
    assert result["media_type"] == MediaDataType.IMAGE.value
    assert result["text"] == "A fierce dragon"
    assert result["source_id"] == str(fragment.source_id)
