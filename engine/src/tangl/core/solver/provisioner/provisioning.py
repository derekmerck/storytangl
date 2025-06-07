from typing import Optional

from tangl.type_hints import StringMap
from tangl.core.entity import Node
from tangl.core.handler import HandlerRegistry, HandlerPriority as Priority, on_check_satisfied
from .dependency import DependencyEdge, AffordanceEdge

#### HANDLERS ####

on_provision_dependency = HandlerRegistry(
    label="provision_dependency", default_aggregation_strategy="first")
"""
The global pipeline for provisioning dependencies. Handlers for resolving 
dependencies should decorate methods with ``@on_provision_dependency.register(...)``.
"""

@on_provision_dependency.register(priority=Priority.EARLY)
def search_direct_providers(dep: DependencyEdge | AffordanceEdge, ctx: StringMap) -> Optional[Node]:
    ...

@on_provision_dependency.register(priority=Priority.LATE)
def search_indirect_providers(dep: DependencyEdge | AffordanceEdge, ctx: StringMap) -> Optional[Node]:
    ...

# on_provision_affordances = HandlerRegistry(
#     label="provision_affordances", default_aggregation_strategy="first")
# """
# The global pipeline for provisioning affordance requirements. Handlers for resolving
# affordance requirements should decorate methods with ``@on_provision_affordance.register(...)``.
# """

class ResolvableNode(Node):

    @property
    def dependencies(self):
        return list( *self.edges(has_cls=DependencyEdge, direct="out"),
                     *self.edges(has_cls=AffordanceEdge, direct="in") )

    @property
    def affordances(self):
        return list( *self.edges(has_cls=DependencyEdge, direct="in"),
                     *self.edges(has_cls=AffordanceEdge, direct="out") )

    def provision_dependencies(self, ctx: StringMap = None) -> bool:
        ctx = ctx or self.gather_context()
        for dep in self.dependencies:
            if not dep.is_resolved:
                provider = on_provision_dependency.execute_all(dep, ctx=ctx)  # type: Node
                if provider is not None:
                    dep.dest_id = provider.uid
        return self.is_resolved

    @on_check_satisfied.register()
    def _confirm_is_resolved(self, ctx: StringMap) -> bool:
        return self.is_resolved

    @property
    def is_resolved(self) -> bool:
        # All dependencies and requirements are resolved
        return all(dep.is_resolved for dep in self.dependencies)
