from __future__ import annotations

import io
import json
import logging
from hashlib import blake2b, sha224
from pathlib import Path
from typing import Any

from tangl.type_hints import Hash   # bytes

try:
    from tangl.config import settings
    HASHING_SALT = settings.service.salt.encode('utf-8')
except (ImportError, AttributeError):
    # Fallback
    HASHING_SALT = b'==$t0ryT4nG1-3=='

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

logger.debug( "Hashing with salt: %s", HASHING_SALT )

# Sets and JSON mapping keys are ordered for hashing. Arbitrary fallback Python
# objects still use str(); durable callers must explicitly encode those values.


def _hash_json_default(value: Any) -> str | list[Any]:
    """Order unordered collections, including mixed and nested member types."""
    if isinstance(value, (set, frozenset)):
        return sorted(
            value,
            key=lambda member: json.dumps(member, default=_hash_json_default, sort_keys=True),
        )
    return str(value)


def hashing_func(
    *data: Any, salt: bytes = HASHING_SALT, digest_size: int | None = None,
) -> Hash:
    """Hash values with stable unordered collection encoding, preserving sequence order."""

    if digest_size is None:
        # legacy, slightly more secure but can probably replace with blake
        # for speed and consistency
        hasher = sha224()
        hasher.update(salt)
    else:
        # provides digest size for creating ints or uids without truncating
        if len(salt) > 16:
            salt = salt[:16]
        hasher = blake2b(digest_size=digest_size, salt=salt)

    for item in data:
        if isinstance(item, bytes):
            item_bytes = item
        elif hasattr(item, 'bytes'):
            item_bytes = item.bytes
        elif isinstance(item, int):
            # 8 bytes is enough for seeds; change if you need larger state
            item_bytes = item.to_bytes(8, byteorder="big", signed=True)
        elif isinstance(item, str):
            item_bytes = item.encode('utf-8')
        elif isinstance(item, (dict, set, frozenset)):
            item_bytes = json.dumps(
                item, default=_hash_json_default, sort_keys=True,
            ).encode("utf-8")
        else:
            item_bytes = hash(item).to_bytes(8, byteorder="big", signed=True)
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
