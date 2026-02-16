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
    on_gather_ns(sh.contribute_locals)
    on_gather_ns(sh.contribute_satisfied_deps)
    on_validate(sh.validate_successor_exists)
    on_prereqs(sh.descend_into_container)
    on_prereqs(sh.follow_triggered_prereqs)
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
        node = TraversableNode(label="n", registry=g)
        node.locals = {"key": "val"}
        result = sh.contribute_locals(caller=node, ctx=None)
        assert result == {"key": "val"}

    def test_returns_none_if_no_locals(self) -> None:
        g = Graph()
        node = TraversableNode(label="n", registry=g)
        node.locals = {}
        result = sh.contribute_locals(caller=node, ctx=None)
        # falsy dict returns None
        assert result is None

    def test_fires_through_gather_ns(self, ctx) -> None:
        g = Graph()
        node = TraversableNode(label="n", registry=g)
        node.locals = {"mood": "happy"}
        ns = do_gather_ns(node, ctx=ctx)
        assert ns["mood"] == "happy"


# ============================================================================
# Validate: validate_successor_exists
# ============================================================================


class TestValidateSuccessorExists:
    def test_edge_with_successor_passes(self) -> None:
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        edge = TraversableEdge(registry=g, predecessor_id=a.uid, successor_id=b.uid)
        result = sh.validate_successor_exists(caller=edge, ctx=None)
        assert result is True

    def test_anonymous_edge_passes(self) -> None:
        g = Graph()
        b = TraversableNode(label="b", registry=g)
        edge = AnonymousEdge(successor=b)
        result = sh.validate_successor_exists(caller=edge, ctx=None)
        assert result is True

    def test_fires_through_do_validate(self, ctx) -> None:
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        edge = TraversableEdge(registry=g, predecessor_id=a.uid, successor_id=b.uid)
        assert do_validate(edge, ctx=ctx) is True


# ============================================================================
# Prereqs: descend_into_container
# ============================================================================


class TestDescendIntoContainer:
    def test_container_returns_enter_edge(self) -> None:
        g = Graph()
        container = TraversableNode(label="scene", registry=g)
        entry = TraversableNode(label="entry", registry=g)
        container.add_child(entry)
        container.source_id = entry.uid

        result = sh.descend_into_container(caller=container, ctx=None)
        assert isinstance(result, AnonymousEdge)
        assert result.successor is entry

    def test_leaf_returns_none(self) -> None:
        g = Graph()
        leaf = TraversableNode(label="leaf", registry=g)
        result = sh.descend_into_container(caller=leaf, ctx=None)
        assert result is None

    def test_fires_through_do_prereqs(self, ctx) -> None:
        g = Graph()
        container = TraversableNode(label="scene", registry=g)
        entry = TraversableNode(label="entry", registry=g)
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
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        TraversableEdge(
            registry=g, predecessor_id=a.uid, successor_id=b.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )
        result = sh.follow_triggered_prereqs(caller=a, ctx=None)
        assert result is not None
        assert result.successor is b

    def test_no_triggered_edges_returns_none(self) -> None:
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        TraversableEdge(registry=g, predecessor_id=a.uid, successor_id=b.uid)
        result = sh.follow_triggered_prereqs(caller=a, ctx=None)
        assert result is None

    def test_postreq_triggered_not_returned(self) -> None:
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        TraversableEdge(
            registry=g, predecessor_id=a.uid, successor_id=b.uid,
            trigger_phase=ResolutionPhase.POSTREQS,
        )
        result = sh.follow_triggered_prereqs(caller=a, ctx=None)
        assert result is None


# ============================================================================
# Update: mark_visited
# ============================================================================


class TestMarkVisited:
    def test_sets_visited_flag(self) -> None:
        g = Graph()
        node = TraversableNode(label="n", registry=g)
        node.locals = {}
        sh.mark_visited(caller=node, ctx=None)
        assert node.locals["_visited"] is True
        assert node.locals["_visit_count"] == 1

    def test_increments_on_repeat(self) -> None:
        g = Graph()
        node = TraversableNode(label="n", registry=g)
        node.locals = {}
        sh.mark_visited(caller=node, ctx=None)
        sh.mark_visited(caller=node, ctx=None)
        assert node.locals["_visit_count"] == 2

    def test_initializes_none_locals(self) -> None:
        g = Graph()
        node = TraversableNode(label="n", registry=g)
        node.locals = None
        sh.mark_visited(caller=node, ctx=None)
        assert node.locals["_visited"] is True

    def test_fires_through_do_update(self, ctx) -> None:
        g = Graph()
        node = TraversableNode(label="n", registry=g)
        node.locals = {}
        do_update(node, ctx=ctx)
        assert node.locals["_visited"] is True


# ============================================================================
# Postreqs: follow_triggered_postreqs
# ============================================================================


class TestFollowTriggeredPostreqs:
    def test_postreq_triggered_edge_returned(self) -> None:
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        TraversableEdge(
            registry=g, predecessor_id=a.uid, successor_id=b.uid,
            trigger_phase=ResolutionPhase.POSTREQS,
        )
        result = sh.follow_triggered_postreqs(caller=a, ctx=None)
        assert result is not None
        assert result.successor is b

    def test_prereq_triggered_not_returned(self) -> None:
        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        TraversableEdge(
            registry=g, predecessor_id=a.uid, successor_id=b.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )
        result = sh.follow_triggered_postreqs(caller=a, ctx=None)
        assert result is None
