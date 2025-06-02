from typing import Optional

from tangl.type_hints import Primitive
from .base_response_model import BaseResponse
from .style_hints_model import StyleHints

# KV with style properties

class KvItem(StyleHints, BaseResponse):
    """
    Kv-items have no uid and key/value rather than text.  Kv-items
    can carry style hints.

    Key is optional, so it can also be used as a styled list.
    """
    key: Optional[str] = None
    value: Primitive | list[Primitive]
    icon: str = None

KvList = list[KvItem]
