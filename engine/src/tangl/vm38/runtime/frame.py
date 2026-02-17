# tangl/vm38/runtime/frame.py
"""Ephemeral traversal driver for the VM phase pipeline.

A Frame drives one ``resolve_choice`` call: a sequence of ``follow_edge`` steps
that move the cursor through the graph, running the phase pipeline at each node,
until the pipeline produces no redirect (block for input) or the return stack
is exhausted.

Frames are ephemeral — they are created by the Ledger for each player action,
consume edges, produce output (fragments, patches) into the output stream, and
are then discarded.  Their output is deterministically reproducible from the
graph state and the chosen edge.

Design Principle — Atomic Pipeline, No Split
---------------------------------------------
The phase pipeline runs fully at each node the cursor visits.  There is no
split around "block for input" — FINALIZE and POSTREQS run immediately after
JOURNAL, not after the player's next choice.  The player's choice is recorded
at the start of the *next* ``resolve_choice`` call, not at the end of the
current pipeline.

The pipeline phases in causal order:

- **VALIDATE** — is the movement legal? (all_true)
- **PLANNING** — provision this node + frontier for availability (gather)
- **PREREQS** — auto-redirect? container descent? (first_result → edge)
- **UPDATE** — mutate state for arrival (gather)
- **JOURNAL** — emit content fragments (last_result → fragments)
- **FINALIZE** — commit step record, emit patch (last_result → patch)
- **POSTREQS** — continuation redirect? (first_result → edge)

If PREREQS or POSTREQS returns an edge, ``follow_edge`` returns it and
``resolve_choice`` loops.  Otherwise the pipeline completes and
``resolve_choice`` checks the return stack or yields to the caller.

See Also
--------
:mod:`tangl.vm38.traversable`
    Node and edge types consumed by the frame.
:mod:`tangl.vm38.dispatch`
    ``do_*`` functions called at each pipeline phase.
:mod:`tangl.vm38.runtime.ledger`
    Creates and manages frames across player actions.
"""

from __future__ import annotations

import logging
from collections import ChainMap
from dataclasses import dataclass, field
from random import Random
from typing import Any, Callable, Iterable, Mapping, Optional, TypeAlias
from uuid import UUID

from tangl.core38 import (
    Behavior,
    BehaviorRegistry,
    CallReceipt,
    Graph,
    Node,
    OrderedRegistry,
    Record,
    Selector,
)
from tangl.utils.hashing import hashing_func
from ..dispatch import (
    dispatch as vm_dispatch,
    do_finalize,
    do_gather_ns,
    do_journal,
    do_postreqs,
    do_prereqs,
    do_provision,
    do_update,
    do_validate,
)
from ..resolution_phase import ResolutionPhase
from ..traversable import (
    AnonymousEdge,
    AnyTraversableEdge,
    TraversableEdge,
    TraversableNode,
)

logger = logging.getLogger(__name__)

NS: TypeAlias = Mapping[str, Any]

__all__ = ["PhaseCtx", "Frame"]


# ---------------------------------------------------------------------------
# PhaseCtx — dispatch context for the phase pipeline
# ---------------------------------------------------------------------------

