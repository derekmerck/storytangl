"""Authentication helpers for service transports."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import MutableMapping, cast
from uuid import UUID

from tangl.persistence import PersistenceManager
from tangl.service.user.user import User


@dataclass(frozen=True)
class UserAuthInfo:
    """Authenticated identity and the user's current privilege flag."""

    user_id: UUID
    is_privileged: bool = False


def user_id_by_key(
    api_key: str,
    persistence: PersistenceManager,
    *,
    reverse_index: MutableMapping[str, UUID] | None = None,
) -> UserAuthInfo | None:
    """Find a persisted credential match without restoring unrelated records.

    Cached UIDs are hints: the current stored hash is checked on every lookup.
    Constructor-form records are decoded first; only a matching User is restored
    through the manager's ordinary load path. Native profiles already contain objects.
    """
    if not api_key:
        return None
    expected_hash = _decode_key_hash(api_key)
    if expected_hash is None:
        return None

    if reverse_index is not None:
        cached_id = reverse_index.get(api_key)
        if cached_id is not None and cached_id in persistence:
            user = _read_matching_user(persistence, cached_id, expected_hash)
            if user is not None:
                return UserAuthInfo(user_id=user.uid, is_privileged=user.privileged)
        reverse_index.pop(api_key, None)

    for uid in persistence:
        user = _read_matching_user(persistence, uid, expected_hash)
        if user is None:
            continue
        if reverse_index is not None:
            reverse_index[api_key] = user.uid
        return UserAuthInfo(user_id=user.uid, is_privileged=user.privileged)
    return None


def _read_matching_user(
    persistence: PersistenceManager,
    uid: UUID,
    expected_hash: bytes,
) -> User | None:
    record = persistence.read_record(uid)
    if isinstance(record, User):
        user = record
    elif isinstance(record, dict):
        kind = record.get("kind")
        if isinstance(kind, str):
            kind = persistence.kind_map.get(kind)
        if not isinstance(kind, type) or not issubclass(kind, User):
            return None
        if record.get("content_hash") != expected_hash:
            return None
        user = cast(User, persistence.load(uid))
    else:
        return None
    return user if user.content_hash == expected_hash else None


def _decode_key_hash(api_key: str) -> bytes | None:
    missing_padding = (-len(api_key)) % 4
    padded_key = api_key + ("=" * missing_padding)
    try:
        return base64.urlsafe_b64decode(padded_key)
    except (ValueError, TypeError):
        return None


__all__ = ["UserAuthInfo", "user_id_by_key"]
