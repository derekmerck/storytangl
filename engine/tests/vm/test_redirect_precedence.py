"""Precedence matrix for PREREQS / POSTREQS redirects.

``get_prereqs`` and ``get_postreqs`` fold with :meth:`CallReceipt.first_result`, so a
redirect **intercepts**: the first handler to return an edge claims the traversal and
nothing downstream can un-claim it. Which handler gets there first is decided by
``Behavior.sort_key``, whose first element is the dispatch layer.

Existing tests cover the pieces in isolation — layer sorting, authority-chain assembly,
``first_result``, handler redirects, declarative trigger edges. This module covers the
*combination*: several simultaneous redirect claims at different layers, conditional
abstention, and an assertion about which destination actually wins.

These are **contract tests**. They pin registry reach independently from dispatch order:
the ``SYSTEM`` trigger-edge scanner preempts ``APPLICATION`` by design, while an explicit
``GLOBAL`` claim can hard-intercept it. A handler's layer never changes which authority
chains can see its registry.
"""

from __future__ import annotations

import pytest

from tangl.core import BehaviorRegistry, DispatchLayer, Selector
from tangl.vm.dispatch import dispatch as vm_dispatch, do_prereqs, on_prereqs
from tangl.vm.resolution_phase import ResolutionPhase
from tangl.vm.system_handlers import follow_triggered_prereqs

from .conftest import _edge, _node


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def crossing(graph):
    """Origin with two reachable destinations, plus a spare for global redirects.

    Returns ``(origin, regular, collapse, outro)``. No edge is triggered by default.
    """
    origin = _node(graph, label="bridge_approach")
    regular = _node(graph, label="far_side")
    collapse = _node(graph, label="abyss")
    outro = _node(graph, label="subscribe_outro")
    _edge(graph, predecessor_id=origin.uid, successor_id=regular.uid)
    return origin, regular, collapse, outro


@pytest.fixture
def scanner():
    """Re-register the real declarative trigger-edge scanner at its own layer.

    The autouse ``clean_vm_dispatch`` fixture clears ``vm_dispatch``, which removes the
    system handlers. Tests that exercise declarative ``trigger_phase`` edges need the
    genuine article back. ``BehaviorRegistry.register`` returns the decorated function
    and stashes the Behavior on ``func._behavior``, so re-adding *that* restores the
    real registration — including its SYSTEM layer — rather than re-deriving one.
    """
    behavior = follow_triggered_prereqs._behavior
    vm_dispatch.add(behavior)
    return behavior


def _claim(edge, *, layer, calls=None, name=None, when=lambda **kw: True):
    """Build a redirect handler that claims ``edge`` when ``when`` passes."""

    def handler(*, caller, ctx, **kw):
        if calls is not None:
            calls.append(name or layer.name)
        return edge if when(caller=caller, ctx=ctx, **kw) else None

    handler.__name__ = f"claim_{name or layer.name.lower()}"
    return handler


def _world_registry(label="world_dispatch", layer=DispatchLayer.AUTHOR):
    """A world's own authority registry, as ``World.get_authorities()`` would supply."""
    return BehaviorRegistry(label=label, default_dispatch_layer=layer)


# ---------------------------------------------------------------------------
# The ladder
# ---------------------------------------------------------------------------


