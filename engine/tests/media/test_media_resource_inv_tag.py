from pathlib import Path

from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag


def test_content_hash_serializes_to_hex() -> None:
    rit = MediaResourceInventoryTag(path=Path("foo.png"), content_hash=b"\x01\x02")

    dumped = rit.model_dump()

    assert dumped["content_hash"] == "0102"


def test_content_hash_parses_from_hex_string() -> None:
    rit = MediaResourceInventoryTag(path=Path("bar.png"), content_hash="0a0b")

    assert rit.content_hash == b"\n\x0b"


def test_blank_content_hash_becomes_none() -> None:
    rit = MediaResourceInventoryTag(path=Path("baz.png"), content_hash="   ")

    assert rit.content_hash is None
