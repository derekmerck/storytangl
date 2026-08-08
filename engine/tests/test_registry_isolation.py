"""Contract tests for the autouse shared-registry isolation fixture.

The fixture under test is ``isolate_behavior_registries`` in this directory's
``conftest.py``. It exists because ``DispatchLayer`` confers no visibility:
layers order handlers, registries scope them, so a handler is live exactly while
the registry holding it is in the dispatch chain. Registering into a
process-global registry is therefore global mutation, and nothing about the layer
value contains it.

These tests are deliberately at ``engine/tests/`` root rather than under ``vm/``:
``vm/conftest.py`` has its own ``clean_vm_dispatch`` fixture that clears and
restores ``vm_dispatch`` wholesale, which would mask what is being proven here.

.. storytangl-topic::
   :topics: dispatch
   :facets: tests
   :relation: tests
"""

from __future__ import annotations

from uuid import UUID

from tangl.story.dispatch import on_render_text, story_dispatch
from tangl.vm.dispatch import dispatch as vm_dispatch, on_gather_ns
from tangl.vm.traversable import TraversableNode

#: Uids registered by the first test, read back by the second. Module state is the
#: point: the whole failure mode this guards against is state outliving a test.
_REGISTERED: dict[str, UUID] = {}


def test_broad_handlers_register_into_shared_registries() -> None:
    """Register on a broad caller kind — the case where type-filtering stops saving us.

    ``TraversableNode`` matches essentially every node the VM walks, so without
    isolation these two handlers would fire for the rest of the session.
    """

    @on_gather_ns(wants_caller_kind=TraversableNode, wants_exact_kind=False)
    def _leaky_ns_contributor(*, caller, ctx, **_kw):
        return {"isolation_probe": True}

    @on_render_text(wants_caller_kind=TraversableNode, wants_exact_kind=False)
    def _leaky_text_handler(*, caller, aspect, ctx, **_kw):
        return "isolation probe"

    _REGISTERED["vm"] = _leaky_ns_contributor._behavior.uid
    _REGISTERED["story"] = _leaky_text_handler._behavior.uid

    assert _REGISTERED["vm"] in vm_dispatch.members
    assert _REGISTERED["story"] in story_dispatch.members


def test_broad_handlers_did_not_survive_the_previous_test() -> None:
    """The fixture removed both without being asked, and without a manual cleanup."""
    assert _REGISTERED, (
        "expected the registering test to have run first; this pair asserts "
        "cross-test isolation and depends on declaration order"
    )

    assert _REGISTERED["vm"] not in vm_dispatch.members
    assert _REGISTERED["story"] not in story_dispatch.members


def test_import_time_handlers_survive_the_fixture() -> None:
    """The fixture is a diff, not a ``clear()``.

    Production handlers register at import time and must still be present, or the
    fixture would be quietly disarming the engine for every test that follows.
    """
    assert vm_dispatch.members, "vm_dispatch was emptied; the fixture over-reached"
    assert story_dispatch.members, "story_dispatch was emptied; the fixture over-reached"
