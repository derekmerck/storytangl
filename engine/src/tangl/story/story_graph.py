from __future__ import annotations

from pydantic import BaseModel

from tangl.core.handlers import HasContext, TraversableGraph, on_gather_context
from tangl.user import HasUser
from tangl.world.world import HasWorld
from .journal.has_journal import HasJournal
from .story_node import StoryNode

# todo: ConceptController, StructureController, JournalController and mixins

class Story(HasJournal, HasWorld, HasUser, HasContext, TraversableGraph[StoryNode]):

    dirty: bool = False  # flag for when the story has been tampered with

    def is_dirty(self):
        return self.dirty or any( v.dirty for v in self.values() if hasattr(v, "dirty") )

    @on_gather_context.register()
    def _provide_dirty(self, **context) -> dict:
        return {"dirty": self.is_dirty()}
