from typing import Literal, Any, Optional, Collection

from pydantic import Field

from .base_fragment import BaseFragment

class GroupFragment(BaseFragment, extra='allow'):
    fragment_type: Literal['group'] = Field("group", alias='type')
    # client-friendly name for the collection type, dialog, character card, spellbook, etc.
    group_type: Optional[str] = None  # group's intended role in journal, e.g., dialog, list, card, etc.
    content: list[BaseFragment] = Field(...)
