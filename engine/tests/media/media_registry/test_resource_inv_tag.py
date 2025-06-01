import pytest
from datetime import datetime, timedelta
from tangl.media.media_registry import MediaRegistryTag, MediaDataType

def test_resource_inventory_tag_initialization():
    tag = MediaRegistryTag(label="test", content_hash=b"hash123", data_type=MediaDataType.IMAGE)
    assert tag.label == "test"
    assert tag.data_type == MediaDataType.IMAGE
    assert tag.data_type.ext == "png"


def test_resource_inventory_tag_validation():

    # missing data, path, or content_hash
    with pytest.raises(ValueError):
        MediaRegistryTag(data_type=MediaDataType.IMAGE)

    with pytest.raises(ValueError):
        MediaRegistryTag()


def test_resource_inventory_tag_expiry_conversion():
    now = datetime.now()
    expiry_delta = timedelta(days=1)
    tag = MediaRegistryTag(label="test",
                           content_hash=b"hash123",
                           data_type=MediaDataType.IMAGE,
                           expiry=expiry_delta)
    assert tag.expiry.date() == (now + expiry_delta).date()


@pytest.mark.xfail(reason="aliases not implemented yet in current rev")
def test_resource_inventory_tag_get_aliases():
    tag = MediaRegistryTag(label="test", content_hash=b"hash123", data_type=MediaDataType.IMAGE)
    assert {"test", b"hash123"}.issubset(tag.get_identifiers())


@pytest.mark.xfail(reason="hash caching not implemented yet in current rev")
def test_compute_hash_caching(temp_image_fp):
    import tangl.utils.shelved2 as shelved
    starting_hits, starting_misses = shelved.hit_count, shelved.miss_count
    MediaRegistryTag(path=temp_image_fp)
    # should be no initial cache entry
    assert shelved.miss_count == starting_misses + 1
    MediaRegistryTag(path=temp_image_fp)
    # should have gotten a cache hit
    assert shelved.hit_count == starting_hits + 1
    # by touching the file, we should invalidate the cache entry ...
    temp_image_fp.touch(exist_ok=True)
    MediaRegistryTag(path=temp_image_fp)
    # ... so we should register a miss
    assert shelved.miss_count == starting_misses + 2
