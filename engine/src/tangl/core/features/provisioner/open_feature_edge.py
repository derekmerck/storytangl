from typing import Generic, TypeVar, Optional
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.handler import Predicate
from ..feature_nodes import FeatureEdge, FeatureNode, ResourceNode

# NodeT = TypeVar("NodeT", bound=FeatureNode)

##### OPEN EDGES ####

# open dependencies on the frontier will be provisioned by the resolver
class DependencyEdge(FeatureEdge[FeatureNode, Optional[ResourceNode]]):  # open dest
    dest_id: Optional[UUID] = Field(None)  # Optional now
    dest_criteria: StringMap = Field(default_factory=dict)
    dest_predicate: Predicate = None
    is_unresolvable: bool = False  # tried to resolve but failed

# all open requirements will be tested by the resolver against the frontier
# edges will bind whenever conditions are met, usually to present a flexible choice
# or introduce a resource asap
class RequirementEdge(FeatureEdge[Optional[FeatureNode], FeatureNode]):  # open source
    source_id: Optional[UUID] = Field(None)  # Optional now
    source_criteria: StringMap = Field(default_factory=dict)
    source_predicate: Predicate = None
    is_unresolvable: bool = False  # tried to resolve but failed

    # def is_satisfied_by(self, node: FeatureNode) -> bool:
    #     # todo: how do we annotate for candidate.has_cls(NodeT)
    #     return node.matches(has_cls=NodeT, **self.dest_criteria)
    #
    # @property
    # def is_resolved(self) -> bool:
    #     return self.dest is not None


class ResolvableNode(FeatureNode):

    @property
    def is_resolved(self) -> bool:
        # All dependencies and requirements are resolved
        return all(edge.is_resolved for edge in self.edges(has_cls=(DependencyEdge, RequirementEdge)))
