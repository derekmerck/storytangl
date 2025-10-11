from typing import Literal

from pydantic import Field

from tangl.core.entity.fragment import GroupFragment
from tangl.core.solver.journal import ContentFragment


class AttributedFragment(ContentFragment, extra='allow'):
    """
    A chunk of text content and metadata annotations.

    Presentation hint fields are optional and may not be respected by the client.
    """
    fragment_type: Literal['attributed'] = Field('attributed', alias='type')
    who: str     # reference voice
    how: str     # manner
    media: str   # avatar or vox media


class DialogFragment(GroupFragment, extra='allow'):
    fragment_type: Literal['dialog'] = Field('dialog')
    content: list[AttributedFragment]
