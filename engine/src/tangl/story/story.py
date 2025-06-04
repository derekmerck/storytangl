# incrementally resolve a narrative solution frontier
from typing import NewType

from tangl.core.solver import ContentFragment
from tangl.core.solver.forward_resolve import ForwardResolver

JournalEntry = NewType("JournalEntry", list[ContentFragment])

# todo: Stories should have context (story.locals are globals)

class Story(ForwardResolver):

    user: 'User' = None            # todo: Inject this into resolution domains?
    story_domain: 'Domain' = None  # todo: Inject this into resolution domains?

    def tell(self, choice, section_bookmark = None) -> JournalEntry:
        self.resolve_choice(choice, bookmark=section_bookmark)
        return self.journal.get_current_entry()

    def get_info(self, **kwargs):
        # status update
        ...
