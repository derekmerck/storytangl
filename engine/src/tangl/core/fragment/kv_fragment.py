from typing import Literal, Any

from pydantic import Field

from .content_fragment import ContentFragment
from .group_fragment import GroupFragment

class KvFragment(ContentFragment, extra='allow'):
    fragment_type: Literal["kv"] = Field("kv", alias='type')
    label: str = Field(None, alias='key')
    content: Any = Field(..., alias='value')

class KvGroup(GroupFragment, extra='allow'):
    content: list[KvFragment] = []
