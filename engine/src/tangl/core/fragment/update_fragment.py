from typing import Literal

from pydantic import Field

from tangl.type_hints import Identifier
from .content_fragment import ContentFragment

UpdateFragmentType = Literal['update', 'delete']

class UpdateFragment(ContentFragment, extra='allow'):
    fragment_type: UpdateFragmentType = Field("update", alias='type')
    reference_type: Literal['content'] = "content"
    reference_id: Identifier = Field(..., alias='ref_id')
    # identifier (uid or unique label) for the content fragment we want to update content or presentation of
