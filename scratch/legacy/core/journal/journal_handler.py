from __future__ import annotations
from typing import ClassVar, Type
import logging
from pprint import pformat

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel
from tangl.core.handler import BaseHandler
from tangl.core.entity import Entity
from tangl.core.entity.handlers import Renderable
from tangl.core.graph import Node
from tangl.core.graph.handlers import TraversalStage, TraversalHandler
from .journal_item_model import JournalItem, JournalEntry

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Journal(Entity):
    """
    A Journal object tracks content updates for a JournaledGraph and
    provides an index of start and end points between choices and sections.

    - "Items" are blocks of content
    - "Entries" are sequences of blocks between choices
    - "Sections" are sequences of blocks belonging to a named range (e.g., chapters)
    """

    items: list[JournalItem] = Field(default_factory=list)             # items in order received
    entry_index: list[int] = Field(default_factory=list)  # first item index for entry num
    section_index: list[int] = Field(default_factory=list)      # first item index for section
    section_keys: dict[str, int] = Field(default_factory=dict)  # key to section number

    def start_new_entry(self):
        JournalHandler.start_journal_entry(self)

    def start_new_section(self, key: str = None):
        JournalHandler.start_journal_section(self, key)

    def add_item(self, item: JournalItem):
        JournalHandler.add_journal_item(self, item)

    def push_entry(self, *entry: JournalItem):
        JournalHandler.push_journal_entry(self, *entry)

    def get_entry(self, which: int = -1) -> JournalEntry:
        return JournalHandler.get_journal_entry(self, which)

    def get_section(self, which: int | str = -1) -> JournalEntry:
        return JournalHandler.get_journal_section(self, which)


class JournalHandler(BaseHandler):
    """
    The JournalHandler performs operations related to managing journal content, including
    indexing and retrieving journal entries.

    The JournalHandler mediates between the story handler and service layer.
    """
    @classmethod
    def get_journal_entry(cls, journal: Journal, which: int= -1) -> JournalEntry:
        """
        The latest entry is returned by default.
        """
        if not isinstance(which, int):
            raise TypeError(f"Which entry must be <int>, {type(which)} was passed")

        # convert negative indices to positive indices
        if which < 0:
            which = len(journal.entry_index) + which
            which = max(which, 0)

        logger.debug(f"Using which entry={which}")

        if which < 0 or which >= len(journal.entry_index):
            raise IndexError(f"Which entry index {which} is out of range {len(journal.entry_index)}")

        start_el = journal.entry_index[which]
        if which + 1 >= len(journal.entry_index):
            end_el = len(journal.items)   # last item
            logger.debug(f'{which}+1 >= {len(journal.entry_index)}, using last entry')
        else:
            logger.debug(f'{which}+1 < {len(journal.entry_index)}, using {journal.entry_index[which+1]}')
            end_el = journal.entry_index[which + 1]  # item _before_ the next entry begins
        logger.debug(f"Using entry (start_el, end_el) = {start_el, end_el}")
        return journal.items[start_el:end_el]

    @classmethod
    def get_journal_section(cls, journal: Journal,
                    which: str | int = -1) -> JournalEntry:
        """
        The latest section is returned by default.

        If a string is passed, the entire section of that name is returned as a single entry.
        """
        if not isinstance(which, (int, str)):
            raise TypeError(f"Which must be <int> or <str>, {type(which)} was passed")

        if isinstance(which, str):
            if which not in journal.section_keys:
                raise KeyError
            which = journal.section_keys[which]

        logger.debug(f"Using which section={which}")

        if len(journal.section_index) == 0:
            start_el = 0
            end_el = len(journal.items)
            return journal.items[start_el:end_el]

        if which < 0:
            which = len(journal.section_index) + which

        if which < 0 or which > len(journal.section_index):
            raise IndexError(f"Which section index {which} is out of range {len(journal.section_index)}")

        start_el = journal.section_index[which]

        if which + 1 >= len(journal.section_index):
            end_el = len(journal.items)
            logger.debug("Using len items")
        else:
            end_el = journal.section_index[which + 1]
            logger.debug("using next section - 1")
        logger.debug(f"Using section (start_el, end_el) = {start_el, end_el}")

        return journal.items[start_el:end_el]

    @classmethod
    def add_journal_item(cls, journal: Journal, item: JournalItem):
        if not isinstance(item, JournalItem):
            raise TypeError(f"While adding journal item, {type(item)} was passed")
        journal.items.append(item)

    @classmethod
    def push_journal_entry(cls, journal: Journal, *entry: JournalItem):
        cls.start_journal_entry(journal)
        if not all([isinstance(item, JournalItem) for item in entry]):
            raise TypeError(f"While pushing journal entry, {[type(item) for item in entry]} was passed")
        journal.items.extend(entry)

    @classmethod
    def start_journal_entry(cls, journal: Journal):
        """
        The story handler will invoke this whenever a player action is activated.
        """
        journal.entry_index.append(len(journal.items))

    @classmethod
    def start_journal_section(cls, journal: Journal, key: UniqueLabel = None):
        """
        The story handler invokes this whenever a new scene is entered.  Automatically
        starts a new entry.
        """
        if key is not None:
            journal.section_keys[key] = len(journal.section_index)
        journal.section_index.append( len(journal.items) )
        cls.start_journal_entry(journal)

class JournalingGraph(BaseModel):
    """
    Graph mixin that adds a journal for capturing rendered output from nodes
    """
    journal: Journal = Field(default_factory=Journal)

    def enter(self, **kwargs):
        logger.debug(f"starting new journal entry on enter graph")
        JournalHandler.start_journal_entry(self.journal)
        super().enter(**kwargs)

    @BaseHandler.strategy("on_do_action", priority=TraversalStage.BOOK_KEEPING)
    def start_new_journal_entry(self, **kwargs):
        logger.debug(f"starting new journal entry on action")
        JournalHandler.start_journal_entry(self.journal)


class JournalingNode(BaseModel):
    """
    Node mixin for renderable objects that target the story journal for rendering
    """
    journal_item_cls: ClassVar[Type[JournalItem]] = JournalItem

    @property
    def journal(self: Node) -> Journal:
        return self.graph.journal

    @TraversalHandler.enter_strategy(priority=TraversalStage.PROCESSING)
    def _render_to_journal(self: JournalingNode | Renderable, **kwargs):
        if not hasattr(self, 'render') or self.journal_item_cls is None:  # pragma: no cover
            # ignore non-rendering traversables
            return
        entry_item = self.render( **kwargs )  # adds a dict
        logger.debug(pformat(entry_item))
        journal_entry_item = self.journal_item_cls( **entry_item )
        JournalHandler.add_journal_item( self.journal, journal_entry_item )
