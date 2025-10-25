import time
import pytest
from tangl.core import ResourceDataType, ResourceInventoryTag

# todo: image file resources should also create a px hash for comparing images across scales and formats
def test_compute_px_hash(temp_image_fp):
    rit = ResourceInventoryTag(path=temp_image_fp)
    assert rit.data_hash is not None

@pytest.mark.skip(reason="slow, just for timing and testing cache reset")
def test_file_loc_caching():
    # create a large number of small files and try indexing them all

    now = time.time()
    loc = FileResourceLocation(base_path=base_path, clear_cache=True)
    no_cache = time.time() - now

    now = time.time()
    loc = FileResourceLocation(base_path=base_path, clear_cache=False)
    with_cache = time.time() - now

    print( f'no cache: {no_cache}s, with cache: {with_cache}s' )
    assert no_cache > with_cache


def test_file_loc(temp_image_fp):

    # index a loc and find by path name or digest

    resource1 = loc.find_resource(sample_file_aliases[0])
    resource2 = loc.find_resource(sample_file_aliases[1])

    assert resource1 is resource2
