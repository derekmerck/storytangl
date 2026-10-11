"""Tests for static content-digest indexing in media registries."""

from __future__ import annotations

import copy
import pickle
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


def test_readding_mutated_record_repairs_its_registered_digest() -> None:
    """Re-adding a mutated record moves the derived digest entry."""
    record = _static_rit("record", b"old")
    registry = MediaResourceRegistry(label="mutated")
    registry.add(record)

    record.preset_content_hash = b"new"
    registry.add(record)
    assert _static_rit("old", b"old") not in registry
    assert registry._find_by_stored_content_hash(_static_rit("new", b"new")) is record

    record.preset_content_hash = b"observed"
    assert _static_rit("observed", b"observed") in registry


def test_status_transition_then_removal_does_not_leave_dynamic_state() -> None:
    """Removal uses the registration-time state, not mutable current fields."""
    record = MediaRIT(label="pending", status=MediaRITStatus.PENDING)
    registry = MediaResourceRegistry(label="transition")
    registry.add(record)

    record.status = MediaRITStatus.RESOLVED
    record.preset_content_hash = b"resolved"
    registry.remove(record.uid)

    assert registry._dynamic_member_count == 0
    record = MediaRIT(label="readded", status=MediaRITStatus.PENDING)
    registry.add(record)
    record.status = MediaRITStatus.RESOLVED
    record.preset_content_hash = b"readded"
    registry.add(record)
    assert _static_rit("readded", b"readded") in registry
    registry.remove(record.uid)
    assert registry._dynamic_member_count == 0
    registry.add(_static_rit("static", b"static"))
    assert _static_rit("static", b"static") in registry


def test_copies_and_pickle_rebuild_derived_state() -> None:
    """All supported copy paths leave a usable, independent derived view."""
    first = _static_rit("first", b"first")
    second = _static_rit("second", b"second")
    registry = MediaResourceRegistry(label="copied")
    registry.add(first)
    registry.add(second)

    copies = [
        copy.copy(registry),
        copy.deepcopy(registry),
        registry.model_copy(),
        registry.model_copy(deep=True),
        pickle.loads(pickle.dumps(registry)),
    ]
    deep_copy = copies[1]
    assert deep_copy.members[first.uid] is not first
    assert deep_copy._content_hash_members[b"first"] is deep_copy.members[first.uid]
    for clone in copies:
        assert _static_rit("probe", b"first") in clone
        added = _static_rit("added", b"added")
        clone.add(added)
        clone.remove(added.uid)
        clone.clear()
        assert not clone


def test_add_hook_tracks_a_different_uid_replacement() -> None:
    """A registry add hook may replace an item without preserving its UID."""
    replacement = _static_rit("replacement", b"replacement")
    on_add_item(func=lambda **_: replacement)

    for preexisting in (False, True):
        original = _static_rit("original", b"original")
        registry = MediaResourceRegistry(label="hooked")
        if preexisting:
            registry.add(_static_rit("existing", b"original", uid=original.uid))
        registry.add(original, _ctx=Ctx())

        assert registry.get(replacement.uid) is replacement
        assert replacement in registry
        if preexisting:
            assert registry.get(original.uid) is not original
            assert _static_rit("existing", b"original") in registry
        else:
            assert registry.get(original.uid) is None


def test_overwrite_keeps_selector_first_match_order_for_shared_digest() -> None:
    """A same-UID overwrite retains its original dict position."""
    first = _static_rit("first", b"a")
    second = _static_rit("second", b"b")
    replacement = _static_rit("replacement", b"b", uid=first.uid)
    registry = MediaResourceRegistry(label="order")
    registry.add(first)
    registry.add(second)
    registry.add(replacement)
    probe = _static_rit("probe", b"b")

    assert registry.find_one(Selector.from_identifier(b"b")) is replacement
    assert registry._find_by_stored_content_hash(probe) is replacement
    restored = MediaResourceRegistry.structure(registry.unstructure())
    assert restored._find_by_stored_content_hash(probe).uid == replacement.uid

    registry.remove(replacement.uid)
    assert registry._find_by_stored_content_hash(probe) is second


def test_same_digest_overwrite_refreshes_only_its_cached_winner() -> None:
    """Same-digest replacement preserves both identity and first-match order."""
    first = _static_rit("first", b"shared")
    replacement = _static_rit("replacement", b"shared", uid=first.uid)
    registry = MediaResourceRegistry(label="same-digest")
    registry.add(first)
    registry.add(replacement)
    probe = _static_rit("probe", b"shared")

    assert registry._find_by_stored_content_hash(probe) is replacement

    earlier = _static_rit("earlier", b"shared")
    later = _static_rit("later", b"shared")
    later_replacement = _static_rit("later-replacement", b"shared", uid=later.uid)
    registry = MediaResourceRegistry(label="same-digest-order")
    registry.add(earlier)
    registry.add(later)
    registry.add(later_replacement)

    assert registry._find_by_stored_content_hash(probe) is earlier
    registry.remove(earlier.uid)
    assert registry._find_by_stored_content_hash(probe) is later_replacement


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
