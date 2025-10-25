from __future__ import annotations
from uuid import UUID
from typing import Self, Iterator, TypeVar, Generic, Any
from dataclasses import dataclass, field, asdict

from tangl.type_hints import UnstructuredData
from .entity import Entity, Registry
from .scope import HasShape, StructuralScope


@dataclass
class Node(StructuralScope):
    # Can act as a scope

    @property
    def nodes(self) -> Iterator[Node]:
        return filter(lambda e: isinstance(e, Node), self.elements)

    @property
    def edges(self) -> Iterator[Edge]:
        return filter(lambda e: isinstance(e, Edge), self.elements)


PredecessorT = TypeVar("PredecessorT", bound=Node)
SuccessorT = TypeVar("SuccessorT", bound=Node)

@dataclass
class Edge(HasShape, Generic[PredecessorT, SuccessorT]):
    # Not a scope, data type used by graph
    predecessor_id: UUID = None
    successor_id: UUID = None

    @property
    def predecessor(self) -> PredecessorT:
        return self.get_element(self.predecessor_id)  # type: PredecessorT

    @predecessor.setter
    def predecessor(self, value: PredecessorT):
        self.shape_registry.add(value)
        self.predecessor_id = value.uid

    @property
    def successor(self) -> SuccessorT:
        return self.get_element(self.successor_id)   # type: SuccessorT

    @successor.setter
    def successor(self, value: SuccessorT):
        self.shape_registry.add(value)
        self.successor_id = value.uid

@dataclass
class Traversable(StructuralScope):

    # Structural pathing

    # Subgraphs will have a source and a sink for pathing
    source_id: UUID = field(default_factory=UUID)
    sink_id: UUID = field(default_factory=UUID)

    @property
    def source(self) -> Node:
        return self.get_element(self.source_id)

    @source.setter
    def source(self, value: Node):
        self.add_element(value)
        self.source_id = value.uid

    @property
    def sink(self) -> Node:
        return self.get_element(self.sink_id)

    @sink.setter
    def sink(self, value: Node):
        self.add_element(value)
        self.sink_id = value.uid


class ChoiceEdge(Edge[Traversable, Traversable]):
    ...

@dataclass
class Graph(StructuralScope, Traversable, Entity):
    shape_registry: Registry[Node | Edge] = field(default_factory=Registry)  # do serialize
    tick: int = 0

    # Cursor management

    def __init__(self):
        self.cursor = self.source

    cursor_ids: list[UUID] = field(default_factory=list)
    # Jump/return stack

    def push_cursor(self, value: Node):
        self.cursor_ids.append(value.uid)

    def pop_cursor(self):
        self.cursor_ids.pop()

    @property
    def cursor(self) -> Traversable:
        if self.cursor_ids:
            return self.get_element(self.cursor_ids[-1])
        return None

    @cursor.setter
    def cursor(self, value: Traversable):
        self.cursor_jump(value)

    def cursor_jump(self, value: Traversable):
        self.pop_cursor()
        self.push_cursor(value)

    def cursor_jr(self, value: Traversable):
        self.push_cursor(value)

    def cursor_return(self):
        if len(self.cursor_ids) == 0:
            raise RuntimeError("No cursor on stack for return")
        self.pop_cursor()

    # Convenience accessors

    # Don't need to track el_ids for registry owner
    element_ids: type[None] = field(init=False, default=None)

    @property
    def nodes(self) -> Iterator[Node]:
        return self.shape_registry.find(obj_cls=Node)

    @property
    def edges(self) -> Iterator[Edge]:
        return self.shape_registry.find(obj_cls=Edge)

    # Structure

    def unstructure(self) -> UnstructuredData:
        # Only serialize shapes _once_ and reference the single registry when restructuring
        ...

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        ...
