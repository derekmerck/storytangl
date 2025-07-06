from __future__ import annotations
from dataclasses import dataclass, field, replace
from enum import Enum, auto
from typing import Any

from pyrsistent import pmap, pvector, PMap, PVector


NodeId = str
EdgeId = str

@dataclass(frozen=True, slots=True)
class Node:
    id: NodeId
    scope_id: str
    tags: frozenset[str] = frozenset()
    locals: PMap = pmap()      # immutable

@dataclass(frozen=True, slots=True)
class Edge:
    id: EdgeId
    src: NodeId
    dst: NodeId
    predicate: str = "true"    # raw DSL string for now
    effects: tuple = ()        # list later

@dataclass(frozen=True, slots=True)
class Shape:
    nodes: PMap[NodeId, Node] = field(default_factory=pmap)
    edges: PVector[Edge]      = field(default_factory=pvector)

@dataclass(frozen=True, slots=True)
class StoryIR:
    shape: Shape = field(default_factory=Shape)
    state: PMap = field(default_factory=pmap)              # global key → val
    layer_stack: tuple = ()           # empty for S-0
    tick: int = 0

    @classmethod
    def from_raw(cls, d: dict) -> "StoryIR":
        # convert_pmap = lambda m: pmap({k: convert(v) for k, v in m.items()})

        def convert(obj):
            if isinstance(obj, dict):
                return pmap({k: convert(v) for k, v in obj.items()})
            if isinstance(obj, list):
                return pvector(map(convert, obj))
            return obj

        return cls(
            shape=Shape(
                nodes=convert(d["shape"]["nodes"]),
                edges=pvector(d["shape"]["edges"])),
            state=convert(d["state"]),
            layer_stack=tuple(d["layer_stack"]),
            tick=d["tick"],
        )

    def evolve(self, **changes) -> "StoryIR":
        """
        Return a new StoryIR with specified fields replaced.
        Equivalent to dataclasses.replace but preserves type hints.
        """
        return replace(self, **changes)

class Op(Enum):
    SET = auto()
    DELETE = auto()
    ADD_NODE = auto()
    ADD_EDGE = auto()

@dataclass(frozen=True, slots=True)
class Patch:
    tick: int
    op:  Op
    path: tuple[str, ...]   # e.g. ("shape","nodes","castle","locals","hp")
    before: Any
    after:  Any
