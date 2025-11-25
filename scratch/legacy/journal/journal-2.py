from __future__ import annotations

from pydantic import BaseModel, Field

from tangl.entity import BaseJournalItem

class JournalHandler:
    """
    Handles operations related to managing journal content, including
    indexing and retrieving journal entries.

    "Updates" are blocks of content
    "Entries" are sequences of blocks between choices
    "Sections" are sequences of blocks belonging to a named range (e.g., chapters)
    """

    @classmethod
    def start_new_entry(cls, journal: Journal):
        journal.entry_index.append( len(journal.items) )

    @classmethod
    def start_new_section(cls, journal: Journal, key: str = None):
        journal.section_index.append( len(journal.items) )
        if key is not None:
            journal.section_keys[key] = len(journal.section_index) - 1
        cls.start_new_entry(journal)

    @classmethod
    def push_update(cls, journal: Journal, *update: BaseJournalItem):
        for u in update:
            if isinstance(u, dict):
                u = BaseJournalItem(**u)
            if not isinstance(u, BaseJournalItem):
                raise TypeError
            journal.items.append(u)

    @classmethod
    def get_entry(cls, journal: Journal, which: int = -1) -> list[BaseJournalItem]:
        """
        The corresponds to the ui callback for "get journal entry"
        """
        if not isinstance(which, int):
            raise TypeError
        start_el = 0
        end_el = len(journal.items)

        if which < 0:
            which = len(journal.entry_index) - 1
        if 0 <= which < len(journal.entry_index):
            start_el = journal.entry_index[which]
            end_el = journal.entry_index[which + 1] if which + 1 < len(journal.entry_index) else end_el

        return journal.items[start_el:end_el]

    @classmethod
    def get_section(cls, journal: Journal,
                    which: str | int = -1) -> list[BaseJournalItem]:

        if not isinstance(which, (str, int)):
            raise TypeError

        start_el = 0
        end_el = len(journal.items)

        if isinstance(which, str):
            if which not in journal.section_keys:
                raise KeyError
            which = journal.section_keys.get(which)
        if which < 0:
            which = len(journal.section_index) - 1
        if 0 <= which < len(journal.section_index):
            start_el = journal.section_index[which]
            end_el = journal.section_index[which + 1] if which + 1 < len(journal.section_index) else end_el

        return journal.items[start_el:end_el]


class Journal(BaseModel):
    """
    A Journal object tracks content updates for a TraversalGraph and
    provides an index of start and end points between choices.

    The JournalUpdate model is the basic schema for communicating content
    to the front-end.
    """
    items: list[BaseJournalItem] = Field(default_factory=list)

    entry_index: list[int] = Field(default_factory=list)
    section_index: list[int] = Field(default_factory=list)
    section_keys: dict[str, int] = Field(default_factory=dict)  # key to section number

    def start_new_entry(self):
        JournalHandler.start_new_entry(self)

    def start_new_section(self, key: str = None):
        JournalHandler.start_new_section(self, key)

    def push_update(self, *update: BaseJournalItem):
        JournalHandler.push_update(self, *update)

    def get_entry(self, which: int = -1) -> list[BaseJournalItem]:
        return JournalHandler.get_entry(self, which)

    def get_section(self, which: int | str = -1) -> list[BaseJournalItem]:
        return JournalHandler.get_section(self, which)
