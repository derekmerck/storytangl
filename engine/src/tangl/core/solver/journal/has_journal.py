from __future__ import annotations
from typing import TYPE_CHECKING
from uuid import UUID
import logging

from pydantic import Field

from tangl.type_hints import UnstructuredData
from tangl.utils.bookmarked_list import BookmarkedList
from tangl.core.entity import Registry
from tangl.core.entity import Node, Graph
from ..abs_feature_graph import BlameEdge
from .content_fragment import ContentFragment


logger = logging.getLogger(__name__)

# todo: a resolution process might have several different trace journals, for example,
#       std out with content vs process out with process metadata (why, what was added, etc.)
#       Consider them as channels?

# todo: add a pydantic schema for bookmarked list so we can get rid of arbitrary types allowed
#       and manage serialization better.

JournalEntry = list[ContentFragment]

class HasJournal(Registry[ContentFragment], arbitrary_types_allowed=True):
    """
    Manages a journal of trace fragments with functionalities for bookmarking,
    retrieving, and organizing entries.

    The `HasJournal` class extends the functionality of a registry to include
    bookmarking and organizing content fragments into a journal. Each fragment
    can be uniquely identified and associated with sections or entries. It also
    provides mechanisms to establish relationships between fragments and their
    originating structural nodes.

    :ivar journal: A list of bookmarks, where each bookmark corresponds to
        a unique identifier for journal sections or entries.
    :type journal: BookmarkedList[UUID]
    :ivar fragment_counter: A counter that keeps track of the sequence
        number for content fragments.
    :type fragment_counter: int
    """

    journal: BookmarkedList[UUID] = Field(default_factory=BookmarkedList)
    fragment_counter: int = 0

    def start_journal_section(self, which):
        self.journal.set_bookmark(which, bookmark_type="section")

    def get_journal_section(self, which=-1) -> JournalEntry:
        items = self.journal.get_slice(which, bookmark_type="section")
        return [self.get(uid) for uid in items]

    def add_fragment(self, item: ContentFragment | UnstructuredData, blame: Node = None):
        if isinstance(item, dict):
            item = ContentFragment.structure(item)
        if not isinstance(item, ContentFragment):
            raise ValueError(f"Trying to add wrong type {type(item)} to graph via journal")
        # todo: need to unfreeze or set with a trick
        # if item.sequence is None:
        #     # Record the fragment counter as the sequence num
        #     item.sequence = self.fragment_counter
        self.fragment_counter += 1
        self.add(item)
        # If the call indicates the originating structure node, record it as a blame edge
        if blame is not None:
            # todo: maybe this shouldn't be a mixin?
            edge = BlameEdge(src=item, dst=blame, graph=self)
            super().add(edge)

    def add_journal_entry(self, items: JournalEntry, blame: Node = None):
        if not items:
            logger.warning("Tried to do a no-op journal update.  This is harmless, but probably not what you intended to do.")
            return
        for item in items:
            self.add_fragment(item, blame=blame)
        # Use the first fragment's uid to create a unique bookmark name
        bookmark_name = f"entry@{items[0].uid!s}"
        logger.debug(f"Adding entry for bookmark: {bookmark_name}")
        self.journal.add_items([item.uid for item in items],
                               bookmark_name=bookmark_name,
                               bookmark_type="entry")

    def get_journal_entry(self, which=-1) -> list[ContentFragment]:
        # early stop types param looks for terminating section edges, as well
        items = self.journal.get_slice(which, bookmark_type="entry", early_stop_types=["section"])
        return [self.get(uid) for uid in items]
