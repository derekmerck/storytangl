from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from tangl.journal.media import MediaFragment
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.service.controllers.runtime_controller import RuntimeController


def test_system_media_dereference_to_sys_url(tmp_path: Path) -> None:
    path = tmp_path / "logo.png"
    path.write_bytes(b"fake image bytes")
    rit = MediaRIT(path=path, data_type=MediaDataType.IMAGE, label="logo.png")

    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        content_type=MediaDataType.IMAGE,
        media_role="ui_logo",
        text="System logo",
        source_id=uuid4(),
        scope="sys",
    )

    controller = RuntimeController()
    result = controller._dereference_media(fragment, world_id="ignored")

    assert result["url"].startswith("/media/sys/")
    assert result["url"].endswith("logo.png")
    assert result["fragment_type"] == "media"
    assert result["media_role"] == "ui_logo"
