from __future__ import annotations
from typing import TYPE_CHECKING
from uuid import UUID
import logging

from pydantic import Field

from tangl.utils.bookmarked_list import BookmarkedList
from tangl.core.entity import Registry
from .content_fragment import ContentFragment

if TYPE_CHECKING:
    from ..structure import Node

logger = logging.getLogger(__name__)

class HasJournal(Registry[ContentFragment], arbitrary_types_allowed=True):
    """
    Manages a journal of trace fragments with functionalities for bookmarking,
    retrieving, and organizing entries.

    The `HasTraceJournal` class extends the functionality of a registry to include
    bookmarking and organizing content fragments into a journal. Each fragment
    can be uniquely identified and associated with sections or entries. It also
    provides mechanisms to establish relationships between fragments and their
    originating structural nodes.

    :ivar trace_journal: A list of bookmarks, where each bookmark corresponds to
        a unique identifier for journal sections or entries.
    :type trace_journal: BookmarkedList[UUID]
    :ivar fragment_counter: A counter that keeps track of the sequence
        number for content fragments.
    :type fragment_counter: int
    """

    journal: BookmarkedList[UUID] = Field(default_factory=BookmarkedList)
    fragment_counter: int = 0

    def start_journal_section(self, which):
        self.journal.set_bookmark(which, bookmark_type="section")

    def get_journal_section(self, which=-1) -> list[ContentFragment]:
        items = self.journal.get_slice(which, bookmark_type="section")
        return [self.get(uid) for uid in items]

    def add_fragment(self, item: ContentFragment, blame: Node = None):
        if not isinstance(item, ContentFragment):
            raise ValueError(f"Trying to add wrong type {type(item)} to graph via journal")
        if item.sequence is None:
            # Record the fragment counter as the sequence num
            item.sequence = self.fragment_counter
        self.fragment_counter += 1
        self.add(item)
        # If the call indicates the originating structure node, record it as a blame edge
        if blame is not None:
            from ..structure import Graph, EdgeKind
            Graph.add_edge(self, src=item, dst=blame, edge_kind=EdgeKind.BLAME)

    def add_journal_entry(self, items: list[ContentFragment], blame: Node = None):
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
