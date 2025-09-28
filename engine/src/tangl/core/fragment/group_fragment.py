# tangl.core.fragment.group_fragment.py
from typing import Literal, Any, Optional, Collection
from uuid import UUID

from pydantic import Field

from tangl.core.registry import Registry
from tangl.core.record import Record

# This is basically a subgraph fragment
class GroupFragment(Record, extra='allow'):
    record_type: Literal['group_fragment'] = Field("group_fragment", alias='type')
    # client-friendly name for the collection type, dialog, character card, spellbook, etc.
    group_type: Optional[str] = None  # group's intended role in fragment stream, e.g., dialog, list, card, etc.
    member_ids: list[UUID] = Field(default_factory=list)

    def members(self, registry: Registry[Record]) -> list[Record]:
        return [registry.get(uid) for uid in self.content]

    # todo: probably want a member map too, with role assignments by group type
