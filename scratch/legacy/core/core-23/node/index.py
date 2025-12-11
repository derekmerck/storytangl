from __future__ import annotations
from uuid import UUID
from typing import Optional, Callable, Iterable, TYPE_CHECKING

import pluggy

if TYPE_CHECKING:
    from .node import Node

class Index:
    """
    Index serves as a comprehensive collection of all nodes present within the story tree.
    It offers efficient mechanisms to add, remove, and look up nodes based on their unique
    identifiers or UID paths.

    Features:
    - Stores nodes using their unique identifiers.
    - Provides quick node lookup by unique ID or UID path.
    - Supports filtering nodes by type or custom filters.
    - Designed with extensibility in mind for future additions or plugins.

    Note:
    The class is crucial for managing complex collections with numerous interconnected nodes.
    """
    def __init__(self):
        self._nodes = dict()

    def add(self, node: 'Node'):
        self._nodes[node.guid] = node
        for child in node.children.values():
            if child not in self:
                self.add(child)

    def remove(self, node: 'Node'):
        del self._nodes[node.guid]

    def __contains__(self, item):
        from .node import Node
        if isinstance(item, Node):
            return item in self._nodes.values()
        elif isinstance(item, UUID):
            return item in self._nodes
        elif isinstance(item, str):
            return item in self._path_map
        raise TypeError

    @property
    def _path_map(self):
        return { v.path: v for v in self._nodes.values() }

    def find(self, key: str | UUID ):
        try:
            key = UUID(key, version=4)
        except (ValueError, AttributeError):
            pass
        if isinstance(key, UUID):
            if key in self._nodes:
                return self._nodes[key]
            raise KeyError(f"{key} not found in {self._nodes.keys()}")
        elif isinstance(key, str):
            if key in self._path_map:
                return self._path_map[key]
            raise KeyError(f"{key} not found in {self._path_map.keys()}")
        raise TypeError

    def filter_values(self, filt: Callable) -> list[Node]:
        return list( filter( filt, self._nodes.values() ) )

    def filter_by_type(self, node_cls: type[Node], filt: Callable = None) -> list[Node]:
        if filt:
            filt_ = lambda x: isinstance(x, node_cls) and filt(x)
        else:
            filt_ = lambda x: isinstance(x, node_cls)
        return self.filter_values( filt_ )

    @property
    def pm(self) -> Optional[pluggy.PluginManager]:
        # placeholder for a plugin-manager
        return None
