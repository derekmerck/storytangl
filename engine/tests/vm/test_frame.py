"""Contract tests for ``tangl.vm.runtime.frame``.

Organized by concept:
- PhaseCtx: namespace caching, registry assembly
- Frame.follow_edge: pipeline execution, entry_phase skipping
- Frame.resolve_choice: redirect chaining, return stack, recursion guard
- Frame.goto_node: forced jump
"""

from __future__ import annotations

import logging

import pytest

from tangl.core import (
    BehaviorRegistry,
    DispatchLayer,
    EntityTemplate,
    Graph,
    GraphFactory,
    OrderedRegistry,
    Record,
    Selector,
    TemplateRegistry,
)
from tangl.vm.dispatch import (
    on_provision,
    on_journal,
    on_prereqs,
    on_postreqs,
    on_update,
    on_validate,
)
from tangl.vm.factory import TraversableGraphFactory
from tangl.vm.resolution_phase import ResolutionPhase
from tangl.vm.runtime.frame import Frame, PhaseCtx
from tangl.vm.traversable import (
    AnonymousEdge,
    TraversableEdge,
    TraversableNode,
)


def _node(graph: Graph, **kwargs) -> TraversableNode:
    node = TraversableNode(**kwargs)
    graph.add(node)
    return node


def _edge(graph: Graph, **kwargs) -> TraversableEdge:
    edge = TraversableEdge(**kwargs)
    graph.add(edge)
    return edge


class RefTraversableEdge(TraversableEdge):
    """Test edge exposing factory predecessor/successor refs."""

    predecessor_ref: bytes | None = None
    successor_ref: str | None = None


class FrameFactoryTestDouble(TraversableGraphFactory):
    """Test-local singleton subclass used for VM frame factory coverage."""


# ============================================================================
# Helpers
# ============================================================================

class SimpleFragment(Record):
    content: str = ""


def _simple_graph(*labels: str) -> tuple[Graph, list[TraversableNode]]:
    """Quick linear graph: a→b→c..."""
    g = Graph()
    nodes = [_node(g, label=lbl) for lbl in labels]
    for i in range(len(nodes) - 1):
        _edge(g, predecessor_id=nodes[i].uid,
            successor_id=nodes[i + 1].uid,
        )
    return g, nodes


def _factory_graph(*labels: str) -> tuple[Graph, list[TraversableNode], TraversableEdge]:
    """Build a linear traversable graph through the VM factory."""
    FrameFactoryTestDouble.clear_instances()
    template_registry = TemplateRegistry(label="frame_factory_templates")
    templates = [
        EntityTemplate(label=label, payload=TraversableNode(label=label), registry=template_registry)
        for label in labels
    ]
    for index in range(len(templates) - 1):
        EntityTemplate(
            label=f"{labels[index]}.go",
            payload=RefTraversableEdge(
                label=f"{labels[index]}_go",
                predecessor_ref=templates[index].content_hash(),
                successor_ref=labels[index + 1],
            ),
            registry=template_registry,
        )

    factory = FrameFactoryTestDouble(label="frame_factory", templates=template_registry)
    graph = factory.materialize_graph()
    nodes = [graph.find_node(Selector(label=label)) for label in labels]
    edge = graph.find_edge(Selector(label=f"{labels[0]}_go"))
    assert all(isinstance(node, TraversableNode) for node in nodes)
    assert isinstance(edge, TraversableEdge)
    return graph, nodes, edge


# ============================================================================
# PhaseCtx
# ============================================================================


