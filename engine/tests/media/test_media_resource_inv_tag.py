from __future__ import annotations

from pathlib import Path

import pytest

from tangl.media import MediaDataType
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.persistence.structuring import StructuringHandler

def test_content_hash_parses_from_hex_string() -> None:
    rit = MediaResourceInventoryTag(path=Path("bar.png"), content_hash="0a0b")
    assert rit.content_hash == b"\n\x0b"


@pytest.mark.parametrize(
    ("extension", "mime_type"),
    [("mp3", "audio/mpeg"), ("wav", "audio/wav"), ("ogg", "audio/ogg"),
     ("flac", "audio/flac"), ("m4a", "audio/mp4")],
)
def test_audio_file_metadata_declares_format_not_codec(extension: str, mime_type: str) -> None:
    rit = MediaResourceInventoryTag(path=Path(f"music.{extension.upper()}"))
    assert rit.data_type is MediaDataType.AUDIO
    assert rit.media_format == extension
    assert rit.mime_type == mime_type
    assert "codec" not in rit.unstructure()
    restored = StructuringHandler.structure(
        Json.deserialize(Json.serialize(rit.unstructure())),
        kind_map={"MediaResourceInventoryTag": MediaResourceInventoryTag},
    )
    assert restored.uid == rit.uid
    assert restored.media_format == extension
    assert restored.mime_type == mime_type
    assert restored.data_type is MediaDataType.AUDIO


def test_explicit_metadata_is_not_replaced_by_filename_inference() -> None:
    rit = MediaResourceInventoryTag(
        path=Path("recording.ogg"), media_format="ogg", mime_type='audio/ogg; codecs="opus"',
    )
    assert rit.mime_type == 'audio/ogg; codecs="opus"'


@pytest.mark.parametrize(("declared", "mime_type"), [("flac", "audio/flac"), ("custom", None)])
def test_declared_format_controls_mime_inference(declared: str, mime_type: str | None) -> None:
    rit = MediaResourceInventoryTag(path=Path("recording.ogg"), media_format=declared)
    assert rit.media_format == declared
    assert rit.mime_type == mime_type


def test_unknown_audio_format_does_not_guess_a_mime_type() -> None:
    rit = MediaResourceInventoryTag(path=Path("recording.custom"), data_type=MediaDataType.AUDIO)
    assert rit.media_format is None
    assert rit.mime_type is None

