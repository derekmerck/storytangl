from __future__ import annotations
import base64
import functools
from hashlib import sha224
import uuid
import logging

from tangl.config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

salt = settings.get("service.local.salt", "%s3krit s4Lt%")
logger.debug( f"hashing with salt: {salt}" )

@functools.lru_cache
def hash_for_secret(secret: str) -> bytes:
    # Hash a secret string with salt
    b = (secret + salt).encode('utf8')
    h = sha224(b)
    return h.digest()

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
    h = base64.urlsafe_b64decode(key)  # convert utf8 to b4-bytes
    return uuid.UUID(bytes=h[:16])
