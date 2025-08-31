import json
from hashlib import sha224

try:
    from tangl.config import settings
    HASHING_SALT = settings.hashing_salt
except (ImportError, AttributeError):
    # Fallback
    HASHING_SALT = b'<!--2t0ryT4n5L--/>'

def hashing_func(*data, salt=HASHING_SALT) -> bytes:
    hasher = sha224(salt)
    for item in data:
        if isinstance(item, bytes):
            item_bytes = item
        elif x := getattr(item, 'bytes', None):
            # uids and such
            item_bytes = x
        elif x := getattr(item, 'to_bytes', None):
            # ints
            item_bytes = x.to_bytes(4)
        elif isinstance(item, str):
            item_bytes = item.encode('utf-8')
        elif isinstance(item, dict):
            # unstructured state data
            item_bytes = json.dumps(item, default=str).encode('utf-8')
        else:
            # Use bytes from the built-in hash
            item_bytes = hash(item).to_bytes(4)
        hasher.update(item_bytes)
    return hasher.digest()

