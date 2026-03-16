"""Contract tests for ``tangl.service.api_endpoint``.

This is the service replacement for ``engine/tests/service/test_api_endpoints.py``
(see parity matrix row: PORT_ADAPT → ``engine/tests/service/test_api_endpoint.py``).

The legacy tests validated ``ApiEndpoint.annotate`` decorator plumbing against the
legacy service surface.  These tests validate the *service-specific* additions:

- ``ApiEndpoint.annotate`` stores ``binds``, ``writeback_mode``, ``persist_paths``
- ``ResourceBinding`` enum normalises string inputs
- ``EndpointPolicy`` extracts defaults from an endpoint and merges runtime overrides
- ``WritebackMode`` enum round-trips correctly
- ``ApiEndpoint`` is the canonical endpoint model and preserves the existing
  ``method_type``, ``response_type``, ``access_level``, ``preprocessors``,
  and ``postprocessors`` contracts
- Endpoints missing ``binds`` (i.e. pure legacy endpoints) still have the
  ``_api_endpoint`` attribute and are accepted by the orchestrator

See Also
--------
- ``tangl.service.api_endpoint`` – ``ApiEndpoint``, ``EndpointPolicy``,
  ``ResourceBinding``, ``WritebackMode``
- ``tangl.service.orchestrator.Orchestrator._resolve_hydration_bindings``
- ``engine/tests/service/test_orchestrator38.py`` – integration evidence
"""

from __future__ import annotations

import pytest

from tangl.service.api_endpoint import (
    AccessLevel,
    HasApiEndpoints,
    MethodType,
    ResponseType,
)
from tangl.service.api_endpoint import (
    ApiEndpoint,
    EndpointPolicy,
    ResourceBinding,
    WritebackMode,
)
from tangl.service.orchestrator import Orchestrator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_annotated(
    *,
    binds=None,
    writeback_mode=WritebackMode.AUTO,
    persist_paths=None,
    method_type=MethodType.READ,
    response_type=ResponseType.INFO,
    access_level=AccessLevel.PUBLIC,
    postprocessors=None,
):
    """Return a minimal annotated controller class for inspection."""

    class _Controller(HasApiEndpoints):
        @ApiEndpoint.annotate(
            binds=binds,
            writeback_mode=writeback_mode,
            persist_paths=persist_paths,
            method_type=method_type,
            response_type=response_type,
            access_level=access_level,
            postprocessors=postprocessors,
        )
        def my_endpoint(self) -> dict:
            return {"ok": True}

    return _Controller


# ---------------------------------------------------------------------------
# ApiEndpoint.annotate — basic decorator contract
# ---------------------------------------------------------------------------

class TestApiEndpoint38Annotate:
    def test_decorated_method_has_api_endpoint_attribute(self) -> None:
        ctrl = _make_annotated()
        ep = getattr(ctrl.my_endpoint, "_api_endpoint", None)
        assert ep is not None

    def test_endpoint_is_api_endpoint38_instance(self) -> None:
        ctrl = _make_annotated(binds=(ResourceBinding.USER,))
        ep = ctrl.my_endpoint._api_endpoint
        assert isinstance(ep, ApiEndpoint)

    def test_method_type_is_forwarded(self) -> None:
        ctrl = _make_annotated(method_type=MethodType.UPDATE)
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.method_type is MethodType.UPDATE

    def test_response_type_is_forwarded(self) -> None:
        ctrl = _make_annotated(response_type=ResponseType.RUNTIME)
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.response_type is ResponseType.RUNTIME

    def test_access_level_is_forwarded(self) -> None:
        ctrl = _make_annotated(access_level=AccessLevel.USER)
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.access_level is AccessLevel.USER

    def test_postprocessors_are_forwarded(self) -> None:
        called = []
        def _pp(result):
            called.append(True)
            return result

        ctrl = _make_annotated(postprocessors=[_pp])
        ep = ctrl.my_endpoint._api_endpoint
        assert _pp in (ep.postprocessors or [])

    def test_decorated_method_still_callable(self) -> None:
        ctrl = _make_annotated()
        instance = ctrl()
        result = instance.my_endpoint()
        assert result == {"ok": True}


# ---------------------------------------------------------------------------
# ResourceBinding enum
# ---------------------------------------------------------------------------

