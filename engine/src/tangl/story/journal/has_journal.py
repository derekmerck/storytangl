from pydantic import Field

from tangl.utils.bookmarked_list import BookmarkedList
from tangl.core import Entity
from tangl.core.fragment import ContentFragment
from tangl.story.story_node import StoryNode

class JournalNode(StoryNode):

    content_fragments: list[ContentFragment]


class HasJournal(Entity, arbitrary_types_allowed=True):
    # Functional wrapper for bookmarked list of ContentFragments

    journal: BookmarkedList[ContentFragment] = Field(default_factory=BookmarkedList)

    def start_journal_section(self, which):
        self.journal.set_bookmark(which, bookmark_type="section")

    def get_journal_section(self, which=-1) -> list[ContentFragment]:
        return self.journal.get_slice(which, bookmark_type="section")

    def add_journal_entry(self, items: list[ContentFragment]):
        self.journal.add_items(items, bookmark_type="entry")

    def get_journal_entry(self, which=-1) -> list[ContentFragment]:
        # early stop types param looks for terminating section edges, as well
        return self.journal.get_slice(which, bookmark_type="entry", early_stop_types=["section"])
