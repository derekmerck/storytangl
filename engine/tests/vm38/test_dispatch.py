"""Contract tests for ``tangl.vm38.dispatch``.

Organized by concept:
- Hook registration: on_* decorators
- Hook execution: do_* functions with aggregation
- Namespace gathering: do_gather_ns ancestor walk and ChainMap scoping
"""

from __future__ import annotations

from collections import ChainMap
from types import SimpleNamespace

import pytest

from tangl.core38 import BehaviorRegistry, Graph, Node, Selector
from tangl.vm38.dispatch import (
    dispatch as vm_dispatch,
    do_finalize,
    do_gather_ns,
    do_journal,
    do_postreqs,
    do_prereqs,
    do_provision,
    do_update,
    do_validate,
    on_finalize,
    on_gather_ns,
    on_journal,
    on_postreqs,
    on_prereqs,
    on_provision,
    on_update,
    on_validate,
)
from tangl.vm38.traversable import TraversableNode


def _node(graph: Graph, **kwargs) -> TraversableNode:
    node = TraversableNode(**kwargs)
    graph.add(node)
    return node


# ============================================================================
# Hook registration
# ============================================================================


class TestHookRegistration:
    """on_* decorators register handlers into the module-level vm_dispatch."""

    def test_on_validate_registers(self) -> None:
        @on_validate
        def my_validator(*, caller, ctx, **kw):
            return True

        behaviors = list(vm_dispatch.find_all(Selector(task="validate_edge")))
        assert len(behaviors) >= 1

    def test_on_journal_registers(self) -> None:
        @on_journal
        def my_journal(*, caller, ctx, **kw):
            return "fragment"

        behaviors = list(vm_dispatch.find_all(Selector(task="render_journal")))
        assert len(behaviors) >= 1

    def test_on_hook_works_as_decorator_with_kwargs(self) -> None:
        @on_update(priority=0)
        def early_update(*, caller, ctx, **kw):
            return "early"

        behaviors = list(vm_dispatch.find_all(Selector(task="apply_update")))
        assert len(behaviors) >= 1

    def test_all_phase_hooks_register_to_correct_tasks(self) -> None:
        """Each on_* hook maps to its expected task name."""
        pairs = [
            (on_validate,  "validate_edge"),
            (on_provision, "provision_node"),
            (on_prereqs,   "get_prereqs"),
            (on_update,    "apply_update"),
            (on_journal,   "render_journal"),
            (on_finalize,  "finalize_step"),
            (on_postreqs,  "get_postreqs"),
            (on_gather_ns, "gather_ns"),
        ]
        for on_hook, expected_task in pairs:
            on_hook(lambda *, caller, ctx, **kw: None)
            # Just verify no exception — task mapping is correct
            assert list(vm_dispatch.find_all(Selector(task=expected_task)))


# ============================================================================
# Hook execution — aggregation modes
# ============================================================================


class TestDoValidate:
    """do_validate uses all_true aggregation."""

    def test_no_handlers_returns_true(self, null_ctx) -> None:
        """No validators registered → vacuously true."""
        g = Graph()
        edge = _node(g, label="e")
        # all_true with no receipts returns True (vacuous truth)
        result = do_validate(edge, ctx=null_ctx)
        assert result is True

    def test_truthy_handler(self, null_ctx) -> None:
        on_validate(lambda *, caller, ctx, **kw: True)
        g = Graph()
        edge = _node(g, label="e")
        assert do_validate(edge, ctx=null_ctx) is True

    def test_falsy_handler_blocks(self, null_ctx) -> None:
        on_validate(lambda *, caller, ctx, **kw: False)
        g = Graph()
        edge = _node(g, label="e")
        assert do_validate(edge, ctx=null_ctx) is False


class TestDoPrereqs:
    """do_prereqs uses first_result aggregation."""

    def test_no_handlers_returns_none(self, null_ctx) -> None:
        g = Graph()
        node = _node(g, label="n")
        assert do_prereqs(node, ctx=null_ctx) is None

    def test_first_non_none_returned(self, null_ctx) -> None:
        on_prereqs(lambda *, caller, ctx, **kw: None)
        on_prereqs(lambda *, caller, ctx, **kw: "redirect_edge")
        g = Graph()
        node = _node(g, label="n")
        assert do_prereqs(node, ctx=null_ctx) == "redirect_edge"


class TestDoJournal:
    """do_journal uses last_result aggregation (pipe)."""

    def test_no_handlers_returns_none(self, null_ctx) -> None:
        g = Graph()
        node = _node(g, label="n")
        assert do_journal(node, ctx=null_ctx) is None

    def test_last_handler_wins(self, null_ctx) -> None:
        on_journal(lambda *, caller, ctx, **kw: "first")
        on_journal(lambda *, caller, ctx, **kw: "second")
        g = Graph()
        node = _node(g, label="n")
        result = do_journal(node, ctx=null_ctx)
        assert result == "second"


class TestDoProvision:
    """do_provision uses gather_results aggregation."""

    def test_gathers_from_multiple_handlers(self, null_ctx) -> None:
        on_provision(lambda *, caller, ctx, **kw: "a")
        on_provision(lambda *, caller, ctx, **kw: "b")
        g = Graph()
        node = _node(g, label="n")
        result = do_provision(node, ctx=null_ctx)
        assert "a" in result and "b" in result


# ============================================================================
# Namespace gathering — ancestor walk
# ============================================================================


class TestDoGatherNs:
    """do_gather_ns walks the ancestor chain and builds a scoped ChainMap."""

    def test_empty_ns_with_no_handlers(self, null_ctx) -> None:
        g = Graph()
        node = _node(g, label="n")
        ns = do_gather_ns(node, ctx=null_ctx)
        assert isinstance(ns, ChainMap)
        assert len(ns) == 0

    def test_node_locals_contributed(self, null_ctx) -> None:
        """Handler contributing locals maps through namespace."""
        @on_gather_ns
        def add_locals(*, caller, ctx, **kw):
            if hasattr(caller, "locals") and caller.locals:
                return dict(caller.locals)
            return None

        g = Graph()
        node = _node(g, label="n")
        node.locals = {"mood": "angry"}
        ns = do_gather_ns(node, ctx=null_ctx)
        assert ns["mood"] == "angry"

    def test_closer_scope_overrides(self, null_ctx) -> None:
        """Child locals override parent locals in the ChainMap."""
        @on_gather_ns
        def add_locals(*, caller, ctx, **kw):
            if hasattr(caller, "locals") and caller.locals:
                return dict(caller.locals)
            return None

        g = Graph()
        parent = _node(g, label="scene")
        child = _node(g, label="block")
        parent.add_child(child)

        parent.locals = {"color": "red", "shared": "parent"}
        child.locals = {"shared": "child"}

        ns = do_gather_ns(child, ctx=null_ctx)
        assert ns["shared"] == "child"
        assert ns["color"] == "red"

    def test_rootless_node_still_works(self, null_ctx) -> None:
        """A node with no parent gets its own namespace."""
        @on_gather_ns
        def add_locals(*, caller, ctx, **kw):
            if hasattr(caller, "locals") and caller.locals:
                return dict(caller.locals)
            return None

        g = Graph()
        node = _node(g, label="orphan")
        node.locals = {"key": "val"}
        ns = do_gather_ns(node, ctx=null_ctx)
        assert ns["key"] == "val"
