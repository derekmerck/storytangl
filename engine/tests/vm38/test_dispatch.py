"""Contract tests for ``tangl.vm38.dispatch``.

Organized by concept:
- Hook registration: on_* decorators
- Hook execution: do_* functions with aggregation
- Namespace gathering: two-phase ``do_gather_ns`` behavior
"""

from __future__ import annotations

from collections import ChainMap

import pytest

from tangl.core38 import Graph, Record, Selector
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
import tangl.vm38 as vm38_api
import tangl.vm38.dispatch as vm38_dispatch_api
from tangl.vm38.traversable import AnonymousEdge, TraversableNode


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
        fragment = Record()

        @on_journal
        def my_journal(*, caller, ctx, **kw):
            return fragment

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
            (on_validate, "validate_edge"),
            (on_provision, "provision_node"),
            (on_prereqs, "get_prereqs"),
            (on_update, "apply_update"),
            (on_journal, "render_journal"),
            (on_finalize, "finalize_step"),
            (on_postreqs, "get_postreqs"),
            (on_gather_ns, "gather_ns"),
        ]
        for on_hook, expected_task in pairs:
            on_hook(lambda *, caller, ctx, **kw: None)
            assert list(vm_dispatch.find_all(Selector(task=expected_task)))

    def test_on_gather_ns_uses_explicit_caller_kind_fields(self) -> None:
        @on_gather_ns(wants_caller_kind=TraversableNode, wants_exact_kind=False)
        def _typed(*, caller, ctx, **kw):
            return {"ok": True}

        behavior = list(vm_dispatch.find_all(Selector(task="gather_ns")))[0]
        assert behavior.wants_caller_kind is TraversableNode
        assert behavior.wants_exact_kind is False

    def test_on_gather_ns_rejects_has_kind_kwarg(self) -> None:
        with pytest.raises(TypeError, match="wants_caller_kind"):
            on_gather_ns(lambda *, caller, ctx, **kw: None, has_kind=TraversableNode)

    def test_on_get_ns_not_exposed_in_vm38_api(self) -> None:
        assert not hasattr(vm38_dispatch_api, "on_get_ns")
        assert not hasattr(vm38_api, "on_get_ns")


# ============================================================================
# Hook execution — aggregation modes
# ============================================================================


class TestDoValidate:
    """do_validate uses all_true aggregation."""

    def test_no_handlers_returns_true(self, null_ctx) -> None:
        g = Graph()
        edge = _node(g, label="e")
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

    def test_bad_ctx_shape_raises(self) -> None:
        g = Graph()
        edge = _node(g, label="e")
        with pytest.raises(TypeError, match="Dispatch context"):
            do_validate(edge, ctx=object())


class TestDoPrereqs:
    """do_prereqs uses first_result aggregation."""

    def test_no_handlers_returns_none(self, null_ctx) -> None:
        g = Graph()
        node = _node(g, label="n")
        assert do_prereqs(node, ctx=null_ctx) is None

    def test_first_non_none_returned(self, null_ctx) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        redirect = AnonymousEdge(predecessor=a, successor=b)
        on_prereqs(lambda *, caller, ctx, **kw: None)
        on_prereqs(lambda *, caller, ctx, **kw: redirect)
        assert do_prereqs(a, ctx=null_ctx) is redirect

    def test_bad_redirect_type_raises(self, null_ctx) -> None:
        g = Graph()
        node = _node(g, label="n")
        on_prereqs(lambda *, caller, ctx, **kw: "redirect_edge")
        with pytest.raises(TypeError, match="traversable edge"):
            do_prereqs(node, ctx=null_ctx)


class TestDoJournal:
    """do_journal merges all handler contributions in execution order."""

    def test_no_handlers_returns_none(self, null_ctx) -> None:
        g = Graph()
        node = _node(g, label="n")
        assert do_journal(node, ctx=null_ctx) is None

    def test_multiple_handlers_merge_results(self, null_ctx) -> None:
        first = Record(label="first")
        second = Record(label="second")
        on_journal(lambda *, caller, ctx, **kw: first)
        on_journal(lambda *, caller, ctx, **kw: second)
        g = Graph()
        node = _node(g, label="n")
        result = do_journal(node, ctx=null_ctx)
        assert isinstance(result, list)
        assert result == [first, second]

    def test_invalid_journal_payload_raises(self, null_ctx) -> None:
        on_journal(lambda *, caller, ctx, **kw: "second")
        g = Graph()
        node = _node(g, label="n")
        with pytest.raises(TypeError, match="render_journal"):
            do_journal(node, ctx=null_ctx)


