"""Contract tests for ``tangl.vm.dispatch``.

Organized by concept:
- Hook registration: on_* decorators
- Hook execution: do_* functions with aggregation
- Namespace gathering: two-phase ``do_gather_ns`` behavior
"""

from __future__ import annotations

from collections import ChainMap
from contextlib import contextmanager

import pytest

from tangl.core import Graph, Record, Selector, Singleton, TemplateRegistry, TokenCatalog
from tangl.media.media_resource import MediaInventory, MediaResourceRegistry
from tangl.vm.dispatch import (
    dispatch as vm_dispatch,
    do_compose_journal,
    do_finalize,
    do_gather_ns,
    do_get_media_inventories,
    do_get_template_scope_groups,
    do_get_token_catalogs,
    do_journal,
    do_postreqs,
    do_prereqs,
    do_provision,
    do_update,
    do_validate,
    on_compose_journal,
    on_finalize,
    on_gather_ns,
    on_get_media_inventories,
    on_get_template_scope_groups,
    on_get_token_catalogs,
    on_journal,
    on_postreqs,
    on_prereqs,
    on_provision,
    on_update,
    on_validate,
)
import tangl.vm as vm38_api
import tangl.vm.dispatch as vm38_dispatch_api
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.traversable import AnonymousEdge, TraversableNode


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

    def test_on_compose_journal_registers(self) -> None:
        fragment = Record()

        @on_compose_journal
        def my_compose(*, caller, ctx, fragments, **kw):
            return fragment

        behaviors = list(vm_dispatch.find_all(Selector(task="compose_journal")))
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
            (on_compose_journal, "compose_journal"),
            (on_finalize, "finalize_step"),
            (on_postreqs, "get_postreqs"),
            (on_gather_ns, "gather_ns"),
            (on_get_media_inventories, "get_media_inventories"),
            (on_get_template_scope_groups, "get_template_scope_groups"),
            (on_get_token_catalogs, "get_token_catalogs"),
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

    def test_compose_handler_receives_merged_fragments_and_can_replace_output(self, null_ctx) -> None:
        first = Record(label="first")
        second = Record(label="second")
        seen: dict[str, list[Record]] = {}

        on_journal(lambda *, caller, ctx, **kw: first)
        on_journal(lambda *, caller, ctx, **kw: second)

        @on_compose_journal
        def _compose(*, caller, ctx, fragments, **kw):
            seen["fragments"] = list(fragments)
            return [Record(label="composed")]

        g = Graph()
        node = _node(g, label="n")
        result = do_journal(node, ctx=null_ctx)

        assert seen["fragments"] == [first, second]
        assert isinstance(result, Record)
        assert result.label == "composed"

    def test_compose_handler_can_inspect_prior_render_results_on_ctx_pipe(self) -> None:
        first = Record(label="first")
        second = Record(label="second")
        seen: dict[str, list[object]] = {}

        on_journal(lambda *, caller, ctx, **kw: first)
        on_journal(lambda *, caller, ctx, **kw: second)

        @on_compose_journal
        def _compose(*, caller, ctx, fragments, **kw):
            seen["results"] = list(ctx.results)
            return None

        g = Graph()
        node = _node(g, label="n")
        ctx = PhaseCtx(graph=g, cursor_id=node.uid)

        result = do_journal(node, ctx=ctx)

        assert seen["results"] == [first, second]
        assert result == [first, second]


class TestDoComposeJournal:
    """do_compose_journal uses last non-None replacement semantics."""

    def test_no_handlers_returns_none(self, null_ctx) -> None:
        g = Graph()
        node = _node(g, label="n")
        assert do_compose_journal(node, ctx=null_ctx, fragments=[Record(label="raw")]) is None

    def test_last_non_none_result_wins(self, null_ctx) -> None:
        first = Record(label="first")
        second = Record(label="second")

        on_compose_journal(lambda *, caller, ctx, fragments, **kw: [first])
        on_compose_journal(lambda *, caller, ctx, fragments, **kw: None)
        on_compose_journal(lambda *, caller, ctx, fragments, **kw: [second])

        g = Graph()
        node = _node(g, label="n")
        result = do_compose_journal(node, ctx=null_ctx, fragments=[Record(label="raw")])

        assert result == [second]

    def test_later_handlers_can_inspect_prior_compose_results_on_ctx_pipe(self) -> None:
        first = Record(label="first")
        second = Record(label="second")
        seen: dict[str, list[object]] = {}

        @on_compose_journal
        def _first(*, caller, ctx, fragments, **kw):
            return [first]

        @on_compose_journal
        def _second(*, caller, ctx, fragments, **kw):
            seen["results"] = list(ctx.results)
            return [second]

        g = Graph()
        node = _node(g, label="n")
        ctx = PhaseCtx(graph=g, cursor_id=node.uid)

        result = do_compose_journal(node, ctx=ctx, fragments=[Record(label="raw")])

        assert seen["results"] == [[first]]
        assert result == [second]

    def test_invalid_compose_payload_raises(self, null_ctx) -> None:
        on_compose_journal(lambda *, caller, ctx, fragments, **kw: "bad")
        g = Graph()
        node = _node(g, label="n")
        with pytest.raises(TypeError, match="compose_journal"):
            do_compose_journal(node, ctx=null_ctx, fragments=[Record(label="raw")])


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