class TestPhaseCtx:
    def test_authorities_default_empty_for_plain_graph(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        ctx = PhaseCtx(graph=g, cursor_id=a.uid)
        authorities = ctx.get_authorities()
        assert authorities == []

    def test_ns_caching(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        a.locals = {"key": "val"}

        @on_journal  # just to have _something_ registered, ns uses gather_ns
        def _noop(*, caller, ctx, **kw):
            return None

        from tangl.vm.dispatch import on_gather_ns
        @on_gather_ns
        def _locals(*, caller, ctx, **kw):
            if hasattr(caller, "locals") and caller.locals:
                return dict(caller.locals)

        ctx = PhaseCtx(graph=g, cursor_id=a.uid)
        ns1 = ctx.get_ns(a)
        ns2 = ctx.get_ns(a)
        # Same object — cached
        assert ns1 is ns2

    def test_step_passes_through_constructor(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        ctx = PhaseCtx(graph=g, cursor_id=a.uid, step=9)
        assert ctx.step == 9

    def test_derive_copies_runtime_state_and_resets_per_pass_fields(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        authority = BehaviorRegistry(label="local")
        inline_behavior = lambda **_: None
        logger = logging.getLogger("phase-ctx-derive")
        transitions: list[tuple[str, str | None]] = []

        def _escalate(reason: str, step_id: str | None = None) -> bool:
            transitions.append((reason, step_id))
            return True

        ctx = PhaseCtx(
            graph=g,
            cursor_id=a.uid,
            step=9,
            current_phase=ResolutionPhase.UPDATE,
            correlation_id="corr-1",
            logger=logger,
            meta={"base": "meta"},
            inline_behaviors=[inline_behavior],
            local_authorities=[authority],
            incoming_payload={"kind": "payload"},
            escalate_to_hard_dirty_callback=_escalate,
        )
        ctx.push_result("parent-result")
        ctx._ns_cache[a.uid] = {}

        derived = ctx.derive(
            meta_overrides={"request_ctx_path": "scene.entry"},
        )

        assert derived is not ctx
        assert derived.graph is g
        assert derived.cursor_id == a.uid
        assert derived.step == 9
        assert derived.current_phase is ResolutionPhase.INIT
        assert derived.correlation_id == "corr-1"
        assert derived.logger is logger
        assert derived.meta == {
            "base": "meta",
            "request_ctx_path": "scene.entry",
        }
        assert derived.random is ctx.random
        assert derived.inline_behaviors == [inline_behavior]
        assert derived.inline_behaviors is not ctx.inline_behaviors
        assert derived.local_authorities == [authority]
        assert derived.local_authorities is not ctx.local_authorities
        assert derived.incoming_payload == {"kind": "payload"}
        assert derived.results == []
        assert derived._ns_cache == {}
        assert derived._result_pipe_stack == [[]]
        assert ctx.results == ["parent-result"]

    def test_authorities_include_graph_authorities_when_available(self) -> None:
        authority = BehaviorRegistry(
            label="story.auth",
            default_dispatch_layer=DispatchLayer.APPLICATION,
        )

        class AuthorityGraph(Graph):
            def get_authorities(self):
                return [authority]

        g = AuthorityGraph()
        a = _node(g, label="a")
        ctx = PhaseCtx(graph=g, cursor_id=a.uid)
        authorities = ctx.get_authorities()
        assert authority in authorities

    def test_authorities_include_explicit_local_authorities(self) -> None:
        authority = BehaviorRegistry(
            label="frame.local.auth",
            default_dispatch_layer=DispatchLayer.LOCAL,
        )
        g = Graph()
        a = _node(g, label="a")
        ctx = PhaseCtx(graph=g, cursor_id=a.uid, local_authorities=[authority])
        authorities = ctx.get_authorities()
        assert authority in authorities

    def test_location_groups_include_immediate_neighbors_at_distance_zero(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")
        _edge(g, predecessor_id=a.uid, successor_id=b.uid)
        _edge(g, predecessor_id=c.uid, successor_id=a.uid)

        ctx = PhaseCtx(graph=g, cursor_id=a.uid)
        groups = ctx.get_location_entity_groups()
        assert groups
        near_ids = {node.uid for node in groups[0]}
        assert a.uid in near_ids
        assert b.uid in near_ids
        assert c.uid in near_ids

    def test_with_subdispatch_context_manager_yields_ctx(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        ctx = PhaseCtx(graph=g, cursor_id=a.uid)
        with ctx.with_subdispatch() as nested:
            assert nested is ctx

    def test_template_scope_groups_resolve_via_graph_factory_authority(self) -> None:
        class TestFactory(GraphFactory):
            def get_template_scope_groups(self, *, caller=None, graph=None):
                return [marker]

        marker = TemplateRegistry(label="marker")
        TestFactory.clear_instances()
        try:
            factory = TestFactory(label="phase_ctx_scope_factory")
            g = Graph()
            g.bind_factory(factory)
            a = _node(g, label="a")
            ctx = PhaseCtx(graph=g, cursor_id=a.uid)

            assert ctx.get_template_scope_groups() == [marker]
        finally:
            TestFactory.clear_instances()

    def test_template_scope_groups_fall_back_to_graph_factory_templates(self) -> None:
        class TestFactory(GraphFactory):
            pass

        TestFactory.clear_instances()
        try:
            marker = TemplateRegistry(label="factory_templates")
            factory = TestFactory(label="phase_ctx_factory", templates=marker)
            g = Graph()
            g.bind_factory(factory)
            a = _node(g, label="a")

            ctx = PhaseCtx(graph=g, cursor_id=a.uid)

            assert ctx.get_template_scope_groups() == [marker]
        finally:
            TestFactory.clear_instances()


class TestFrameRandomDeterminism:
    def test_same_inputs_seed_same_sequence(self) -> None:
        g, [a] = _simple_graph("a")
        frame_a = Frame(graph=g, cursor=a, step_base=2)
        frame_b = Frame(graph=g, cursor=a, step_base=2)

        ctx_a = frame_a._make_ctx()
        ctx_b = frame_b._make_ctx()
        seq_a = [ctx_a.get_random().random() for _ in range(5)]
        seq_b = [ctx_b.get_random().random() for _ in range(5)]
        assert seq_a == seq_b

    def test_step_base_changes_sequence(self) -> None:
        g, [a] = _simple_graph("a")
        frame_a = Frame(graph=g, cursor=a, step_base=2)
        frame_b = Frame(graph=g, cursor=a, step_base=3)

        ctx_a = frame_a._make_ctx()
        ctx_b = frame_b._make_ctx()
        seq_a = [ctx_a.get_random().random() for _ in range(3)]
        seq_b = [ctx_b.get_random().random() for _ in range(3)]
        assert seq_a != seq_b


# ============================================================================
# Frame.follow_edge — basic pipeline
# ============================================================================


class TestFollowEdge:
    def test_moves_cursor(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        edge = AnonymousEdge(predecessor=a, successor=b)
        frame.follow_edge(edge)
        assert frame.cursor is b

    def test_increments_cursor_steps(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        assert frame.cursor_steps == 1

    def test_records_cursor_trace(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        assert frame.cursor_trace == [b.uid]

    def test_no_redirect_returns_none(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        result = frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        assert result is None

    def test_journal_output_appended(self) -> None:
        """Journal handler output goes to the output stream."""
        frag = SimpleFragment(content="hello")

        @on_journal
        def emit(*, caller, ctx, **kw):
            return frag

        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        assert frag in list(frame.output_stream.values())

    def test_journal_list_output_flattened(self) -> None:
        """Journal returning a list appends each fragment."""
        f1 = SimpleFragment(content="one")
        f2 = SimpleFragment(content="two")

        @on_journal
        def emit(*, caller, ctx, **kw):
            return [f1, f2]

        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        values = list(frame.output_stream.values())
        assert f1 in values and f2 in values

    def test_journal_mutation_logs_debug_diagnostic(self, caplog: pytest.LogCaptureFixture) -> None:
        @on_journal
        def mutate(*, caller, ctx, **kw):
            if hasattr(caller, "locals"):
                caller.locals["journal_mark"] = "set"
            return None

        g, [a, b] = _simple_graph("a", "b")
        b.locals = {}
        frame = Frame(graph=g, cursor=a)
        caplog.set_level(logging.DEBUG, logger="tangl.vm.runtime.frame")

        frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))

        assert any(
            "JOURNAL mutation detected" in record.message for record in caplog.records
        )

    def test_frame_local_behaviors_participate_as_context_authorities(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        b.locals = {}
        frame = Frame(graph=g, cursor=a)

        frame.local_behaviors.register(
            task="apply_update",
            func=lambda *, caller, ctx, **_: caller.locals.__setitem__("frame_local", True),
        )

        frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        assert b.locals["frame_local"] is True

    def test_planning_phase_runs_on_factory_built_traversable_graph(self, clean_vm_dispatch) -> None:
        provisioned: list[str] = []

        @on_provision
        def track(*, caller, ctx, **kw):
            provisioned.append(caller.label)
            return None

        graph, nodes, edge = _factory_graph("start", "next")
        start, _next = nodes

        try:
            frame = Frame(graph=graph, cursor=start)
            frame.follow_edge(edge)
        finally:
            FrameFactoryTestDouble.clear_instances()

        assert "next" in provisioned


class TestFollowEdgeEntryPhase:
    """entry_phase controls which pipeline phases are skipped."""

    def test_entry_at_update_skips_validate_and_planning(self) -> None:
        validate_called = []

        @on_validate
        def track(*, caller, ctx, **kw):
            validate_called.append(True)
            return True

        g, [a, b] = _simple_graph("a", "b")
        edge = AnonymousEdge(
            predecessor=a, successor=b,
            entry_phase=ResolutionPhase.UPDATE,
        )
        frame = Frame(graph=g, cursor=a)
        frame.follow_edge(edge)
        assert frame.cursor is b
        # Validate should NOT have been called
        assert len(validate_called) == 0

    def test_validation_failure_raises(self) -> None:
        @on_validate
        def block(*, caller, ctx, **kw):
            return False

        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        with pytest.raises(ValueError, match="validation failed"):
            frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))


class TestFollowEdgeRedirects:
    """PREREQS and POSTREQS can return edges for redirection."""

    def test_prereq_redirect(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")

        @on_prereqs
        def redirect_to_c(*, caller, ctx, **kw):
            if caller is b:
                return AnonymousEdge(predecessor=b, successor=c)
            return None

        frame = Frame(graph=g, cursor=a)
        result = frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        # follow_edge returns the redirect edge
        assert result is not None
        assert result.successor is c
        assert frame.last_redirect is not None
        assert frame.last_redirect["phase"] == "prereqs"
        assert frame.last_redirect["successor_id"] == str(c.uid)
        assert len(frame.redirect_trace) == 1

    def test_postreq_redirect(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")

        @on_postreqs
        def redirect_to_c(*, caller, ctx, **kw):
            if caller is b:
                return AnonymousEdge(predecessor=b, successor=c)
            return None

        frame = Frame(graph=g, cursor=a)
        result = frame.follow_edge(AnonymousEdge(predecessor=a, successor=b))
        assert result is not None
        assert result.successor is c
        assert frame.last_redirect is not None
        assert frame.last_redirect["phase"] == "postreqs"
        assert frame.last_redirect["successor_id"] == str(c.uid)
        assert len(frame.redirect_trace) == 1


# ============================================================================
# Frame.resolve_choice — the main loop
# ============================================================================


class TestResolveChoice:
    def test_simple_move_to_leaf(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(AnonymousEdge(predecessor=a, successor=b))
        assert frame.cursor is b

    def test_update_ctx_exposes_selected_payload_from_edge(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        captured: list[tuple[object, object]] = []

        @on_update
        def capture_payload(*, caller, ctx, **kw):
            if caller is b:
                captured.append((ctx.selected_edge, ctx.selected_payload))
            return None

        edge = AnonymousEdge(predecessor=a, successor=b)
        edge.payload = {"move": "rock"}  # dynamic attribute for anonymous traversal edges
        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(edge)

        assert captured
        assert captured[-1][0] is edge
        assert captured[-1][1] == {"move": "rock"}
        assert frame.selected_payload == {"move": "rock"}

    def test_choice_payload_overrides_and_merges_edge_payload(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        seen: list[object] = []

        @on_update
        def capture_payload(*, caller, ctx, **kw):
            if caller is b:
                seen.append(ctx.selected_payload)
            return None

        edge = AnonymousEdge(predecessor=a, successor=b)
        edge.payload = {"move": "knight", "from": "g8", "to": "f6"}
        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(edge, choice_payload={"to": "e7", "capture": "queen"})

        assert seen
        assert seen[-1] == {
            "move": "knight",
            "from": "g8",
            "to": "e7",
            "capture": "queen",
        }

    def test_follows_redirect_chain(self) -> None:
        """a→b redirects to c via prereqs."""
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")
        c = _node(g, label="c")

        @on_prereqs
        def redirect(*, caller, ctx, **kw):
            if caller is b:
                return AnonymousEdge(predecessor=b, successor=c)
            return None

        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(AnonymousEdge(predecessor=a, successor=b))
        # Lands on c after the redirect chain
        assert frame.cursor is c
        assert frame.cursor_trace == [b.uid, c.uid]

    def test_recursion_guard(self) -> None:
        """Infinite redirect loop raises RecursionError."""
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")

        @on_prereqs
        def infinite_loop(*, caller, ctx, **kw):
            if caller is a:
                return AnonymousEdge(predecessor=a, successor=b)
            elif caller is b:
                return AnonymousEdge(predecessor=b, successor=a)
            return None

        frame = Frame(graph=g, cursor=a)
        with pytest.raises(RecursionError, match="exceeded"):
            frame.resolve_choice(AnonymousEdge(predecessor=a, successor=b))


class TestResolveChoiceReturnStack:
    """Call edges push to return stack; terminals pop back."""

    def test_direct_call_edge_pushes_and_returns(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")

        call_edge = _edge(
            g,
            predecessor_id=a.uid,
            successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )

        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(call_edge)
        assert frame.cursor is a

    def test_call_and_return(self) -> None:
        g = Graph()
        a = _node(g, label="a")
        b = _node(g, label="b")

        # a→b is a call edge: push b, return to a at UPDATE
        call_edge = _edge(g, predecessor_id=a.uid, successor_id=b.uid,
            return_phase=ResolutionPhase.UPDATE,
        )

        # When we visit b, PREREQS returns the call_edge as a redirect
        # Then when b pipeline completes (no redirect), return stack pops
        # to a at UPDATE.
        # Actually, let's set up a prereq that returns the call edge to b
        @on_prereqs
        def trigger_call(*, caller, ctx, **kw):
            if caller is a:
                return call_edge
            return None

        frame = Frame(graph=g, cursor=a)
        frame.resolve_choice(AnonymousEdge(predecessor=a, successor=a))
        # After: a PREREQS → call_edge(a→b) pushed, follow b,
        # b completes cleanly, pop stack → return to a at UPDATE
        # Should end on a (returned)
        assert frame.cursor is a


# ============================================================================
# Frame.goto_node
# ============================================================================


class TestGotoNode:
    def test_goto_moves_cursor(self) -> None:
        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        frame.goto_node(b)
        assert frame.cursor is b

    def test_goto_skips_validation(self) -> None:
        called = []

        @on_validate
        def block(*, caller, ctx, **kw):
            called.append(True)
            return False  # Would block normal follow_edge

        g, [a, b] = _simple_graph("a", "b")
        frame = Frame(graph=g, cursor=a)
        # goto_node starts at PLANNING, skipping VALIDATE
        frame.goto_node(b)
        assert frame.cursor is b
        assert len(called) == 0
