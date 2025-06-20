from typing import Literal, Any, Optional
from enum import Enum

from pydantic import ConfigDict
import yaml

from tangl.type_hints import StringMap
import tangl.utils.setup_yaml
from tangl.core.entity import Edge, Node, Graph  # Must import graph to define Node subclasses
from tangl.core.handler import Satisfiable


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

class ContentFragment(Node):
    # red, output, linked within by red, without by yellow
    """
    Minimal content fragment, fundamental unit for trace processes journal/log
    output.  Extended elsewhere.

    Fragments may be connected to their originating structure or resource nodes
    by 'blame' edges if they are part of the same graph.

    Edges between journal items are implicit in sequence since the journal is strictly
    linear and monotonic in sequence.
    """
    # fragments are immutable once created
    model_config = ConfigDict(frozen=True)

    content_type: Optional[str|Enum] = None  # intent for content, e.g., 'text', 'choice', 'media'
    content: Any
    sequence: Optional[int] = None
    # mime-type is added in the service layer, when the fragment is serialized into a dto.

    def __str__(self):
        data = self.model_dump()
        s = yaml.dump(data, default_flow_style=False)
        return s

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

# Irrelevant, managed by the journal handler
# class TraceEdge(Edge[ContentFragment, ContentFragment]):
#     # Linear across ContentFragment seq
#     ...

# DependencyEdge and AffordanceEdge are detailed in the provisioner subpackage
