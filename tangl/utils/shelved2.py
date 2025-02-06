import os
import hashlib
import shelve
from functools import wraps
from pathlib import Path
import atexit
import threading
import logging

from tangl.config import settings

try:
    cache_dir: Path = settings.service.paths.cache_data
except AttributeError:  # pragma: no cover
    cache_dir: Path = Path.cwd() / "shelf"

logger = logging.getLogger(__name__)

os.makedirs(cache_dir, exist_ok=True)

opened_shelves: dict[str, shelve.Shelf] = {}
shelf_locks: dict[str, threading.Lock] = {}

hit_count = 0
miss_count = 0


class CacheMissError(KeyError):
    """Exception raised when a cache miss occurs and computation is declined."""


def close_shelves():
    for shelf in opened_shelves.values():
        shelf.close()
    opened_shelves.clear()
    # Clear the dictionary after closing all shelves to indicate proper clean-up

atexit.register(close_shelves)

def generate_key(*args):
    hash_input = "".join(str(arg) for arg in args)
    return hashlib.sha224(hash_input.encode('utf8')).hexdigest()

def shelved(fn, keep_open=True, skip_if_not_cached=False):
    """
    Decorator pattern for simple file-based return-value caching.

    Options:

    - `keep_open=True`: defer write-outs for this shelf until the
       program exits.  This will be much faster than opening and
       closing the shelve cache-file each time.
    - `skip_if_not_cached=False`: decline to compute new values for
      the wrapped function.  Useful for x-failing tests without
      regenerating unnecessary caches for fresh installations.

    Wrapper accepts only string-able arguments the 'check_value' kw.

    - `check_value`: attach a validation key to the result.
      When making another otherwise _identical_ query, if the validation
      key doesn't match, the wrapped function will be recomputed.
    """

    def decorator(f):
        @wraps(f)
        def cache(*args, check_value=None):
            global opened_shelves, shelf_locks, hit_count, miss_count
            key = generate_key(*args)

            if str(fn) not in opened_shelves:
                fp = cache_dir / fn
                opened_shelves[str(fn)] = shelve.open(str(fp), 'c')
                shelf_locks[str(fn)] = threading.Lock()

            with shelf_locks[str(fn)]:
                shelf = opened_shelves[str(fn)]
                if key not in shelf or (check_value is not None and shelf[key][1] != check_value):
                    miss_count += 1
                    if skip_if_not_cached:
                        raise CacheMissError(f"Cache miss for key: {key}")
                    shelf[key] = (f(*args), check_value)
                else:
                    hit_count += 1

                result = shelf[key][0]

            if not keep_open:
                opened_shelves[str(fn)].close()
                del opened_shelves[str(fn)]
                del shelf_locks[str(fn)]

            return result

        return cache
    return decorator

def unshelf(fn, *args):
    key = generate_key(*args)

    if str(fn) in opened_shelves:
        shelf = opened_shelves[str(fn)]
        if key in shelf:
            del shelf[key]

def clear_shelf(fn: str):

    logger.debug(f'clearing shelf {fn}')
    if str(fn) in opened_shelves:
        opened_shelves[str(fn)].clear()
        opened_shelves[str(fn)].close()
        del opened_shelves[str(fn)]
        del shelf_locks[str(fn)]

    matches = list(cache_dir.glob( f"{fn}.*" ))
    for fp in matches:
        logger.debug( f'removing {fp}')
        os.remove(fp)
    # raise RuntimeError(f"No such shelf {fn}")