class TestResourceBinding:
    def test_standard_variants_exist(self) -> None:
        assert ResourceBinding.USER == "user"
        assert ResourceBinding.LEDGER == "ledger"
        assert ResourceBinding.FRAME == "frame"

    def test_binds_stored_as_tuple_of_resource_binding(self) -> None:
        ctrl = _make_annotated(binds=(ResourceBinding.USER, ResourceBinding.LEDGER))
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.binds == (ResourceBinding.USER, ResourceBinding.LEDGER)

    def test_string_binds_are_normalised_to_enum(self) -> None:
        ctrl = _make_annotated(binds=("user", "ledger"))
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.binds == (ResourceBinding.USER, ResourceBinding.LEDGER)

    def test_mixed_string_and_enum_binds(self) -> None:
        ctrl = _make_annotated(binds=(ResourceBinding.USER, "frame"))
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.binds == (ResourceBinding.USER, ResourceBinding.FRAME)

    def test_empty_binds_tuple(self) -> None:
        ctrl = _make_annotated(binds=())
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.binds == ()

    def test_none_binds_stored_as_none(self) -> None:
        ctrl = _make_annotated(binds=None)
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.binds is None

    def test_invalid_binding_string_raises(self) -> None:
        with pytest.raises((ValueError, KeyError)):
            _make_annotated(binds=("nosuchbinding",))


# ---------------------------------------------------------------------------
# WritebackMode
# ---------------------------------------------------------------------------

class TestWritebackMode:
    def test_auto_is_default(self) -> None:
        ctrl = _make_annotated()
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.writeback_mode is WritebackMode.AUTO

    def test_always_and_never_stored(self) -> None:
        for mode in (WritebackMode.ALWAYS, WritebackMode.NEVER):
            ctrl = _make_annotated(writeback_mode=mode)
            ep = ctrl.my_endpoint._api_endpoint
            assert ep.writeback_mode is mode


# ---------------------------------------------------------------------------
# persist_paths
# ---------------------------------------------------------------------------

class TestPersistPaths:
    def test_no_persist_paths_default_is_empty(self) -> None:
        ctrl = _make_annotated()
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.persist_paths == ()

    def test_persist_paths_stored_as_tuple(self) -> None:
        ctrl = _make_annotated(persist_paths=("details.ledger", "details.user"))
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.persist_paths == ("details.ledger", "details.user")

    def test_bare_string_persist_path_becomes_single_tuple_item(self) -> None:
        ctrl = _make_annotated(persist_paths="details.ledger")
        ep = ctrl.my_endpoint._api_endpoint
        assert ep.persist_paths == ("details.ledger",)


# ---------------------------------------------------------------------------
# EndpointPolicy
# ---------------------------------------------------------------------------

class TestEndpointPolicy:
    def test_from_endpoint_extracts_defaults(self) -> None:
        ctrl = _make_annotated(
            writeback_mode=WritebackMode.ALWAYS,
            persist_paths=("details.ledger",),
        )
        ep = ctrl.my_endpoint._api_endpoint
        policy = EndpointPolicy.from_endpoint(ep)
        assert policy.writeback_mode is WritebackMode.ALWAYS
        assert "details.ledger" in policy.persist_paths

    def test_from_endpoint_legacy_no_fields_defaults_to_auto(self) -> None:
        """A legacy endpoint with no service fields should produce AUTO policy."""
        class _LegacyCtrl(HasApiEndpoints):
            from tangl.service.api_endpoint import ApiEndpoint as _LegacyEP

            @_LegacyEP.annotate(method_type=MethodType.READ, response_type=ResponseType.INFO)
            def legacy(self) -> dict:
                return {}

        ep = _LegacyCtrl.legacy._api_endpoint
        policy = EndpointPolicy.from_endpoint(ep)
        assert policy.writeback_mode is WritebackMode.AUTO
        assert policy.persist_paths == ()

    def test_merged_overrides_mode(self) -> None:
        base = EndpointPolicy(writeback_mode=WritebackMode.AUTO, persist_paths=("x",))
        override = EndpointPolicy(writeback_mode=WritebackMode.ALWAYS)
        merged = base.merged(override)
        assert merged.writeback_mode is WritebackMode.ALWAYS
        assert merged.persist_paths == ("x",)  # paths from base when override empty

    def test_merged_overrides_paths(self) -> None:
        base = EndpointPolicy(writeback_mode=WritebackMode.AUTO, persist_paths=("x",))
        override = EndpointPolicy(writeback_mode=WritebackMode.AUTO, persist_paths=("y", "z"))
        merged = base.merged(override)
        assert merged.persist_paths == ("y", "z")

    def test_merged_with_none_is_identity(self) -> None:
        base = EndpointPolicy(writeback_mode=WritebackMode.NEVER, persist_paths=("a",))
        assert base.merged(None) is base


