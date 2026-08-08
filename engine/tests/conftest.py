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


#: Module-level ``BehaviorRegistry`` singletons shared by the whole process.
#:
#: Layers order, registries scope: ``DispatchLayer`` only sorts handlers within a
#: chain, so a handler is visible exactly when the registry holding it is in the
#: chain ``chain_execute_all`` assembles. Registering into one of these therefore
#: mutates global program state, and no layer value contains it.
#:
#: Per-instance registries built by ``default_factory`` (frame/ledger locals, the
#: per-world ``world_domain_dispatch``) are not listed: they die with their owner.
_SHARED_BEHAVIOR_REGISTRIES: tuple[tuple[str, str], ...] = (
    ("tangl.core.dispatch", "dispatch"),
    ("tangl.vm.dispatch", "dispatch"),
    ("tangl.story.dispatch", "story_dispatch"),
    ("tangl.ir.dispatch", "script_dispatch"),
    ("tangl.service.dispatch", "service_info_dispatch"),
    ("tangl.mechanics.sandbox.dispatch", "sandbox_dispatch"),
    ("tangl.media.dispatch", "media_dispatch"),
    ("tangl.media.media_resource.media_provisioning", "on_provision_media"),
    ("tangl.media.media_creators.media_spec", "on_adapt_media_spec"),
    ("tangl.media.media_creators.media_spec", "on_create_media"),
)


def _shared_behavior_registries() -> list:
    """Resolve the shared behavior registries, importing their modules once."""
    from importlib import import_module

    return [
        getattr(import_module(module_name), attr)
        for module_name, attr in _SHARED_BEHAVIOR_REGISTRIES
    ]


@pytest.fixture(autouse=True)
def isolate_behavior_registries() -> None:
    """Undo handler registrations a test *body* makes against shared registries.

    Module-level decorators (``@on_gather_ns``, ``@on_render_text``,
    ``@vm_dispatch.register``, ...) register into process-global singletons, so a
    test that registers a handler otherwise keeps it live for every test that
    follows. Snapshot the member uids, then drop whatever appeared during the
    test.

    Two things this deliberately does not do:

    * It never calls ``clear()``. Production handlers register at import time and
      must survive; only the added-during-this-test diff is removed.
    * It exempts handlers contributed by a module first imported *during* the
      test. World domain modules (``worlds/*/domain.py``) register into the shared
      vm/story registries at import time, but are imported lazily by
      ``WorldCompiler`` rather than at collection. ``importlib.import_module``
      caches, so a second ``compile()`` never re-runs those decorators — removing
      them would break every later test that loads the same world. Import-time
      registration is once-per-process by design, whenever the import happens.
    """
    registries = _shared_behavior_registries()
    snapshots = [(registry, set(registry.members)) for registry in registries]
    modules_before = set(sys.modules)
    yield
    imported_during_test = set(sys.modules) - modules_before
    for registry, known in snapshots:
        for uid in set(registry.members) - known:
            behavior = registry.members[uid]
            origin = getattr(getattr(behavior, "func", None), "__module__", None)
            if origin in imported_during_test:
                continue  # import-time registration; once-per-process by design
            registry.remove(uid)