class TestRedirectLadder:
    """Which layer's claim survives when several handlers all return an edge."""

    def test_global_beats_every_later_layer(self, graph, crossing, null_ctx):
        origin, regular, collapse, outro = crossing
        to_outro = _edge(graph, predecessor_id=origin.uid, successor_id=outro.uid)
        to_collapse = _edge(graph, predecessor_id=origin.uid, successor_id=collapse.uid)

        on_prereqs(_claim(to_collapse, layer=DispatchLayer.AUTHOR),
                   dispatch_layer=DispatchLayer.AUTHOR)
        on_prereqs(_claim(to_collapse, layer=DispatchLayer.APPLICATION),
                   dispatch_layer=DispatchLayer.APPLICATION)
        on_prereqs(_claim(to_outro, layer=DispatchLayer.GLOBAL),
                   dispatch_layer=DispatchLayer.GLOBAL)

        result = do_prereqs(origin, ctx=null_ctx)
        assert result is to_outro
        assert result.successor.get_label() == "subscribe_outro"

    def test_application_beats_author(self, graph, crossing, null_ctx):
        origin, regular, collapse, outro = crossing
        to_outro = _edge(graph, predecessor_id=origin.uid, successor_id=outro.uid)
        to_collapse = _edge(graph, predecessor_id=origin.uid, successor_id=collapse.uid)

        on_prereqs(_claim(to_collapse, layer=DispatchLayer.AUTHOR),
                   dispatch_layer=DispatchLayer.AUTHOR)
        on_prereqs(_claim(to_outro, layer=DispatchLayer.APPLICATION),
                   dispatch_layer=DispatchLayer.APPLICATION)

        assert do_prereqs(origin, ctx=null_ctx) is to_outro

    def test_same_layer_falls_through_to_registration_order(self, graph, crossing, null_ctx):
        """Peers at one layer resolve by ``seq`` — first registered wins."""
        origin, regular, collapse, outro = crossing
        first = _edge(graph, predecessor_id=origin.uid, successor_id=collapse.uid)
        second = _edge(graph, predecessor_id=origin.uid, successor_id=outro.uid)

        on_prereqs(_claim(first, layer=DispatchLayer.AUTHOR, name="first"),
                   dispatch_layer=DispatchLayer.AUTHOR)
        on_prereqs(_claim(second, layer=DispatchLayer.AUTHOR, name="second"),
                   dispatch_layer=DispatchLayer.AUTHOR)

        assert do_prereqs(origin, ctx=null_ctx) is first


# ---------------------------------------------------------------------------
# The declarative scanner's position — issue #360
# ---------------------------------------------------------------------------


class TestTriggerEdgePrecedence:
    """Where the declarative ``trigger_phase`` surface sits in the ladder."""

    def test_system_trigger_edge_preempts_application_handler(
        self, graph, crossing, null_ctx, scanner
    ):
        """The VM's declarative trigger scanner claims before application handlers.

        The edge carries authored data, but the scanner interpreting ``trigger_phase``
        is VM infrastructure registered at SYSTEM (1), before APPLICATION (2).
        """
        origin, regular, collapse, outro = crossing
        to_outro = _edge(graph, predecessor_id=origin.uid, successor_id=outro.uid)
        to_collapse = _edge(
            graph,
            predecessor_id=origin.uid,
            successor_id=collapse.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )

        on_prereqs(_claim(to_outro, layer=DispatchLayer.APPLICATION),
                   dispatch_layer=DispatchLayer.APPLICATION)

        result = do_prereqs(origin, ctx=null_ctx)
        assert result is to_collapse, "the SYSTEM trigger scanner beats APPLICATION"
        assert result.successor.get_label() == "abyss"

    def test_global_handler_beats_system_trigger_edge(
        self, graph, crossing, null_ctx, scanner
    ):
        """GLOBAL is the intentional hard-interception band."""
        origin, regular, collapse, outro = crossing
        to_outro = _edge(graph, predecessor_id=origin.uid, successor_id=outro.uid)
        _edge(
            graph,
            predecessor_id=origin.uid,
            successor_id=collapse.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )

        on_prereqs(_claim(to_outro, layer=DispatchLayer.GLOBAL),
                   dispatch_layer=DispatchLayer.GLOBAL)

        result = do_prereqs(origin, ctx=null_ctx)
        assert result is to_outro
        assert result.successor.get_label() == "subscribe_outro"


# ---------------------------------------------------------------------------
# Abstention
# ---------------------------------------------------------------------------


