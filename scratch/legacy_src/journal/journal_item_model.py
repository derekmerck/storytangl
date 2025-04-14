from typing import Optional
from uuid import UUID

from tangl.utils.response_models import BaseResponse, StyleHints


class JournalItem(BaseResponse, extra='allow'):
    """
    Represents a basic content element in the journal and the core
    schema for communicating story-content to the front-end.

    Attributes:
      - uid (UUID): Unique identifier of the generating story entity.
      - label (str): Optional name for the entry.
      - text (str): Optional rendered content text.
      - icon (str): Optional suggested icon.
    """
    # base features
    uid: UUID

    # rendered
    label: Optional[str] = None
    text: Optional[str] = None
    icon: Optional[str] = None


class StyledJournalItem(JournalItem, StyleHints, extra="allow"):
    """
    Extends BaseJournalItem with style information.

    Attributes:
      - uid (uuid.UUID): Unique identifier of the generating story entity.
      - text (str): Main content text.
      - icon (str): Suggested icon.
      - style_dict (dict[str, str]): Suggested HTML style attributes
      - style_cls (list[str]): Suggested HTML .classes for styling
      - style_id (str): Suggested HTML #id
    """
    pass

JournalEntry = list[JournalItem | StyledJournalItem]
