from __future__ import annotations

from tangl.service38.bootstrap import register_default_controllers
from tangl.service38.controllers import DEFAULT_CONTROLLERS
from tangl.service38.orchestrator import Orchestrator38
from tangl.service38.operations import ServiceOperation38, endpoint_for_operation, operation_for_endpoint


def _default_controller_endpoints() -> set[str]:
    endpoints: set[str] = set()
    for controller in DEFAULT_CONTROLLERS:
        for name in controller.get_api_endpoints():
            endpoints.add(f"{controller.__name__}.{name}")
    return endpoints


def test_service_operation_endpoints_exist_on_default_controller_set() -> None:
    known_endpoints = _default_controller_endpoints()
    missing: list[tuple[str, str]] = []

    for operation in ServiceOperation38:
        endpoint_name = endpoint_for_operation(operation)
        if endpoint_name not in known_endpoints:
            missing.append((operation.value, endpoint_name))

    assert not missing, f"Missing operation mappings: {missing}"


def test_operation_endpoint_round_trip_mapping() -> None:
    for operation in ServiceOperation38:
        endpoint_name = endpoint_for_operation(operation)
        assert operation_for_endpoint(endpoint_name) == operation


def test_bootstrap_uses_service38_controller_overrides_for_operation_endpoints() -> None:
    orchestrator = Orchestrator38(persistence_manager={})
    register_default_controllers(orchestrator)

    for operation in ServiceOperation38:
        endpoint_name = endpoint_for_operation(operation)
        binding = orchestrator._endpoints[endpoint_name]

        assert binding.endpoint.func.__module__ == "tangl.service38.controllers"
        assert binding.endpoint.binds is not None
