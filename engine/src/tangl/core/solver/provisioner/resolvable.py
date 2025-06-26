from tangl.type_hints import StringMap
from tangl.core.entity import Node
from tangl.core.handler import on_check_satisfied
from .open_edge import DependencyEdge, AffordanceEdge


class ResolvableNode(Node):

    @property
    def dependencies(self):
        return list( *self.edges(has_cls=DependencyEdge, direction="out"),
                     *self.edges(has_cls=AffordanceEdge, direction="in") )

    @property
    def affordances(self):
        return list( *self.edges(has_cls=DependencyEdge, direction="in"),
                     *self.edges(has_cls=AffordanceEdge, direction="out") )

    # todo: consider order, if an actor, for example, has been provided as an
    #       affordance, it should get priority over actors anywhere, which gets
    #       priority over creating something new
    def provision_dependencies(self, *, ctx: StringMap = None) -> bool:
        ctx = ctx or self.gather_context()
        for dep in self.dependencies:
            if dep.is_satisfied(ctx=ctx) and not dep.is_resolved:
                dep.resolve_requirement(ctx=ctx)
        return self.is_resolved

    def discover_affordances(self, *, ctx: StringMap = None):
        # This will attach affordances in scope to _this_ node temporarily, while it is being evaluated
        # todo: allow multiple sources for affordances so they aren't lost?
        ctx = ctx or self.gather_context()
        affordances = self.graph.find_all(obj_cls=AffordanceEdge)
        for aff in affordances:
            if self.matches(**aff.source_criteria) and aff.is_satisfied(ctx=ctx):
                aff.src_id = self.uid  # Now it's a temporary dep

    @on_check_satisfied.register()
    def _confirm_is_resolved(self, ctx: StringMap) -> bool:
        return self.is_resolved

    @property
    def is_resolved(self) -> bool:
        # All dependencies and requirements are resolved, or unresolvable but inactive or weak
        return all(dep.is_resolved or not dep.is_satisfied(ctx=self) for dep in self.dependencies)
