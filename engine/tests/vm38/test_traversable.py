"""Contract tests for ``tangl.vm38.traversable``.

Organized by concept:
- LCA utilities: lca(), decompose_move()
- TraversableNode: container/leaf duality, enter(), hierarchy
- TraversableEdge: entry_phase, return_phase, get_return_edge()
- AnonymousEdge: lightweight construction, interface compatibility
"""

from __future__ import annotations

import doctest
from random import Random
from types import SimpleNamespace
from uuid import uuid4

import pytest

import tangl.vm38.traversable as traversable_module
from tangl.core38 import Graph
from tangl.core38.runtime_op import Predicate
from tangl.vm38.resolution_phase import ResolutionPhase
from tangl.vm38.traversable import (
    AnonymousEdge,
    AnyTraversableEdge,
    TraversableEffect,
    TraversableEdge,
    TraversableNode,
    assert_traversal_contracts,
    decompose_move,
    lca,
    validate_traversal_contracts,
)


def _node(graph: Graph, **kwargs) -> TraversableNode:
    node = TraversableNode(**kwargs)
    graph.add(node)
    return node


def _edge(graph: Graph, **kwargs) -> TraversableEdge:
    edge = TraversableEdge(**kwargs)
    graph.add(edge)
    return edge


# ============================================================================
# LCA
# ============================================================================


