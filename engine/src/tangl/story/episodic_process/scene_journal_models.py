from typing import Optional
from tangl.journal import JournalItem

class BlockJournalItem(JournalItem):
    actions: Optional[list[JournalItem]] = None
