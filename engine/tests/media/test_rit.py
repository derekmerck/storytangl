from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tangl.media import MediaDataType, MediaResourceInventoryTag
from tangl.utils.hashing import compute_data_hash, uuid_from_secret


@pytest.fixture()
def image_file(tmp_path: Path) -> Path:
    path = tmp_path / "forest-background.png"
    path.write_bytes(b"pixel-data")
    return path


def test_from_path_populates_core_fields(image_file: Path) -> None:
    rit = MediaResourceInventoryTag.from_path(image_file, tags={"scene"})

    assert rit.path == image_file.resolve()
    assert rit.media_type is MediaDataType.IMAGE
    assert rit.data_type is MediaDataType.IMAGE
    assert rit.tags.issuperset({"forest", "background", "scene"})
    assert rit.source == f"filesystem:{image_file.resolve().parent}"

    assert rit.content_hash is not None
    assert rit.content_hash == compute_data_hash(image_file)
    assert rit.uid == uuid_from_secret(rit.content_hash)

    now = datetime.utcnow()
    assert now - rit.created_at < timedelta(seconds=5)


def test_from_path_unknown_extension(tmp_path: Path) -> None:
    path = tmp_path / "mystery.asset"
    path.write_text("unknown format")

    rit = MediaResourceInventoryTag.from_path(path)

    assert rit.media_type is MediaDataType.UNKNOWN
    assert rit.tags == {"mystery"}


def test_matches_supports_tag_queries(image_file: Path) -> None:
    rit = MediaResourceInventoryTag.from_path(image_file, tags=["world"], role="background")

    assert rit.matches(tags="forest")
    assert rit.matches(tags={"forest", "background"})
    assert not rit.matches(tags={"forest", "missing"})

    assert rit.matches(role="background")
    assert not rit.matches(role="foreground")
    assert rit.matches(media_type=MediaDataType.IMAGE)


def test_is_resolved_always_true(image_file: Path) -> None:
    rit = MediaResourceInventoryTag.from_path(image_file)
    assert rit.is_resolved
