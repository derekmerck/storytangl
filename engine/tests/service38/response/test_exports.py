"""Service38 export contract tests.

This suite is the service38 replacement for:
  ``engine/tests/service/response/test_exports.py``
  → ``engine/tests/service38/response/test_exports.py``

It verifies that service38 public exports remain importable and that
``tangl.service38.__all__`` advertises the expected compatibility surface.
"""

from __future__ import annotations


def test_service38_response_types_importable() -> None:
    from tangl.service38.response import (
        FragmentStream,
        InfoModel,
        MediaNative,
        NativeResponse,
        RuntimeInfo,
        coerce_runtime_info,
    )

    assert FragmentStream is not None
    assert InfoModel is not None
    assert MediaNative is not None
    assert NativeResponse is not None
    assert RuntimeInfo is not None
    assert coerce_runtime_info is not None


def test_service38_package_exports_include_response_and_gateway_contracts() -> None:
    import tangl.service38 as service38

    expected = {
        "ApiEndpoint38",
        "EndpointPolicy",
        "ExecuteOptions",
        "FragmentStream",
        "GatewayExecuteOptions",
        "GatewayRequest38",
        "GatewayRestAdapter38",
        "InfoModel",
        "MediaNative",
        "NativeResponse",
        "Orchestrator38",
        "ResourceBinding",
        "RuntimeInfo",
        "ServiceGateway38",
        "ServiceOperation38",
        "UserAuthInfo",
        "WritebackMode",
        "build_service_gateway38",
        "coerce_runtime_info",
        "user_id_by_key",
    }

    exported = set(service38.__all__)
    assert expected.issubset(exported)
    for name in expected:
        assert getattr(service38, name, None) is not None, f"Missing export: {name}"