class TestDiscoveryHooks:
    def test_template_scope_groups_merge_in_dispatch_order(self, null_ctx) -> None:
        first_registry = TemplateRegistry(label="first")
        second_registry = TemplateRegistry(label="second")

        @on_get_template_scope_groups
        def first(*, caller, ctx, **kw):
            return [first_registry]

        @on_get_template_scope_groups
        def second(*, caller, ctx, **kw):
            return [second_registry]

        g = Graph()
        node = _node(g, label="n")
        registries = do_get_template_scope_groups(node, ctx=null_ctx)
        assert registries == [first_registry, second_registry]

    def test_discovery_subdispatch_uses_fresh_ctx_result_pipe(self) -> None:
        first_registry = TemplateRegistry(label="first")
        seen: dict[str, list[object]] = {}

        @on_get_template_scope_groups
        def first(*, caller, ctx, **kw):
            seen["during"] = list(ctx.results)
            return [first_registry]

        g = Graph()
        node = _node(g, label="n")
        ctx = PhaseCtx(graph=g, cursor_id=node.uid)
        ctx.push_result("outer")

        registries = do_get_template_scope_groups(node, ctx=ctx)

        assert seen["during"] == []
        assert ctx.results == ["outer"]
        assert registries == [first_registry]

    def test_template_scope_groups_invalid_shape_raises(self, null_ctx) -> None:
        @on_get_template_scope_groups
        def bad(*, caller, ctx, **kw):
            return ["not-a-group"]

        g = Graph()
        node = _node(g, label="n")
        with pytest.raises(TypeError, match="TemplateRegistry entries only"):
            do_get_template_scope_groups(node, ctx=null_ctx)

    def test_token_catalogs_dedupe_by_wrapped_type(self, null_ctx) -> None:
        class GearType(Singleton):
            pass

        cat_a = TokenCatalog(wst=GearType)
        cat_b = TokenCatalog(wst=GearType)

        @on_get_token_catalogs
        def first(*, caller, requirement, ctx, **kw):
            return [cat_a]

        @on_get_token_catalogs
        def second(*, caller, requirement, ctx, **kw):
            return [cat_b]

        g = Graph()
        node = _node(g, label="n")
        catalogs = do_get_token_catalogs(node, requirement=None, ctx=null_ctx)
        assert len(catalogs) == 1
        assert catalogs[0].wst is GearType

    def test_token_catalogs_invalid_entries_raise(self, null_ctx) -> None:
        @on_get_token_catalogs
        def bad(*, caller, requirement, ctx, **kw):
            return ["not-a-catalog"]

        g = Graph()
        node = _node(g, label="n")
        with pytest.raises(TypeError, match="TokenCatalog entries only"):
            do_get_token_catalogs(node, requirement=None, ctx=null_ctx)

    def test_media_inventories_dedupe_by_registry(self, null_ctx) -> None:
        registry = MediaResourceRegistry(label="media")
        inv_a = MediaInventory(registry=registry, scope="world", label="a")
        inv_b = MediaInventory(registry=registry, scope="world", label="b")

        @on_get_media_inventories
        def first(*, caller, requirement, ctx, **kw):
            return [inv_a]

        @on_get_media_inventories
        def second(*, caller, requirement, ctx, **kw):
            return [inv_b]

        g = Graph()
        node = _node(g, label="n")
        inventories = do_get_media_inventories(node, requirement=None, ctx=null_ctx)
        assert inventories == [inv_a]

    def test_media_inventories_invalid_entries_raise(self, null_ctx) -> None:
        @on_get_media_inventories
        def bad(*, caller, requirement, ctx, **kw):
            return ["not-an-inventory"]

        g = Graph()
        node = _node(g, label="n")
        with pytest.raises(TypeError, match="MediaInventory entries only"):
            do_get_media_inventories(node, requirement=None, ctx=null_ctx)

    def test_discovery_uses_subdispatch_context_when_available(self) -> None:
        seen_ctx = {"value": None}

        class _SubCtx:
            def __init__(self, parent) -> None:
                self.parent = parent

            def get_authorities(self):
                return []

            def get_inline_behaviors(self):
                return []

        class _Ctx:
            def __init__(self) -> None:
                self.entered = False
                self.exited = False

            def get_authorities(self):
                return []

            def get_inline_behaviors(self):
                return []

            def with_subdispatch(self):
                @contextmanager
                def _cm():
                    self.entered = True
                    subctx = _SubCtx(self)
                    try:
                        yield subctx
                    finally:
                        self.exited = True
                return _cm()

        @on_get_template_scope_groups
        def _noop(*, caller, ctx, **kw):
            seen_ctx["value"] = ctx
            return []

        g = Graph()
        node = _node(g, label="n")
        ctx = _Ctx()
        assert do_get_template_scope_groups(node, ctx=ctx) == []
        assert ctx.entered is True
        assert ctx.exited is True
        assert seen_ctx["value"] is not None
        assert seen_ctx["value"] is not ctx


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
