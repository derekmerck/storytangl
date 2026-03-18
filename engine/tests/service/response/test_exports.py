"""Service export contract tests.

This suite is the service replacement for:
  ``engine/tests/service/response/test_exports.py``
  → ``engine/tests/service/response/test_exports.py``

It verifies that service public exports remain importable and that
``tangl.service.__all__`` advertises the expected compatibility surface.
"""

from __future__ import annotations


def test_service_response_types_importable() -> None:
    from tangl.service.response import (
        BadgeListValue,
        FragmentStream,
        InfoModel,
        ItemListValue,
        KvListValue,
        MediaNative,
        NativeResponse,
        ProjectedSection,
        ProjectedState,
        RuntimeInfo,
        ScalarValue,
        coerce_runtime_info,
    )

    assert BadgeListValue is not None
    assert FragmentStream is not None
    assert InfoModel is not None
    assert ItemListValue is not None
    assert KvListValue is not None
    assert MediaNative is not None
    assert NativeResponse is not None
    assert ProjectedSection is not None
    assert ProjectedState is not None
    assert RuntimeInfo is not None
    assert ScalarValue is not None
    assert coerce_runtime_info is not None


def test_service_package_exports_include_response_and_gateway_contracts() -> None:
    import tangl.service as service

    expected = {
        "ApiEndpoint",
        "EndpointPolicy",
        "ExecuteOptions",
        "FragmentStream",
        "GatewayExecuteOptions",
        "GatewayRequest",
        "GatewayRestAdapter",
        "InfoModel",
        "ItemListValue",
        "KvListValue",
        "MediaNative",
        "NativeResponse",
        "Orchestrator",
        "ProjectedSection",
        "ProjectedState",
        "ResourceBinding",
        "RuntimeInfo",
        "ScalarValue",
        "ServiceGateway",
        "ServiceOperation",
        "UserAuthInfo",
        "WritebackMode",
        "build_service_gateway",
        "coerce_runtime_info",
        "user_id_by_key",
    }

    exported = set(service.__all__)
    assert expected.issubset(exported)
    for name in expected:
        assert getattr(service, name, None) is not None, f"Missing export: {name}"
