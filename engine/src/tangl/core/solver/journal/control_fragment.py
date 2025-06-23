from typing import Literal

from pydantic import Field

from tangl.type_hints import Identifier
from .journal_fragment import JournalFragment

ControlFragmentType = Literal['update', 'delete']

class ControlFragment(JournalFragment, extra='allow'):
    fragment_type: ControlFragmentType = Field("update", alias='type')
    reference_type: Literal['content'] = Field("content", alias='ref_type')
    reference_id: Identifier = Field(..., alias='ref_id')
    # identifier (uid or unique label) for the content fragment we want to update content or presentation of
