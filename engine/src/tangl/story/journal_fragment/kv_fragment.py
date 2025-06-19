from typing import Literal, Any
from collections import namedtuple

from pydantic import Field

from tangl.utils.ordered_tuple_dict import OrderedTupleDict
from .content_fragment import ContentFragment

# todo: OrderedTupleDict should be type OTDict[str, tuple[Primitive, PresentationHints]]
# todo: implement __get_pydantic_core_schema__ on OTDict so it will get represented properly in dto schema

class KvFragment(ContentFragment, extra='allow', arbitrary_types_allowed=True):
    # Used for info-responses that require ordered, hinted kv data (story info, world info, etc.)
    fragment_type: Literal["kv"] = "kv"
    content: list[OrderedTupleDict] = Field(...)

