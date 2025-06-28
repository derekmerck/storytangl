from typing import Literal

from tangl.type_hints import StringMap
from tangl.core.entity import Edge, Node, Graph  # Must import graph to define Node subclasses
from tangl.core.handlers import Satisfiable


#### TYPED NODES ####

class StructureNode(Satisfiable, Node):
    # events, linked within by choice/flow control edge, blue

    # scoped in hierarchical subgraphs, where parent is node in the super-graph that contains this one
    # connected by choices
    
    def choices(self, ctx: StringMap = None):
        return self.edges(direction="out", has_cls=ChoiceEdge, ctx=ctx)

    # todo: need phased effect handler, like choice with 'when'
    # todo: mixin for journaling node that wraps render in journal fragments

class ResourceNode(Satisfiable, Node):
    # concepts, green
    # scoped in anchored subgraphs, where parent is the anchor node for this component
    ...

# ContentFragment is detailed in journal

#### TYPED EDGES ####

When = Literal["before", "after"]

class ChoiceEdge(Satisfiable, Edge[StructureNode, StructureNode]):
    # Flow control between structure nodes, blue
    choice_type: When = "before"

class BlameEdge(Edge[Node, Node]):
    # audit links, yellow
    blame_type: str  # what we are assigning blame for

class AssociationEdge(Edge[Node, Node]):
    # unspecified link, black, possibly bi-directional
    # Used for other types of node links, such as tradable assets or relationship quality measures
    association_type: str  # association type, e.g., 'friend', 'has', 'owned_by'

# Irrelevant, trace edges are implicitly managed by the journal handler
# class TraceEdge(Edge[ContentFragment, ContentFragment]):
#     # Linear across ContentFragment seq
#     ...

# DependencyEdge and AffordanceEdge are detailed in the provisioner subpackage
