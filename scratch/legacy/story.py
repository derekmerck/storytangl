# incrementally resolve a narrative solution frontier
from typing import NewType

from tangl.core.entity import Entity
from tangl.core.services import HasContext, on_gather_context
from tangl.core.solver.forward_resolve import ForwardResolver
from tangl.core.solver.journal import ContentFragment

JournalEntry = NewType("JournalEntry", list[ContentFragment])


class Story(HasContext, ForwardResolver):

    user: 'User' = None            # todo: Inject this into resolution domains?
    story_domain: 'Domain' = None  # todo: Inject this into resolution domains?

    def tell(self, choice, section_bookmark = None) -> JournalEntry:
        self.resolve_choice(choice, bookmark=section_bookmark)
        return self.journal.get_current_entry()

    def get_info(self, **kwargs):
        # status update
        ...

    # Delegations

    def find_one(self, *args, **kwargs):
        return self.graph.find_one(*args, **kwargs)

    def find_all(self, *args, **kwargs):
        return self.graph.find_one(*args, **kwargs)

    def get_journal_entry(self, item):
        return self.journal.get_entry(item)

    def add_journal_entry(self, entry):
        return self.journal.add_entry(entry)
