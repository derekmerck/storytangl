from typing import Literal

from pydantic import Field

from tangl.type_hints import Identifier
from tangl.core import GraphItem, Graph
from .content_fragment import ContentFragment

ControlFragmentType = Literal['update', 'delete']

class ControlFragment(ContentFragment, GraphItem, extra='allow'):
    # a graph item fragment
    fragment_type: ControlFragmentType = Field("update", alias='type')
    reference_type: Literal['content'] = Field("content", alias='ref_type')
    reference_id: Identifier = Field(..., alias='ref_id')
    # identifier (uid or unique label) for the content fragment that we want to update content or presentation for

    @property
    def reference(self) -> ContentFragment:
        return self.graph.get(self.reference_id)
