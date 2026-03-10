from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from tangl.journal.media import MediaFragment
from tangl.media import story_media as story_media_mod
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.service.user.user import User


def _rit_from_svg(tmp_path: Path, filename: str) -> MediaRIT:
    path = tmp_path / filename
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<circle cx="16" cy="16" r="14" fill="red"/></svg>',
        encoding="utf-8",
    )
    return MediaRIT(path=path, data_type=MediaDataType.IMAGE, label=filename)


def test_dereference_media_world_scope_uses_world_prefix(tmp_path: Path) -> None:
    rit = _rit_from_svg(tmp_path, "scene.svg")
    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        content_type=MediaDataType.IMAGE,
        source_id=uuid4(),
        scope="world",
    )

    payload = RuntimeController()._dereference_media(fragment, world_id="w1")

    assert payload["url"] == "/media/world/w1/scene.svg"
    assert payload["scope"] == "world"


def test_dereference_media_sys_scope_uses_sys_prefix(tmp_path: Path) -> None:
    rit = _rit_from_svg(tmp_path, "logo.svg")
    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        content_type=MediaDataType.IMAGE,
        source_id=uuid4(),
        scope="sys",
    )

    payload = RuntimeController()._dereference_media(fragment, world_id="w1")

    assert payload["url"] == "/media/sys/logo.svg"
    assert payload["scope"] == "sys"


def test_dereference_media_story_scope_uses_story_prefix_and_story_id(tmp_path: Path) -> None:
    rit = _rit_from_svg(tmp_path, "avatar.svg")
    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        content_type=MediaDataType.IMAGE,
        source_id=uuid4(),
        scope="story",
        story_id="story-77",
    )

    payload = RuntimeController()._dereference_media(fragment, world_id="w1")

    assert payload["url"] == "/media/story/story-77/avatar.svg"
    assert payload["scope"] == "story"


def test_drop_story_removes_story_media_when_not_archived(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "story_media"
    story_dir = root / "story-1"
    story_dir.mkdir(parents=True)
    (story_dir / "asset.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")

    monkeypatch.setattr(
        story_media_mod,
        "get_story_media_dir",
        lambda story_id=None: root if story_id is None else root / str(story_id),
    )

    user = User(label="runtime-user")
    user.current_ledger_id = "story-1"

    info = RuntimeController().drop_story(user=user, ledger=None, archive=False)

    assert info.details is not None
    assert info.details["story_media_deleted"] is True
    assert not story_dir.exists()


def test_drop_story_preserves_story_media_when_archived(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "story_media"
    story_dir = root / "story-2"
    story_dir.mkdir(parents=True)
    (story_dir / "asset.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")

    monkeypatch.setattr(
        story_media_mod,
        "get_story_media_dir",
        lambda story_id=None: root if story_id is None else root / str(story_id),
    )

    user = User(label="runtime-user")
    user.current_ledger_id = "story-2"

    info = RuntimeController().drop_story(user=user, ledger=None, archive=True)

    assert info.details is not None
    assert "story_media_deleted" not in info.details
    assert story_dir.exists()
