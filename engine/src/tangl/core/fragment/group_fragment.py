from typing import Literal, Any, Optional, Collection
from uuid import UUID

from pydantic import Field

from tangl.core import GraphItem, Graph
from .content_fragment import ContentFragment

# This is basically a subgraph fragment
class GroupFragment(ContentFragment, GraphItem, extra='allow'):
    fragment_type: Literal['group'] = Field("group", alias='type')
    # client-friendly name for the collection type, dialog, character card, spellbook, etc.
    group_type: Optional[str] = None  # group's intended role in fragment stream, e.g., dialog, list, card, etc.
    content: list[UUID] = Field(...)

    @property
    def members(self) -> list[ContentFragment]:
        return [self.graph.get(uid) for uid in self.content]
