from pydantic import Field

from tangl.business.core import Entity
from tangl.utils.bookmarked_list2 import UniversalBookmarkedList as BookmarkedList
from tangl.service.content_fragment import ContentFragment


class HasJournal(Entity, arbitrary_types_allowed=True):

    journal: BookmarkedList[ContentFragment] = Field(default_factory=BookmarkedList)

    def start_journal_section(self, which):
        return self.journal.set_bookmark("section", which)

    def get_journal_entry(self, which=-1) -> list[ContentFragment]:
        return self.journal.get_slice(which, bookmark_type="entry")

    def add_journal_entry(self, items: list[ContentFragment]):
        return self.journal.add_items(items, bookmark_type="entry")
