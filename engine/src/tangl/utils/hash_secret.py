from __future__ import annotations
import base64
import functools
import uuid

from tangl.type_hints import Hash
from tangl.utils.hashing import compute_data_hash


@functools.lru_cache
def hash_for_secret(secret: str) -> Hash:
    # Hash a secret string with salt into a 16 byte digest
    return compute_data_hash(secret, digest_size=16)

def uuid_for_secret(secret: str) -> uuid.UUID:
    # Compute a 16-byte uuid from a secret
    h = hash_for_secret(secret)
    return uuid.UUID(bytes=h[:16])  # 16 bytes in a uuid

def key_for_secret(secret: str) -> str:
    # Compute a b64 encoded string from a secret
    h = hash_for_secret(secret)
    return base64.urlsafe_b64encode(h).decode('utf8')

def uuid_for_key(key: str) -> uuid.UUID:
    # Convert a b64 encoded string into a uuid
    h = base64.urlsafe_b64decode(key)  # convert b64-bytes back into the hash bytes
    return uuid.UUID(bytes=h[:16])
