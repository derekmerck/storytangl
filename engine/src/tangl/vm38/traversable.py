# tangl/vm38/traversable.py
"""Traversal primitives for the VM phase pipeline.

This module defines the node and edge types that participate in cursor-driven
graph traversal.  Core provides the topology (nodes, edges, hierarchy); this
module adds the **traversal contract**: which nodes can the cursor visit, how
does movement between them work, and what does container structure mean for
the phase pipeline.

Design Principle — LCA-Based Movement
--------------------------------------
Every cursor movement is a ``goto(target)`` whose context implications are
determined by the lowest common ancestor (LCA) of source and target in the
hierarchy.  The ancestor chain at any cursor position defines the complete
namespace and resource scope.  There are no separate enter/exit mechanisms —
the graph structure IS the context stack, and the pipeline fires at each node
the cursor passes through (including containers, via prereq descent chaining).

See Also
--------
:mod:`tangl.core38.graph`
    ``HierarchicalNode`` provides the parent/child hierarchy that defines
    traversal scope.
:mod:`tangl.vm38.dispatch`
    Phase hooks (``on_prereqs``, ``on_postreqs``, etc.) that fire at each
    pipeline stage during cursor movement.
:mod:`tangl.vm38.runtime.frame`
    ``Frame.follow_edge`` and ``Frame.resolve_choice`` drive the pipeline
    using these traversal primitives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TypeAlias, Union
from uuid import UUID

from tangl.core38 import HierarchicalNode, Edge, Node, Selector
from .resolution_phase import ResolutionPhase


__all__ = [
    "TraversableNode",
    "TraversableEdge",
    "AnonymousEdge",
    "AnyTraversableEdge",
    "lca",
    "decompose_move",
]


# ---------------------------------------------------------------------------
# LCA utilities
# ---------------------------------------------------------------------------

def lca(a: HierarchicalNode, b: HierarchicalNode) -> Optional[HierarchicalNode]:
    """Lowest common ancestor of two nodes in the same hierarchy.

    Returns the deepest node that appears in both ancestor chains, or ``None``
    if the nodes share no common ancestor (disjoint trees — should not happen
    within a single graph).

    For the shallow hierarchies typical of narrative structure (depth 3–6),
    the set-intersection approach is simple and fast.

    Examples
    --------
    >>> from tangl.core38 import Graph
    >>> g = Graph()
    >>> root = TraversableNode(label="root", registry=g)
    >>> ch1  = TraversableNode(label="ch1", registry=g)
    >>> ch2  = TraversableNode(label="ch2", registry=g)
    >>> a    = TraversableNode(label="a", registry=g)
    >>> b    = TraversableNode(label="b", registry=g)
    >>> root.add_child(ch1); root.add_child(ch2)
    >>> ch1.add_child(a); ch2.add_child(b)

    Siblings share their parent:

    >>> lca(a, b) is root
    True

    Children share the parent:

    >>> lca(ch1, a) is ch1
    True

    Same node:

    >>> lca(a, a) is a
    True
    """
    # ancestors includes self: [a, parent, grandparent, ...]
    ancestors_a = {id(n) for n in a.ancestors}
    for node in b.ancestors:
        if id(node) in ancestors_a:
            return node
    return None


def decompose_move(
    source: HierarchicalNode,
    target: HierarchicalNode,
) -> tuple[list[HierarchicalNode], list[HierarchicalNode], Optional[HierarchicalNode]]:
    """Decompose a cursor movement into exit and enter paths around the LCA.

    Returns ``(exit_path, enter_path, pivot)`` where:

    - ``exit_path``: nodes from ``source`` up to (not including) the LCA.
      These are leaving scope — teardown hooks fire here (future).
    - ``enter_path``: nodes from the LCA's child down to ``target``.
      These are entering scope — setup/provision hooks fire here (future).
    - ``pivot``: the LCA itself.  Context at and above this node is unchanged.

    The paths are useful for understanding what changed, but for MVP the
    namespace is always recomputed from ``cursor.ancestors`` rather than
    incrementally maintained.

    Examples
    --------
    >>> from tangl.core38 import Graph
    >>> g = Graph()
    >>> root = TraversableNode(label="root", registry=g)
    >>> ch1  = TraversableNode(label="ch1", registry=g)
    >>> ch2  = TraversableNode(label="ch2", registry=g)
    >>> a    = TraversableNode(label="a", registry=g)
    >>> b    = TraversableNode(label="b", registry=g)
    >>> root.add_child(ch1); root.add_child(ch2)
    >>> ch1.add_child(a); ch2.add_child(b)

    Cross-branch move pops one side and pushes the other:

    >>> ex, en, pivot = decompose_move(a, b)
    >>> [n.label for n in ex]
    ['a', 'ch1']
    >>> [n.label for n in en]
    ['ch2', 'b']
    >>> pivot.label
    'root'

    Within-group move only swaps the leaf:

    >>> c = TraversableNode(label="c", registry=g)
    >>> ch1.add_child(c)
    >>> ex, en, pivot = decompose_move(a, c)
    >>> [n.label for n in ex]
    ['a']
    >>> [n.label for n in en]
    ['c']
    >>> pivot.label
    'ch1'

    Descent into child:

    >>> ex, en, pivot = decompose_move(ch1, a)
    >>> [n.label for n in ex]
    []
    >>> [n.label for n in en]
    ['a']
    >>> pivot.label
    'ch1'
    """
    pivot = lca(source, target)
    if pivot is None:
        raise ValueError(
            f"Nodes {source!r} and {target!r} share no common ancestor"
        )

    exit_path: list[HierarchicalNode] = []
    node = source
    while node is not pivot:
        exit_path.append(node)
        node = node.parent
        if node is None:
            raise ValueError("LCA not in source ancestor chain")

    enter_path: list[HierarchicalNode] = []
    node = target
    while node is not pivot:
        enter_path.append(node)
        node = node.parent
        if node is None:
            raise ValueError("LCA not in target ancestor chain")
    enter_path.reverse()  # ordered: [lca_child, ..., target]

    return exit_path, enter_path, pivot


# ---------------------------------------------------------------------------
# TraversableNode
# ---------------------------------------------------------------------------

class TraversableNode(HierarchicalNode):
    """Graph node that participates in cursor-driven traversal.

    Why
    ---
    Core's ``HierarchicalNode`` provides topology (edges, parent/child hierarchy).
    ``TraversableNode`` adds the **traversal contract**: a node is either a leaf
    (the cursor lands on it directly and the pipeline fires) or a container (the
    cursor descends into its ``source`` member via a prereq redirect).

    Container semantics are structural, not behavioral.  When the cursor arrives
    at a container, a system-level prereq handler detects ``is_container`` and
    returns an anonymous edge to the source.  The frame follows that edge, which
    runs the full pipeline on the source — including its own prereqs, which may
    redirect further.  This means nested containers descend recursively through
    normal pipeline execution, with no special mechanism.

    The ancestor chain at any cursor position defines the complete resource scope.
    Each ancestor's locals, satisfied dependencies, and registered behaviors
    contribute to the namespace via ``scoped_dispatch``.  Container entry adds
    layers; container exit (moving to a node with a higher LCA) removes them.
    This is computed from the hierarchy, not maintained as a mutable stack.

    Key Features
    ------------
    * **Leaf / container duality** — one class, container behavior activates when
      ``source_id`` is set.  No separate ``TraversableLeaf`` / ``TraversableContainer``.
    * **UUID-referenced source/sink** — stored as ``source_id`` / ``sink_id``,
      dereferenced through the graph.  Source and sink must be members.
    * **enter()** — produces an ``AnonymousEdge`` to the source for prereq descent.
    * **Hierarchy = context** — ``self.ancestors`` defines the full scope; the LCA
      of source/target determines what changes on movement.

    API
    ---
    - ``source_id`` / ``sink_id`` — UUIDs of the designated entry/exit members.
    - ``source`` / ``sink`` — dereferenced property accessors.
    - ``is_container`` — ``True`` when ``source_id`` is set.
    - ``enter()`` — descent edge to source (called by prereq handler).
    - ``default_egress_id`` — optional fallback destination when no explicit exit.
    - ``has_forward_progress(from_node)`` — softlock detection (stub for MVP).

    Notes
    -----
    **No synthetic source/sink nodes.**  Unlike legacy ``TraversableSubgraph``,
    which created hidden ``__SOURCE`` / ``__SINK`` nodes with auto-wired edges,
    ``TraversableNode`` designates existing members as source and sink.  The
    canonical single-source/single-sink form is achieved by having edges into
    the container target the container itself (prereq descends to source) and
    edges out of the container originate from the sink.

    **No exit() method.**  Ascent from a container is not a method on the node.
    It is either: (a) an explicit edge from the sink to a node outside the
    container, (b) a postreq continuation that the pipeline follows, or (c) a
    return-stack pop when a call edge completes.  All three are handled by
    ``Frame.resolve_choice`` through normal pipeline execution.

    Examples
    --------
    Leaf node (no container structure):

    >>> from tangl.core38 import Graph
    >>> g = Graph()
    >>> leaf = TraversableNode(label="leaf", registry=g)
    >>> leaf.is_container
    False
    >>> leaf.enter()
    Traceback (most recent call last):
      ...
    ValueError: ...not a container...

    Container with source and sink:

    >>> container = TraversableNode(label="scene", registry=g)
    >>> src = TraversableNode(label="enter", registry=g)
    >>> snk = TraversableNode(label="leave", registry=g)
    >>> mid = TraversableNode(label="middle", registry=g)
    >>> container.add_child(src)
    >>> container.add_child(mid)
    >>> container.add_child(snk)
    >>> container.source_id = src.uid
    >>> container.sink_id = snk.uid
    >>> container.is_container
    True
    >>> edge = container.enter()
    >>> edge.successor is src
    True
    >>> edge.predecessor is container
    True
    """

    source_id: Optional[UUID] = None
    """UUID of the designated entry member, or ``None`` for leaf nodes."""

    sink_id: Optional[UUID] = None
    """UUID of the designated exit/teardown member, or ``None`` for leaf nodes."""

    default_egress_id: Optional[UUID] = None
    """Optional fallback destination when no explicit exit edge from sink."""

    @property
    def source(self) -> Optional[TraversableNode]:
        """The designated entry member, dereferenced through the graph."""
        if self.source_id is None:
            return None
        return self.graph.get(self.source_id)

    @property
    def sink(self) -> Optional[TraversableNode]:
        """The designated exit member, dereferenced through the graph."""
        if self.sink_id is None:
            return None
        return self.graph.get(self.sink_id)

    @property
    def default_egress(self) -> Optional[TraversableNode]:
        """Optional fallback destination, dereferenced through the graph."""
        if self.default_egress_id is None:
            return None
        return self.graph.get(self.default_egress_id)

    @property
    def is_container(self) -> bool:
        """``True`` if this node has internal structure to descend into.

        A container has a ``source_id`` designating its entry member.  When the
        cursor arrives at a container, a prereq handler should call ``enter()``
        and follow the returned edge.

        >>> from tangl.core38 import Graph
        >>> g = Graph()
        >>> leaf = TraversableNode(label="leaf", registry=g)
        >>> leaf.is_container
        False
        """
        return self.source_id is not None

    def enter(self) -> AnonymousEdge:
        """Produce the descent edge from this container to its source member.

        Called by the system-level prereq handler when the cursor arrives at a
        container.  The returned edge, when followed by the frame, moves the
        cursor to the source and runs the full pipeline — which may itself
        trigger further descent if the source is also a container.

        Raises
        ------
        ValueError
            If this node is not a container (``source_id is None``).
        RuntimeError
            If the source member cannot be resolved from the graph.

        Returns
        -------
        AnonymousEdge
            A lightweight edge from ``self`` to ``self.source``.

        >>> from tangl.core38 import Graph
        >>> g = Graph()
        >>> scene = TraversableNode(label="scene", registry=g)
        >>> enter = TraversableNode(label="enter", registry=g)
        >>> scene.add_child(enter)
        >>> scene.source_id = enter.uid
        >>> edge = scene.enter()
        >>> edge.successor is enter
        True
        >>> edge.predecessor is scene
        True
        >>> edge.entry_phase is None
        True
        """
        if not self.is_container:
            raise ValueError(f"{self!r} is not a container (source_id is None)")
        source = self.source
        if source is None:
            raise RuntimeError(
                f"{self!r} source_id={self.source_id} not found in graph"
            )
        return AnonymousEdge(predecessor=self, successor=source)

    def has_forward_progress(
        self,
        from_node: TraversableNode,
        *,
        ns: dict | None = None,
    ) -> bool:
        """Check whether the sink is reachable from ``from_node``.

        Traverses only member nodes and only edges whose availability
        conditions are satisfied in the given namespace.  Used for
        softlock detection.

        .. note::
           Stub for MVP.  Returns ``True`` unconditionally.
        """
        # TODO: BFS/DFS over members checking edge availability,
        #       similar to legacy TraversableSubgraph.has_forward_progress
        return True


# ---------------------------------------------------------------------------
# TraversableEdge
# ---------------------------------------------------------------------------

class TraversableEdge(Edge):
    """Directed edge with traversal metadata for the phase pipeline.

    Why
    ---
    Core's ``Edge`` provides topology (predecessor/successor endpoints).
    ``TraversableEdge`` adds two fields that control how the frame processes
    movement along this edge:

    - ``entry_phase``: which pipeline phase to start at when arriving via this
      edge.  A return edge might set ``entry_phase=UPDATE`` to skip validation
      and planning on a node that was already processed.
    - ``return_phase``: if set, this edge represents a **call**.  The frame
      pushes it onto the return stack before following.  When the callee's
      pipeline reaches a terminal (no redirect), the frame pops the stack
      and follows ``get_return_edge()`` back to the predecessor at the
      specified phase.

    Key Features
    ------------
    * **Phase control** — ``entry_phase`` lets call/return and continuation
      edges skip already-completed phases.
    * **Call semantics** — ``return_phase`` marks an edge as a call.  The
      edge itself is the return bookmark (one UUID in the graph, not a
      separate data structure).
    * **Type narrowing** — properties narrow ``predecessor``/``successor``
      to ``TraversableNode`` for downstream convenience.

    API
    ---
    - ``entry_phase`` — pipeline start phase at the successor.
    - ``return_phase`` — if set, push this edge as return bookmark.
    - ``get_return_edge()`` — construct the return ``AnonymousEdge``.

    Examples
    --------
    >>> from tangl.core38 import Graph
    >>> g = Graph()
    >>> a = TraversableNode(label="a", registry=g)
    >>> b = TraversableNode(label="b", registry=g)
    >>> e = TraversableEdge(registry=g, predecessor_id=a.uid, successor_id=b.uid)
    >>> e.predecessor is a and e.successor is b
    True
    >>> e.entry_phase is None
    True

    Call edge with return:

    >>> call = TraversableEdge(
    ...     registry=g, predecessor_id=a.uid, successor_id=b.uid,
    ...     return_phase=ResolutionPhase.UPDATE,
    ... )
    >>> ret = call.get_return_edge()
    >>> ret.successor is a
    True
    >>> ret.entry_phase == ResolutionPhase.UPDATE
    True
    """

    trigger_phase: Optional[ResolutionPhase] = None
    """If set, this edge is an auto-follow redirect during the named phase.

    When the cursor arrives at this edge's predecessor and the pipeline
    reaches the trigger phase (PREREQS or POSTREQS), the system handler
    scans outgoing edges for ones with a matching ``trigger_phase``.  The
    first available one is returned as a redirect.

    This is NOT the same as ``entry_phase``.  ``trigger_phase`` says *when
    to activate me*; ``entry_phase`` says *where to start the pipeline at
    my destination*.

    Typical values:
    - ``ResolutionPhase.PREREQS`` — auto-redirect before the player sees content.
    - ``ResolutionPhase.POSTREQS`` — continuation after content, before choices.
    """

    entry_phase: Optional[ResolutionPhase] = None
    """Pipeline phase to start at when the cursor arrives via this edge.

    When an edge is followed (whether by player choice or auto-redirect),
    ``entry_phase`` controls where the pipeline begins at the destination.
    ``None`` means start from VALIDATE (the beginning).

    Typical values:
    - ``None`` — full pipeline (default for player choices).
    - ``ResolutionPhase.PLANNING`` — skip validation (used by ``goto_node``).
    - ``ResolutionPhase.UPDATE`` — skip validation and planning (used by
      return edges where the destination was already provisioned).
    """

    return_phase: Optional[ResolutionPhase] = None
    """If set, this is a call edge.  The frame pushes it onto the return
    stack and, on completion, follows ``get_return_edge()`` back to
    ``predecessor`` starting at this phase."""

    @property
    def predecessor(self) -> Optional[TraversableNode]:
        """Type-narrowed predecessor."""
        return super().predecessor

    @property
    def successor(self) -> Optional[TraversableNode]:
        """Type-narrowed successor."""
        return super().successor

    def get_return_edge(self) -> AnonymousEdge:
        """Construct the return edge from this call edge.

        The return edge targets the predecessor (the call site) and starts
        the pipeline at ``return_phase`` (skipping phases already completed
        before the call).

        Raises
        ------
        ValueError
            If ``return_phase`` is not set (not a call edge).
        """
        if self.return_phase is None:
            raise ValueError(f"{self!r} is not a call edge (return_phase is None)")
        return AnonymousEdge(
            successor=self.predecessor,
            entry_phase=self.return_phase,
        )


# ---------------------------------------------------------------------------
# AnonymousEdge
# ---------------------------------------------------------------------------

@dataclass(kw_only=True)
class AnonymousEdge:
    """Lightweight edge without graph membership.

    Why
    ---
    ``TraversableEdge`` is a full graph item — it requires a managing graph,
    gets a UUID, participates in persistence.  For transient traversal
    operations (prereq redirects, descent edges, return edges), that overhead
    is unnecessary.  ``AnonymousEdge`` is a plain dataclass: create it, follow
    it, let it be garbage collected.

    Key Features
    ------------
    * **No graph required** — not a ``GraphItem``, no ``bind_registry``.
    * **Same interface for Frame** — ``entry_phase``, ``predecessor``,
      ``successor`` match ``TraversableEdge`` so ``follow_edge`` accepts both.
    * **GC-friendly** — no persistent identity, no UUID, no registry reference.

    API
    ---
    - ``successor`` — required destination node.
    - ``predecessor`` — optional origin node (for context, not navigation).
    - ``entry_phase`` — optional pipeline start phase at successor.

    Notes
    -----
    ``AnonymousEdge`` has no ``return_phase`` because transient edges are never
    push targets for the return stack — only persistent ``TraversableEdge``
    instances (with graph-stable UUIDs) serve as call bookmarks.

    Examples
    --------
    >>> from tangl.core38 import Graph
    >>> g = Graph()
    >>> a = TraversableNode(label="a", registry=g)
    >>> b = TraversableNode(label="b", registry=g)
    >>> e = AnonymousEdge(successor=b)
    >>> e.successor is b
    True
    >>> e.predecessor is None
    True
    >>> e.entry_phase is None
    True

    With entry phase (for return edges):

    >>> e2 = AnonymousEdge(successor=a, entry_phase=ResolutionPhase.UPDATE)
    >>> e2.entry_phase == ResolutionPhase.UPDATE
    True
    """

    successor: TraversableNode
    """Destination node (required)."""

    predecessor: Optional[TraversableNode] = None
    """Origin node (optional, for context)."""

    entry_phase: Optional[ResolutionPhase] = None
    """Pipeline phase to start at when following this edge."""

    def __repr__(self) -> str:
        src = self.predecessor.get_label() if self.predecessor is not None else "anon"
        dst = self.successor.get_label() if self.successor is not None else "anon"
        phase = f"@{self.entry_phase.name}" if self.entry_phase else ""
        return f"<AnonymousEdge:{src}->{dst}{phase}>"


# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

AnyTraversableEdge: TypeAlias = Union[AnonymousEdge, TraversableEdge]
"""Either a persistent graph edge or a transient anonymous edge.

``Frame.follow_edge`` accepts both — the interface overlap (``successor``,
``predecessor``, ``entry_phase``) is sufficient for pipeline execution.
"""
