from typing import Literal, Any
from collections import namedtuple

from pydantic import Field

from tangl.utils.ordered_tuple_dict import OrderedTupleDict
from .content_fragment import ContentFragment
from .presentation_hints import PresentationHints

# todo: OrderedTupleDict should be type OTDict[str, tuple[Primitive, PresentationHints]]
# todo: implement __get_pydantic_core_schema__ on OTDict so it will get represented properly in dto schema

# This is maybe a service layer construct?

class KvFragment(ContentFragment, extra='allow', arbitrary_types_allowed=True):
    """
    Used for info-responses that require ordered, hinted kv data (story info, world info, etc.)

    Content in a KvFragment is a single key value pair along with styling information.
    Kv fragments almost always come in KvList groups, which can be interpreted as an
    ordered, styled dictionary.
    """
    fragment_type: Literal["kv"] = Field("kv", alias="type")
    content: OrderedTupleDict = Field(...)

    # todo: converter from list of annotated items to otd

