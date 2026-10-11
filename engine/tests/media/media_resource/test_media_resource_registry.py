"""Tests for static content-digest indexing in media registries."""

from __future__ import annotations

from uuid import uuid4

from tangl.core import Ctx, Selector, on_add_item
from tangl.media import MediaDataType
from tangl.media.media_resource.media_resource_inv_tag import (
    MediaRITStatus,
    MediaResourceInventoryTag as MediaRIT,
)
from tangl.media.media_resource.media_resource_registry import MediaResourceRegistry


def _static_rit(label: str, digest: bytes, *, uid=None) -> MediaRIT:
    return MediaRIT(
        label=label,
        content_hash=digest,
        data_type=MediaDataType.IMAGE,
        uid=uid or uuid4(),
    )


def test_index_reuses_first_static_digest_match_without_selector_scans(tmp_path, monkeypatch) -> None:
    """Static inventory lookup remains constant work per source record."""
    paths = []
    for index in range(128):
        path = tmp_path / f"asset-{index}.png"
        path.write_bytes(index.to_bytes(2, "big"))
        paths.append(path)

    calls = 0
    real_matches = Selector.matches

    def counting_matches(self, entity):
        nonlocal calls
        calls += 1
        return real_matches(self, entity)

    monkeypatch.setattr(Selector, "matches", counting_matches)
    registry = MediaResourceRegistry(label="static")

    indexed = registry.index(paths)
    duplicate_path = tmp_path / "duplicate.png"
    duplicate_path.write_bytes(paths[0].read_bytes())
    duplicate = registry.index([duplicate_path])[0]

    assert duplicate is indexed[0]
    assert len(registry) == len(paths)
    assert calls == 0


def test_static_digest_index_handles_overwrite_remove_clear_and_restore() -> None:
    """Derived state follows the normal registry lifecycle, not persistence."""
    first = _static_rit("first", b"first")
    replacement = _static_rit("replacement", b"replacement", uid=first.uid)
    second = _static_rit("second", b"second")
    second_copy = _static_rit("second-copy", b"second")
    registry = MediaResourceRegistry(label="static", members={first.uid: first})

    assert _static_rit("same", b"first") in registry
    registry.add(replacement)
    assert _static_rit("old", b"first") not in registry
    assert _static_rit("new", b"replacement") in registry

    registry.add(second)
    registry.add(second_copy)
    registry.remove(uuid4())
    registry.remove(replacement.uid)
    probe = _static_rit("still present", b"second")
    assert registry._find_by_stored_content_hash(probe) is second
    registry.remove(second.uid)
    assert registry._find_by_stored_content_hash(probe) is second_copy

    restored = MediaResourceRegistry.structure(registry.unstructure())
    assert _static_rit("restored", b"second") in restored
    registry._content_hash_members.clear()
    assert registry == restored

    registry.clear()
    assert not registry
    assert _static_rit("cleared", b"second") not in registry


def test_add_tracks_the_dispatch_replacement_not_the_input() -> None:
    """A registry add hook may replace a record before it enters the side-map."""
    original = _static_rit("original", b"original")
    replacement = _static_rit("replacement", b"replacement", uid=original.uid)
    on_add_item(func=lambda **_: replacement)
    registry = MediaResourceRegistry(label="hooked")

    registry.add(original, _ctx=Ctx())

    assert registry.get(original.uid) is replacement
    assert original not in registry
    assert replacement in registry


def test_dynamic_records_keep_selector_fallback_and_never_share_empty_digest() -> None:
    """Pending media remains outside the static index until its lifecycle resolves."""
    pending = MediaRIT(label="pending", status=MediaRITStatus.PENDING)
    static = _static_rit("static", b"static")
    registry = MediaResourceRegistry(label="mixed")
    registry.add(pending)
    registry.add(static)

    assert pending not in registry
    assert static in registry
    assert registry.find_one(Selector(label="pending")) is pending