# ---------------------------------------------------------------------------
# Orchestrator binding inference
# ---------------------------------------------------------------------------

class TestOrchestratorBindingInference:
    """Orchestrator resolves hydration bindings from ApiEndpoint.binds."""

    def test_explicit_binds_used_for_hydration(self) -> None:
        class _Ctrl(HasApiEndpoints):
            @ApiEndpoint.annotate(
                binds=(ResourceBinding.USER,),
                method_type=MethodType.READ,
                response_type=ResponseType.INFO,
            )
            def needs_user(self, user) -> dict:
                return {"user_label": user.label}

        orchestrator = Orchestrator(persistence_manager={})
        orchestrator.register_controller(_Ctrl)
        binding = orchestrator._endpoints["_Ctrl.needs_user"]
        assert ResourceBinding.USER in binding.hydration_bindings

    def test_empty_binds_result_in_no_hydration(self) -> None:
        class _Ctrl(HasApiEndpoints):
            @ApiEndpoint.annotate(
                binds=(),
                method_type=MethodType.READ,
                response_type=ResponseType.INFO,
            )
            def needs_nothing(self) -> dict:
                return {"ok": True}

        orchestrator = Orchestrator(persistence_manager={})
        orchestrator.register_controller(_Ctrl)
        binding = orchestrator._endpoints["_Ctrl.needs_nothing"]
        assert binding.hydration_bindings == ()

    def test_policy_defaults_extracted_from_endpoint(self) -> None:
        class _Ctrl(HasApiEndpoints):
            @ApiEndpoint.annotate(
                binds=(),
                writeback_mode=WritebackMode.NEVER,
                persist_paths=("details.ledger",),
                method_type=MethodType.CREATE,
                response_type=ResponseType.RUNTIME,
            )
            def create_thing(self) -> dict:
                return {}

        orchestrator = Orchestrator(persistence_manager={})
        orchestrator.register_controller(_Ctrl)
        binding = orchestrator._endpoints["_Ctrl.create_thing"]
        assert binding.policy.writeback_mode is WritebackMode.NEVER
        assert "details.ledger" in binding.policy.persist_paths

    def test_set_endpoint_policy_overrides_extracted_defaults(self) -> None:
        class _Ctrl(HasApiEndpoints):
            @ApiEndpoint.annotate(
                binds=(),
                method_type=MethodType.CREATE,
                response_type=ResponseType.RUNTIME,
            )
            def create_thing(self) -> dict:
                return {}

        orchestrator = Orchestrator(persistence_manager={})
        orchestrator.register_controller(_Ctrl)
        orchestrator.set_endpoint_policy(
            "_Ctrl.create_thing",
            writeback_mode=WritebackMode.ALWAYS,
            persist_paths=("result",),
        )
        binding = orchestrator._endpoints["_Ctrl.create_thing"]
        assert binding.policy.writeback_mode is WritebackMode.ALWAYS
        assert binding.policy.persist_paths == ("result",)

    def test_get_api_endpoints_returns_all_decorated_methods(self) -> None:
        class _Multi(HasApiEndpoints):
            @ApiEndpoint.annotate(binds=(), response_type=ResponseType.INFO, method_type=MethodType.READ)
            def alpha(self) -> dict:
                return {}

            @ApiEndpoint.annotate(binds=(), response_type=ResponseType.INFO, method_type=MethodType.READ)
            def beta(self) -> dict:
                return {}

        endpoints = _Multi.get_api_endpoints()
        assert "alpha" in endpoints
        assert "beta" in endpoints
        assert len(endpoints) >= 2
