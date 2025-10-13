from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

import tangl
import tangl.service
import tangl.utils
import tangl.utils.hash_secret as _hash_secret
from tangl.service.api_endpoint import (
    AccessLevel,
    ApiEndpoint,
    HasApiEndpoints,
    MethodType,
    ResponseType,
)

# ROOT = Path(__file__).resolve().parents[3]
# SERVER_SRC = ROOT / "apps" / "server" / "src"
#
# uuid_stub = types.ModuleType("tangl.utils.uuid_for_secret")
# uuid_stub.uuid_for_key = _hash_secret.uuid_for_key
# uuid_stub.key_for_secret = _hash_secret.key_for_secret
# sys.modules.setdefault("tangl.utils.uuid_for_secret", uuid_stub)
# setattr(tangl.utils, "uuid_for_secret", uuid_stub)
#
# rest_pkg = types.ModuleType("tangl.rest")
# rest_pkg.__path__ = [str(SERVER_SRC / "tangl" / "rest")]  # type: ignore[attr-defined]
# rest_pkg = sys.modules.setdefault("tangl.rest", rest_pkg)
# setattr(tangl, "rest", rest_pkg)
#
# routers_pkg = types.ModuleType("tangl.rest.routers")
# routers_pkg.__path__ = [str(SERVER_SRC / "tangl" / "rest" / "routers")]  # type: ignore[attr-defined]
# routers_pkg = sys.modules.setdefault("tangl.rest.routers", routers_pkg)
# setattr(rest_pkg, "routers", routers_pkg)
#
#
# def load_module(module_name: str, relative_path: str):
#     module_path = SERVER_SRC / relative_path
#     spec = importlib.util.spec_from_file_location(module_name, module_path)
#     module = importlib.util.module_from_spec(spec)
#     assert spec and spec.loader
#     sys.modules[module_name] = module
#     spec.loader.exec_module(module)
#     return module

from tangl.rest import routers
from tangl.rest import dependencies


class _StubSystemController(HasApiEndpoints):
    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.INFO,
        method_type=MethodType.READ,
    )
    def get_system_info(self, **_: object) -> dict[str, object]:  # pragma: no cover - stub
        return {}


class _StubWorldController(HasApiEndpoints):
    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.CONTENT,
        method_type=MethodType.READ,
    )
    def list_worlds(self, **_: object) -> list[object]:  # pragma: no cover - stub
        return []


@pytest.fixture(scope="module")
def dependencies_module() -> tuple[types.ModuleType, types.ModuleType]:
    original_controllers = importlib.import_module("tangl.service.controllers")
    controllers_stub = types.ModuleType("tangl.service.controllers")
    controllers_stub.RuntimeController = original_controllers.RuntimeController
    controllers_stub.UserController = original_controllers.UserController
    controllers_stub.SystemController = _StubSystemController
    controllers_stub.WorldController = _StubWorldController
    sys.modules["tangl.service.controllers"] = controllers_stub
    setattr(tangl.service, "controllers", controllers_stub)

    dependencies = load_module("tangl.rest.dependencies", "tangl/rest/dependencies.py")
    load_module("tangl.rest.routers.story_router", "tangl/rest/routers/story_router.py")
    from tangl.rest.routers import story_router as router_module  # type: ignore[attr-defined]

    yield dependencies, router_module

    dependencies.reset_orchestrator_for_testing()
    sys.modules["tangl.service.controllers"] = original_controllers
    setattr(tangl.service, "controllers", original_controllers)
    sys.modules.pop("tangl.rest.routers.story_router", None)


@pytest.fixture()
def dependencies(dependencies_module: tuple[types.ModuleType, types.ModuleType]) -> types.ModuleType:
    module, _ = dependencies_module
    module.reset_orchestrator_for_testing()
    yield module
    module.reset_orchestrator_for_testing()


@pytest.fixture()
def story_router(dependencies_module: tuple[types.ModuleType, types.ModuleType]):
    return dependencies_module[1]


def test_get_orchestrator_singleton(dependencies: types.ModuleType) -> None:
    orchestrator = dependencies.get_orchestrator()
    assert orchestrator is dependencies.get_orchestrator()
    assert "RuntimeController.get_journal_entries" in orchestrator._endpoints


def test_story_router_uses_orchestrator_dependency(story_router, dependencies) -> None:
    update_route = next(route for route in story_router.router.routes if route.path == "/update")
    dependency_funcs = {dep.call for dep in update_route.dependant.dependencies}
    assert dependencies.get_orchestrator in dependency_funcs
