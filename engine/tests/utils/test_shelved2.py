from unittest.mock import MagicMock
import os
import shelve as stdlib_shelve

import pytest

import tangl.utils.shelved2 as shelved

def test_caching_with_shelved():
    assert not shelved.cache_dir.exists()

    shelf_name = 'test_cache'

    @shelved.shelved(shelf_name)
    def expensive_computation(x):
        return x * x

    # Call the function twice with the same argument
    result1 = expensive_computation(2)
    assert result1 == 4
    assert os.path.isdir(str(shelved.cache_dir))
    assert (shelved.hit_count, shelved.miss_count) == (0, 1)

    result2 = expensive_computation(2)
    assert result1 == result2
    assert (shelved.hit_count, shelved.miss_count) == (1, 1)

    # Check that the result is cached
    cache_files = list(shelved.cache_dir.glob(f'{shelf_name}*'))
    assert len(cache_files) > 0, "No cache file found with the expected filename stem."

    # Check if the cache is being used (result should be the same)
    shelf_key = shelved.generate_key(2)
    with stdlib_shelve.open(str(shelved.cache_dir / shelf_name), flag="r") as shelf:
        assert shelf.get(shelf_key) == (4, None)


def test_file_closure(monkeypatch):
    shelf_name = 'test_cache'

    @shelved.shelved(shelf_name)
    def expensive_computation(x):
        return x * x

    handles = []
    original = stdlib_shelve.open
    def record(*args, **kwargs):
        handle = original(*args, **kwargs)
        handles.append(handle)
        return handle
    monkeypatch.setattr(stdlib_shelve, "open", record)
    expensive_computation(5)
    with pytest.raises(ValueError):
        len(handles[0])


def test_cache_invalidation():
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


def test_expensive_computation():
    @shelved.shelved('test_cache', skip_if_not_cached=True)
    def expensive_computation(x):
        # Long-running operation
        return x * x

    with pytest.raises(shelved.CacheMissError):
        expensive_computation(2)

    # Tests can use pytest's `xfail` in combination with this approach
    # @pytest.xfail("Expected cache miss on fresh install")

def test_unshelf():

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


def test_clear_shelf():

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

    shelved.clear_shelf(shelf_name)

    # Call again
    result3 = computation_with_check(3)
    assert (shelved.hit_count, shelved.miss_count) == (0, 3)
    result4 = computation_with_check(4)
    assert (shelved.hit_count, shelved.miss_count) == (0, 4)

    # Verify that the function was called four times, indicating re-computation
    assert computation_mock.call_count == 4
