from __future__ import annotations
from typing import Union, Protocol, TYPE_CHECKING

from .type_hints import UniqueString, StringMap, StyledStringMap
from .entity import TaskHandler, Renderable

if TYPE_CHECKING:
    # various fragment types
    from .entity import TextFragment
    from .content import MediaFragment, NarrativeFragment
    from .story_nodes import ChoiceFragment

# ----------------
# Journal-related Type Hints
# ----------------
JournalFeature = UniqueString  # format, dialog avatars, media, styled dialog, html, etc

# ----------------
# Journal
# ----------------
class Journal(Protocol):
    entries: list[JournalEntry]        # list of entries
    section_bookmarks: dict[str, int]  # names to entry indices

# annotated output for narrative, media, choices or annotated kv's
StatusFragment = StringMap | StyledStringMap

JournalFragment = Union[
    TextFragment,
    NarrativeFragment,
    MediaFragment,
    ChoiceFragment,
    StatusFragment
]

JournalEntry = list[JournalFragment]

class HasJournal(Protocol):
    journal: Journal

class JournalManager(TaskHandler):

    graph: HasJournal

    @classmethod
    def render_journal_fragment(cls, entity: Renderable) -> JournalEntry: ...

    def get_journal_entry(self, which: int | str) -> JournalEntry: ...

    def get_journal_entries(self, start: int | str, end: int = None) -> list[JournalEntry]: ...

    def push_journal_entry(self, entry: JournalEntry, section_bookmark: str = None): ...



