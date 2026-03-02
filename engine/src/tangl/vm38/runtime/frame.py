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
- **JOURNAL** — emit content fragments (merge all handler contributions)
- **FINALIZE** — commit step record, emit patch (last_result → patch)
- **POSTREQS** — continuation redirect? (first_result → edge)

If PREREQS or POSTREQS returns an edge, ``follow_edge`` returns it and
``resolve_choice`` loops.  Otherwise the pipeline completes and
``resolve_choice`` checks the return stack or yields to the caller.

JOURNAL Mutation Policy
-----------------------
JOURNAL handlers are expected to primarily emit records. UPDATE/FINALIZE remain
the canonical mutation phases. If JOURNAL mutates graph state, vm38 logs a
debug diagnostic so authors can audit and decide whether to move that logic or
emit explicit annotation records.

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
from contextlib import contextmanager
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
    TemplateRegistry,
)
from tangl.utils.hashing import hashing_func
from ..ctx import VmPhaseCtx
from ..dispatch import (
    do_finalize,
    do_gather_ns,
    do_get_template_scope_groups,
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
    ``BehaviorRegistry.chain_execute_all`` protocol: ``get_authorities()`` and
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
    ``get_ns(node)`` delegates to ``do_gather_ns`` which composes namespace
    data in two phases: caller/ancestor ``get_ns()`` maps, then immediate-
    caller dispatch contributors. Results are cached per node UID for the
    lifetime of this context — the namespace is stable within a single
    pipeline pass.

    The cache is keyed by node UID, so different nodes (cursor vs. frontier
    nodes during PLANNING, different ancestors during condition evaluation)
    each get their own cached namespace.  The cache dies with the context
    (one ``follow_edge`` call), so mutations in UPDATE are reflected in the
    next pipeline pass.

    API
    ---
    - ``get_authorities()`` — authority registries for dispatch expansion.
    - ``get_registries()`` — compatibility alias for ``get_authorities()``.
    - ``get_inline_behaviors()`` — inline behaviors (empty for now).
    - ``get_ns(node)`` — cached scoped namespace from local + dispatch contributors.
    - ``get_random()`` — deterministic RNG for this frame.
    - ``cursor`` — the current node (resolved from ``cursor_id``).

    Implements
    ----------
    :class:`tangl.vm38.ctx.VmPhaseCtx`
        Protocol consumed by vm38 phase handlers and resolver helpers.
    """

    graph: Graph
    cursor_id: UUID
    step: int = 0
    current_phase: ResolutionPhase = ResolutionPhase.INIT
    correlation_id: UUID | str | None = None
    logger: Any | None = None
    meta: Mapping[str, Any] | None = field(default_factory=dict)

    random: Random = field(default_factory=Random)
    inline_behaviors: list[Callable | Behavior] = field(default_factory=list)
    incoming_edge: Any | None = None
    incoming_payload: Any = None

    _ns_cache: dict[UUID, ChainMap[str, Any]] = field(default_factory=dict)
    _ns_inflight: set[UUID] = field(default_factory=set)

    # -- Dispatch protocol --------------------------------------------------

    def get_authorities(self) -> list[BehaviorRegistry]:
        """Authority registries contributed by the graph/runtime environment."""
        registries: list[BehaviorRegistry] = []
        get_authorities = getattr(self.graph, "get_authorities", None)
        if callable(get_authorities):
            for registry in get_authorities() or ():
                if isinstance(registry, BehaviorRegistry) and registry not in registries:
                    registries.append(registry)
        return registries

    # Backwards-compatible alias retained during v38 migration.
    def get_registries(self) -> list[BehaviorRegistry]:
        return self.get_authorities()

    def get_inline_behaviors(self) -> list[Callable | Behavior]:
        return self.inline_behaviors

    def get_random(self) -> Random:
        return self.random

    def get_meta(self) -> Mapping[str, Any]:
        return dict(self.meta or {})

    @contextmanager
    def with_subdispatch(self):
        """Isolate nested dispatch calls from the parent phase invocation."""
        yield self

    @property
    def selected_edge(self) -> Any | None:
        """Alias for incoming edge during this pipeline pass."""
        return self.incoming_edge

    @property
    def selected_payload(self) -> Any:
        """Alias for incoming payload during this pipeline pass."""
        return self.incoming_payload

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

        Delegates to ``do_gather_ns`` on cache miss. The result is cached per
        node UID for the lifetime of this context.

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
            if uid in self._ns_inflight:
                raise RuntimeError(
                    f"Recursive namespace build detected for node uid={uid}",
                )
            self._ns_inflight.add(uid)
            try:
                self._ns_cache[uid] = do_gather_ns(node, ctx=self)
            finally:
                self._ns_inflight.discard(uid)

        return self._ns_cache[uid]

    def get_location_entity_groups(self) -> list[Iterable]:
        """Entity pools ordered by runtime location distance from cursor."""
        cursor = self.cursor
        if cursor is None:
            return [self.graph.values()]

        groups: list[list[Any]] = []
        seen_ids: set[UUID] = set()

        def add_group(values: Iterable[Any]) -> None:
            bucket: list[Any] = []
            for value in values:
                uid = getattr(value, "uid", None)
                if uid is None:
                    continue
                if uid in seen_ids:
                    continue
                seen_ids.add(uid)
                bucket.append(value)
            if bucket:
                groups.append(bucket)

        # Closest scope first: cursor + immediate linked neighbors.
        near_values: list[Any] = [cursor]
        if hasattr(cursor, "successors"):
            near_values.extend(cursor.successors())
        if hasattr(cursor, "predecessors"):
            near_values.extend(cursor.predecessors())
        add_group(near_values)

        # Then each ancestor's child set (template/location neighborhood).
        if hasattr(cursor, "ancestors"):
            for ancestor in cursor.ancestors:
                children = getattr(ancestor, "children", None)
                if callable(children):
                    add_group(children())
                elif isinstance(children, Iterable):
                    add_group(children)

        # Final fallback group: any remaining graph members.
        add_group(self.graph.values())
        return groups or [list(self.graph.values())]

    def get_template_scope_groups(self) -> list[TemplateRegistry]:
        """Template registries available for scoped provisioning."""
        groups = do_get_template_scope_groups(self.cursor, ctx=self)
        if groups:
            return groups

        factory = getattr(self.graph, "factory", None)
        if isinstance(factory, TemplateRegistry):
            return [factory]
        return []

    # Backwards-compatible aliases for existing resolver contexts.
    def get_entity_groups(self) -> list[Iterable]:
        return self.get_location_entity_groups()

    def get_template_groups(self) -> list[TemplateRegistry]:
        return self.get_template_scope_groups()


# ---------------------------------------------------------------------------
# Frame — the pipeline driver
# ---------------------------------------------------------------------------

MAX_RESOLVE_DEPTH = 50
"""Safety limit for ``resolve_choice`` to prevent runaway redirect chains."""


@dataclass
class StepTrace:
    """Replay trace emitted for one completed ``follow_edge`` hop."""

    step: int
    edge_id: UUID | None
    cursor_id: UUID
    entry_phase: ResolutionPhase
    was_choice: bool
    state_hash: bytes
    before_graph: Graph
    after_graph: Graph
    call_stack_ids: list[UUID] = field(default_factory=list)


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

    last_redirect: dict[str, Any] | None = None
    """Last redirect record captured during this resolve cycle."""

    redirect_trace: list[dict[str, Any]] = field(default_factory=list)
    """Ordered redirect records captured during this resolve cycle."""

    step_base: int = 0
    """Absolute step offset at frame start (usually ledger.cursor_steps)."""

    step_observer: Callable[[StepTrace], None] | None = None
    """Optional observer called once for each completed cursor hop."""

    _last_step_trace: StepTrace | None = field(default=None, init=False, repr=False)

    correlation_id: UUID | str | None = None
    logger: Any | None = None
    meta: Mapping[str, Any] | None = field(default_factory=dict)

    _random: Random = field(default_factory=Random)
    selected_edge: AnyTraversableEdge | None = None
    selected_payload: Any = None

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

    def _make_ctx(
        self,
        *,
        incoming_edge: AnyTraversableEdge | None = None,
        incoming_payload: Any = None,
    ) -> VmPhaseCtx:
        """Build a fresh PhaseCtx for the current cursor position.

        A new context is created for each ``follow_edge`` call because the
        cursor changes between calls and the context (including ns cache)
        must reflect the new position.
        """
        return PhaseCtx(
            graph=self.graph,
            cursor_id=self.cursor.uid,
            step=self.step_base + self.cursor_steps,
            correlation_id=self.correlation_id,
            logger=self.logger,
            meta=dict(self.meta or {}),
            random=self._random,
            incoming_edge=incoming_edge,
            incoming_payload=incoming_payload,
        )

    @staticmethod
    def _resolve_incoming_payload(
        edge: AnyTraversableEdge,
        override: Any = None,
    ) -> Any:
        """Build effective incoming payload for the current traversal hop."""
        edge_payload = getattr(edge, "payload", None)
        if override is None:
            return edge_payload
        if isinstance(edge_payload, Mapping) and isinstance(override, Mapping):
            merged = dict(edge_payload)
            merged.update(override)
            return merged
        return override

    @staticmethod
    def _with_step(record: Record, *, step: int) -> Record:
        """Return a step-annotated record, preserving immutability."""
        if not hasattr(record, "step"):
            return record
        current = getattr(record, "step", None)
        if isinstance(current, int) and current >= 0:
            return record
        if hasattr(record, "evolve"):
            return record.evolve(step=step)
        return record

    def _record_redirect(self, *, phase: ResolutionPhase, edge: AnyTraversableEdge) -> None:
        """Capture minimal redirect observability for service/debug surfaces."""
        predecessor = getattr(edge, "predecessor", None)
        successor = getattr(edge, "successor", None)
        record = {
            "phase": phase.name.lower(),
            "edge_id": str(getattr(edge, "uid", "")) or None,
            "predecessor_id": str(getattr(predecessor, "uid", "")) or None,
            "successor_id": str(getattr(successor, "uid", "")) or None,
        }
        self.last_redirect = record
        self.redirect_trace.append(record)

    def _snapshot_graph(self) -> Graph:
        """Create a detached snapshot graph for replay tracing."""
        return Graph.structure(self.graph.unstructure())

    def _capture_step_trace(
        self,
        *,
        edge: AnyTraversableEdge,
        entry_phase: ResolutionPhase,
        was_choice: bool,
        before_graph: Graph | None,
    ) -> None:
        if self.step_observer is None or before_graph is None:
            self._last_step_trace = None
            return
        edge_id = getattr(edge, "uid", None)
        self._last_step_trace = StepTrace(
            step=self.step_base + self.cursor_steps,
            edge_id=edge_id,
            cursor_id=self.cursor.uid,
            entry_phase=entry_phase,
            was_choice=was_choice,
            state_hash=self.graph.value_hash(),
            before_graph=before_graph,
            after_graph=self._snapshot_graph(),
        )

    def _emit_step_trace(self) -> None:
        if self.step_observer is None or self._last_step_trace is None:
            return
        trace = self._last_step_trace
        trace.call_stack_ids = [edge.uid for edge in self.return_stack]
        self.step_observer(trace)
        self._last_step_trace = None

    # -- Pipeline execution -------------------------------------------------

    def follow_edge(
        self,
        edge: AnyTraversableEdge,
        *,
        was_choice: bool = False,
        selected_payload_override: Any = None,
    ) -> Optional[AnyTraversableEdge]:
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
        incoming_payload = self._resolve_incoming_payload(edge, selected_payload_override)
        self.selected_edge = edge
        self.selected_payload = incoming_payload

        before_graph: Graph | None = None
        if self.step_observer is not None:
            before_graph = self._snapshot_graph()

        # -- VALIDATE (pre-move) --------------------------------------------
        if entry_phase <= ResolutionPhase.VALIDATE:
            pre_ctx = self._make_ctx(
                incoming_edge=edge,
                incoming_payload=incoming_payload,
            )
            pre_ctx.current_phase = ResolutionPhase.VALIDATE
            if not do_validate(edge, ctx=pre_ctx):
                raise ValueError(f"Edge validation failed: {edge!r}")

        # -- Update cursor --------------------------------------------------
        self.cursor = edge.successor
        self.cursor_steps += 1
        self.cursor_trace.append(self.cursor.uid)

        # -- Build context at new position ----------------------------------
        ctx = self._make_ctx(
            incoming_edge=edge,
            incoming_payload=incoming_payload,
        )

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
                self._record_redirect(phase=ResolutionPhase.PREREQS, edge=prereq_result)
                self._capture_step_trace(
                    edge=edge,
                    entry_phase=entry_phase,
                    was_choice=was_choice,
                    before_graph=before_graph,
                )
                return prereq_result

        # -- UPDATE ---------------------------------------------------------
        if entry_phase <= ResolutionPhase.UPDATE:
            ctx.current_phase = ResolutionPhase.UPDATE
            do_update(self.cursor, ctx=ctx)

        # -- JOURNAL --------------------------------------------------------
        if entry_phase <= ResolutionPhase.JOURNAL:
            ctx.current_phase = ResolutionPhase.JOURNAL
            journal_hash_before = self.graph.value_hash()
            fragments = do_journal(self.cursor, ctx=ctx)
            if fragments:
                if isinstance(fragments, Iterable) and not isinstance(fragments, (Record, str, bytes)):
                    for f in fragments:
                        if isinstance(f, Record):
                            f = self._with_step(f, step=ctx.step)
                        self.output_stream.append(f)
                else:
                    if isinstance(fragments, Record):
                        fragments = self._with_step(fragments, step=ctx.step)
                    self.output_stream.append(fragments)
            if logger.isEnabledFor(logging.DEBUG):
                journal_hash_after = self.graph.value_hash()
                if journal_hash_after != journal_hash_before:
                    logger.debug(
                        "JOURNAL mutation detected at step=%s cursor_id=%s; "
                        "prefer UPDATE/FINALIZE for state mutation or emit annotation records",
                        ctx.step,
                        self.cursor.uid,
                    )

        # -- FINALIZE -------------------------------------------------------
        if entry_phase <= ResolutionPhase.FINALIZE:
            ctx.current_phase = ResolutionPhase.FINALIZE
            patch = do_finalize(self.cursor, ctx=ctx)
            if patch:
                if isinstance(patch, Record):
                    patch = self._with_step(patch, step=ctx.step)
                self.output_stream.append(patch)

        # -- POSTREQS -------------------------------------------------------
        if entry_phase <= ResolutionPhase.POSTREQS:
            ctx.current_phase = ResolutionPhase.POSTREQS
            postreq_result = do_postreqs(self.cursor, ctx=ctx)
            if postreq_result is not None:
                self._record_redirect(phase=ResolutionPhase.POSTREQS, edge=postreq_result)
                self._capture_step_trace(
                    edge=edge,
                    entry_phase=entry_phase,
                    was_choice=was_choice,
                    before_graph=before_graph,
                )
                return postreq_result

        self._capture_step_trace(
            edge=edge,
            entry_phase=entry_phase,
            was_choice=was_choice,
            before_graph=before_graph,
        )
        return None

    # -- Choice resolution --------------------------------------------------

    def resolve_choice(
        self,
        edge: AnyTraversableEdge,
        *,
        max_depth: int = MAX_RESOLVE_DEPTH,
        choice_payload: Any = None,
    ):
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
        is_choice_edge = True

        while edge is not None:
            if depth >= max_depth:
                raise RecursionError(
                    f"resolve_choice exceeded {max_depth} steps — "
                    f"likely a redirect loop at {self.cursor!r}"
                )

            current_edge = edge
            payload_override = choice_payload if is_choice_edge else None
            result = self.follow_edge(
                current_edge,
                was_choice=is_choice_edge,
                selected_payload_override=payload_override,
            )
            depth += 1

            if getattr(current_edge, "return_phase", None) is not None:
                self.return_stack.append(current_edge)

            if result is not None:
                edge = result

            elif self.return_stack:
                call_edge = self.return_stack.pop()
                edge = call_edge.get_return_edge()

            else:
                edge = None

            self._emit_step_trace()
            is_choice_edge = False

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
