from typing import Optional, Literal

from tangl.journal.content import ContentFragment

from pydantic import Field

from .choice_fragment import ChoiceFragment

class BlockFragment(ContentFragment):
    fragment_type: Literal['block'] = Field('block')
    choices: Optional[list[ChoiceFragment]] = Field(default_factory=list)
