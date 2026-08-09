"""Contract tests for shared behavior-registry isolation.

Covers `pytest_helpers.registry_isolation` and the autouse
``isolate_behavior_registries`` fixture in this directory's ``conftest.py``.
The fixture exists because ``DispatchLayer`` confers no visibility: layers order
handlers, registries scope them, so a handler is live exactly while the registry
holding it is in the dispatch chain. Registering into a process-global registry
is global mutation, and nothing about the layer value contains it.

Each test drives a cleanup cycle itself rather than reading state left by a
neighbour, so every one passes when selected alone or in any order.

These live at ``engine/tests/`` root rather than under ``vm/``: ``vm/conftest.py``
has its own ``clean_vm_dispatch`` fixture that clears and restores ``vm_dispatch``
wholesale, which would mask what is being proven here.

.. storytangl-topic::
   :topics: dispatch
   :facets: tests
   :relation: tests
"""

from __future__ import annotations

import importlib
import sys

from pytest_helpers.registry_isolation import restore_shared_behavior_registries
from tangl.story.dispatch import on_render_text, story_dispatch
from tangl.vm.dispatch import dispatch as vm_dispatch, on_gather_ns
from tangl.vm.traversable import TraversableNode

#: A module that registers on import, standing in for ``worlds/*/domain.py``.
_PROBE_DOMAIN_SOURCE = '''\
from tangl.vm.dispatch import on_gather_ns
from tangl.vm.traversable import TraversableNode


@on_gather_ns(wants_caller_kind=TraversableNode, wants_exact_kind=False)
def probe_domain_handler(*, caller, ctx, **_kw):
    return {"probe_domain": True}
'''


def test_isolation_fixture_applies_to_every_test(request) -> None:
    """The fixture is wired autouse, not opt-in.

    This test never requests it, so finding it among the active fixtures is proof
    the whole ``engine/tests`` tree is covered — including tests that have no idea
    the registries exist.
    """
    assert "isolate_behavior_registries" in request.fixturenames


def test_test_body_registration_is_removed() -> None:
    """Register on a broad caller kind — where type-filtering stops saving us.

    ``TraversableNode`` matches essentially every node the VM walks, so without
    isolation these two handlers would fire for the rest of the session.
    """
    with restore_shared_behavior_registries():

        @on_gather_ns(wants_caller_kind=TraversableNode, wants_exact_kind=False)
        def _leaky_ns_contributor(*, caller, ctx, **_kw):
            return {"isolation_probe": True}

        @on_render_text(wants_caller_kind=TraversableNode, wants_exact_kind=False)
        def _leaky_text_handler(*, caller, aspect, ctx, **_kw):
            return "isolation probe"

        vm_uid = _leaky_ns_contributor._behavior.uid
        story_uid = _leaky_text_handler._behavior.uid
        assert vm_uid in vm_dispatch.members
        assert story_uid in story_dispatch.members

    assert vm_uid not in vm_dispatch.members
    assert story_uid not in story_dispatch.members


def test_import_time_registration_is_preserved(tmp_path, monkeypatch) -> None:
    """A module first imported inside the block keeps its handlers.

    ``WorldCompiler`` imports ``worlds/*/domain.py`` lazily through
    ``importlib.import_module``, which caches: a second ``compile()`` never
    re-runs the decorators. Removing them breaks every later test that loads the
    same world.
    """
    module_name = "isolation_probe_domain"
    (tmp_path / f"{module_name}.py").write_text(_PROBE_DOMAIN_SOURCE)
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    module = None
    try:
        with restore_shared_behavior_registries():
            module = importlib.import_module(module_name)
            probe_uid = module.probe_domain_handler._behavior.uid
            assert probe_uid in vm_dispatch.members

        assert probe_uid in vm_dispatch.members, (
            "import-time handler was removed; a second import would not re-register it"
        )
    finally:
        # The autouse fixture exempts this handler for the same reason, so the
        # test that created it has to be the one to take it back out.
        sys.modules.pop(module_name, None)
        if module is not None:
            vm_dispatch.remove(module.probe_domain_handler._behavior.uid)


def test_preexisting_handlers_survive_a_cleanup_cycle() -> None:
    """The fixture is a diff, not a ``clear()``.

    Production handlers register at import time; emptying the registries would
    quietly disarm the engine for every test that follows.
    """
    before = set(vm_dispatch.members), set(story_dispatch.members)
    assert all(before), "expected import-time production handlers to be registered"

    with restore_shared_behavior_registries():
        pass

    assert before[0] <= set(vm_dispatch.members)
    assert before[1] <= set(story_dispatch.members)
