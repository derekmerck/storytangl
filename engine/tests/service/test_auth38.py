from __future__ import annotations

from uuid import uuid4

from tangl.service.api_endpoint import AccessLevel
from tangl.service.user.user import User
from tangl.service38.auth import user_id_by_key
from tangl.utils.hash_secret import key_for_secret, uuid_for_key


def test_user_id_by_key_resolves_hash_backed_user_and_populates_index() -> None:
    secret = "story-secret"
    api_key = key_for_secret(secret)
    user = User(uid=uuid4())
    user.set_secret(secret)
    store = {user.uid: user}
    reverse_index: dict[str, object] = {}

    auth = user_id_by_key(api_key, store, reverse_index=reverse_index)

    assert auth is not None
    assert auth.user_id == user.uid
    assert auth.access_level == AccessLevel.USER
    assert reverse_index.get(api_key) == user.uid


def test_user_id_by_key_uses_cached_mapping_when_available() -> None:
    secret = "cached-secret"
    api_key = key_for_secret(secret)
    user = User(uid=uuid4())
    user.set_secret(secret)
    store = {user.uid: user}
    reverse_index: dict[str, object] = {api_key: user.uid}

    auth = user_id_by_key(api_key, store, reverse_index=reverse_index)

    assert auth is not None
    assert auth.user_id == user.uid
    assert auth.access_level == AccessLevel.USER


def test_user_id_by_key_returns_restricted_for_privileged_user() -> None:
    secret = "admin-secret"
    api_key = key_for_secret(secret)
    user = User(uid=uuid4(), privileged=True)
    user.set_secret(secret)
    store = {user.uid: user}

    auth = user_id_by_key(api_key, store)

    assert auth is not None
    assert auth.user_id == user.uid
    assert auth.access_level == AccessLevel.RESTRICTED


def test_user_id_by_key_supports_legacy_uid_by_key_fallback() -> None:
    secret = "legacy-secret"
    api_key = key_for_secret(secret)
    user = User(uid=uuid_for_key(api_key))
    store = {user.uid: user}

    auth = user_id_by_key(api_key, store)

    assert auth is not None
    assert auth.user_id == user.uid
    assert auth.access_level == AccessLevel.USER


def test_user_id_by_key_returns_none_when_unresolved() -> None:
    auth = user_id_by_key(key_for_secret("missing-user"), {})
    assert auth is None
