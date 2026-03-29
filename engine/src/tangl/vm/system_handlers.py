# tangl/vm/system_handlers.py
"""Default system-layer handlers for the VM phase pipeline.

This module registers the baseline behaviors that make the pipeline functional
out of the box.  They fire at ``DispatchLayer.SYSTEM`` (lowest priority layer),
so story-layer and application-layer handlers can override or extend them.

These handlers implement the VM's generic traversal mechanics.  They know about
graph topology, edge types, and the provisioning system, but nothing about
narrative semantics (scenes, characters, story structure).  Story-layer handlers
registered at ``APPLICATION`` or ``AUTHOR`` layers add domain-specific behavior
on top.

Handler Inventory
-----------------
**gather_ns** (namespace):
- ``contribute_runtime_baseline`` — inject ``cursor`` / ``graph`` symbols
- ``contribute_locals`` — inject ``caller.locals`` dict
- ``contribute_satisfied_deps`` — inject label→provider for satisfied deps

**validate_edge**:
- ``validate_successor_exists`` — successor must resolve from graph and be available

**get_prereqs** (PREREQS):
- ``descend_into_container`` — if cursor is_container, return enter() edge
- ``follow_triggered_prereqs`` — first available edge with trigger_phase=PREREQS

**apply_update** (UPDATE):
- ``apply_runtime_effects`` — apply node runtime effects to scoped namespace
- ``mark_visited`` — set ``caller.locals['_visited'] = True``, increment visit count

**render_journal** (JOURNAL):
- (no default — story layer provides content rendering)

**finalize_step** (FINALIZE):
- ``apply_final_runtime_effects`` — apply node/runtime finalize effects

**get_postreqs** (POSTREQS):
- ``follow_triggered_postreqs`` — first available edge with trigger_phase=POSTREQS

**provision_node** (PLANNING):
- Already registered by ``tangl.vm.provision.resolver.provision_node``

Usage
-----
Import this module to register the handlers::

    import tangl.vm.system_handlers  # registers all defaults

Or import selectively::

    from tangl.vm.system_handlers import descend_into_container

See Also
--------
:mod:`tangl.vm.dispatch`
    Registration and execution surface for hooks.
:mod:`tangl.vm.traversable`
    ``TraversableNode``, ``TraversableEdge``, ``AnonymousEdge`` types.
:mod:`tangl.vm.provision`
    ``Dependency``, ``Affordance``, and the ``Resolver`` that handles PLANNING.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING

from tangl.core import Node, Priority, Selector

from .dispatch import (
    on_gather_ns,
    on_validate,
    on_prereqs,
    on_update,
    on_journal,
    on_finalize,
    on_postreqs,
)
from .resolution_phase import ResolutionPhase
from .traversal import get_visit_count, is_first_visit, steps_since_last_visit
from .traversable import TraversableNode, TraversableEdge, AnonymousEdge

if TYPE_CHECKING:
    from .runtime.frame import PhaseCtx

logger = logging.getLogger(__name__)


def _ctx_cursor_history(ctx: "PhaseCtx | None") -> list[object]:
    if ctx is None:
        return []
    meta = ctx.get_meta() if hasattr(ctx, "get_meta") else {}
    if not isinstance(meta, Mapping):
        return []
    history = meta.get("cursor_history")
    return list(history) if isinstance(history, list) else []


# ---------------------------------------------------------------------------
# Namespace contributors
# ---------------------------------------------------------------------------

@on_gather_ns(
    wants_caller_kind=TraversableNode,
    wants_exact_kind=False,
    priority=Priority.FIRST,
)
def contribute_runtime_baseline(*, caller, ctx, **kw):
    """Inject context baseline symbols for runtime expressions."""
    graph = getattr(ctx, "graph", None)
    cursor = getattr(ctx, "cursor", None)
    result: dict[str, object] = {}
    if cursor is not None:
        result["cursor"] = cursor
    if graph is not None:
        result["graph"] = graph
    return result or None


@on_gather_ns(wants_caller_kind=TraversableNode, wants_exact_kind=False)
def contribute_locals(*, caller, ctx, **kw):
    """Inject ``caller.locals`` into the namespace.

    Any entity with a ``locals`` dict contributes its contents.  This is the
    primary mechanism for story-authored state: ``node.locals['mood'] = 'angry'``
    becomes available as ``ns['mood']`` in descendant scopes.

    This handler runs for the immediate caller only. Ancestor locals are
    included via phase-1 ``ancestor.get_ns()`` in ``do_gather_ns``.
    """
    if hasattr(caller, "locals") and caller.locals:
        return dict(caller.locals)
    return None


@on_gather_ns(wants_caller_kind=TraversableNode, wants_exact_kind=False)
def contribute_satisfied_deps(*, caller, ctx, **kw):
    """Inject satisfied dependency/affordance providers as named symbols.

    Walks caller scope from far to near (ancestors -> caller) and, for each
    satisfied ``Dependency`` or ``Affordance`` edge, contributes
    ``edge.label → edge.successor`` (the provider).

    Nearer scopes overwrite farther scopes for duplicate labels.

    This makes provisioned resources available by name in the namespace.
    For example, a scene with a satisfied ``"companion"`` dependency makes
    ``ns['companion']`` resolve to the companion entity.
    """
    # Lazy import to avoid circular dependency at module load
    from .provision import Dependency, Affordance

    result = {}
    scope_nodes = list(caller.ancestors) if hasattr(caller, "ancestors") else [caller]
    for scope in reversed(scope_nodes):
        for edge in scope.edges_out(Selector(has_kind=Dependency)):
            if edge.satisfied and edge.successor is not None:
                label = edge.get_label()
                if label:
                    result[label] = edge.successor

        for edge in scope.edges_out(Selector(has_kind=Affordance)):
            if edge.satisfied and edge.successor is not None:
                label = edge.get_label()
                if label:
                    result[label] = edge.successor

    return result if result else None


@on_gather_ns(wants_caller_kind=TraversableNode, wants_exact_kind=False)
def contribute_runtime_user_context(*, caller, ctx, **kw):
    """Inject runtime user symbols from frame metadata when available."""
    _ = (caller, kw)
    get_meta = getattr(ctx, "get_meta", None)
    if not callable(get_meta):
        return None

    meta = get_meta() or {}
    if not isinstance(meta, Mapping):
        return None

    user = meta.get("user")
    user_id = meta.get("user_id")
    user_ns = None
    get_user_ns = getattr(user, "get_ns", None)
    if callable(get_user_ns):
        user_ns = get_user_ns()
        if not isinstance(user_ns, Mapping):
            user_ns = None

    result: dict[str, object] = {}
    if user is not None:
        result["user"] = user
    if user_id is not None:
        result["user_id"] = user_id
    if user_ns:
        reserved = {"user", "user_id"}
        result.update({key: value for key, value in user_ns.items() if key not in reserved})
    return result or None


@on_gather_ns(wants_caller_kind=TraversableNode, wants_exact_kind=False)
def contribute_visit_stats(*, caller, ctx, **kw):
    """Inject generic visit statistics for the assembled caller namespace.

    ``node_completed`` intentionally aliases ``node_visited`` for the generic
    VM surface. Richer completion semantics remain a story/mechanics concern.
    """
    _ = kw
    history = _ctx_cursor_history(ctx)
    visit_count = get_visit_count(caller.uid, history)
    visited = visit_count > 0
    return {
        "node_visited": visited,
        "node_num_visits": visit_count,
        "node_steps_since": steps_since_last_visit(caller.uid, history),
        "node_completed": visited,
        "is_first_visit": is_first_visit(caller.uid, history),
    }


# ---------------------------------------------------------------------------
# VALIDATE — is the movement legal?
# ---------------------------------------------------------------------------

@on_validate
def validate_successor_exists(*, caller, ctx, **kw):
    """Check that successor resolves and traversal is available.

    This is the minimum traversal guard: destination exists and edge/node
    availability passes for the destination namespace.

    ``caller`` here is the edge being validated, not the destination node.
    """
    successor = getattr(caller, "successor", None)
    if successor is None:
        return False
    if hasattr(caller, "available"):
        return bool(caller.available(ctx=ctx))
    if hasattr(successor, "available"):
        ns = ctx.get_ns(successor) if ctx is not None and hasattr(ctx, "get_ns") else None
        return bool(successor.available(ns=ns))
    return True


# ---------------------------------------------------------------------------
# PREREQS — auto-redirect before player sees content
# ---------------------------------------------------------------------------

@on_prereqs
def descend_into_container(*, caller, ctx, **kw):
    """If the cursor is a container, redirect to its source member.

    This is the only special traversal logic in the whole system.  Everything
    else is generic pipeline execution.  Container descent chains naturally:
    if the source is also a container, its own PREREQS will fire
    ``descend_into_container`` again, descending further.

    Priority: EARLY-ish — should fire before triggered edge checks, because
    container descent takes precedence over edges originating from the
    container node itself (those edges would be choices WITHIN the container,
    not entries).
    """
    if isinstance(caller, TraversableNode) and caller.is_container:
        logger.debug("Container descent: %s → %s", caller.get_label(), caller.source.get_label())
        return caller.enter()
    return None


@on_prereqs
def follow_triggered_prereqs(*, caller, ctx, **kw):
    """Follow the first available auto-triggering PREREQS edge.

    Scans edges out from ``caller`` for ``TraversableEdge`` instances with
    ``trigger_phase == PREREQS``. Returns the first one whose guard
    condition passes against the current namespace.

    For v38 MVP, availability delegates to ``edge.available(ctx=ctx)``
    (which currently delegates to successor availability).

    This handler should fire AFTER ``descend_into_container`` — if the
    cursor is a container, descent takes priority.  We rely on registration
    order (container handler registered first) for this.
    """
    for edge in caller.edges_out():
        if not isinstance(edge, TraversableEdge):
            continue
        # trigger_phase controls auto-activation timing.
        # entry_phase controls where the pipeline starts after taking the edge.
        trigger = getattr(edge, "trigger_phase", None)
        if trigger == ResolutionPhase.PREREQS:
            if edge.successor is not None and edge.available(ctx=ctx):
                logger.debug("Prereq redirect: %s → %s", caller.get_label(), edge.successor.get_label())
                return edge

    return None


# ---------------------------------------------------------------------------
# UPDATE — mutate state for arrival
# ---------------------------------------------------------------------------

@on_update
def apply_runtime_effects(*, caller, ctx, **kw):
    """Apply UPDATE-phase runtime effects attached to the current node."""
    if hasattr(caller, "apply_effects"):
        caller.apply_effects(phase=ResolutionPhase.UPDATE, ctx=ctx)
    return None


@on_update
def mark_visited(*, caller, ctx, **kw):
    """Mark the cursor node as visited and increment visit count.

    Sets ``caller.locals['_visited'] = True`` and increments
    ``caller.locals['_visit_count']``.  These are available in the namespace
    for condition evaluation (e.g., ``visited(gutter)`` checks this flag,
    ``visit_count > 3`` triggers different content on repeat visits).

    Only fires on nodes that have a ``locals`` attribute (which includes
    any ``HierarchicalNode`` or story-layer block).
    """
    if not hasattr(caller, "locals"):
        return None

    if caller.locals is None:
        # Some models may initialize locals as None
        caller.locals = {}

    caller.locals["_visited"] = True
    caller.locals["_visit_count"] = caller.locals.get("_visit_count", 0) + 1

    return None


# ---------------------------------------------------------------------------
# JOURNAL — emit content (no default, story layer provides rendering)
# ---------------------------------------------------------------------------

# Story layer registers handlers that:
# 1. Render caller.content as a template against the namespace
# 2. Collect concept descriptions
# 3. Gather available choices for the player
#
# No system-level default — a node with no journal handler just produces
# no output, which is correct for abstract/structural nodes.


# ---------------------------------------------------------------------------
# FINALIZE — finalize-phase runtime hooks
# ---------------------------------------------------------------------------

@on_finalize
def apply_final_runtime_effects(*, caller, ctx, **kw):
    """Apply FINALIZE-phase runtime effects attached to the current node."""
    if hasattr(caller, "apply_effects"):
        caller.apply_effects(phase=ResolutionPhase.FINALIZE, ctx=ctx)
    return None


# Post-MVP: event-sourcing integration may also register a handler here that:
# 1. Collects mutations from the watched graph
# 2. Builds a Patch record
# 3. Appends it to the output stream
#
# For MVP, the frame appends fragments directly. No patch mechanism yet.


# ---------------------------------------------------------------------------
# POSTREQS — continuation redirect after content, before player chooses
# ---------------------------------------------------------------------------

@on_postreqs
def follow_triggered_postreqs(*, caller, ctx, **kw):
    """Follow the first available auto-triggering POSTREQS edge.

    Same logic as ``follow_triggered_prereqs`` but for POSTREQS-triggered
    edges.  These fire after JOURNAL — the player sees the content but
    doesn't get to choose yet.  The pipeline continues to the next node.

    Useful for narrative pacing: "You enter the tavern" (JOURNAL) → auto-advance
    to "You approach the bar" (POSTREQS redirect) → THEN the player gets choices.
    """
    for edge in caller.edges_out():
        if not isinstance(edge, TraversableEdge):
            continue
        trigger = getattr(edge, "trigger_phase", None)
        if trigger == ResolutionPhase.POSTREQS:
            if edge.successor is not None and edge.available(ctx=ctx):
                logger.debug("Postreq redirect: %s → %s", caller.get_label(), edge.successor.get_label())
                return edge

    return None


# ---------------------------------------------------------------------------
# Note: provision_node is registered in tangl.vm.provision.resolver
# ---------------------------------------------------------------------------
# The resolver's @on_provision handler fires during PLANNING and handles
# dependency resolution for the current node and frontier.  It's defined
# there rather than here because it's tightly coupled to the Resolver class.
