"""Contract tests for ``tangl.vm38.system_handlers``.

Tests each system handler function directly, then verifies they fire
correctly through the dispatch do_* functions.

Organized by pipeline phase:
- gather_ns: contribute_locals, contribute_satisfied_deps
- validate: validate_successor_exists
- prereqs: descend_into_container, follow_triggered_prereqs
- update: mark_visited
- postreqs: follow_triggered_postreqs
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tangl.core38 import Graph, Selector
from tangl.core38.runtime_op import Effect, Predicate
from tangl.vm38.dispatch import (
    dispatch as vm_dispatch,
    do_gather_ns,
    do_prereqs,
    do_update,
    do_validate,
    do_postreqs,
)
from tangl.vm38.resolution_phase import ResolutionPhase
from tangl.vm38.traversable import (
    AnonymousEdge,
    TraversableEdge,
    TraversableNode,
)
from tangl.vm38 import Dependency, Requirement


def _node(graph: Graph, **kwargs) -> TraversableNode:
    node = TraversableNode(**kwargs)
    graph.add(node)
    return node


def _edge(graph: Graph, **kwargs) -> TraversableEdge:
    edge = TraversableEdge(**kwargs)
    graph.add(edge)
    return edge

# Import registers the handlers — must happen after clean_vm_dispatch yields
import tangl.vm38.system_handlers as sh


@pytest.fixture(autouse=True)
def register_system_handlers(clean_vm_dispatch):
    """Re-register system handlers after dispatch is cleared.

    The autouse ``clean_vm_dispatch`` fixture clears the registry.
    We need to re-import/re-register handlers for these tests.
    """
    # Re-register each handler explicitly
    from tangl.vm38.dispatch import on_gather_ns, on_validate, on_prereqs, on_update, on_postreqs
    on_gather_ns(sh.contribute_runtime_baseline)
    on_gather_ns(sh.contribute_locals)
    on_gather_ns(sh.contribute_satisfied_deps)
    on_validate(sh.validate_successor_exists)
    on_prereqs(sh.descend_into_container)
    on_prereqs(sh.follow_triggered_prereqs)
    on_update(sh.apply_runtime_effects)
    on_update(sh.mark_visited)
    on_postreqs(sh.follow_triggered_postreqs)


@pytest.fixture
def ctx() -> SimpleNamespace:
    return SimpleNamespace(
        get_registries=lambda: [vm_dispatch],
        get_inline_behaviors=lambda: [],
    )


# ============================================================================
# Namespace: contribute_locals
# ============================================================================


class TestContributeLocals:
    def test_returns_locals_dict(self) -> None:
        g = Graph()
        node = _node(g, label="n")
        node.locals = {"key": "val"}
        result = sh.contribute_locals(caller=node, ctx=None)
        assert result == {"key": "val"}

    def test_returns_none_if_no_locals(self) -> None:
        g = Graph()
        node = _node(g, label="n")
        node.locals = {}
        result = sh.contribute_locals(caller=node, ctx=None)
        # falsy dict returns None
        assert result is None

    def test_fires_through_gather_ns(self, ctx) -> None:
        g = Graph()
        node = _node(g, label="n")
        node.locals = {"mood": "happy"}
        ns = do_gather_ns(node, ctx=ctx)
        assert ns["mood"] == "happy"


class TestContributeRuntimeBaseline:
    def test_cursor_and_graph_present_without_ctx_symbol(self) -> None:
        g = Graph()
        node = _node(g, label="n")
        baseline_ctx = SimpleNamespace(
            graph=g,
            cursor=node,
            get_registries=lambda: [vm_dispatch],
            get_inline_behaviors=lambda: [],
        )
        ns = do_gather_ns(node, ctx=baseline_ctx)
        assert ns["cursor"] is node
        assert ns["graph"] is g
        assert "ctx" not in ns

    def test_satisfied_deps_include_ancestor_scopes(self, ctx) -> None:
        g = Graph()
        scene = _node(g, label="scene")
        block = _node(g, label="block")
        provider = _node(g, label="guide")
        scene.add_child(block)

        dep = Dependency(
            predecessor_id=scene.uid,
            label="companion",
            requirement=Requirement(has_kind=TraversableNode),
        )
        g.add(dep)
        dep.set_provider(provider)

        ns = do_gather_ns(block, ctx=ctx)
        assert ns["companion"] is provider

    def test_nearer_satisfied_deps_override_ancestor_scopes(self, ctx) -> None:
        g = Graph()
        scene = _node(g, label="scene")
        block = _node(g, label="block")
        parent_provider = _node(g, label="parent_guide")
        child_provider = _node(g, label="child_guide")
        scene.add_child(block)

        parent_dep = Dependency(
            predecessor_id=scene.uid,
            label="companion",
            requirement=Requirement(has_kind=TraversableNode),
        )
        child_dep = Dependency(
            predecessor_id=block.uid,
            label="companion",
            requirement=Requirement(has_kind=TraversableNode),
        )
        g.add(parent_dep)
        g.add(child_dep)
        parent_dep.set_provider(parent_provider)
        child_dep.set_provider(child_provider)

        ns = do_gather_ns(block, ctx=ctx)
        assert ns["companion"] is child_provider


# ============================================================================
# Validate: validate_successor_exists
# ============================================================================


class TestValidateSuccessorExists:
    def test_edge_with_successor_passes(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        result = sh.validate_successor_exists(caller=edge, ctx=None)
        assert result is True

    def test_anonymous_edge_passes(self) -> None:
        g = Graph()
        b = _node(g, label="b")
        edge = AnonymousEdge(successor=b)
        result = sh.validate_successor_exists(caller=edge, ctx=None)
        assert result is True

    def test_edge_with_unavailable_successor_fails(self, ctx) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b", availability=[Predicate(expr="False")])
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        result = sh.validate_successor_exists(caller=edge, ctx=ctx)
        assert result is False

    def test_fires_through_do_validate(self, ctx) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        assert do_validate(edge, ctx=ctx) is True


# ============================================================================
# Prereqs: descend_into_container
# ============================================================================


class TestDescendIntoContainer:
    def test_container_returns_enter_edge(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        entry = _node(g, label="entry")
        container.add_child(entry)
        container.source_id = entry.uid

        result = sh.descend_into_container(caller=container, ctx=None)
        assert isinstance(result, AnonymousEdge)
        assert result.successor is entry

    def test_leaf_returns_none(self) -> None:
        g = Graph()
        leaf = _node(g, label="leaf")
        result = sh.descend_into_container(caller=leaf, ctx=None)
        assert result is None

    def test_fires_through_do_prereqs(self, ctx) -> None:
        g = Graph()
        container = _node(g, label="scene")
        entry = _node(g, label="entry")
        container.add_child(entry)
        container.source_id = entry.uid

        result = do_prereqs(container, ctx=ctx)
        assert isinstance(result, AnonymousEdge)
        assert result.successor is entry


# ============================================================================
# Prereqs: follow_triggered_prereqs
# ============================================================================


class TestFollowTriggeredPrereqs:
    def test_prereq_triggered_edge_returned(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )
        result = sh.follow_triggered_prereqs(caller=a, ctx=None)
        assert result is not None
        assert result.successor is b

    def test_no_triggered_edges_returns_none(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        result = sh.follow_triggered_prereqs(caller=a, ctx=None)
        assert result is None

    def test_postreq_triggered_not_returned(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            trigger_phase=ResolutionPhase.POSTREQS,
        )
        result = sh.follow_triggered_prereqs(caller=a, ctx=None)
        assert result is None

    def test_unavailable_prereq_triggered_edge_not_returned(self, ctx) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b", availability=[Predicate(expr="False")])
        _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )
        result = sh.follow_triggered_prereqs(caller=a, ctx=ctx)
        assert result is None


# ============================================================================
# Update: mark_visited
# ============================================================================


class TestMarkVisited:
    def test_apply_runtime_effects(self, ctx) -> None:
        g = Graph()
        node = _node(g, label="n", effects=[Effect(expr="score = score + 1")])
        node.locals = {"score": 1}
        effect_ctx = SimpleNamespace(get_ns=lambda _caller: node.locals)
        sh.apply_runtime_effects(caller=node, ctx=effect_ctx)
        assert node.locals["score"] == 2

    def test_sets_visited_flag(self) -> None:
        g = Graph()
        node = _node(g, label="n")
        node.locals = {}
        sh.mark_visited(caller=node, ctx=None)
        assert node.locals["_visited"] is True
        assert node.locals["_visit_count"] == 1

    def test_increments_on_repeat(self) -> None:
        g = Graph()
        node = _node(g, label="n")
        node.locals = {}
        sh.mark_visited(caller=node, ctx=None)
        sh.mark_visited(caller=node, ctx=None)
        assert node.locals["_visit_count"] == 2

    def test_initializes_none_locals(self) -> None:
        g = Graph()
        node = _node(g, label="n")
        node.locals = None
        sh.mark_visited(caller=node, ctx=None)
        assert node.locals["_visited"] is True

    def test_fires_through_do_update(self, ctx) -> None:
        g = Graph()
        node = _node(g, label="n")
        node.locals = {}
        do_update(node, ctx=ctx)
        assert node.locals["_visited"] is True


# ============================================================================
# Postreqs: follow_triggered_postreqs
# ============================================================================


class TestFollowTriggeredPostreqs:
    def test_postreq_triggered_edge_returned(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            trigger_phase=ResolutionPhase.POSTREQS,
        )
        result = sh.follow_triggered_postreqs(caller=a, ctx=None)
        assert result is not None
        assert result.successor is b

    def test_prereq_triggered_not_returned(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )
        result = sh.follow_triggered_postreqs(caller=a, ctx=None)
        assert result is None

    def test_unavailable_postreq_triggered_edge_not_returned(self, ctx) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b", availability=[Predicate(expr="False")])
        _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            trigger_phase=ResolutionPhase.POSTREQS,
        )
        result = sh.follow_triggered_postreqs(caller=a, ctx=ctx)
        assert result is None
