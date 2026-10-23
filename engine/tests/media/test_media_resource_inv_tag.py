from __future__ import annotations

from pathlib import Path
import shelve

import pytest

from tangl.media import MediaDataType
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.persistence.structuring import StructuringHandler
from tangl.journal.fragments import MediaFragment
from tangl.service.media import media_fragment_to_payload
from tangl.utils import shelved2

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
        kind_map={MediaResourceInventoryTag.__fqn__(): MediaResourceInventoryTag},
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


@pytest.mark.parametrize(
    ("extension", "old_type", "expected_type"),
    [("svg", MediaDataType.VECTOR, MediaDataType.VECTOR),
     ("ogg", MediaDataType.OTHER, MediaDataType.AUDIO)],
)
def test_old_pickled_rit_cache_is_invalidated_before_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extension: str,
    old_type: MediaDataType, expected_type: MediaDataType,
) -> None:
    path = tmp_path / f"unchanged.{extension}"
    path.write_bytes(b"<svg/>" if extension == "svg" else b"OggS container fixture")
    stat = path.stat()
    legacy = MediaResourceInventoryTag(path=path, data_type=old_type)
    legacy.preset_content_hash = legacy.get_content_hash()
    legacy.__dict__.pop("media_format")
    legacy.__dict__.pop("mime_type")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    key = shelved2.generate_key(MediaResourceInventoryTag, path)
    with shelve.open(str(cache_dir / "rits")) as shelf:
        shelf[key] = (legacy, (stat.st_mtime_ns, stat.st_size))
        # The fixture is really pickled pre-change state, not a fresh model.
        stored, check_value = shelf[key]
        assert "mime_type" not in stored.__dict__
        assert check_value == (stat.st_mtime_ns, stat.st_size)
    monkeypatch.setattr(shelved2, "cache_dir", cache_dir)
    monkeypatch.setattr(shelved2, "opened_shelves", {})
    monkeypatch.setattr(shelved2, "shelf_locks", {})
    monkeypatch.setattr(shelved2, "SHELVED_CACHE_ENABLED", True)
    try:
        hits, misses = shelved2.hit_count, shelved2.miss_count
        fresh = MediaResourceInventoryTag.from_source(path)
        assert fresh.uid != legacy.uid
        assert fresh.data_type is expected_type
        assert fresh.media_format == ("ogg" if extension == "ogg" else None)
        assert fresh.mime_type == ("audio/ogg" if extension == "ogg" else None)
        fragment = MediaFragment(
            content=fresh, content_format="rit", content_type=fresh.data_type,
        )
        assert media_fragment_to_payload(fragment, world_id="cache_test")["url"].endswith(path.name)
        reused = MediaResourceInventoryTag.from_source(path)
        assert reused.uid == fresh.uid
        assert reused.preset_content_hash == fresh.preset_content_hash
        assert (shelved2.hit_count, shelved2.miss_count) == (hits + 1, misses + 1)
        assert path.stat() == stat
    finally:
        shelved2.close_shelves()

