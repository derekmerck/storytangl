from typing import Literal, Any

from pydantic import Field

from .base_fragment import ResponseFragment

KvFragmentType = Literal["kv"]

class KvResponseFragment(ResponseFragment, extra='allow'):
    fragment_type: KvFragmentType = Field("kv", alias='type')
    label: str = Field(None, alias='key')
    content: Any = Field(..., alias='value')
