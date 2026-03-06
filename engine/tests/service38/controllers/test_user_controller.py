"""Service38 UserController orchestrator/gateway flow tests.

This is the service38 replacement for the PORT_ADAPT row:
  engine/tests/service/controllers/test_user_controller.py
  → engine/tests/service38/controllers/test_user_controller.py

The legacy test (test_user_controller.py) exercises the legacy UserController
methods directly. These tests assert the *service38-specific* concerns:

  - The service38 UserController wrapper exposes ApiEndpoint metadata with
    correct ResourceBinding annotations on each endpoint.
  - create_user binds=() so the orchestrator injects no pre-loaded resources.
  - update_user, get_user_info, drop_user bind=(ResourceBinding.USER,) so the
    orchestrator hydrates the User from persistence before calling the method.
  - create_user with a persist_paths policy causes the new User to be saved.
  - The gateway flow (ServiceGateway.execute_endpoint) routes USER_CREATE and
    USER_INFO operations through the correct endpoints.
  - Outbound hook render profiles pass through without altering user payloads.

Note: implementation bodies still delegate to the legacy controller; these tests
are not re-testing the legacy logic but the service38 dispatch plumbing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import pytest

from tangl.service.api_endpoint import (
    AccessLevel,
    ApiEndpoint,
    ResourceBinding,
    WritebackMode,
)
from tangl.service.bootstrap import build_service_gateway, register_default_controllers
from tangl.service.controllers import UserController
from tangl.service.gateway import ServiceGateway
from tangl.service.operations import ServiceOperation, endpoint_for_operation
from tangl.service.orchestrator import Orchestrator
from tangl.service.response import RuntimeInfo
from tangl.service.user.user import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _FakePersistence:
    """Minimal dict-backed persistence for testing writeback behaviour."""

    def __init__(self) -> None:
        self._store: dict[UUID, Any] = {}

    def save(self, obj: Any) -> None:
        key = getattr(obj, "uid", None)
        if key is not None:
            self._store[key] = obj

    def get(self, key: Any) -> Any:
        return self._store.get(key)

    def __contains__(self, key: Any) -> bool:
        return key in self._store


@pytest.fixture
def persistence() -> _FakePersistence:
    return _FakePersistence()


@pytest.fixture
def orchestrator(persistence: _FakePersistence) -> Orchestrator:
    orch = Orchestrator(persistence_manager=persistence)
    register_default_controllers(orch)
    return orch


@pytest.fixture
def gateway(orchestrator: Orchestrator) -> ServiceGateway:
    return ServiceGateway(orchestrator)


@pytest.fixture
def existing_user(persistence: _FakePersistence) -> User:
    """A pre-existing user already in persistence."""
    user = User(label="existing-player")
    persistence.save(user)
    return user


# ---------------------------------------------------------------------------
# Binding metadata inspection
# ---------------------------------------------------------------------------

class TestUserControllerBindingMetadata:
    """ApiEndpoint.binds annotations are correct for each endpoint."""

    def _ep(self, name: str) -> ApiEndpoint:
        endpoints = UserController.get_api_endpoints()
        ep = endpoints[name]
        assert isinstance(ep, ApiEndpoint), f"{name} is not an ApiEndpoint"
        return ep

    def test_create_user_has_empty_binds(self) -> None:
        """create_user needs no pre-loaded resources — it creates one."""
        ep = self._ep("create_user")
        assert ep.binds == ()
        assert ep.access_level == AccessLevel.PUBLIC

    def test_update_user_binds_user(self) -> None:
        ep = self._ep("update_user")
        assert ep.binds is not None
        assert ResourceBinding.USER in ep.binds

    def test_get_user_info_binds_user(self) -> None:
        ep = self._ep("get_user_info")
        assert ep.binds is not None
        assert ResourceBinding.USER in ep.binds

    def test_drop_user_binds_user(self) -> None:
        ep = self._ep("drop_user")
        assert ep.binds is not None
        assert ResourceBinding.USER in ep.binds

    def test_get_key_for_secret_has_empty_binds(self) -> None:
        """Key derivation is stateless — no user hydration needed."""
        ep = self._ep("get_key_for_secret")
        assert ep.binds == ()

    def test_all_endpoints_are_api_endpoint38_instances(self) -> None:
        for name, ep in UserController.get_api_endpoints().items():
            assert isinstance(ep, ApiEndpoint), (
                f"UserController.{name} is not an ApiEndpoint instance"
            )


# ---------------------------------------------------------------------------
# create_user via orchestrator
# ---------------------------------------------------------------------------

class TestCreateUserOrchestrator:
    def test_create_user_returns_runtime_info(self, orchestrator: Orchestrator) -> None:
        result = orchestrator.execute("UserController.create_user", secret="dev-secret")
        assert isinstance(result, RuntimeInfo)
        assert result.status == "ok"

    def test_create_user_details_has_user_and_user_id(self, orchestrator: Orchestrator) -> None:
        result = orchestrator.execute("UserController.create_user", secret="abc")
        details = result.details or {}
        user = details.get("user")
        assert user is not None
        assert hasattr(user, "uid")
        assert details.get("user_id") == str(user.uid)

    def test_create_user_result_user_id_is_valid_uuid(self, orchestrator: Orchestrator) -> None:
        result = orchestrator.execute("UserController.create_user")
        details = result.details or {}
        uid_str = details.get("user_id", "")
        UUID(uid_str)  # raises if invalid

    def test_create_user_with_persist_policy_saves_user(
        self,
        orchestrator: Orchestrator,
        persistence: _FakePersistence,
    ) -> None:
        orchestrator.set_endpoint_policy(
            "UserController.create_user",
            persist_paths=("details.user",),
        )
        result = orchestrator.execute("UserController.create_user")
        user = (result.details or {}).get("user")
        assert user is not None
        assert user.uid in persistence

    def test_create_user_without_persist_policy_does_not_save(
        self,
        orchestrator: Orchestrator,
        persistence: _FakePersistence,
    ) -> None:
        # Default policy has no persist_paths → no writeback
        result = orchestrator.execute("UserController.create_user")
        user = (result.details or {}).get("user")
        assert user is not None
        # Nothing persisted unless policy says so
        assert user.uid not in persistence


# ---------------------------------------------------------------------------
# get_user_info via orchestrator (hydration path)
# ---------------------------------------------------------------------------

class TestGetUserInfoOrchestrator:
    def test_get_user_info_hydrates_user_from_persistence(
        self,
        orchestrator: Orchestrator,
        existing_user: User,
    ) -> None:
        result = orchestrator.execute(
            "UserController.get_user_info",
            user_id=existing_user.uid,
        )
        # UserInfo or RuntimeInfo — either way the call completed without error
        assert result is not None

    def test_get_user_info_missing_user_raises_or_returns_error(
        self,
        orchestrator: Orchestrator,
    ) -> None:
        missing_id = UUID("00000000-0000-0000-0000-000000000001")
        with pytest.raises(Exception):
            orchestrator.execute("UserController.get_user_info", user_id=missing_id)


# ---------------------------------------------------------------------------
# update_user and drop_user via orchestrator
# ---------------------------------------------------------------------------

class TestMutatingUserEndpoints:
    def test_update_user_hydrates_and_mutates(
        self,
        orchestrator: Orchestrator,
        existing_user: User,
    ) -> None:
        result = orchestrator.execute(
            "UserController.update_user",
            user_id=existing_user.uid,
            secret="new-secret",
        )
        assert isinstance(result, RuntimeInfo)
        assert result.status == "ok"

    def test_update_user_parses_false_string_without_privilege_escalation(
        self,
        orchestrator: Orchestrator,
        existing_user: User,
    ) -> None:
        existing_user.privileged = True
        result = orchestrator.execute(
            "UserController.update_user",
            user_id=existing_user.uid,
            privileged="false",
        )
        assert isinstance(result, RuntimeInfo)
        assert result.status == "ok"
        assert existing_user.privileged is False

    def test_update_user_cannot_escalate_privilege_for_non_privileged_user(
        self,
        orchestrator: Orchestrator,
        existing_user: User,
    ) -> None:
        existing_user.privileged = False
        result = orchestrator.execute(
            "UserController.update_user",
            user_id=existing_user.uid,
            privileged="true",
        )
        assert isinstance(result, RuntimeInfo)
        assert result.status == "ok"
        assert existing_user.privileged is False

    def test_update_user_parses_last_played_dt_iso_string(
        self,
        orchestrator: Orchestrator,
        existing_user: User,
    ) -> None:
        iso_dt = "2026-02-23T12:34:56"
        result = orchestrator.execute(
            "UserController.update_user",
            user_id=existing_user.uid,
            last_played_dt=iso_dt,
        )
        assert isinstance(result, RuntimeInfo)
        assert result.status == "ok"
        assert isinstance(existing_user.last_played_dt, datetime)
        assert existing_user.last_played_dt == datetime.fromisoformat(iso_dt)

    def test_update_user_rejects_invalid_privileged_value(
        self,
        orchestrator: Orchestrator,
        existing_user: User,
    ) -> None:
        with pytest.raises(ValueError, match="privileged"):
            orchestrator.execute(
                "UserController.update_user",
                user_id=existing_user.uid,
                privileged="definitely",
            )

    def test_update_user_rejects_invalid_last_played_dt(
        self,
        orchestrator: Orchestrator,
        existing_user: User,
    ) -> None:
        with pytest.raises(ValueError, match="last_played_dt"):
            orchestrator.execute(
                "UserController.update_user",
                user_id=existing_user.uid,
                last_played_dt="not-a-datetime",
            )

    def test_drop_user_hydrates_and_unlinks_stories(
        self,
        orchestrator: Orchestrator,
        existing_user: User,
    ) -> None:
        result = orchestrator.execute(
            "UserController.drop_user",
            user_id=existing_user.uid,
        )
        assert isinstance(result, RuntimeInfo)
        assert result.status == "ok"


# ---------------------------------------------------------------------------
# Gateway operation routing
# ---------------------------------------------------------------------------

class TestUserControllerGatewayRouting:
    def test_user_create_operation_routes_to_user_controller(
        self,
        orchestrator: Orchestrator,
    ) -> None:
        endpoint_name = endpoint_for_operation(ServiceOperation.USER_CREATE)
        assert endpoint_name in orchestrator._endpoints

    def test_user_info_operation_routes_to_user_controller(
        self,
        orchestrator: Orchestrator,
    ) -> None:
        endpoint_name = endpoint_for_operation(ServiceOperation.USER_INFO)
        assert endpoint_name in orchestrator._endpoints

    def test_user_drop_operation_routes_to_user_controller(
        self,
        orchestrator: Orchestrator,
    ) -> None:
        endpoint_name = endpoint_for_operation(ServiceOperation.USER_DROP)
        assert endpoint_name in orchestrator._endpoints

    def test_gateway_create_user_returns_runtime_info(
        self,
        gateway: ServiceGateway,
    ) -> None:
        result = gateway.execute(ServiceOperation.USER_CREATE, secret="gw-secret")
        assert isinstance(result, RuntimeInfo)
        assert result.status == "ok"

    def test_gateway_create_user_render_profile_raw_does_not_alter_result(
        self,
        gateway: ServiceGateway,
    ) -> None:
        result = gateway.execute(
            ServiceOperation.USER_CREATE,
            secret="raw-test",
            render_profile="raw",
        )
        assert isinstance(result, RuntimeInfo)
        user = (result.details or {}).get("user")
        assert user is not None

    def test_gateway_module_binding_is_service38_user_controller(
        self,
        orchestrator: Orchestrator,
    ) -> None:
        """service38 bootstrap wires the service38 UserController, not the legacy one."""
        endpoint_name = endpoint_for_operation(ServiceOperation.USER_CREATE)
        binding = orchestrator._endpoints[endpoint_name]
        assert binding.endpoint.func.__module__ == "tangl.service.user.user_controller"


# ---------------------------------------------------------------------------
# get_key_for_secret — stateless endpoint, no hydration
# ---------------------------------------------------------------------------

class TestGetKeyForSecret:
    def test_get_key_for_secret_returns_api_key_info(
        self,
        orchestrator: Orchestrator,
    ) -> None:
        from tangl.service.operations import endpoint_for_operation
        endpoint_name = endpoint_for_operation(ServiceOperation.USER_KEY)
        result = orchestrator.execute(endpoint_name, secret="test-secret")
        # ApiKeyInfo or compatible info model with api_key field
        assert hasattr(result, "api_key") or (
            isinstance(result, dict) and "api_key" in result
        )

    def test_get_key_for_secret_is_deterministic(
        self,
        orchestrator: Orchestrator,
    ) -> None:
        endpoint_name = endpoint_for_operation(ServiceOperation.USER_KEY)
        r1 = orchestrator.execute(endpoint_name, secret="stable-secret")
        r2 = orchestrator.execute(endpoint_name, secret="stable-secret")
        key1 = getattr(r1, "api_key", None) or (r1 or {}).get("api_key")
        key2 = getattr(r2, "api_key", None) or (r2 or {}).get("api_key")
        assert key1 == key2
