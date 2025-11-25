from __future__ import annotations
from typing import Protocol
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from tangl.type_hints import UniqueLabel
from .journal import MediaFragment
from .entity import TaskHandler, Registry, Identifier
from .graph import Graph

# roughly analogous to a Journal for GraphDeltas
# todo: are bookmarks shared with Journal?

# ----------------
# Graph-History-related Type Hints
# ----------------

GraphDelta = dict

# ----------------
# Graph History Handler
# ----------------

class GraphHistory(Protocol):
    transitions: list[GraphTransitionStep]          # list of entries

class GraphTransitionStep(BaseModel):
    step_id: UUID
    story_id: UUID
    timestamp: datetime
    delta: GraphDelta

class BookmarkMetadata(BaseModel):
    step_id: UUID
    automatic: bool = False
    label: UniqueLabel = None
    chapter: str | None = None
    location: str | None = None
    text: str = None             # preview comment
    media: list[MediaFragment]   # preview thumbnail

class HasGraphHistory(Protocol):
    history: GraphHistory

class GraphHistoryManager(TaskHandler):

    graph: Graph

    def push_graph_transition(self, step: GraphTransitionStep): ...
    def pop_graph_transition(self) -> GraphTransitionStep: ...
    def step_graph_back(self): ...
    def step_graph_forward(self): ...