class TestAbstention:
    """Returning ``None`` is how a handler declines to claim the traversal."""

    def test_abstaining_layer_yields_to_the_next(self, graph, crossing, null_ctx):
        origin, regular, collapse, outro = crossing
        to_collapse = _edge(graph, predecessor_id=origin.uid, successor_id=collapse.uid)

        on_prereqs(_claim(None, layer=DispatchLayer.GLOBAL, when=lambda **kw: False),
                   dispatch_layer=DispatchLayer.GLOBAL)
        on_prereqs(_claim(to_collapse, layer=DispatchLayer.AUTHOR),
                   dispatch_layer=DispatchLayer.AUTHOR)

        assert do_prereqs(origin, ctx=null_ctx) is to_collapse

    def test_all_abstaining_means_no_redirect(self, graph, crossing, null_ctx):
        origin, regular, collapse, outro = crossing

        for layer in (DispatchLayer.GLOBAL, DispatchLayer.APPLICATION, DispatchLayer.AUTHOR):
            on_prereqs(_claim(None, layer=layer, when=lambda **kw: False),
                       dispatch_layer=layer)

        assert do_prereqs(origin, ctx=null_ctx) is None

    def test_conditional_world_redirect_abstains_when_prerequisite_met(
        self, graph, crossing, ctx_factory
    ):
        """The bridge: collapse when the crossing prerequisite was not met, else abstain.

        Abstention is what lets the regular crossing happen — the redirect is an
        alternate destination, not a failure.
        """
        origin, regular, collapse, outro = crossing
        to_collapse = _edge(graph, predecessor_id=origin.uid, successor_id=collapse.uid)

        world = _world_registry()
        world.register(
            func=_claim(
                to_collapse,
                layer=DispatchLayer.AUTHOR,
                when=lambda *, ctx, **kw: not getattr(ctx, "rope_secured", False),
            ),
            task="get_prereqs",
        )

        unprepared = ctx_factory(registries=[world])
        unprepared.rope_secured = False
        assert do_prereqs(origin, ctx=unprepared) is to_collapse

        prepared = ctx_factory(registries=[world])
        prepared.rope_secured = True
        assert do_prereqs(origin, ctx=prepared) is None, "prepared crossing is not redirected"


# ---------------------------------------------------------------------------
# Folds select; they do not gate
# ---------------------------------------------------------------------------


class TestFoldDoesNotGateExecution:
    def test_every_handler_runs_even_after_a_winner_is_found(self, graph, crossing, null_ctx):
        """``first_result`` selects over completed calls — later handlers still execute."""
        origin, regular, collapse, outro = crossing
        to_outro = _edge(graph, predecessor_id=origin.uid, successor_id=outro.uid)
        to_collapse = _edge(graph, predecessor_id=origin.uid, successor_id=collapse.uid)
        calls: list[str] = []

        on_prereqs(_claim(to_outro, layer=DispatchLayer.GLOBAL, calls=calls),
                   dispatch_layer=DispatchLayer.GLOBAL)
        on_prereqs(_claim(to_collapse, layer=DispatchLayer.APPLICATION, calls=calls),
                   dispatch_layer=DispatchLayer.APPLICATION)
        on_prereqs(_claim(to_collapse, layer=DispatchLayer.AUTHOR, calls=calls),
                   dispatch_layer=DispatchLayer.AUTHOR)

        assert do_prereqs(origin, ctx=null_ctx) is to_outro
        assert calls == ["GLOBAL", "APPLICATION", "AUTHOR"], (
            "all handlers execute in ladder order despite GLOBAL winning"
        )


# ---------------------------------------------------------------------------
# The four scoping patterns
# ---------------------------------------------------------------------------


