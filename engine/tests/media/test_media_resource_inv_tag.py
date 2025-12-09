from pathlib import Path

from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag

def test_content_hash_parses_from_hex_string() -> None:
    rit = MediaResourceInventoryTag(path=Path("bar.png"), content_hash="0a0b")
    assert rit.content_hash == b"\n\x0b"

