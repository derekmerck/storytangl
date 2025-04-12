from typing import Optional

from tangl.type_hints import Uid
from tangl.utils.response_models import BaseResponse, StyleHints

class BaseJournalItem(BaseResponse, extra='allow'):
    """
    Represents a basic content element in the journal and the core
    schema for communicating story-content to the front-end.

    Attributes:
      - uid (UUID): Unique identifier of the generating story entity.
      - text (str): Rendered content text.
      - icon (str): Suggested icon.
    """
    # base features
    uid: Uid

    # rendered
    label: Optional[str] = None
    text: Optional[str] = None
    icon: Optional[str] = None


class StyledJournalItem(BaseJournalItem, StyleHints, extra="allow"):
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
