from __future__ import annotations
import functools
from typing import Optional, Iterable, Callable, Type, TypeVar, TYPE_CHECKING, ClassVar
import logging
from uuid import UUID

from pydantic import Field, model_validator

from tangl.type_hints import Uid, Label, Tags, UniqueLabel
from tangl.utils.is_valid_uuid import is_valid_uuid
from tangl.entity import Entity, SingletonEntity

if TYPE_CHECKING:
    from .factory import GraphFactory

logger = logging.getLogger('tangl.node')

NodePath = str            # will be unique
NodeRef = Uid | NodePath  # will be unique


class Node(Entity):
    graph: Graph = Field(default=None, repr=False, exclude=True)
    parent_uid: Optional[Uid] = None

    @property
    def parent(self) -> Optional[Node]:
        if self.parent_uid:
            # print( self )
            return self.graph.nodes[self.parent_uid]

    @parent.setter
    def parent(self, value: Node | Uid | None):
        if isinstance(value, Node):
            new_parent = value
        elif isinstance(value, Uid):
            new_parent = self.graph.nodes[value]
        elif value is None:
            new_parent = None
        else:
            raise TypeError
        if self.parent is not new_parent:
            if self.parent:
                self.parent.remove_child(self)
            if new_parent:
                new_parent.add_child(self)

    children_uids: list[Uid] = Field( default_factory=list )

    @property
    def children(self) -> list[Node]:
        return [ self.graph.get_node(key) for key in self.children_uids ]

    def add_child(self, node: Node, reparent=True):
        if node.uid in self.children_uids:
            # logger.debug(f"skipped {node.uid}, already in children")
            return
        # logger.debug(f"adding {node.uid}")
        if not isinstance(node, SingletonEntity) and reparent:
            # Sometimes we add entities/singletons
            node.parent_uid = self.uid
        self.children_uids.append( node.uid )
        self.graph.add_node(node)

    def remove_child(self, node: Node):
        logger.debug(f"removing {node.uid}")
        if node.parent_uid == self.uid:
            node.parent_uid = None
        self.children_uids.remove(node.uid)

    def find_children(self,
                      node_cls: Type[T] = None,
                      filt: Callable = None,
                      has_tags: Tags = None) -> Iterable[T]:

        def filt_(x) -> bool:
            if node_cls and not isinstance(x, node_cls):
                return False
            if filt and not filt(x):
                return False
            if has_tags and not x.has_tags(has_tags):
                return False
            return True

        return filter( filt_, self.children )

    def find_child(self, *args, **kwargs) -> T:
        # convenience function for the first matching child
        candidates = list(self.find_children(*args, **kwargs))
        if candidates:
            return candidates[0]

    @property
    def ancestors(self) -> list[Node]:
        root = self
        res = [ root ]
        while root.parent:
            root = root.parent
            res.append( root )
        return res

    @property
    def root(self) -> Node:
        return self.ancestors[-1]

    @property
    def path(self) -> NodePath:
        # should be unique within a graph
        return "/".join( [x.label for x in reversed( self.ancestors ) ] )

    def __eq__(self, other: Node) -> bool:
        # This is silly, but comparing the graph field throws a recursion error
        # __eq__ is rarely used explicitly except in testing, so it's probably ok
        self_graph = self.graph
        other_graph = other.graph
        self.graph = other.graph = None
        if not super().__eq__(other):
            self.graph = self_graph
            other.graph = other_graph
            return False
        self.graph = self_graph
        other.graph = other_graph
        return True

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        if self.graph:
            self.graph.add_node(self)

T = TypeVar("T", bound=Node)

class Graph(Entity):

    nodes: dict[Uid, Node] = Field(default_factory=dict)

    def add_node(self, node: Node):
        node.graph = self
        self.nodes[node.uid] = node
        if hasattr(self, "nodes_by_path"):
            delattr( self, "nodes_by_path" )

    @functools.cached_property
    def nodes_by_path(self) -> dict[Label, Node]:
        return { v.path: v for v in self.nodes.values() }

    def get_node(self, key: NodeRef):
        if isinstance(key, str) and is_valid_uuid(key):
            key = UUID(key)
        if key in self.nodes:
            return self.nodes[key]
        elif key in self.nodes_by_path:
            return self.nodes_by_path[key]
        raise KeyError(f"No key {key}")

    def __contains__(self, key: NodeRef) -> bool:
        if key in self.nodes or key in self.nodes_by_path:
            return True
        return False

    def find_nodes(self,
                   node_cls: Type[T] = None,
                   filt: Callable = None,
                   has_tags: Tags = None) -> Iterable[T]:

        def filt_(x) -> bool:
            if node_cls and not isinstance(x, node_cls):
                return False
            if filt and not filt(x):
                return False
            if has_tags and not x.has_tags(has_tags):
                return False
            return True

        return filter(filt_, self.nodes.values())

    factory: Optional[SingletonEntity] = None  # Improperly typed for Pydantic to avoid circular imports

    # factory_: Optional[ tuple[ type[SingletonEntity], UniqueLabel ]] = Field(None, init_var=False)
    #
    # @model_validator(mode='before')
    # @classmethod
    # def _convert_factory_to_uid(cls, data):
    #     factory = data.pop('factory', None)
    #     if isinstance(factory, SingletonEntity):
    #         logger.debug(f'adding factory label {factory.label}')
    #         data['factory_'] = ( factory.__class__, factory.label )
    #     elif factory:
    #         raise TypeError(f"factory arg is wrong type {factory}")
    #     return data
    #
    # @property
    # def factory(self) -> 'GraphFactory':
    #     if self.factory_:
    #         return self.factory_[0]._instances.get(self.factory_[1])
