# tangl/vm38/system_handlers.py
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
- ``contribute_locals`` — inject ``caller.locals`` dict
- ``contribute_satisfied_deps`` — inject label→provider for satisfied deps

**validate_edge**:
- ``validate_successor_exists`` — successor must resolve from graph

**get_prereqs** (PREREQS):
- ``descend_into_container`` — if cursor is_container, return enter() edge
- ``follow_triggered_prereqs`` — first available edge with trigger_phase=PREREQS

**apply_update** (UPDATE):
- ``mark_visited`` — set ``caller.locals['_visited'] = True``, increment visit count

**render_journal** (JOURNAL):
- (no default — story layer provides content rendering)

**finalize_step** (FINALIZE):
- (no default for MVP — replay/patch generation is post-MVP)

**get_postreqs** (POSTREQS):
- ``follow_triggered_postreqs`` — first available edge with trigger_phase=POSTREQS

**provision_node** (PLANNING):
- Already registered by ``tangl.vm38.provision.resolver.provision_node``

Usage
-----
Import this module to register the handlers::

    import tangl.vm38.system_handlers  # registers all defaults

Or import selectively::

    from tangl.vm38.system_handlers import descend_into_container

See Also
--------
:mod:`tangl.vm38.dispatch`
    Registration and execution surface for hooks.
:mod:`tangl.vm38.traversable`
    ``TraversableNode``, ``TraversableEdge``, ``AnonymousEdge`` types.
:mod:`tangl.vm38.provision`
    ``Dependency``, ``Affordance``, and the ``Resolver`` that handles PLANNING.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tangl.core38 import Node, Selector

from .dispatch import (
    on_gather_ns,
    on_validate,
    on_prereqs,
    on_update,
    on_journal,
    on_finalize,
    on_postreqs,
)
from .traversable import TraversableNode, TraversableEdge, AnonymousEdge

if TYPE_CHECKING:
    from .runtime.frame import PhaseCtx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Namespace contributors
# ---------------------------------------------------------------------------

@on_gather_ns
def contribute_locals(*, caller, ctx, **kw):
    """Inject ``caller.locals`` into the namespace.

    Any entity with a ``locals`` dict contributes its contents.  This is the
    primary mechanism for story-authored state: ``node.locals['mood'] = 'angry'``
    becomes available as ``ns['mood']`` in descendant scopes.

    Fires at every ancestor level.  Closer scope overrides via ChainMap
    ordering in ``do_gather_ns``.
    """
    if hasattr(caller, "locals") and caller.locals:
        return dict(caller.locals)
    return None


@on_gather_ns
def contribute_satisfied_deps(*, caller, ctx, **kw):
    """Inject satisfied dependency/affordance providers as named symbols.

    For each satisfied ``Dependency`` or ``Affordance`` edge originating from
    ``caller``, contributes ``edge.label → edge.successor`` (the provider).

    This makes provisioned resources available by name in the namespace.
    For example, a scene with a satisfied ``"companion"`` dependency makes
    ``ns['companion']`` resolve to the companion entity.
    """
    # Lazy import to avoid circular dependency at module load
    from .provision import Dependency, Affordance

    result = {}
    for edge in caller.edges_out(Selector(has_kind=Dependency)):
        if edge.satisfied and edge.successor is not None:
            label = edge.get_label()
            if label:
                result[label] = edge.successor

    for edge in caller.edges_out(Selector(has_kind=Affordance)):
        if edge.satisfied and edge.successor is not None:
            label = edge.get_label()
            if label:
                result[label] = edge.successor

    return result if result else None


# ---------------------------------------------------------------------------
# VALIDATE — is the movement legal?
# ---------------------------------------------------------------------------

@on_validate
def validate_successor_exists(*, caller, ctx, **kw):
    """Check that the edge's successor resolves to a node in the graph.

    This is the minimum validation: the destination exists.  Story-layer
    handlers can add guard conditions (``edge.available(ns)``), requirement
    checks, or access control.

    ``caller`` here is the edge being validated, not the destination node.
    """
    successor = getattr(caller, "successor", None)
    if successor is None:
        # AnonymousEdge — successor is a direct reference
        successor = getattr(caller, "successor", None)
    return successor is not None


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
    ``entry_phase == PREREQS`` (the v38 equivalent of legacy's
    ``trigger_phase == PREREQS``).  Returns the first one whose guard
    condition passes against the current namespace.

    For v38 MVP, "available" means the edge exists and isn't explicitly
    disabled.  Full guard/condition evaluation against the namespace is
    a story-layer concern that can be added by registering a higher-priority
    handler or by adding an ``available(ns)`` method to a TraversableEdge
    subclass.

    This handler should fire AFTER ``descend_into_container`` — if the
    cursor is a container, descent takes priority.  We rely on registration
    order (container handler registered first) for this.
    """
    from .resolution_phase import ResolutionPhase

    for edge in caller.edges_out():
        if not isinstance(edge, TraversableEdge):
            continue
        # Prereq-triggered edges: entry_phase explicitly set to PREREQS
        # means "follow me automatically on arrival"
        trigger = getattr(edge, "trigger_phase", None)
        if trigger == ResolutionPhase.PREREQS:
            # TODO: check edge.available(ns) when guard conditions are implemented
            if edge.successor is not None:
                logger.debug("Prereq redirect: %s → %s", caller.get_label(), edge.successor.get_label())
                return edge

    return None


# ---------------------------------------------------------------------------
# UPDATE — mutate state for arrival
# ---------------------------------------------------------------------------

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
# FINALIZE — commit step record (no default for MVP)
# ---------------------------------------------------------------------------

# Post-MVP: event-sourcing integration would register a handler here that:
# 1. Collects mutations from the watched graph
# 2. Builds a Patch record
# 3. Appends it to the output stream
#
# For MVP, the frame appends fragments directly.  No patch mechanism.


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
    from .resolution_phase import ResolutionPhase

    for edge in caller.edges_out():
        if not isinstance(edge, TraversableEdge):
            continue
        trigger = getattr(edge, "trigger_phase", None)
        if trigger == ResolutionPhase.POSTREQS:
            if edge.successor is not None:
                logger.debug("Postreq redirect: %s → %s", caller.get_label(), edge.successor.get_label())
                return edge

    return None


# ---------------------------------------------------------------------------
# Note: provision_node is registered in tangl.vm38.provision.resolver
# ---------------------------------------------------------------------------
# The resolver's @on_provision handler fires during PLANNING and handles
# dependency resolution for the current node and frontier.  It's defined
# there rather than here because it's tightly coupled to the Resolver class.