class TestDoProvision:
    """do_provision enforces no non-None handler returns."""

    def test_no_result_handlers_return_none(self, null_ctx) -> None:
        on_provision(lambda *, caller, ctx, **kw: None)
        on_provision(lambda *, caller, ctx, **kw: None)
        g = Graph()
        node = _node(g, label="n")
        assert do_provision(node, ctx=null_ctx) is None

    def test_non_none_result_raises(self, null_ctx) -> None:
        on_provision(lambda *, caller, ctx, **kw: "a")
        g = Graph()
        node = _node(g, label="n")
        with pytest.raises(TypeError, match="provision_node"):
            do_provision(node, ctx=null_ctx)


class TestDoUpdate:
    def test_non_none_result_raises(self, null_ctx) -> None:
        on_update(lambda *, caller, ctx, **kw: "unexpected")
        g = Graph()
        node = _node(g, label="n")
        with pytest.raises(TypeError, match="apply_update"):
            do_update(node, ctx=null_ctx)


# ============================================================================
# Namespace gathering — two-phase contract
# ============================================================================


class TestDoGatherNs:
    """``do_gather_ns`` composes local ``get_ns`` + immediate dispatch."""

    def test_nonempty_base_ns_with_no_handlers(self, null_ctx) -> None:
        g = Graph()
        node = _node(g, label="n")
        ns = do_gather_ns(node, ctx=null_ctx)
        assert isinstance(ns, ChainMap)
        assert ns["self"] is node
        assert ns["n"] is node

    def test_locals_come_from_entity_get_ns(self, null_ctx) -> None:
        g = Graph()
        node = _node(g, label="n")
        node.locals = {"mood": "angry"}
        ns = do_gather_ns(node, ctx=null_ctx)
        assert ns["mood"] == "angry"

    def test_closer_scope_overrides_ancestor_scope(self, null_ctx) -> None:
        g = Graph()
        parent = _node(g, label="scene")
        child = _node(g, label="block")
        parent.add_child(child)

        parent.locals = {"color": "red", "shared": "parent"}
        child.locals = {"shared": "child"}

        ns = do_gather_ns(child, ctx=null_ctx)
        assert ns["shared"] == "child"
        assert ns["color"] == "red"

    def test_dispatch_fires_only_for_immediate_caller(self, null_ctx) -> None:
        @on_gather_ns
        def dispatch_marker(*, caller, ctx, **kw):
            return {"dispatch_for": caller.get_label()}

        g = Graph()
        parent = _node(g, label="scene")
        child = _node(g, label="block")
        parent.add_child(child)

        ns = do_gather_ns(child, ctx=null_ctx)
        assert ns["dispatch_for"] == "block"

    def test_wants_caller_kind_filters_dispatch_handlers(self, null_ctx) -> None:
        @on_gather_ns(wants_caller_kind=TraversableNode, wants_exact_kind=False)
        def include_node(*, caller, ctx, **kw):
            return {"typed": caller.get_label()}

        @on_gather_ns(wants_caller_kind=Graph, wants_exact_kind=False)
        def exclude_graph(*, caller, ctx, **kw):
            return {"graph_handler": True}

        g = Graph()
        node = _node(g, label="n")
        ns = do_gather_ns(node, ctx=null_ctx)
        assert ns["typed"] == "n"
        assert "graph_handler" not in ns

    def test_self_binding_includes_label_and_path_aliases(self, null_ctx) -> None:
        g = Graph()
        parent = _node(g, label="scene")
        child = _node(g, label="block")
        parent.add_child(child)

        ns = do_gather_ns(child, ctx=null_ctx)
        assert ns["self"] is child
        assert ns["block"] is child
        assert ns[child.path] is child

    def test_nested_roles_and_settings_deep_merge(self, null_ctx) -> None:
        @on_gather_ns
        def add_roles(*, caller, ctx, **kw):
            return {"roles": {"alpha": "a"}}

        @on_gather_ns
        def add_settings(*, caller, ctx, **kw):
            return {"settings": {"castle": "c"}, "roles": {"beta": "b"}}

        g = Graph()
        node = _node(g, label="n")
        ns = do_gather_ns(node, ctx=null_ctx)
        assert ns["roles"] == {"alpha": "a", "beta": "b"}
        assert ns["settings"] == {"castle": "c"}