class TestLCA:
    """Lowest common ancestor of two nodes in a hierarchy."""

    def test_same_node(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        assert lca(a, a) is a

    def test_siblings_share_parent(self) -> None:
        g = Graph()
        root = _node(g, label="root")
        a = _node(g, label="a")
        b = _node(g, label="b")
        root.add_child(a)
        root.add_child(b)
        assert lca(a, b) is root

    def test_parent_child(self) -> None:
        g = Graph()
        parent = _node(g, label="p")
        child = _node(g, label="c")
        parent.add_child(child)
        assert lca(parent, child) is parent

    def test_cousins(self) -> None:
        g = Graph()
        root = _node(g, label="root")
        ch1 = _node(g, label="ch1")
        ch2 = _node(g, label="ch2")
        a = _node(g, label="a")
        b = _node(g, label="b")
        root.add_child(ch1)
        root.add_child(ch2)
        ch1.add_child(a)
        ch2.add_child(b)
        assert lca(a, b) is root

    def test_disjoint_returns_none(self) -> None:
        g1 = Graph()
        g2 = Graph()
        a = _node(g1, label="a")
        b = _node(g2, label="b")
        assert lca(a, b) is None


# ============================================================================
# decompose_move
# ============================================================================


class TestDecomposeMove:
    """Move decomposition into exit/enter paths around the LCA."""

    def test_cross_branch_move(self) -> None:
        g = Graph()
        root = _node(g, label="root")
        ch1 = _node(g, label="ch1")
        ch2 = _node(g, label="ch2")
        a = _node(g, label="a")
        b = _node(g, label="b")
        root.add_child(ch1)
        root.add_child(ch2)
        ch1.add_child(a)
        ch2.add_child(b)

        exit_path, enter_path, pivot = decompose_move(a, b)
        assert [n.label for n in exit_path] == ["a", "ch1"]
        assert [n.label for n in enter_path] == ["ch2", "b"]
        assert pivot is root

    def test_sibling_move(self) -> None:
        g = Graph()
        parent = _node(g, label="p")
        a = _node(g, label="a")
        c = _node(g, label="c")
        parent.add_child(a)
        parent.add_child(c)

        ex, en, pivot = decompose_move(a, c)
        assert [n.label for n in ex] == ["a"]
        assert [n.label for n in en] == ["c"]
        assert pivot is parent

    def test_descent_into_child(self) -> None:
        g = Graph()
        parent = _node(g, label="p")
        child = _node(g, label="c")
        parent.add_child(child)

        ex, en, pivot = decompose_move(parent, child)
        assert ex == []
        assert [n.label for n in en] == ["c"]
        assert pivot is parent

    def test_ascent_to_parent(self) -> None:
        g = Graph()
        parent = _node(g, label="p")
        child = _node(g, label="c")
        parent.add_child(child)

        ex, en, pivot = decompose_move(child, parent)
        assert [n.label for n in ex] == ["c"]
        assert en == []
        assert pivot is parent

    def test_disjoint_raises(self) -> None:
        g1 = Graph()
        g2 = Graph()
        a = _node(g1, label="a")
        b = _node(g2, label="b")
        with pytest.raises(ValueError, match="no common ancestor"):
            decompose_move(a, b)


# ============================================================================
# TraversableNode — container/leaf duality
# ============================================================================


class TestTraversableNodeLeaf:
    """Leaf nodes — no container structure."""

    def test_leaf_is_not_container(self) -> None:
        g = Graph()
        node = _node(g, label="leaf")
        assert not node.is_container

    def test_leaf_enter_raises(self) -> None:
        g = Graph()
        node = _node(g, label="leaf")
        with pytest.raises(ValueError, match="not a container"):
            node.enter()

    def test_source_none_for_leaf(self) -> None:
        g = Graph()
        node = _node(g, label="leaf")
        assert node.source is None

    def test_available_defaults_true(self) -> None:
        g = Graph()
        node = _node(g, label="leaf")
        assert node.available() is True


class TestTraversableNodeContainer:
    """Container nodes with designated source/sink members."""

    def test_is_container_when_source_set(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        entry = _node(g, label="entry")
        container.add_child(entry)
        container.source_id = entry.uid
        assert container.is_container

    def test_enter_returns_anonymous_edge(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        entry = _node(g, label="entry")
        container.add_child(entry)
        container.source_id = entry.uid

        edge = container.enter()
        assert isinstance(edge, AnonymousEdge)
        assert edge.predecessor is container
        assert edge.successor is entry

    def test_sink_property(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        entry = _node(g, label="entry")
        exit_node = _node(g, label="exit")
        container.add_child(entry)
        container.add_child(exit_node)
        container.source_id = entry.uid
        container.sink_id = exit_node.uid

        assert container.source is entry
        assert container.sink is exit_node

    def test_has_forward_progress_true_when_sink_reachable(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        source = _node(g, label="entry")
        mid = _node(g, label="mid")
        sink = _node(g, label="exit")
        container.add_child(source)
        container.add_child(mid)
        container.add_child(sink)
        container.source_id = source.uid
        container.sink_id = sink.uid
        _edge(g, predecessor_id=source.uid, successor_id=mid.uid)
        _edge(g, predecessor_id=mid.uid, successor_id=sink.uid)
        assert container.has_forward_progress(source) is True

    def test_has_forward_progress_false_when_sink_unreachable(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        source = _node(g, label="entry")
        mid = _node(g, label="mid")
        sink = _node(g, label="exit")
        container.add_child(source)
        container.add_child(mid)
        container.add_child(sink)
        container.source_id = source.uid
        container.sink_id = sink.uid
        _edge(g, predecessor_id=source.uid, successor_id=mid.uid)
        assert container.has_forward_progress(source) is False

    def test_availability_predicates_must_all_pass(self) -> None:
        g = Graph()
        node = _node(
            g,
            label="gate",
            availability=[Predicate(expr="has_key"), Predicate(expr="level > 2")],
        )
        assert node.available(ns={"has_key": True, "level": 3}) is True
        assert node.available(ns={"has_key": True, "level": 1}) is False

    def test_soft_dirty_context_still_enforces_availability(self) -> None:
        g = Graph()
        node = _node(
            g,
            label="gate",
            availability=[Predicate(expr="has_key"), Predicate(expr="level > 2")],
        )
        ctx = SimpleNamespace(causality_mode="soft_dirty")
        assert node.available(ns={"has_key": True, "level": 1}, ctx=ctx) is False

    def test_hard_dirty_context_short_circuits_availability(self) -> None:
        g = Graph()
        node = _node(
            g,
            label="gate",
            availability=[Predicate(expr="has_key"), Predicate(expr="level > 2")],
        )
        ctx = SimpleNamespace(causality_mode="hard_dirty")
        assert node.available(ns={"has_key": False, "level": 0}, ctx=ctx) is True

    def test_hard_dirty_context_short_circuits_available_for(self) -> None:
        g = Graph()
        node = _node(
            g,
            label="gate",
            availability=[Predicate(expr="has_key"), Predicate(expr="level > 2")],
        )
        other = _node(g, label="other")
        ctx = SimpleNamespace(
            causality_mode="hard_dirty",
            get_ns=lambda _item: {"has_key": False, "level": 0},
        )
        assert node.available_for(other, ctx=ctx) is True

    def test_apply_effects_mutates_namespace(self) -> None:
        g = Graph()
        node = _node(g, label="gate", effects=[TraversableEffect(expr="counter = counter + 1")])
        ns = {"counter": 1}
        node.apply_effects(ns=ns)
        assert ns["counter"] == 2

    def test_apply_final_effects_fires_at_finalize_phase(self) -> None:
        g = Graph()
        node = _node(
            g,
            label="n",
            effects=[
                TraversableEffect(
                    expr="counter = counter + 1",
                    trigger_phase=ResolutionPhase.UPDATE,
                ),
                TraversableEffect(
                    expr="counter = counter * 10",
                    trigger_phase=ResolutionPhase.FINALIZE,
                ),
            ],
        )
        ns = {"counter": 1}

        node.apply_effects(ResolutionPhase.UPDATE, ns=ns)
        assert ns["counter"] == 2

        node.apply_effects(ResolutionPhase.FINALIZE, ns=ns)
        assert ns["counter"] == 20

    def test_apply_effects_accepts_int_phase_values(self) -> None:
        g = Graph()
        node = _node(
            g,
            label="n",
            effects=[TraversableEffect(expr="counter = counter + 1")],
        )
        ns = {"counter": 1}
        node.apply_effects(ResolutionPhase.UPDATE.value, ns=ns)
        assert ns["counter"] == 2

    def test_apply_effects_rejects_non_phase_non_mapping_positional(self) -> None:
        g = Graph()
        node = _node(g, label="n", effects=[TraversableEffect(expr="counter = 1")])
        with pytest.raises(TypeError, match="phase must be ResolutionPhase"):
            node.apply_effects("not-a-phase")

    def test_apply_effects_to_targets_other_namespace(self) -> None:
        g = Graph()
        provider = _node(
            g,
            label="provider",
            effects=[TraversableEffect(expr="gold = gold - 5")],
        )
        host_ns = {"gold": 20}
        ctx = SimpleNamespace(get_ns=lambda _: host_ns, random=None)

        provider.apply_effects_to(object(), ctx=ctx)
        assert host_ns["gold"] == 15

    def test_available_for_uses_other_namespace(self) -> None:
        g = Graph()
        req = _node(
            g,
            label="req",
            availability=[Predicate(expr="level >= 5")],
        )
        ctx_pass = SimpleNamespace(get_ns=lambda _: {"level": 6}, random=None)
        ctx_fail = SimpleNamespace(get_ns=lambda _: {"level": 3}, random=None)

        assert req.available_for(object(), ctx=ctx_pass) is True
        assert req.available_for(object(), ctx=ctx_fail) is False

    def test_rand_injected_into_predicate(self) -> None:
        g = Graph()
        node = _node(
            g,
            label="n",
            availability=[Predicate(expr="rand.random() < 0.9")],
        )
        rng = Random(42)

        assert node.available(ns={}, rand=rng) is True

    def test_available_uses_ctx_get_random_when_present(self) -> None:
        g = Graph()
        node = _node(
            g,
            label="n",
            availability=[Predicate(expr="rand.random() < 0.9")],
        )
        ctx = SimpleNamespace(get_ns=lambda _: {}, get_random=lambda: Random(42))
        assert node.available(ctx=ctx) is True

    def test_apply_effects_uses_ctx_get_random_when_present(self) -> None:
        g = Graph()
        node = _node(g, label="n", effects=[TraversableEffect(expr="coin = rand.random() < 0.9")])
        ns: dict[str, object] = {}
        ctx = SimpleNamespace(get_ns=lambda _: ns, get_random=lambda: Random(42))
        node.apply_effects(ctx=ctx)
        assert ns["coin"] is True


# ============================================================================
# TraversableEdge
# ============================================================================


class TestTraversableEdge:
    """Persistent graph edge with traversal metadata."""

    def test_default_phases_are_none(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        assert e.entry_phase is None
        assert e.return_phase is None
        assert e.trigger_phase is None

    def test_entry_phase_set(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            entry_phase=ResolutionPhase.UPDATE,
        )
        assert e.entry_phase == ResolutionPhase.UPDATE

    def test_call_edge_return(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        call = _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )
        ret = call.get_return_edge()
        assert isinstance(ret, AnonymousEdge)
        assert ret.successor is a
        assert ret.entry_phase == ResolutionPhase.UPDATE

    def test_non_call_edge_return_raises(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        with pytest.raises(ValueError, match="not a call edge"):
            e.get_return_edge()

    def test_call_edge_without_predecessor_raises(self) -> None:
        g = Graph()
        b = _node(g, label="b")
        e = _edge(g, successor_id=b.uid, return_phase=ResolutionPhase.UPDATE)
        with pytest.raises(ValueError, match="no predecessor"):
            e.get_return_edge()

    def test_trigger_phase_for_auto_redirect(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )
        assert e.trigger_phase == ResolutionPhase.PREREQS

    def test_phase_fields_have_distinct_semantics(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            trigger_phase=ResolutionPhase.PREREQS,
            entry_phase=ResolutionPhase.UPDATE,
            return_phase=ResolutionPhase.POSTREQS,
        )
        assert e.trigger_phase == ResolutionPhase.PREREQS
        assert e.entry_phase == ResolutionPhase.UPDATE
        ret = e.get_return_edge()
        assert ret.entry_phase == ResolutionPhase.POSTREQS

    def test_predecessor_successor_narrowing(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        assert e.predecessor is a
        assert e.successor is b

    def test_property_setters_delegate_to_core_edge_accessors(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        e.successor = c
        e.predecessor = b
        assert e.successor is c
        assert e.predecessor is b

    def test_available_delegates_to_successor(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b", availability=[Predicate(expr="False")])
        e = _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        assert e.available() is False


# ============================================================================
# AnonymousEdge
# ============================================================================


class TestAnonymousEdge:
    """Lightweight transient edge — no graph, no UUID."""

    def test_minimal_construction(self) -> None:
        g = Graph()
        b = _node(g, label="b")
        e = AnonymousEdge(successor=b)
        assert e.successor is b
        assert e.predecessor is None
        assert e.entry_phase is None

    def test_full_construction(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = AnonymousEdge(predecessor=a, successor=b, entry_phase=ResolutionPhase.UPDATE)
        assert e.predecessor is a
        assert e.successor is b
        assert e.entry_phase == ResolutionPhase.UPDATE

    def test_repr_includes_labels(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        e = AnonymousEdge(predecessor=a, successor=b)
        r = repr(e)
        assert "a" in r and "b" in r

    def test_no_return_phase(self) -> None:
        """AnonymousEdge is never a call edge — no return_phase attribute."""
        g = Graph()
        b = _node(g, label="b")
        e = AnonymousEdge(successor=b)
        assert not hasattr(e, "return_phase")

    def test_available_delegates_to_successor(self) -> None:
        g = Graph()
        b = _node(g, label="b", availability=[Predicate(expr="False")])
        e = AnonymousEdge(successor=b)
        assert e.available() is False


# ============================================================================
# Doctest regression
# ============================================================================


class TestTraversableDocExamples:
    """Regression coverage for ``traversable`` doctest examples."""

    def test_doctest_examples_run_under_std_runner(self) -> None:
        finder = doctest.DocTestFinder()
        runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)

        for test in finder.find(traversable_module):
            runner.run(test)

        result = runner.summarize(verbose=False)
        assert result.failed == 0


class TestTraversalContractValidation:
    def test_valid_container_has_no_issues(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        source = _node(g, label="entry")
        sink = _node(g, label="exit")
        container.add_child(source)
        container.add_child(sink)
        container.source_id = source.uid
        container.sink_id = sink.uid

        assert validate_traversal_contracts(g) == []
        assert_traversal_contracts(g)

    def test_unresolved_source_reports_issue(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        container.source_id = uuid4()

        issues = validate_traversal_contracts(g)
        assert any("source_id" in issue for issue in issues)
        assert any("sink_id is missing" in issue for issue in issues)
        with pytest.raises(ValueError, match="Traversal contract validation failed"):
            assert_traversal_contracts(g)

    def test_sink_not_member_reports_issue(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        source = _node(g, label="entry")
        sink = _node(g, label="elsewhere")
        container.add_child(source)
        container.source_id = source.uid
        container.sink_id = sink.uid

        issues = validate_traversal_contracts(g)
        assert any("sink" in issue and "not a member/child" in issue for issue in issues)

    def test_source_without_sink_reports_issue(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        source = _node(g, label="entry")
        container.add_child(source)
        container.source_id = source.uid

        issues = validate_traversal_contracts(g)
        assert any("source_id is set but sink_id is missing" in issue for issue in issues)

    def test_sink_without_source_reports_issue(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        sink = _node(g, label="exit")
        container.add_child(sink)
        container.sink_id = sink.uid

        issues = validate_traversal_contracts(g)
        assert any("sink_id is set but source_id is missing" in issue for issue in issues)
