from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from tangl.media.media_data_type import MediaDataType


class MediaDeclaration(BaseModel):
    """Minimal authored data boundary for media-type coercion."""

    data_type: MediaDataType


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("IMAGE", MediaDataType.IMAGE),
        ("image", MediaDataType.IMAGE),
        ("MediaDataType:vector", MediaDataType.VECTOR),
    ],
)
def test_media_data_type_accepts_authored_enum_values(
    value: str,
    expected: MediaDataType,
) -> None:
    assert MediaDataType(value) is expected
    assert MediaDeclaration(data_type=value).data_type is expected


def test_media_data_type_from_path_infers_known_extensions() -> None:
    assert MediaDataType.from_path(Path("example.png")) is MediaDataType.IMAGE
    assert MediaDataType.from_path(".PNG") is MediaDataType.IMAGE
    assert MediaDataType.from_path(Path("vector.svg")) is MediaDataType.VECTOR
    assert MediaDataType.from_path(Path("clip.mp4")) is MediaDataType.VIDEO
    assert MediaDataType.from_path(Path("voice.mp3")) is MediaDataType.AUDIO


def test_media_data_type_unknown_extension_defaults_to_other() -> None:
    assert MediaDataType.from_path(Path("custom.bin")) is MediaDataType.OTHER


@pytest.mark.parametrize("value", ["png", ".png", "unknown"])
def test_media_data_type_rejects_invalid_explicit_declarations(value: str) -> None:
    with pytest.raises(ValueError):
        MediaDataType(value)

    with pytest.raises(ValueError):
        MediaDeclaration(data_type=value)