class TestScopingPatterns:
    """Each redirect scope reaches its destination when nothing above it claims."""

    def test_world_specific_choice_to_alternate_destination(
        self, graph, crossing, ctx_factory
    ):
        """One world, one situation — a handler in that world's own registry."""
        origin, regular, collapse, outro = crossing
        to_collapse = _edge(graph, predecessor_id=origin.uid, successor_id=collapse.uid)

        world = _world_registry()
        world.register(
            func=_claim(
                to_collapse,
                layer=DispatchLayer.AUTHOR,
                when=lambda *, caller, **kw: caller.get_label() == "bridge_approach",
            ),
            task="get_prereqs",
        )

        ctx = ctx_factory(registries=[world])
        assert do_prereqs(origin, ctx=ctx) is to_collapse
        assert do_prereqs(regular, ctx=ctx) is None, "other nodes are unaffected"

    def test_any_choice_in_one_world_to_common_ending(self, graph, crossing, ctx_factory):
        """A broad handler in one world's registry — invisible to other worlds."""
        origin, regular, collapse, outro = crossing
        to_outro = _edge(graph, predecessor_id=origin.uid, successor_id=outro.uid)

        world = _world_registry()
        world.register(
            func=_claim(to_outro, layer=DispatchLayer.AUTHOR), task="get_prereqs"
        )

        in_world = ctx_factory(registries=[world])
        assert do_prereqs(origin, ctx=in_world) is to_outro
        assert do_prereqs(regular, ctx=in_world) is to_outro, "any node in this world"

        other_world = ctx_factory(registries=[_world_registry("other_world")])
        assert do_prereqs(origin, ctx=other_world) is None, (
            "registry membership scopes it — a different world never sees this handler"
        )

    def test_global_layer_in_world_registry_remains_world_private(
        self, graph, crossing, ctx_factory
    ):
        """An explicit layer override changes precedence, never registry reach."""
        origin, regular, collapse, outro = crossing
        to_outro = _edge(graph, predecessor_id=origin.uid, successor_id=outro.uid)

        world = _world_registry()
        world.register(
            func=_claim(to_outro, layer=DispatchLayer.GLOBAL),
            task="get_prereqs",
            dispatch_layer=DispatchLayer.GLOBAL,
        )

        assert do_prereqs(origin, ctx=ctx_factory(registries=[world])) is to_outro
        assert do_prereqs(
            origin,
            ctx=ctx_factory(registries=[_world_registry("other_world")]),
        ) is None

    def test_any_choice_in_any_world_to_system_interruption(
        self, graph, crossing, ctx_factory
    ):
        """A shared registry supplies broad reach; GLOBAL supplies hard precedence."""
        origin, regular, collapse, outro = crossing
        to_outro = _edge(graph, predecessor_id=origin.uid, successor_id=outro.uid)

        on_prereqs(_claim(to_outro, layer=DispatchLayer.GLOBAL),
                   dispatch_layer=DispatchLayer.GLOBAL)

        for registries in ([], [_world_registry()], [_world_registry("another")]):
            ctx = ctx_factory(registries=registries)
            assert do_prereqs(origin, ctx=ctx) is to_outro

    def test_specific_choice_in_specific_world_to_system_warning(
        self, graph, crossing, ctx_factory
    ):
        """A shared handler that inspects caller and world before claiming."""
        origin, regular, collapse, outro = crossing
        to_outro = _edge(graph, predecessor_id=origin.uid, successor_id=outro.uid)

        target_world = _world_registry("target_world")

        def in_target_world(*, ctx, **kw):
            return any(r.label == "target_world" for r in ctx.get_authorities())

        on_prereqs(
            _claim(
                to_outro,
                layer=DispatchLayer.GLOBAL,
                when=lambda *, caller, ctx, **kw: (
                    caller.get_label() == "bridge_approach" and in_target_world(ctx=ctx)
                ),
            ),
            dispatch_layer=DispatchLayer.GLOBAL,
        )

        hit = ctx_factory(registries=[target_world])
        assert do_prereqs(origin, ctx=hit) is to_outro

        wrong_node = ctx_factory(registries=[target_world])
        assert do_prereqs(regular, ctx=wrong_node) is None

        wrong_world = ctx_factory(registries=[_world_registry("elsewhere")])
        assert do_prereqs(origin, ctx=wrong_world) is None


# ---------------------------------------------------------------------------
# Guard: the scanner's layer is what the matrix above assumes
# ---------------------------------------------------------------------------


def test_trigger_scanner_registers_at_system_layer(scanner):
    """Declarative trigger interpretation remains VM infrastructure."""
    registered = [
        b for b in vm_dispatch.find_all(Selector(task="get_prereqs"))
        if b.func is follow_triggered_prereqs
    ]
    assert registered, "scanner not registered"
    # ``DispatchLayer`` is an IntEnum and the field round-trips as a plain int,
    # so compare by value rather than identity.
    assert registered[0].dispatch_layer == DispatchLayer.SYSTEM
    assert scanner.dispatch_layer == DispatchLayer.SYSTEM
