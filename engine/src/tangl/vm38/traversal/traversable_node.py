from typing import Optional, Literal
from dataclasses import dataclass

from tangl.core38 import HierarchicalNode, Edge, Node
from tangl.vm38.runtime import ResolutionPhase


class TraversableNode(HierarchicalNode):
    ...


class TraversableEdge(Edge):

    entry_phase: Optional[ResolutionPhase] = None
    return_phase: Optional[ResolutionPhase] = None

    @property
    def predecessor(self) -> Optional[TraversableNode]:
        # for the type hint
        return super().predecessor

    @property
    def successor(self) -> Optional[TraversableNode]:
        # for the type hint
        return super().successor

    def get_return_edge(self):
        return AnonymousEdge(successor=self.predecessor, entry_phase=self.return_phase)


@dataclass(kw_only=True)
class AnonymousEdge:
    """
    AnonymousEdge(predecessor: Node, successor: Node)

    Lightweight edge without a managing graph (GC-friendly helper).

    Why
    ----
    Useful for transient computations (e.g., previews, diffs) where full graph
    membership and registration would be unnecessary overhead.

    API
    ---
    - :attr:`predecessor` – optional node reference.
    - :attr:`successor` – required node reference.
    """
    # Minimal Edge that does not require a graph, so it can be garbage collected
    entry_phase: Optional[ResolutionPhase] = None
    predecessor: Optional[TraversableNode] = None
    successor: TraversableNode

    __repr__ = Edge.__repr__
