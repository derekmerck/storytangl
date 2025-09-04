from __future__ import annotations

from os import WCONTINUED
from typing import Optional, Iterator, Self, ClassVar
from uuid import UUID

from pydantic import Field, model_validator

from tangl.type_hints import StringMap
from tangl.core.entity import Entity, Node, Graph
from tangl.core.handler import HasHandlers, HandlerPriority as Priority
from tangl.core.services import HasContext, on_gather_context


class HierarchicalScope(HasContext, Node):
    """
    Represents a one-to-many hierarchical scope with parent-child relationships
    -- graphs and subgraphs _do_ care about which nodes/subgraphs belong to them.

    Nodes on partitionable graphs are implicitly _part of_ the hierarchy stack.

    Parent is the conceptual anchor for a subgraph.  Purpose is to be able to
    inherit scope from parents, or use within scope as a predicate for children.

    The underlying shared graph object is only used for dereferencing memberships,
    is-parent and is-within are _not_ explicit edges in the sense of structural
    edges, dependencies, blame, etc.

    For nodes, this is equivalent to an anchored subgraph.  For a registry of
    generic entities, this would be a partition and require a reference
    to the containing registry for all accessors.  Using Graph here is primarily
    a syntactic convenience b/c generic entities don't carry a reference to a
    single management container.
    """
    parent_id: Optional[UUID] = None
    # Either a node, or None if it is a partition on the graph itself

    @model_validator(mode="before")
    @classmethod
    def _convert_parent_to_id(cls, data):
        parent = data.pop("parent", None)
        if parent is not None:
            if "parent_id" in data:
                if parent.uid != data["parent_id"]:
                    raise ValueError("Mismatched parent_id and parent in build kwargs")
                # otherwise can just ignore parent
            else:
                data["parent_id"] = parent.uid
        return data

    @property
    def parent(self) -> Optional[Node]:
        if self.parent_id is not None:
            return self.graph.get(self.parent_id)
        return None

    @parent.setter
    def parent(self, value: None | Node) -> None:
        self.parent_id = value

    children_ids: list[UUID] = Field(default_factory=list)

    @property
    def children(self) -> Iterator[Node]:
        yield from [ self.graph.get(g) for g in self.children_ids ]

    def find_children(self, **criteria) -> Iterator[Entity]:
        for child in self.children:
            if child.matches(**criteria):
                yield child

    def add_child(self, node: Node) -> None:
        if node not in self.graph:
            self.graph.add(node)
        self.children_ids.append(node.uid)

    def remove_child(self, node: Node, discard: bool = False) -> None:
        self.children_ids.remove(node.uid)
        if discard:
            # todo: check if it's linked anywhere in children or edges
            # if self.graph.is_linked(node):
            #     raise RuntimeError("Cannot discard a linked node")
            self.graph.remove(node)

    @property
    def ancestors(self) -> Iterator[Self]:
        # nearest to farthest
        current = self
        while current is not None:
            yield current
            current = current.parent

    @property
    def root(self):
        return list(self.ancestors)[0]

    def subgraph_path(self) -> Iterator[Self]:
        """Get the full subgraph path from root to this subgraph"""
        return reversed(list(self.ancestors))

    PATH_SEP: ClassVar[str] = "/"

    @property
    def path(self) -> str:
        return self.PATH_SEP.join( [ s.label for s in self.subgraph_path() ] )

    @on_gather_context.register(priority=Priority.EARLY)
    def _addend_parent_context(self, **kwargs) -> StringMap:
        # Gather ancestor context recursively
        if self.parent is not None:
            if isinstance(self.parent, HasContext):
                return self.parent.gather_context()
        else:
            # Pipelines will only collect each handler once, but this is a nested pipeline
            # _inside_ another pipeline, so it would trigger for ancestor.
            # Wrapping it with 'if parent is None' means only the root of a dag will trigger it.
            if isinstance(self.graph, HasContext):
                return self.graph.gather_context()
