from typing import Generic, TypeVar, Optional
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.models import Edge, Node
from tangl.core.handler import Predicate

NodeT = TypeVar("NodeT", bound=Node)

class DynamicEdge(Edge, Generic[NodeT]):
    dest_id: Optional[UUID] = Field(None)
    dest_criteria: StringMap = Field(default_factory=dict)
    dest_predicate: Predicate = None
    is_unresolvable: bool = False  # tried to resolve but failed

    def is_satisfied_by(self, node: Node) -> bool:
        # todo: how do we annotate for candidate.has_cls(NodeT)
        return node.matches(has_cls=NodeT, **self.dest_criteria)

    @property
    def is_resolved(self) -> bool:
        return self.dest is not None

# todo: dependencies have edges with dynamically assigned _dest_.

# todo: events may have edges with dynamically assigned _source_.  That is,
#       the edge will bind when conditions are met and present a choice.


class DynamicNode(Node):

    @property
    def is_resolved(self) -> bool:
        return all(edge.is_resolved for edge in self.edges_out(has_cls=DynamicEdge))
