from typing import Optional
from tangl.entity import BaseJournalItem, StyledJournalItem
from tangl.media import MediaNode, JournalMediaItem

class JournalStoryUpdate(StyledJournalItem):
    """
    Extends the basic StyledJournalItem model to represent a block of content
    in the journal, including media and choice and dialog micro-blocks.

    Attributes:
      - uid (UUID): Unique identifier of the generating story entity.
      - text (str): Main content text.
      - icon (str): Suggested icon.

      - media (list[MediaItem]): List of associated media items.
      - actions (list[JournalItem]): User choices in this update.
      - dialog (list[JournalItem]): Dialog items in this update.

      - style_dict (dict[str, str]): Suggested HTML style attributes.
      - style_classes (list[str]): Suggested HTML .classes for styling.
      - style_id (str): Suggested HTML #id.
    """
    media: Optional[list[MediaNode | JournalMediaItem]] = None
    actions: Optional[list[BaseJournalItem]] = None
    dialog: Optional[list[StyledJournalItem]] = None


