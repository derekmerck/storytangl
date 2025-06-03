from tangl.type_hints import StringMap
from tangl.core.handler import HandlerRegistry, BaseHandler
from ..feature_nodes import _FeatureEdge, _FeatureNode, ResourceNode
from .open_feature_edge import DependencyEdge

#### HANDLERS ####

class DependencyProvisioner(BaseHandler):

    def get_provider_for(self, dependency: DependencyEdge, *scopes, ctx: StringMap) -> bool:
        ...

    @classmethod
    def provision_dependency(cls, dependency: DependencyEdge, *scopes, ctx: StringMap) -> _FeatureNode:
        for h in cls.registry.gather_handlers(dependency, *scopes):
            if dependency.is_satisfied_by(h.get_provider_for(dependency, ctx=ctx)):
                return h.func(dependency, ctx)
                dependency.dest = node
                return node
        else:
            raise RuntimeError(f"Cannot satisfy dependency {dependency}")

    # return first

    @classmethod
    def provision_node(cls, node: _FeatureNode, *scopes, ctx: StringMap):
        for dependency in node.dependencies():
            if not dependency.is_resolved():
                node = cls.provision_dependency(dependency, *scopes, ctx=ctx)
                dependency.dest = node  # todo: this should create an provides edge back


dependency_provisioner = HandlerRegistry[DependencyProvisioner](
    label="dependency_provisioner",
    default_aggregation_strategy="pipeline")
