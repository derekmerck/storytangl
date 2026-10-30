"""Small process-local, operation-scoped shelf cache."""
from __future__ import annotations

import hashlib
import shelve
import threading
from functools import wraps
from pathlib import Path

from tangl.config import settings

cache_dir: Path = settings.service.paths.cache_data
SHELVED_CACHE_ENABLED = bool(settings.get("service.caches.shelved", True))

_locks_guard = threading.Lock()
_shelf_locks: dict[Path, threading.Lock] = {}
hit_count = 0
miss_count = 0


class CacheMissError(KeyError):
    """A requested cached value is unavailable and computation was declined."""


def _path_and_lock(fn: str) -> tuple[Path, threading.Lock]:
    path = (cache_dir / fn).resolve()
    with _locks_guard:
        lock = _shelf_locks.setdefault(path, threading.Lock())
    return path, lock


def _exists(path: Path) -> bool:
    # dbm backends may use the bare name or files such as .db, .dat and .dir.
    return path.exists() or any(path.parent.glob(f"{path.name}.*"))


def generate_key(*args: object) -> str:
    hash_input = "".join(str(arg) for arg in args)
    return hashlib.sha224(hash_input.encode("utf8")).hexdigest()


def shelved(fn: str, skip_if_not_cached: bool = False):
    """Cache results by arguments, optionally rejecting a miss.

    ``check_value`` invalidates a stored result when its value changes. Each
    operation opens and closes its shelf on the caller's thread while holding
    the process-local lock for its canonical path.
    """
    def decorator(f):
        @wraps(f)
        def cache(*args, check_value=None):
            global hit_count, miss_count

            if not SHELVED_CACHE_ENABLED:
                if skip_if_not_cached:
                    raise CacheMissError(f"Cache disabled for shelf: {fn}")
                return f(*args)

            key = generate_key(*args)
            path, lock = _path_and_lock(fn)
            with lock:
                path.parent.mkdir(parents=True, exist_ok=True)
                with shelve.open(str(path), flag="c") as shelf:
                    if key not in shelf or (check_value is not None and shelf[key][1] != check_value):
                        miss_count += 1
                        if skip_if_not_cached:
                            raise CacheMissError(f"Cache miss for key: {key}")
                        shelf[key] = (f(*args), check_value)
                    else:
                        hit_count += 1
                    return shelf[key][0]
        return cache
    return decorator


def unshelf(fn: str, *args: object) -> None:
    path, lock = _path_and_lock(fn)
    with lock:
        if _exists(path):
            with shelve.open(str(path), flag="w") as shelf:
                key = generate_key(*args)
                if key in shelf:
                    del shelf[key]


def clear_shelf(fn: str) -> None:
    """Invalidate an existing shelf without unlinking its database files."""
    path, lock = _path_and_lock(fn)
    with lock:
        if _exists(path):
            with shelve.open(str(path), flag="w") as shelf:
                shelf.clear()
