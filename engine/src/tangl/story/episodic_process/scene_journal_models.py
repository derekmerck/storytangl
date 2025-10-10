from typing import Optional
from tangl.core.fragment import ContentFragment

class BlockJournalItem(ContentFragment):
    actions: Optional[list[ContentFragment]] = None
