from __future__ import annotations

from pathlib import Path

from tangl.media.media_data_type import MediaDataType


def test_media_data_type_from_path_infers_known_extensions() -> None:
    assert MediaDataType.from_path(Path("example.png")) is MediaDataType.IMAGE
    assert MediaDataType.from_path(Path("vector.svg")) is MediaDataType.VECTOR
    assert MediaDataType.from_path(Path("clip.mp4")) is MediaDataType.VIDEO
    assert MediaDataType.from_path(Path("voice.mp3")) is MediaDataType.AUDIO


def test_media_data_type_unknown_extension_defaults_to_other() -> None:
    assert MediaDataType.from_path(Path("custom.bin")) is MediaDataType.OTHER
