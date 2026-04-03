"""Tests for the remote REST-backed service manager.

Organized by functionality:
- Transport/auth: request mapping and auth behavior
- Response hydration: runtime envelope and runtime-info decoding
- Bootstrap: local versus remote manager selection
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
import requests

from tangl.core import BaseFragment
from tangl.journal.fragments import BlockFragment, ChoiceFragment
from tangl.persistence import PersistenceManagerFactory
from tangl.service.bootstrap import build_service_manager
from tangl.service.exceptions import AccessDeniedError, InvalidOperationError, ServiceError
from tangl.service.remote_service_manager import RemoteServiceManager
from tangl.service.service_manager import ServiceManager


class StubResponse:
    """Minimal response stub for remote-manager tests."""

    def __init__(
        self,
        status_code: int,
        payload: object,
        *,
        reason: str = "OK",
        json_error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.reason = reason
        self._json_error = json_error

    def json(self) -> object:
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class RecordingSession:
    """Record outbound requests and replay queued responses."""

    def __init__(self, behaviors: list[StubResponse | Exception]) -> None:
        self.behaviors = list(behaviors)
        self.calls: list[dict[str, object]] = []

    def request(
        self,
        *,
        method: str,
        url: str,
        params: dict[str, object] | None = None,
        json: object | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> StubResponse:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        if not self.behaviors:
            raise AssertionError("Unexpected remote request")
        behavior = self.behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


def _runtime_envelope_payload() -> dict[str, object]:
    choice_id = uuid4()
    return {
        "cursor_id": str(uuid4()),
        "step": 3,
        "fragments": [
            {
                "fragment_type": "block",
                "content": "Start",
                "choices": [
                    {
                        "fragment_type": "choice",
                        "edge_id": str(choice_id),
                        "content": "Continue",
                        "text": "Continue",
                        "active": True,
                    }
                ],
            },
            {
                "fragment_type": "mystery",
                "foo": "bar",
            },
        ],
        "last_redirect": None,
        "redirect_trace": [],
        "metadata": {
            "ledger_id": str(uuid4()),
            "world_id": "demo_world",
        },
    }


class TestRemoteTransportAndAuth:
    """Tests for request routing and auth semantics."""

    def test_public_call_works_without_auth(self) -> None:
        session = RecordingSession(
            [
                StubResponse(
                    200,
                    [{"label": "demo", "title": "Demo", "author": "Tests"}],
                )
            ]
        )
        manager = RemoteServiceManager(
            "https://example.test/api/v2",
            session=session,
        )

        worlds = manager.list_worlds()

        assert [world.label for world in worlds] == ["demo"]
        assert session.calls[0]["url"] == "https://example.test/api/v2/system/worlds"
        assert session.calls[0]["headers"] is None
        assert session.calls[0]["params"] == {"render_profile": "raw"}

    def test_protected_call_without_auth_fails_before_request(self) -> None:
        session = RecordingSession([])
        manager = RemoteServiceManager("https://example.test/api/v2", session=session)

        with pytest.raises(AccessDeniedError, match="bound API key"):
            manager.create_story(user_id=uuid4(), world_id="demo_world")

        assert not session.calls

    def test_secret_derived_key_that_cannot_auth_maps_to_access_denied(self) -> None:
        session = RecordingSession(
            [
                StubResponse(200, {"api_key": "derived-key", "user_secret": "bad-secret"}),
                StubResponse(401, {"detail": "Invalid API key"}, reason="Unauthorized"),
            ]
        )
        manager = RemoteServiceManager(
            "https://example.test/api/v2",
            secret="bad-secret",
            session=session,
        )

        with pytest.raises(AccessDeniedError, match="Invalid API key"):
            manager.create_story(user_id=uuid4(), world_id="demo_world")

        assert session.calls[0]["url"] == "https://example.test/api/v2/system/secret"
        assert session.calls[1]["headers"] == {
            "X-API-Key": "derived-key",
            "api-key": "derived-key",
        }

    def test_bad_api_key_maps_to_access_denied(self) -> None:
        session = RecordingSession(
            [StubResponse(401, {"detail": "Invalid API key"}, reason="Unauthorized")]
        )
        manager = RemoteServiceManager(
            "https://example.test/api/v2",
            api_key="bad-key",
            session=session,
        )

        with pytest.raises(AccessDeniedError, match="Invalid API key"):
            manager.get_story_update(user_id=uuid4())

        assert session.calls[0]["headers"] == {
            "X-API-Key": "bad-key",
            "api-key": "bad-key",
        }

    def test_create_user_refreshes_auth_and_supports_immediate_story_creation(self) -> None:
        user_id = uuid4()
        session = RecordingSession(
            [
                StubResponse(
                    200,
                    {
                        "api_key": "new-key",
                        "user_secret": "new-secret",
                    },
                ),
                StubResponse(
                    200,
                    {
                        "user_id": str(user_id),
                        "user_secret": "new-secret",
                        "created_dt": "2026-01-01T00:00:00",
                        "worlds_played": [],
                    },
                ),
                StubResponse(200, _runtime_envelope_payload()),
            ]
        )
        manager = RemoteServiceManager("https://example.test/api/v2", session=session)

        created = manager.create_user(secret="new-secret")
        envelope = manager.create_story(user_id=user_id, world_id="demo_world")

        assert created.details == {"user_id": str(user_id)}
        assert envelope.metadata["world_id"] == "demo_world"
        assert session.calls[1]["headers"] == {
            "X-API-Key": "new-key",
            "api-key": "new-key",
        }
        assert session.calls[2]["headers"] == {
            "X-API-Key": "new-key",
            "api-key": "new-key",
        }

    def test_update_user_refreshes_auth_and_does_not_reuse_old_key(self) -> None:
        user_id = uuid4()
        session = RecordingSession(
            [
                StubResponse(
                    200,
                    {
                        "api_key": "new-key",
                        "user_secret": "new-secret",
                        "user_id": str(user_id),
                    },
                ),
                StubResponse(200, _runtime_envelope_payload()),
            ]
        )
        manager = RemoteServiceManager(
            "https://example.test/api/v2",
            api_key="old-key",
            session=session,
        )
        manager._bound_user_id = user_id

        updated = manager.update_user(user_id=user_id, secret="new-secret")
        manager.create_story(user_id=user_id, world_id="demo_world")

        assert updated.details == {
            "user_id": str(user_id),
            "api_key": "new-key",
        }
        assert session.calls[0]["headers"] == {
            "X-API-Key": "old-key",
            "api-key": "old-key",
        }
        assert session.calls[1]["headers"] == {
            "X-API-Key": "new-key",
            "api-key": "new-key",
        }

    def test_update_user_rejects_non_secret_updates(self) -> None:
        manager = RemoteServiceManager("https://example.test/api/v2", api_key="bound-key")
        manager._bound_user_id = uuid4()

        with pytest.raises(InvalidOperationError, match="does not support arguments"):
            manager.update_user(user_id=manager._bound_user_id, last_played_dt="2026-01-01")


class TestRemoteResponseHydration:
    """Tests for typed response decoding from REST payloads."""

    def test_story_update_decodes_runtime_envelope_and_fragments(self) -> None:
        user_id = uuid4()
        session = RecordingSession([StubResponse(200, _runtime_envelope_payload())])
        manager = RemoteServiceManager(
            "https://example.test/api/v2",
            api_key="bound-key",
            session=session,
        )
        manager._bound_user_id = user_id

        envelope = manager.get_story_update(user_id=user_id, since_step=2, limit=5)

        assert isinstance(envelope.fragments[0], BlockFragment)
        assert isinstance(envelope.fragments[0].choices[0], ChoiceFragment)
        assert isinstance(envelope.fragments[1], BaseFragment)
        assert envelope.fragments[1].fragment_type == "mystery"
        assert envelope.fragments[1].content == {"fragment_type": "mystery", "foo": "bar"}
        assert session.calls[0]["params"] == {
            "limit": 5,
            "since_step": 2,
            "render_profile": "raw",
        }

    def test_drop_story_reassembles_flattened_runtime_info_details(self) -> None:
        user_id = uuid4()
        session = RecordingSession(
            [
                StubResponse(
                    200,
                    {
                        "status": "ok",
                        "message": "Story dropped",
                        "archived": True,
                        "dropped_ledger_id": "ledger-123",
                        "persistence_deleted": False,
                    },
                )
            ]
        )
        manager = RemoteServiceManager(
            "https://example.test/api/v2",
            api_key="bound-key",
            session=session,
        )
        manager._bound_user_id = user_id

        result = manager.drop_story(user_id=user_id, archive=True)

        assert result.status == "ok"
        assert result.details == {
            "archived": True,
            "dropped_ledger_id": "ledger-123",
            "persistence_deleted": False,
        }

    def test_invalid_known_fragment_payload_is_a_decode_error(self) -> None:
        user_id = uuid4()
        session = RecordingSession(
            [
                StubResponse(
                    200,
                    {
                        "cursor_id": str(uuid4()),
                        "step": 1,
                        "fragments": [{"fragment_type": "block", "choices": "not-a-list"}],
                        "metadata": {},
                    },
                )
            ]
        )
        manager = RemoteServiceManager(
            "https://example.test/api/v2",
            api_key="bound-key",
            session=session,
        )
        manager._bound_user_id = user_id

        with pytest.raises(ServiceError, match="invalid block fragment payload"):
            manager.get_story_update(user_id=user_id)

    def test_transport_failure_maps_to_service_error(self) -> None:
        session = RecordingSession([requests.ConnectionError("offline")])
        manager = RemoteServiceManager(
            "https://example.test/api/v2",
            api_key="bound-key",
            session=session,
        )

        with pytest.raises(ServiceError, match="request failed"):
            manager.get_system_info()


class TestRemoteBootstrap:
    """Tests for manager selection in bootstrap."""

    def test_build_service_manager_returns_local_manager_by_default(self) -> None:
        persistence = PersistenceManagerFactory.native_in_mem()

        manager = build_service_manager(persistence)

        assert isinstance(manager, ServiceManager)
        assert not isinstance(manager, RemoteServiceManager)
        assert manager.persistence is persistence

    def test_build_service_manager_returns_remote_manager_when_requested(self) -> None:
        persistence = PersistenceManagerFactory.native_in_mem()

        manager = build_service_manager(
            persistence,
            backend="remote",
            api_url="https://example.test/api/v2",
            api_key="bound-key",
        )

        assert isinstance(manager, RemoteServiceManager)
        assert manager.persistence is persistence
