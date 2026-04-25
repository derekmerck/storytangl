"""Service export contract tests."""

from __future__ import annotations


def test_service_response_types_importable() -> None:
    from tangl.service.response import (
        AuthoringDiagnostic,
        BadgeListValue,
        FragmentStream,
        InfoModel,
        ItemListValue,
        KvListValue,
        MediaNative,
        NativeResponse,
        PreflightReport,
        ProjectedSection,
        ProjectedState,
        RuntimeEnvelope,
        RuntimeInfo,
        ScalarValue,
        UserSecret,
        coerce_runtime_info,
    )
    from tangl.service.story_info import DefaultStoryInfoProjector, StoryInfoProjector

    assert BadgeListValue is not None
    assert AuthoringDiagnostic is not None
    assert FragmentStream is not None
    assert InfoModel is not None
    assert ItemListValue is not None
    assert KvListValue is not None
    assert MediaNative is not None
    assert NativeResponse is not None
    assert PreflightReport is not None
    assert ProjectedSection is not None
    assert ProjectedState is not None
    assert RuntimeEnvelope is not None
    assert RuntimeInfo is not None
    assert ScalarValue is not None
    assert UserSecret is not None
    assert coerce_runtime_info is not None
    assert DefaultStoryInfoProjector is not None
    assert StoryInfoProjector is not None


def test_service_package_exports_include_manager_first_contract() -> None:
    import tangl.service as service

    expected = {
        "AuthoringDiagnostic",
        "BadgeListValue",
        "BlockingMode",
        "DefaultStoryInfoProjector",
        "FragmentStream",
        "InfoModel",
        "ItemListValue",
        "KvListValue",
        "MediaNative",
        "NativeResponse",
        "PreflightReport",
        "PrimitiveValue",
        "ProjectedItem",
        "ProjectedKVItem",
        "ProjectedSection",
        "ProjectedState",
        "RuntimeEnvelope",
        "RuntimeInfo",
        "RemoteServiceManager",
        "ScalarValue",
        "SectionValue",
        "ServiceAccess",
        "ServiceContext",
        "ServiceManager",
        "ServiceMethodSpec",
        "ServiceSession",
        "ServiceWriteback",
        "StoryInfoProjector",
        "SystemInfo",
        "TableValue",
        "UserAuthInfo",
        "UserInfo",
        "UserSecret",
        "WorldInfo",
        "WorldRegistry",
        "build_service_manager",
        "coerce_runtime_info",
        "get_service_method_spec",
        "service_method",
        "user_id_by_key",
    }

    exported = set(service.__all__)
    assert expected.issubset(exported)
    for name in expected:
        assert getattr(service, name, None) is not None, f"Missing export: {name}"


def test_service_package_does_not_export_removed_gateway_stack() -> None:
    import tangl.service as service

    compatibility = {
        "ApiEndpoint",
        "EndpointPolicy",
        "ExecuteOptions",
        "GatewayExecuteOptions",
        "GatewayRequest",
        "GatewayRestAdapter",
        "Orchestrator",
        "ResourceBinding",
        "ServiceGateway",
        "ServiceOperation",
        "WritebackMode",
        "build_service_gateway",
    }

    for name in compatibility:
        assert not hasattr(service, name), f"Unexpected compatibility export: {name}"
