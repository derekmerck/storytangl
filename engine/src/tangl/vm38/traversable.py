from __future__ import annotations
from typing import Optional, Literal, TypeAlias, TypeVar, Union
from dataclasses import dataclass

from tangl.core38 import HierarchicalNode, Edge, Node
from .resolution_phase import ResolutionPhase


class TraversableNode(HierarchicalNode):
    source: TraversableNode  # must exist, must be a member
    sink: TraversableNode    # must exist, must be a member
    default_egress_node: Optional[TraversableNode] = None

    def can_reach_sink_from(self, member: TraversableNode) -> bool:
        ...

    def enter(self) -> AnyTraversableEdge:
        # setup context
        return AnonymousEdge(successor=self.source)

    def exit(self, exit_edge: Optional[TraversableEdge] = None) -> AnyTraversableEdge:
        # tear down context
        if exit_edge:
            # flowing through exit on our way somewhere
            return exit_edge
        elif self.default_egress_node:
            # return to a default node and start from beginning
            return AnonymousEdge(successor=self.default_egress_node)
        elif self.parent:
            # return to where we are defined and head for exit
            return AnonymousEdge(successor=self.parent, entry_phase=ResolutionPhase.POSTREQS)


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

AnyTraversableEdge: TypeAlias = Union[AnonymousEdge, TraversableEdge]
