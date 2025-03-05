from typing import Literal, Any

from pydantic import Field

from .base_fragment import BaseFragment

KvFragmentType = Literal["kv"]

class KvFragment(BaseFragment, extra='allow'):
    fragment_type: KvFragmentType = Field("kv", alias='type')
    label: str = Field(None, alias='key')
    content: Any = Field(..., alias='value')
