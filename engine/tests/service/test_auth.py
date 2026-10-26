"""Service auth regression tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from tangl.core import Graph, Registry
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager
from tangl.service.auth import user_id_by_key
from tangl.service.user.user import User
from tangl.story import World
from tangl.utils.hash_secret import key_for_secret, uuid_for_key
from tangl.vm import Ledger


def test_user_id_by_key_requires_persisted_hash_match() -> None:
    persistence = PersistenceManagerFactory.native_in_mem()

    api_key = key_for_secret("expected-secret")
    user = User(uid=uuid_for_key(api_key), label="legacy-shape-user")
    user.set_secret("different-secret")
    persistence.save(user)

    assert user_id_by_key(api_key, persistence) is None


@pytest.mark.parametrize("profile", ["native_in_mem", "unstructured_in_mem", "json_file"])
@pytest.mark.parametrize("ledger_first", [True, False])
def test_auth_reads_matching_users_without_restoring_unavailable_world_ledgers(
    profile: str,
    ledger_first: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(World, "_instances", Registry())
    world = World.from_script_data(script_data={
        "label": "auth_records",
        "metadata": {"start_at": "intro.start"},
        "scenes": {"intro": {"blocks": {"start": {"content": "Start"}}}},
    })
    ledger = Ledger.from_graph(graph=world.create_story("auth_story").graph)
    user = User(privileged=True, current_ledger_id=ledger.uid)
    user.set_secret("expected")
    ledger.user_id = user.uid
    persistence = PersistenceManagerFactory.create_persistence_manager(
        manager_name=profile,
        user_data_path=tmp_path,
    )
    records = [ledger, user] if ledger_first else [user, ledger]
    for record in records:
        persistence.save(record)
    if profile == "json_file":
        persistence = PersistenceManagerFactory.json_file(base_path=tmp_path)
    service = ServiceManager(persistence)
    ids = [record.uid for record in records]
    monkeypatch.setattr(type(persistence.storage), "__iter__", lambda _: iter(ids))
    assert list(persistence) == ids
    World._instances.clear()
    assert World.get_instance(world.label) is None
    restore_ledger = Mock(side_effect=AssertionError("Auth constructed an unrelated Ledger"))
    restore_graph = Mock(side_effect=AssertionError("Auth constructed an unrelated Graph"))
    monkeypatch.setattr(Ledger, "structure", restore_ledger)
    monkeypatch.setattr(Graph, "structure", restore_graph)
    restore_user = Mock(wraps=User.structure)
    monkeypatch.setattr(User, "structure", restore_user)
    monkeypatch.setattr(
        Ledger, "unstructure", Mock(side_effect=AssertionError("Native ledger serialized")),
    )
    monkeypatch.setattr(
        Graph, "unstructure", Mock(side_effect=AssertionError("Native graph serialized")),
    )

    expected_key = key_for_secret("expected")
    assert user.uid != uuid_for_key(expected_key)
    found = user_id_by_key(expected_key, persistence)
    assert found.user_id == user.uid
    assert found.is_privileged is True
    assert restore_user.call_count == (0 if profile == "native_in_mem" else 1)
    restored_users = restore_user.call_count
    assert user_id_by_key(key_for_secret("unknown"), persistence) is None
    assert restore_user.call_count == restored_users
    restored = service.create_user(secret="expected")
    assert restored.details["user_id"] == str(user.uid)
    created = service.create_user(secret="another-player")
    assert created.status == "ok"
    assert created.details["user_id"] != str(user.uid)

    cache = {}
    assert user_id_by_key(expected_key, persistence, reverse_index=cache).user_id == user.uid
    service.update_user(user_id=user.uid, secret="rotated")
    assert user_id_by_key(expected_key, persistence, reverse_index=cache) is None
    assert expected_key not in cache
    rotated = user_id_by_key(key_for_secret("rotated"), persistence, reverse_index=cache)
    assert rotated.user_id == user.uid
    assert rotated.is_privileged is True
    wrong_key = key_for_secret("wrong")
    cache[wrong_key] = ledger.uid
    assert user_id_by_key(wrong_key, persistence, reverse_index=cache) is None
    assert wrong_key not in cache
    restore_ledger.assert_not_called()
    restore_graph.assert_not_called()
