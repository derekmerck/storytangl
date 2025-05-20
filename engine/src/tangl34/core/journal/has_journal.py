from __future__ import annotations
from uuid import UUID
import logging

from pydantic import Field

from tangl.utils.bookmarked_list import BookmarkedList
from ..entity import Registry
from .content_fragment import ContentFragment

logger = logging.getLogger(__name__)

class HasJournal(Registry[ContentFragment], arbitrary_types_allowed=True):
    # Functional wrapper for BookmarkedList of ContentFragments, implemented
    # as a mixin for Registry/Graph where content fragments are stored on the graph
    # with edges from their creator.
    #
    # Fragments are basically leaf nodes, they are frozen and have no children of their own.

    journal: BookmarkedList[UUID] = Field(default_factory=BookmarkedList)

    def start_journal_section(self, which):
        self.journal.set_bookmark(which, bookmark_type="section")

    def get_journal_section(self, which=-1) -> list[ContentFragment]:
        items = self.journal.get_slice(which, bookmark_type="section")
        return [self.get(uid) for uid in items]

    # todo: a fragment might carry a 'creator_id', which should be linked as a content edge.
    # todo: If there is an 'entry' object or fragment group per entry, we can use that as the name
    def add_journal_entry(self, items: list[ContentFragment]):
        if not items:
            logger.warning("Tried to do a no-op journal update.  This is harmelss, but probably not what you intended to do.")
            return
        for item in items:
            self.add(item)
        self.journal.add_items([item.uid for item in items], bookmark_name=f"entry@{str(items[0].uid)}", bookmark_type="entry")

    def get_journal_entry(self, which=-1) -> list[ContentFragment]:
        # early stop types param looks for terminating section edges, as well
        items = self.journal.get_slice(which, bookmark_type="entry", early_stop_types=["section"])
        return [self.get(uid) for uid in items]
