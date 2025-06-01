from typing import Literal, Generic, TypeVar, Any, Optional

from tangl.type_hints import StringMap
from tangl.core.entity import Edge, Node, Graph
from tangl.core.handler import HasContext, Satisfiable

# todo: need phased effect as well, like choice with when

# class NodeKind(Enum):
#     STRUCTURE = "structure"  # events, linked within by control, blue
#     RESOURCE = "resource"    # concepts, green
#     FRAGMENT = "fragment"    # red, output, linked within by red, without by yellow

# class EdgeKind(Enum):
#     ASSOCIATE = "associate"      # unspecified link, black, possibly bi-directional
#     CONTROL = "control"          # link structure, blue
#     DEPENDENCY = "dependency"    # dynamic link concepts, green
#     TRACE = "trace"              # link fragments, red
#     BLAME = "blame"              # audit links, yellow

#### TYPED NODES ####

class FeatureNode(HasContext, Satisfiable, Node):
    # Node with built-in context and gating
    ...

class StructureNode(FeatureNode):
    # scoped in hierarchical subgraphs, where parent is node in the super-graph that contains this one
    # connected by choices
    
    def choices(self, ctx: StringMap = None):
        return self.edges(direction="out", has_cls=ChoiceEdge)
    
    def dependencies(self, ctx: StringMap = None):
        return self.edges(direction="out", has_cls=DependencyEdge)

class ResourceNode(FeatureNode):
    # scoped in anchored subgraphs, where parent is the anchor node for this component
    
    def affordances(self, ctx: StringMap = None):
        return self.edges(direction="in", has_cls=DependencyEdge)

class ContentFragment(FeatureNode):
    """
    Minimal content fragment, fundamental unit for trace processes journal/log 
    output.  Extended elsewhere.

    Fragments may be connected to their originating structure or resource nodes
    by 'blame' edges if they are part of the same graph.
    
    Edges between journal items are implicit in sequence since the journal is strictly 
    linear and monotonic in sequence.
    """
    content_type: Optional[str] = None  # intent for content, e.g., 'text', 'choice', 'media'
    content: Any
    sequence: Optional[int] = None
    # mime-type is added in the service layer, when the fragment is serialized into a dto.


#### TYPED EDGES ####

When = Literal["before", "after"]

SourceT = TypeVar("SourceT", bound=Node)
DestT = TypeVar("DestT", bound=Node)

class FeatureEdge(HasContext, Satisfiable, Edge, Generic[SourceT, DestT]):
    # Edge with built-in context and gating
    ...

class ChoiceEdge(FeatureEdge[StructureNode, StructureNode]):
    # Links structure nodes
    choice_type: When = "before"

class DependencyEdge(FeatureEdge[Node, ResourceNode]):
    # Any node type may depend on a resource node, dependencies are injected by 
    # edge-type or -name into their source node's context
    dependency_type: str

class BlameEdge(FeatureEdge[Node, Node]):
    blame_type: str  # what we are assigning blame for
    
class AssociationEdge(FeatureEdge[Node, Node]):
    # Used for other types of node links, such as tradable assets or relationship quality measures
    association_type: str  # association type, e.g., 'friend', 'has', 'owned_by'
