"""Keep pytest cache files separate from running StoryTangl instances."""
from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

# Collection can import modules that use the cache before fixtures run.
_collection_cache = TemporaryDirectory(prefix="storytangl-pytest-")
_cache_env = "TANGL_SERVICE__PATHS__CACHE_DATA"
_previous_cache_env = os.environ.get(_cache_env)
os.environ[_cache_env] = f"@path {_collection_cache.name}"


@contextmanager
def shelf_cache(cache: Path) -> Iterator[Path]:
    """Own a cache directory and close its handles before restoring state."""
    from tangl.config import settings
    from tangl.utils import shelved2

    shelved2.close_shelves()
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(_cache_env, f"@path {cache}")
        patch.setitem(settings.service.paths, "cache_data", cache)
        patch.setattr(shelved2, "cache_dir", cache)
        patch.setattr(shelved2, "opened_shelves", {})
        patch.setattr(shelved2, "shelf_locks", {})
        patch.setattr(shelved2, "hit_count", 0)
        patch.setattr(shelved2, "miss_count", 0)
        try:
            yield cache
        finally:
            shelved2.close_shelves()
            shelved2.shelf_locks.clear()


@pytest.fixture(autouse=True)
def isolated_shelf_cache(tmp_path: Path) -> Iterator[Path]:
    """Give each test its own shelf files, counters, and live handles."""
    with shelf_cache(tmp_path / "cache") as cache:
        yield cache


@pytest.fixture
def cache_lifecycle() -> Callable[[Path], AbstractContextManager[Path]]:
    return shelf_cache


def pytest_unconfigure() -> None:
    from tangl.utils import shelved2

    shelved2.close_shelves()
    _collection_cache.cleanup()
    if _previous_cache_env is None:
        os.environ.pop(_cache_env, None)
    else:
        os.environ[_cache_env] = _previous_cache_env