@dataclass
class PhaseCtx:
    """Dispatch context for one ``follow_edge`` call.

    Why
    ---
    Every ``do_*`` call in the pipeline requires a context that satisfies the
    ``BehaviorRegistry.chain_execute`` protocol: ``get_registries()`` and
    ``get_inline_behaviors()``.  ``PhaseCtx`` provides these, plus VM-specific
    accessors for the cursor, graph, namespace, and random state.

    Lifecycle
    ---------
    One ``PhaseCtx`` per ``follow_edge`` invocation.  The cursor is fixed for
    the duration (it was just updated at the top of ``follow_edge``).  The
    ``current_phase`` field is updated as the pipeline progresses — this lets
    handlers know which phase they're executing in.

    Namespace
    ---------
    ``get_ns(node)`` delegates to ``do_gather_ns`` which walks the ancestor
    chain and fires namespace handlers at each level.  Results are cached per
    node UID for the lifetime of this context — the namespace is stable within
    a single pipeline pass.

    The cache is keyed by node UID, so different nodes (cursor vs. frontier
    nodes during PLANNING, different ancestors during condition evaluation)
    each get their own cached namespace.  The cache dies with the context
    (one ``follow_edge`` call), so mutations in UPDATE are reflected in the
    next pipeline pass.

    API
    ---
    - ``get_registries()`` — registries for ``chain_execute``.
    - ``get_inline_behaviors()`` — inline behaviors (empty for now).
    - ``get_ns(node)`` — cached scoped namespace from ancestor chain.
    - ``get_random()`` — deterministic RNG for this frame.
    - ``cursor`` — the current node (resolved from ``cursor_id``).
    """

    graph: Graph
    cursor_id: UUID
    step: int = 0
    current_phase: ResolutionPhase = ResolutionPhase.INIT

    random: Random = field(default_factory=Random)
    inline_behaviors: list[Callable | Behavior] = field(default_factory=list)

    _ns_cache: dict[UUID, ChainMap[str, Any]] = field(default_factory=dict)

    # -- Dispatch protocol --------------------------------------------------

    def get_registries(self) -> list[BehaviorRegistry]:
        """Registries to include in ``chain_execute``.

        Returns the module-level ``vm_dispatch`` registry.  Additional
        registries (application-level, story-level) can be added by
        wrapping or extending this context.
        """
        return [vm_dispatch]

    def get_inline_behaviors(self) -> list[Callable | Behavior]:
        return self.inline_behaviors

    def get_random(self) -> Random:
        return self.random

    # -- VM-specific accessors ----------------------------------------------

    @property
    def cursor(self) -> TraversableNode:
        """The current node, dereferenced through the graph.

        Uses ``graph.get(cursor_id)`` rather than caching, so that watched
        registries (future event-sourcing) can intercept the lookup.
        """
        return self.graph.get(self.cursor_id)

    def get_ns(self, node: Node = None) -> ChainMap[str, Any]:
        """Build or retrieve the cached scoped namespace for a node.

        Delegates to ``do_gather_ns`` on cache miss, which walks the ancestor
        chain and fires all ``gather_ns`` handlers at each level.  The result
        is cached per node UID for the lifetime of this context.

        Parameters
        ----------
        node
            Node to build namespace for.  Defaults to cursor.

        Returns
        -------
        ChainMap[str, Any]
            Scoped namespace with closest ancestor first.

        Notes
        -----
        Namespace handlers must not call ``ctx.get_ns()`` for the same node
        they're currently building — that would cause infinite recursion.
        Use handler priority ordering instead.
        """
        node = node or self.cursor
        if node is None:
            return ChainMap()

        uid = node.uid
        if uid not in self._ns_cache:
            self._ns_cache[uid] = do_gather_ns(node, ctx=self)

        return self._ns_cache[uid]

    def get_entity_groups(self) -> list[Iterable]:
        """Entity pools for provisioning, ordered by distance from cursor.

        For MVP, returns the entire graph as a single group.  A future
        version would walk ``cursor.ancestors`` and group each ancestor's
        satisfied dependencies at increasing distance.
        """
        return [self.graph.values()]

    def get_template_groups(self) -> list[Iterable]:
        """Template pools for provisioning, ordered by scope distance.

        By convention, story graphs expose ``graph.factory`` as a template
        registry-like object. When present, include it as the nearest
        template pool so PLANNING can resolve CREATE offers.
        """
        factory = getattr(self.graph, "factory", None)
        if factory is None:
            return []

        if hasattr(factory, "values"):
            return [factory.values()]

        return [factory]


# ---------------------------------------------------------------------------
# Frame — the pipeline driver
# ---------------------------------------------------------------------------

MAX_RESOLVE_DEPTH = 50
"""Safety limit for ``resolve_choice`` to prevent runaway redirect chains."""


