from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from tangl.journal.media import MediaFragment
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.service.media import media_fragment_to_payload


def test_system_media_dereference_to_sys_url(tmp_path: Path) -> None:
    path = tmp_path / "logo.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<circle cx="16" cy="16" r="14" fill="red"/></svg>',
        encoding="utf-8",
    )
    rit = MediaRIT(path=path, data_type=MediaDataType.IMAGE, label="logo.svg")

    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        content_type=MediaDataType.IMAGE,
        media_role="ui_logo",
        text="System logo",
        source_id=uuid4(),
        scope="sys",
    )

    result = media_fragment_to_payload(fragment, world_id="ignored")

    assert result["url"].startswith("/media/sys/")
    assert result["url"].endswith("logo.svg")
    assert result["fragment_type"] == "media"
    assert result["media_role"] == "ui_logo"
