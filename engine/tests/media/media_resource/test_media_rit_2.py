import pytest
from datetime import datetime, timedelta
from tangl.media import MediaResourceInventoryTag as MediaRIT, MediaDataType
from tangl.core import Selector
from tangl.media.media_resource.media_resource_registry import MediaResourceRegistry

def test_resource_inventory_tag_initialization():
    tag = MediaRIT(label="test", content_hash=b"hash123", data_type=MediaDataType.IMAGE)
    assert tag.label == "test"
    assert tag.data_type == MediaDataType.IMAGE
    assert tag.data_type.ext == "png"


def test_resource_inventory_tag_validation():

    # missing data, path, or content_hash
    with pytest.raises(ValueError):
        MediaRIT(data_type=MediaDataType.IMAGE)

    with pytest.raises(ValueError):
        MediaRIT()


def test_resource_inventory_tag_expiry_conversion():
    now = datetime.now()
    expiry_delta = timedelta(days=1)
    tag = MediaRIT(label="test",
                   content_hash=b"hash123",
                   data_type=MediaDataType.IMAGE,
                   expiry=expiry_delta)
    assert tag.expiry.date() == (now + expiry_delta).date()


def test_resource_inventory_tag_get_aliases():
    tag = MediaRIT(label="test", content_hash=b"hash123", data_type=MediaDataType.IMAGE)
    assert tag.has_identifier(b"hash123")
    assert Selector(has_identifier=b"hash123").matches(tag)


def test_compute_hash_caching(temp_image_fp):
    import tangl.utils.shelved2 as shelved
    starting_hits, starting_misses = shelved.hit_count, shelved.miss_count
    MediaRIT.from_source(temp_image_fp)
    # should be no initial cache entry
    assert shelved.miss_count == starting_misses + 1
    MediaRIT.from_source(temp_image_fp)
    # should have gotten a cache hit
    assert shelved.hit_count == starting_hits + 1
    # by touching the file, we should invalidate the cache entry ...
    temp_image_fp.touch(exist_ok=True)
    MediaRIT.from_source(temp_image_fp)
    # ... so we should register a miss
    assert shelved.miss_count == starting_misses + 2


def test_media_registry_reuses_shelved_file_hashes_for_reindexing(
    temp_image_fp,
    monkeypatch,
    tmp_path,
):
    import tangl.utils.shelved2 as shelved
    import tangl.media.media_resource.media_resource_inv_tag as media_rit_module

    shelf_dir = tmp_path / "shelf"
    shelf_dir.mkdir()
    monkeypatch.setattr(shelved, "cache_dir", shelf_dir)
    MediaRIT.clear_from_source_cache()

    starting_hits, starting_misses = shelved.hit_count, shelved.miss_count
    hash_calls = 0
    real_compute_data_hash = media_rit_module.compute_data_hash

    def spy_compute_data_hash(data, digest_size=None):
        nonlocal hash_calls
        hash_calls += 1
        return real_compute_data_hash(data, digest_size=digest_size)

    monkeypatch.setattr(media_rit_module, "compute_data_hash", spy_compute_data_hash)

    try:
        registry = MediaResourceRegistry(label="cached_media")

        first = registry.index([temp_image_fp])[0]
        assert hash_calls == 1
        assert first.content_hash() == first.get_content_hash()
        assert hash_calls == 1

        second = registry.index([temp_image_fp])[0]
        assert second.uid == first.uid
        assert len(registry) == 1
        assert hash_calls == 1
        assert second.content_hash() == first.content_hash()
        assert hash_calls == 1

        assert shelved.miss_count == starting_misses + 1
        assert shelved.hit_count == starting_hits + 1
    finally:
        MediaRIT.clear_from_source_cache()