@dataclass
class Frame:
    """Drives cursor traversal through the phase pipeline.

    Why
    ---
    Frame is the ephemeral execution context for one player action (one
    ``resolve_choice`` call).  It moves the cursor through the graph by
    repeatedly calling ``follow_edge``, which runs the phase pipeline at
    each destination node.  Redirects from PREREQS or POSTREQS cause the
    loop to continue; when the pipeline produces no redirect, the frame
    either pops the return stack or yields control back to the caller.

    Frame does NOT know about containers, scenes, or story semantics.  It
    knows about nodes, edges, the phase pipeline, and the return stack.
    Container descent is handled by a prereq dispatch handler that detects
    ``TraversableNode.is_container`` and returns an ``enter()`` edge.

    Key Features
    ------------
    * **Pipeline execution** — ``follow_edge`` runs phases in order, respecting
      ``entry_phase`` for return edges that skip early phases.
    * **Redirect chaining** — PREREQS and POSTREQS may return edges; the frame
      follows them in a loop until the pipeline completes cleanly.
    * **Return stack** — call edges (``return_phase`` set) are pushed onto the
      stack.  When the pipeline reaches a terminal, the stack is popped and
      the return edge is followed.
    * **Recursion safety** — ``resolve_choice`` enforces ``MAX_RESOLVE_DEPTH``.

    API
    ---
    - ``follow_edge(edge)`` — move cursor, run pipeline, return redirect or None.
    - ``resolve_choice(edge)`` — loop ``follow_edge`` until terminal.
    - ``goto_node(node)`` — force-provision and jump (skip validation).

    Notes
    -----
    The output stream and return stack are shared references from the Ledger.
    After ``resolve_choice`` returns, the Ledger reads back the updated cursor,
    step counters, and any output that was appended to the stream.

    Examples
    --------
    Basic pipeline — follow an edge to a leaf node:

    >>> from tangl.core38 import Graph
    >>> from tangl.vm38.traversable import TraversableNode, AnonymousEdge
    >>> from tangl.vm38.runtime.frame import Frame
    >>> g = Graph()
    >>> a = TraversableNode(label="a", registry=g)
    >>> b = TraversableNode(label="b", registry=g)
    >>> frame = Frame(graph=g, cursor=a)
    >>> edge = AnonymousEdge(predecessor=a, successor=b)
    >>> result = frame.follow_edge(edge)
    >>> frame.cursor is b
    True
    >>> frame.cursor_steps
    1
    >>> result is None
    True
    """

    graph: Graph
    """The graph being traversed (shared with Ledger)."""

    cursor: TraversableNode
    """Current cursor node.  Updated by ``follow_edge``."""

    output_stream: OrderedRegistry = field(default_factory=OrderedRegistry)
    """Receives fragments and patches from JOURNAL and FINALIZE phases."""

    return_stack: list[TraversableEdge] = field(default_factory=list)
    """Call edges awaiting return.  Shared reference from Ledger."""

    cursor_steps: int = 0
    """Number of cursor movements in this frame's lifetime."""

    cursor_trace: list[UUID] = field(default_factory=list)
    """Visited cursor positions for this resolve cycle, in order."""

    step_base: int = 0
    """Absolute step offset at frame start (usually ledger.cursor_steps)."""

    _random: Random = field(default_factory=Random)

    def __post_init__(self) -> None:
        """Seed RNG deterministically from graph state + cursor + starting step."""
        seed_hash = hashing_func(
            self.graph.value_hash(),
            self.cursor.uid,
            self.step_base,
            digest_size=8,
        )
        seed = int.from_bytes(seed_hash[:8], byteorder="big", signed=False)
        self._random.seed(seed)

    # -- Context factory ----------------------------------------------------

    def _make_ctx(self) -> PhaseCtx:
        """Build a fresh PhaseCtx for the current cursor position.

        A new context is created for each ``follow_edge`` call because the
        cursor changes between calls and the context (including ns cache)
        must reflect the new position.
        """
        return PhaseCtx(
            graph=self.graph,
            cursor_id=self.cursor.uid,
            step=self.step_base + self.cursor_steps,
            random=self._random,
        )

    # -- Pipeline execution -------------------------------------------------

    def follow_edge(self, edge: AnyTraversableEdge) -> Optional[AnyTraversableEdge]:
        """Move cursor along ``edge`` and run the phase pipeline.

        Returns an edge if PREREQS or POSTREQS produced a redirect, or
        ``None`` if the pipeline completed without redirect (the frame
        should block for input or check the return stack).

        The pipeline runs from ``edge.entry_phase`` (default VALIDATE)
        through POSTREQS.  Phases before ``entry_phase`` are skipped —
        this is how return edges resume at a later phase.

        Raises
        ------
        ValueError
            If VALIDATE fails (the edge is not traversable).
        """
        entry_phase = getattr(edge, "entry_phase", None) or ResolutionPhase.VALIDATE

        # -- VALIDATE (pre-move) --------------------------------------------
        if entry_phase <= ResolutionPhase.VALIDATE:
            pre_ctx = self._make_ctx()
            pre_ctx.current_phase = ResolutionPhase.VALIDATE
            if not do_validate(edge, ctx=pre_ctx):
                raise ValueError(f"Edge validation failed: {edge!r}")

        # -- Update cursor --------------------------------------------------
        self.cursor = edge.successor
        self.cursor_steps += 1
        self.cursor_trace.append(self.cursor.uid)

        # -- Build context at new position ----------------------------------
        ctx = self._make_ctx()

        # -- PLANNING -------------------------------------------------------
        if entry_phase <= ResolutionPhase.PLANNING:
            ctx.current_phase = ResolutionPhase.PLANNING
            do_provision(self.cursor, ctx=ctx)
            for successor in self.cursor.successors():
                if isinstance(successor, TraversableNode):
                    do_provision(successor, ctx=ctx)

        # -- PREREQS --------------------------------------------------------
        if entry_phase <= ResolutionPhase.PREREQS:
            ctx.current_phase = ResolutionPhase.PREREQS
            prereq_result = do_prereqs(self.cursor, ctx=ctx)
            if prereq_result is not None:
                return prereq_result

        # -- UPDATE ---------------------------------------------------------
        if entry_phase <= ResolutionPhase.UPDATE:
            ctx.current_phase = ResolutionPhase.UPDATE
            do_update(self.cursor, ctx=ctx)

        # -- JOURNAL --------------------------------------------------------
        if entry_phase <= ResolutionPhase.JOURNAL:
            ctx.current_phase = ResolutionPhase.JOURNAL
            fragments = do_journal(self.cursor, ctx=ctx)
            if fragments:
                if isinstance(fragments, Iterable) and not isinstance(fragments, Record):
                    for f in fragments:
                        self.output_stream.append(f)
                else:
                    self.output_stream.append(fragments)

        # -- FINALIZE -------------------------------------------------------
        if entry_phase <= ResolutionPhase.FINALIZE:
            ctx.current_phase = ResolutionPhase.FINALIZE
            patch = do_finalize(self.cursor, ctx=ctx)
            if patch:
                self.output_stream.append(patch)

        # -- POSTREQS -------------------------------------------------------
        if entry_phase <= ResolutionPhase.POSTREQS:
            ctx.current_phase = ResolutionPhase.POSTREQS
            postreq_result = do_postreqs(self.cursor, ctx=ctx)
            if postreq_result is not None:
                return postreq_result

        return None

    # -- Choice resolution --------------------------------------------------

    def resolve_choice(self, edge: AnyTraversableEdge, *, max_depth: int = MAX_RESOLVE_DEPTH):
        """Follow edges until the pipeline blocks or the return stack empties.

        This is the main entry point called by the Ledger.  It loops:

        1. ``follow_edge(edge)`` — run pipeline, get redirect or None.
        2. If redirect has ``return_phase``, push onto return stack, continue
           following (the redirect is the forward/call edge).
        3. If redirect has no ``return_phase``, it's a continuation — follow it.
        4. If no redirect and return stack is non-empty, pop and follow return.
        5. If no redirect and stack is empty, yield to caller (block for input).

        Parameters
        ----------
        edge
            The initial edge to follow (from the player's chosen edge, or
            from an initial entry point).
        max_depth
            Safety limit to prevent runaway redirect chains.

        Raises
        ------
        RecursionError
            If the redirect chain exceeds ``max_depth``.
        """
        depth = 0

        while edge is not None:
            if depth >= max_depth:
                raise RecursionError(
                    f"resolve_choice exceeded {max_depth} steps — "
                    f"likely a redirect loop at {self.cursor!r}"
                )

            result = self.follow_edge(edge)
            depth += 1

            if result is not None:
                if (hasattr(result, "return_phase")
                        and result.return_phase is not None):
                    self.return_stack.append(result)
                edge = result

            elif self.return_stack:
                call_edge = self.return_stack.pop()
                edge = call_edge.get_return_edge()

            else:
                edge = None

    # -- Direct jump --------------------------------------------------------

    def goto_node(self, node: TraversableNode, *, force: bool = False):
        """Jump directly to a node, skipping validation.

        Used for initialization (placing cursor at the entry point) and for
        forced teleportation.  Provisions the target (optionally with force)
        and then follows an anonymous edge starting at PLANNING.

        Parameters
        ----------
        node
            The target node.
        force
            If True, force-resolve any unmet requirements.
        """
        if force:
            ctx = self._make_ctx()
            do_provision(node, ctx=ctx, force=True)

        edge = AnonymousEdge(
            predecessor=self.cursor,
            successor=node,
            entry_phase=ResolutionPhase.PLANNING,
        )
        self.resolve_choice(edge)
