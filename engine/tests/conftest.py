import logging
import sys
import types

try:  # pragma: no cover - optional dependency shim for tests
    import wrapt  # type: ignore  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - executed in CI environment
    class _ObjectProxy:
        """Minimal stand-in for :class:`wrapt.ObjectProxy` used in tests."""

        def __init__(self, wrapped):
            object.__setattr__(self, "__wrapped__", wrapped)

        def __getattr__(self, name):
            return getattr(object.__getattribute__(self, "__wrapped__"), name)

        def __setattr__(self, name, value):
            if name == "__wrapped__" or name.startswith("_self_"):
                object.__setattr__(self, name, value)
            else:
                setattr(object.__getattribute__(self, "__wrapped__"), name, value)

        def __delattr__(self, name):
            if name == "__wrapped__" or name.startswith("_self_"):
                object.__delattr__(self, name)
            else:
                delattr(object.__getattribute__(self, "__wrapped__"), name)

    stub = types.SimpleNamespace(ObjectProxy=_ObjectProxy)
    sys.modules["wrapt"] = stub

logging.basicConfig(level=logging.WARNING)
logging.getLogger("markdown_it").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)


def _quiet_test_loggers(*names: str, level: int = logging.WARNING) -> None:
    """Clamp especially noisy module loggers during normal pytest runs."""
    for name in names:
        logging.getLogger(name).setLevel(level)


_quiet_test_loggers(
    "tangl.core.behavior",
    "tangl.core.entity.match",
    "tangl.vm.system_handlers",
    "tangl.mechanics.games.handlers",
)

from tangl.type_hints import StringMap
from tangl.core import Graph, Node, Subgraph

from pydantic import create_model, Field

import pytest

_dict_field = StringMap, Field(default_factory=dict)

GraphL_ = create_model("GraphL", __base__=Graph, locals=_dict_field)

@pytest.fixture(scope="session")
def GraphL():
    return GraphL_

SubgraphL_ = create_model("SubgraphL", __base__=Subgraph, locals=_dict_field)
@pytest.fixture(scope="session")
def SubgraphL():
    return SubgraphL_

NodeL_ = create_model("NodeL", __base__=Node, locals=_dict_field)
@pytest.fixture(scope="session")
def NodeL():
    return NodeL_

from pathlib import Path

@pytest.fixture(scope="session")
def resources_dir():
    return Path(__file__).resolve().parent / "resources"

sys.path.append(str(Path(__file__).resolve().parent / "pytest_helpers"))
from pytest_helpers.fragment_helpers import extract_fragments as extract_fragments_, extract_all_choices as extract_all_choices_

@pytest.fixture(scope="session")
def extract_all_choices():
    return extract_all_choices_

@pytest.fixture(scope="session")
def extract_fragments():
    return extract_fragments_


@pytest.fixture(autouse=True)
def clear_story_world_instances() -> None:
    """Keep story world singletons isolated between tests."""
    from tangl.service.world_registry import clear_discovered_world_registries
    from tangl.story import World

    clear_discovered_world_registries()
    World.clear_instances()
    yield
    World.clear_instances()
    clear_discovered_world_registries()


@pytest.fixture(autouse=True)
def isolate_behavior_registries() -> None:
    """Undo handler registrations a test *body* makes against shared registries.

    Module-level decorators (``@on_gather_ns``, ``@on_render_text``,
    ``@vm_dispatch.register``, ...) register into process-global singletons, so a
    test that registers a handler otherwise keeps it live for every test that
    follows. See `pytest_helpers.registry_isolation` for what is snapshotted and
    why import-time registration is exempt.
    """
    from pytest_helpers.registry_isolation import restore_shared_behavior_registries

    with restore_shared_behavior_registries():
        yield
