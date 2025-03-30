import importlib
from unittest.mock import MagicMock
import time
import os

import pytest

import tangl.utils.shelved2 as shelved

@pytest.fixture(scope="function")
def patch_shelved(monkeypatch, tmp_path):
    # Reload the module to ensure it uses the modified cache_dir
    importlib.reload(shelved)
    monkeypatch.setattr('tangl.utils.shelved2.cache_dir', tmp_path)


def test_caching_with_shelved(patch_shelved):

    assert os.path.isdir(str(shelved.cache_dir)), f"Cache directory does not exist: {shelved.cache_dir}"

    shelf_name = 'test_cache'

    @shelved.shelved(shelf_name)
    def expensive_computation(x):
        return x * x

    # Call the function twice with the same argument
    result1 = expensive_computation(2)
    assert result1 == 4
    assert (shelved.hit_count, shelved.miss_count) == (0, 1)

    result2 = expensive_computation(2)
    assert result1 == result2
    assert (shelved.hit_count, shelved.miss_count) == (1, 1)

    # Check that the result is cached
    cache_files = list(shelved.cache_dir.glob(f'{shelf_name}*'))
    assert len(cache_files) > 0, "No cache file found with the expected filename stem."

    # Check if the cache is being used (result should be the same)
    shelf_key = shelved.generate_key(2)
    assert shelf_key in shelved.opened_shelves[shelf_name]
    assert shelved.opened_shelves[str(shelf_name)].get(shelf_key) == (4, None)


def test_file_closure(patch_shelved):
    shelf_name = 'test_cache'

    @shelved.shelved(shelf_name)
    def expensive_computation(x):
        return x * x

    expensive_computation(5)
    assert shelf_name in shelved.opened_shelves

    # Simulate program exit
    shelved.close_shelves()  # Assuming close_shelves is your atexit registered function

    # Open-shelves should have been cleared
    assert not shelved.opened_shelves


def test_cache_invalidation(patch_shelved):
    shelf_name = 'test_cache'
    computation_mock = MagicMock(return_value=9)

    @shelved.shelved(shelf_name)
    def computation_with_check(x, check_value=None):
        return computation_mock(x)

    # Call the function with a check value
    result1 = computation_with_check(3, check_value='initial')
    assert (shelved.hit_count, shelved.miss_count) == (0, 1)

    # Change the check value
    result2 = computation_with_check(3, check_value='changed')
    assert (shelved.hit_count, shelved.miss_count) == (0, 2)

    assert result1 == 9
    assert result2 == 9
    # Verify that the function was called twice, indicating re-computation
    assert computation_mock.call_count == 2


def test_expensive_computation(patch_shelved):
    @shelved.shelved('test_cache', skip_if_not_cached=True)
    def expensive_computation(x):
        # Long-running operation
        return x * x

    with pytest.raises(shelved.CacheMissError):
        expensive_computation(2)

    # Tests can use pytest's `xfail` in combination with this approach
    # @pytest.xfail("Expected cache miss on fresh install")

@pytest.mark.skip(reason="only for benchmarking")
@pytest.mark.parametrize("keep_open", [True, False])
def test_shelve_performance(patch_shelved, keep_open):

    @shelved.shelved('test_cache', keep_open=keep_open)
    def cached_operation(x):
        return x * x

    start_time = time.time()

    # Simulate read-write operations
    for i in range(10000):
        cached_operation(i)
        cached_operation(i)  # Intentional repeat to test cache hit

    end_time = time.time()
    print(f"Execution time with {'keep open' if keep_open else 'close on access'}: {end_time - start_time} seconds")

    assert True  # Placeholder assertion


def test_unshelf(patch_shelved):

    shelf_name = 'test_cache'
    computation_mock = MagicMock(return_value=9)

    @shelved.shelved(shelf_name)
    def computation_with_check(x, check_value=None):
        return computation_mock(x)

    # Call the function
    result1 = computation_with_check(3)
    assert (shelved.hit_count, shelved.miss_count) == (0, 1)

    # Unshelf the prior result
    shelved.unshelf(shelf_name, 3)

    # Call again
    result2 = computation_with_check(3)
    assert (shelved.hit_count, shelved.miss_count) == (0, 2)

    assert result1 == 9
    assert result2 == 9
    # Verify that the function was called twice, indicating re-computation
    assert computation_mock.call_count == 2


def test_clear_shelf(patch_shelved):

    shelf_name = 'test_cache'
    computation_mock = MagicMock(return_value=9)

    @shelved.shelved(shelf_name)
    def computation_with_check(x, check_value=None):
        return computation_mock(x)

    # Call the function
    result1 = computation_with_check(3)
    assert (shelved.hit_count, shelved.miss_count) == (0, 1)
    result2 = computation_with_check(4)
    assert (shelved.hit_count, shelved.miss_count) == (0, 2)

    # shelved.close_shelves()  # Ensure all shelves are closed before clearing

    try:
        shelved.clear_shelf(shelf_name)
    except Exception as e:
        pytest.fail(f"Failed to clear shelf: {e}")

    # Call again
    result3 = computation_with_check(3)
    assert (shelved.hit_count, shelved.miss_count) == (0, 3)
    result4 = computation_with_check(4)
    assert (shelved.hit_count, shelved.miss_count) == (0, 4)

    # Verify that the function was called four times, indicating re-computation
    assert computation_mock.call_count == 4

