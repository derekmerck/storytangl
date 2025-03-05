from __future__ import annotations

from pydantic import BaseModel

from tangl.business.core.handlers import HasContext, TraversableGraph, on_gather_context
from tangl.service.journal import HasJournal
from tangl.service.account import HasUser
from tangl.business.world.world import HasWorld
from .story_node import StoryNode

class StoryInfo(BaseModel):
    ...

class Story(HasJournal, HasWorld, HasUser, HasContext, TraversableGraph[StoryNode]):

    dirty: bool = False  # flag for when the story has been tampered with

    def is_dirty(self):
        return self.dirty or any( v.dirty for v in self.values() if hasattr(v, "dirty") )

    @on_gather_context
    def _provide_dirty(self, **context) -> dict:
        return {"dirty": self.is_dirty()}
