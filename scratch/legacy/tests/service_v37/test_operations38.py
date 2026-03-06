from __future__ import annotations

from tangl.service.bootstrap import register_default_controllers
from tangl.service.controllers import DEFAULT_CONTROLLERS
from tangl.service.orchestrator import Orchestrator38
from tangl.service.operations import ServiceOperation38, endpoint_for_operation, operation_for_endpoint


EXPECTED_ENDPOINTS: dict[ServiceOperation38, str] = {
    ServiceOperation38.STORY38_CREATE: "RuntimeController.create_story38",
    ServiceOperation38.STORY38_UPDATE: "RuntimeController.get_story_update38",
    ServiceOperation38.STORY38_DO: "RuntimeController.resolve_choice38",
    ServiceOperation38.STORY38_STATUS: "RuntimeController.get_story_info38",
    ServiceOperation38.STORY38_DROP: "RuntimeController.drop_story38",
    ServiceOperation38.USER_INFO: "UserController.get_user_info",
    ServiceOperation38.USER_CREATE: "UserController.create_user",
    ServiceOperation38.USER_UPDATE: "UserController.update_user",
    ServiceOperation38.USER_DROP: "UserController.drop_user",
    ServiceOperation38.USER_KEY: "UserController.get_key_for_secret",
    ServiceOperation38.WORLD_LIST: "WorldController.list_worlds",
    ServiceOperation38.WORLD_INFO: "WorldController.get_world_info",
    ServiceOperation38.WORLD_MEDIA: "WorldController.get_world_media",
    ServiceOperation38.WORLD_LOAD: "WorldController.load_world",
    ServiceOperation38.WORLD_UNLOAD: "WorldController.unload_world",
    ServiceOperation38.SYSTEM_INFO: "SystemController.get_system_info",
    ServiceOperation38.SYSTEM_RESET: "SystemController.reset_system",
}


def _default_controller_endpoints() -> set[str]:
    endpoints: set[str] = set()
    for controller in DEFAULT_CONTROLLERS:
        for name in controller.get_api_endpoints():
            endpoints.add(f"{controller.__name__}.{name}")
    return endpoints


def test_operation_to_endpoint_mapping_is_stable() -> None:
    assert len(ServiceOperation38) == len(EXPECTED_ENDPOINTS)
    for operation, expected_endpoint in EXPECTED_ENDPOINTS.items():
        assert endpoint_for_operation(operation) == expected_endpoint


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


def test_bootstrap_registers_all_operation_endpoints() -> None:
    orchestrator = Orchestrator38(persistence_manager={})
    register_default_controllers(orchestrator)

    for operation, endpoint_name in EXPECTED_ENDPOINTS.items():
        assert endpoint_for_operation(operation) == endpoint_name
        binding = orchestrator._endpoints[endpoint_name]
        assert binding.endpoint.binds is not None
        assert binding.endpoint.func.__module__.startswith("tangl.")
