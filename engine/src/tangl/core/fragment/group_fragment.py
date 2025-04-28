from typing import Literal, Any, Optional, Collection

from pydantic import Field

from .content_fragment import ContentFragment

class GroupFragment(ContentFragment, extra='allow'):
    fragment_type: Literal['group'] = Field("group", alias='type')
    # client-friendly name for the collection type, dialog, character card, spellbook, etc.
    group_type: Optional[str] = None
    content: list[ContentFragment] = Field(...)
