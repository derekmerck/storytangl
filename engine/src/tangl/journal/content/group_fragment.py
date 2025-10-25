# tangl.core.fragment.group_fragment.py
from typing import Literal, Any, Optional, Collection
from uuid import UUID
from enum import Enum

from pydantic import Field

from tangl.core.registry import Registry
from tangl.core.record import BaseFragment

# This is basically a subgraph fragment
class GroupFragment(BaseFragment, extra='allow'):
    fragment_type: Literal['group'] = 'group'
    group_type: Optional[str | Enum] = None
    # collection's intended role in fragment stream, e.g., dialog, list, card, etc.
    member_ids: list[UUID] = Field(default_factory=list)

    def members(self, registry: Registry[BaseFragment]) -> list[BaseFragment]:
        return [registry.get(uid) for uid in self.content]

    # todo: probably want a member map too, with role assignments by group type
