import json
from hashlib import sha224, blake2b
from pathlib import Path
import io
import logging

from tangl.type_hints import Hash   # bytes

try:
    from tangl.config import settings
    HASHING_SALT = settings.hashing_salt
except (ImportError, AttributeError):
    # Fallback
    HASHING_SALT = b'<!--2t0ryT4n5L--/>'

logger = logging.getLogger(__name__)
logger.debug( f"Hashing with salt: {HASHING_SALT}" )

def hashing_func(*data, salt=HASHING_SALT, digest_size = None) -> Hash:

    if digest_size is None:
        # legacy, slightly more secure but can probably replace with blake
        # for speed and consistency
        hasher = sha224(salt)
    else:
        # provides digest size for creating ints or uids without truncating
        hasher = blake2b(digest_size=digest_size)

    for item in data:
        if isinstance(item, bytes):
            item_bytes = item
        elif x := getattr(item, 'bytes', None):
            # uids and such
            item_bytes = x
        elif getattr(item, 'to_bytes', None):
            # ints
            item: int
            item_bytes = item.to_bytes(8, signed=True)
        elif isinstance(item, str):
            item_bytes = item.encode('utf-8')
        elif isinstance(item, dict):
            # unstructured state data
            item_bytes = json.dumps(item, default=str).encode('utf-8')
        else:
            # Use bytes from the built-in hash
            item_bytes = hash(item).to_bytes(8)
        hasher.update(item_bytes)
    return hasher.digest()


def compute_data_hash(data: bytes | str | Path | io.IOBase, digest_size = None) -> Hash:
    # centralizing this allows us to keep the hashing func and return type consistent

    if isinstance(data, Path):
        if data.is_file():
            with open(data, 'br') as f:
                data = f.read()
        else:
            raise ValueError(f"No such file {data}")

    elif isinstance(data, io.IOBase):
        data = data.read()  # If it's text io, we convert to bytes in final check

    if isinstance(data, str):
        data = data.encode('utf-8')

    return hashing_func(data, digest_size=digest_size)
