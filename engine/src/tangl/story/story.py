# incrementally resolve a narrative solution frontier
from typing import NewType

from tangl.core.solver.journal import ContentFragment
from tangl.core.solver import CursorDriver

JournalEntry = NewType("JournalEntry", list[TraceFragment])

class Story(CursorDriver):

    user: 'User' = None           # todo: Inject this into domains?
    story_world: 'Domain' = None  # todo: Inject this into domains?

    def tell(self, choice, section_bookmark = None) -> JournalEntry:
        self.resolve_choice(choice, section_bookmark=section_bookmark)
        return self.journal.get_current_entry()
