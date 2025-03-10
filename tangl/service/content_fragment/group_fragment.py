
from typing import Literal, Any, Optional

from pydantic import Field

from .content_fragment import ContentFragment

class GroupFragment(ContentFragment, extra='allow'):
    fragment_type: Literal['group'] = Field("group", alias='type')
    # client-friendly name for the collection type, dialog, character card, spellbook, etc.
    group_type: Optional[str] = None
    content: Optional[Any] = None
    # expected group roles and metadata, avatar, text, idle animation, optional members, etc.
    group_roles: Optional[list] = Field(default_factory=list)
