"""Authentication helpers for service38 transports."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, MutableMapping
from uuid import UUID

from .api_endpoint import AccessLevel
from tangl.utils.hash_secret import uuid_for_key


@dataclass(frozen=True)
class UserAuthInfo:
    """Resolved authentication context for a user-bound request."""

    user_id: UUID
    access_level: AccessLevel


def user_id_by_key(
    api_key: str,
    persistence: Any,
    *,
    reverse_index: MutableMapping[str, UUID] | None = None,
) -> UserAuthInfo | None:
    """Resolve ``api_key`` to :class:`UserAuthInfo` when possible.

    Returns
    -------
    UserAuthInfo | None
        ``UserAuthInfo`` when the key resolves; otherwise ``None``.

    Lookup order:
    1) reverse index cache (if provided),
    2) persistence scan for matching ``content_hash``,
    3) legacy fallback ``uuid_for_key(api_key)``.
    """

    if not api_key or persistence is None:
        return None

    expected_hash = _decode_key_hash(api_key)
    if expected_hash is None:
        return None

    if reverse_index is not None:
        cached_user = _get_from_persistence(persistence, reverse_index.get(api_key))
        if _user_matches_hash(cached_user, expected_hash):
            return _auth_info_from_user(cached_user)
        reverse_index.pop(api_key, None)

    for candidate in _iter_persistence_values(persistence):
        if not _user_matches_hash(candidate, expected_hash):
            continue
        if reverse_index is not None:
            reverse_index[api_key] = candidate.uid
        return _auth_info_from_user(candidate)

    # Compatibility path for older "uid derived from key" workflows.
    try:
        legacy_uid = uuid_for_key(api_key)
    except (ValueError, TypeError):
        return None
    legacy_user = _get_from_persistence(persistence, legacy_uid)
    if _looks_like_user(legacy_user):
        if reverse_index is not None:
            reverse_index[api_key] = legacy_uid
        return _auth_info_from_user(legacy_user)

    return None


def _auth_info_from_user(user: Any) -> UserAuthInfo:
    access_level = AccessLevel.RESTRICTED if bool(getattr(user, "privileged", False)) else AccessLevel.USER
    return UserAuthInfo(user_id=user.uid, access_level=access_level)


def _decode_key_hash(api_key: str) -> bytes | None:
    missing_padding = (-len(api_key)) % 4
    padded_key = api_key + ("=" * missing_padding)
    try:
        return base64.urlsafe_b64decode(padded_key)
    except (ValueError, TypeError):
        return None


def _iter_persistence_values(persistence: Any) -> Iterable[Any]:
    values = getattr(persistence, "values", None)
    if callable(values):
        yield from values()
        return

    if isinstance(persistence, Mapping):
        yield from persistence.values()
        return

    for key in persistence:
        item = _get_from_persistence(persistence, key)
        if item is not None:
            yield item


def _get_from_persistence(persistence: Any, identifier: Any) -> Any:
    if identifier is None:
        return None

    getter = getattr(persistence, "get", None)
    if callable(getter):
        return getter(identifier)

    try:
        return persistence[identifier]
    except KeyError:
        return None


def _normalize_hash(value: Any) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        try:
            return bytes.fromhex(value)
        except ValueError:
            return None
    return None


def _looks_like_user(value: Any) -> bool:
    return (
        value is not None
        and hasattr(value, "uid")
        and hasattr(value, "current_ledger_id")
    )


def _user_matches_hash(candidate: Any, expected_hash: bytes) -> bool:
    if not _looks_like_user(candidate):
        return False
    actual_hash = _normalize_hash(getattr(candidate, "content_hash", None))
    return actual_hash == expected_hash


__all__ = ["UserAuthInfo", "user_id_by_key"]
