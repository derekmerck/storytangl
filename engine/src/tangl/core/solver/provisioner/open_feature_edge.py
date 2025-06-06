from typing import Generic, TypeVar, Optional
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap, Identifier
from tangl.core.handler import Predicate, HandlerRegistry, HandlerPriority as Priority
from ..feature_nodes import _FeatureEdge, _FeatureNode, ResourceNode, StructureNode

# NodeT = TypeVar("NodeT", bound=FeatureNode)

##### OPEN EDGES ####

ResourceT = TypeVar('ResourceT', bound=ResourceNode)

# open dependencies on the frontier will be provisioned by the resolver
class DependencyEdge(_FeatureEdge[_FeatureNode, Optional[ResourceT]], Generic[ResourceT]):  # open dest
    dest_id: Optional[UUID] = Field(None)  # Optional now
    dest_ref: Optional[Identifier] = None  # sugar for criteria={'alias': ref}
    dest_criteria: StringMap = Field(default_factory=dict)
    dest_predicate: Predicate = None
    is_unresolvable: bool = False  # tried to resolve but failed

# all open requirements will be tested by the resolver against the frontier
# edges will bind whenever conditions are met, usually to present a flexible choice
# or introduce a resource asap; some critical affordances may _pre-create_ nodes that
# will be generally preferred for linking.
class RequirementEdge(_FeatureEdge[Optional[StructureNode | ResourceNode], ResourceNode]):  # open source
    source_id: Optional[UUID] = Field(None)  # Optional now
    source_ref: Optional[Identifier] = None  # sugar for criteria={'alias': ref}
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

on_provision_deps = HandlerRegistry(label="provision_deps", default_aggregation_strategy="first")
on_provide_affordances = HandlerRegistry(label="provide_affordances", default_aggregation_strategy="first")

class ResolvableNode(_FeatureNode):

    @property
    def dependencies(self):
        return self.edges(has_cls=(DependencyEdge, RequirementEdge))

    @on_provision_deps.register(priority=Priority.EARLY)
    def search_direct_providers(self, ctx: StringMap) -> Optional[ResourceNode]:
        ...

    @on_provision_deps.register(priority=Priority.LATE)
    def search_indirect_providers(self, ctx: StringMap) -> Optional[ResourceNode]:
        ...

    def provision_dependencies(self, ctx: StringMap = None) -> bool:
        ctx = ctx or self.gather_context()
        for dep in self.dependencies:
            if not dep.is_resolved:
                provider = on_provision_deps.execute_all(dep, ctx=ctx)  # type: ResourceNode
                if provider is not None:
                    dep.dest_id = provider.uid
        return self.is_resolved

    @property
    def is_resolved(self) -> bool:
        # All dependencies and requirements are resolved
        return all(dep.is_resolved for dep in self.dependencies)
