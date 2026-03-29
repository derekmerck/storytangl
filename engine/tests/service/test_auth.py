"""Service auth regression tests."""

from __future__ import annotations

from tangl.persistence import PersistenceManagerFactory
from tangl.service.auth import user_id_by_key
from tangl.service.user.user import User
from tangl.utils.hash_secret import key_for_secret, uuid_for_key


def test_user_id_by_key_requires_persisted_hash_match() -> None:
    persistence = PersistenceManagerFactory.native_in_mem()

    api_key = key_for_secret("expected-secret")
    user = User(uid=uuid_for_key(api_key), label="legacy-shape-user")
    user.set_secret("different-secret")
    persistence.save(user)

    assert user_id_by_key(api_key, persistence) is None
