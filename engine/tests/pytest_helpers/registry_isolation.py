"""Snapshot and restore the process-global behavior registries.

Layers order, registries scope: ``DispatchLayer`` is only the first element of
``Behavior.sort_key``, so a handler is visible exactly while the registry holding
it is in the chain ``chain_execute_all`` assembles. Registering into one of the
module-level singletons below is therefore global mutation, and no layer value
contains it.

Used by the autouse ``isolate_behavior_registries`` fixture in
``engine/tests/conftest.py``. Exposed here rather than inlined there so the
mechanism can be exercised directly by a test instead of only through
declaration-ordered side effects.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from importlib import import_module
from typing import Iterator

from tangl.core import BehaviorRegistry

#: ``(module, attribute)`` for every ``BehaviorRegistry`` singleton shared by the
#: whole process.
#:
#: Per-instance registries built by ``default_factory`` (frame/ledger locals, the
#: per-world ``world_domain_dispatch``) are excluded: they die with their owner.
SHARED_BEHAVIOR_REGISTRIES: tuple[tuple[str, str], ...] = (
    ("tangl.core.dispatch", "dispatch"),
    ("tangl.vm.dispatch", "dispatch"),
    ("tangl.story.dispatch", "story_dispatch"),
    ("tangl.service.dispatch", "service_info_dispatch"),
    ("tangl.mechanics.sandbox.dispatch", "sandbox_dispatch"),
    ("tangl.media.dispatch", "media_dispatch"),
    ("tangl.media.media_resource.media_provisioning", "on_provision_media"),
    ("tangl.media.media_creators.media_spec", "on_adapt_media_spec"),
    ("tangl.media.media_creators.media_spec", "on_create_media"),
)


def shared_behavior_registries() -> list[BehaviorRegistry]:
    """Resolve the shared registries, importing their modules on first use."""
    return [
        getattr(import_module(module_name), attr)
        for module_name, attr in SHARED_BEHAVIOR_REGISTRIES
    ]


@contextmanager
def restore_shared_behavior_registries() -> Iterator[None]:
    """Remove handlers registered by the enclosed block's own code.

    Two things this deliberately does not do:

    * It never calls ``clear()``. Production handlers register at import time and
      must survive; only the added-inside-the-block diff is removed.
    * It exempts handlers contributed by a module first imported *inside* the
      block. World domain modules (``worlds/*/domain.py``) register into the
      shared vm/story registries at import time, but ``WorldCompiler`` imports
      them lazily rather than at collection. ``importlib.import_module`` caches,
      so a second ``compile()`` never re-runs those decorators — removing them
      would break every later test that loads the same world. Import-time
      registration is once-per-process by design, whenever the import happens.

    Known limitation. The exemption keys on the handler's defining module, not on
    a registration timestamp, so it is loose in one direction: a handler defined
    in a module first imported inside the block is kept even when the *test body*
    is what registered it (``import probe; on_gather_ns(probe.handler)``).
    Tightening that needs a registration-time hook — patching
    ``BehaviorRegistry.add``, which ``_wrap_inline`` already bypasses at
    ``core/behavior.py:396``, plus an import-depth flag on every test — which is a
    lot of global machinery for a pattern nothing in the tree uses. Callers that
    deliberately import a registering module inside the block are responsible for
    removing its handlers themselves; the contract test in
    ``test_registry_isolation.py`` does exactly that.
    """
    registries = shared_behavior_registries()
    snapshots = [(registry, set(registry.members)) for registry in registries]
    modules_before = set(sys.modules)
    try:
        yield
    finally:
        imported_inside = set(sys.modules) - modules_before
        for registry, known in snapshots:
            for uid in set(registry.members) - known:
                behavior = registry.members[uid]
                origin = getattr(getattr(behavior, "func", None), "__module__", None)
                if origin in imported_inside:
                    continue  # import-time registration; once-per-process by design
                registry.remove(uid)
