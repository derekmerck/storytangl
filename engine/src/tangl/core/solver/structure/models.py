from typing import TypeVar, Generic, Literal, Any, Optional
from enum import Enum

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.models import Node, Edge
from .provision import DynamicEdge, DynamicNode
from .render import RenderableNode

class NodeKind(Enum):
    STRUCTURE = "structure"  # events, linked within by control, blue
    RESOURCE = "resource"    # concepts, green
    FRAGMENT = "fragment"    # red, output, linked within by red, without by yellow

class StructureNode(Node):
    node_kind: NodeKind.STRUCTURE = NodeKind.STRUCTURE

class ResourceNode(Node):
    node_kind: NodeKind.RESOURCE = NodeKind.RESOURCE

class ContentFragment(Node):
    """
    Minimal content fragment, fundamental unit for journal/log output.
    Extended elsewhere.

    Fragments may be connected to their originating structure or resource nodes
    by 'blame' edges if they are part of the same graph.
    """
    node_kind: NodeKind = NodeKind.FRAGMENT
    fragment_type: str = "content"  # e.g., 'text', 'choice', 'media'
    content: Any
    sequence: Optional[int] = None


class EdgeKind(Enum):
    ASSOCIATE = "associate"      # unspecified link, black, possibly bi-directional
    CONTROL = "control"          # link structure, blue
    DEPENDENCY = "dependency"    # dynamic link concepts, green
    TRACE = "trace"              # link fragments, red
    BLAME = "blame"              # audit links, yellow

Trigger = Literal["before", "after"]

class Choice(Edge[StructureNode]):
    edge_kind: EdgeKind.CONTROL = EdgeKind.CONTROL
    control_trigger: Optional[Trigger] = None

class Dependency(DynamicEdge[ResourceNode]):
    edge_kind: EdgeKind.DEPENDENCY = EdgeKind.DEPENDENCY

class JournalLink(Edge[ContentFragment]):
    edge_kind: EdgeKind.TRACE = EdgeKind.TRACE

