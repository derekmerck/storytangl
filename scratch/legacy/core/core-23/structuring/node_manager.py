"""
Factory/self-factorying feature desiderata:

- node specifications are represented as kwargs (in yaml etc.)
- a graph specification is a list of node specifications
- nodes can be cast to subclasses through their _cls variable
- nodes' attributes are type-cast during initialization
- nodes' children are instantiated during initialization
- nodes with a _templates kwarg can look up default values during initialization
- a graph can be 'structured' from specification into a new registry or a frozen reference registry
- a new registry can be generated from a frozen registry by copying the index node-for-node and relinking
- after initialization, new nodes should be created via the factory (e.g., Actors created for Roles)
"""
from __future__ import annotations
from typing import Mapping, Protocol, TYPE_CHECKING

import attr
from pydantic import BaseModel
from pluggy import PluginManager

if TYPE_CHECKING:
    from .node import Node
    from .node_registry import NodeRegistry
else:
    Node = object
    NodeRegistry = object


class NodeFactory(Protocol):
    def create_registry(self, **kwargs) -> NodeRegistry: ...


class ScriptHandler(NodeFactory):
    script: BaseModel

    @classmethod
    def load_script(cls, script_text: str) -> ScriptHandler: ...


class NodeManager(Protocol):

    label: str
    metadata: dict[str, int | str]
    locals: dict[str, int | str]

    factory: NodeFactory
    def create_registry(self, **kwargs) -> NodeRegistry: ...
    def create_node(self, cls, templates=None, **kwargs) -> Node: ...

    def ns(self, **kwargs) -> Mapping: ...

    pm: PluginManager
