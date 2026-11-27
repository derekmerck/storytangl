"""JSON value encoding shared by persistence and constructor-form hashes."""

import json
from datetime import datetime
from enum import Enum
from uuid import UUID

TYPE_KEY = "__tangl_type__"
BYTES_TYPE = "bytes"
HEX_KEY = "hex"


def encode_json_value(value: object) -> object:
    """Encode values outside JSON's native types."""
    if isinstance(value, (set, frozenset)):
        return sorted(
            value,
            key=lambda member: json.dumps(member, default=encode_json_value, sort_keys=True),
        )
    if isinstance(value, type):
        return f"{value.__module__}.{value.__name__}"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return value.hex
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {TYPE_KEY: BYTES_TYPE, HEX_KEY: bytes(value).hex()}
    return str(value)
