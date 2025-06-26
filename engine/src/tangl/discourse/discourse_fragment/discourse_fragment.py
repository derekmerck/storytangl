# A frozen fragment of the collapsing graph projected onto 1-d journal-space

from typing import Optional, Any, Literal, Tuple, Union

from pydantic import Field, BaseModel, ConfigDict, model_validator
import yaml

import tangl.utils.setup_yaml
from tangl.type_hints import Identifier
from tangl.core.fragment import ControlFragment, GroupFragment, PresentationHints
from tangl.core.solver.journal import ContentFragment


class ChoiceFragment(ContentFragment, extra='allow'):
    fragment_type: Literal['choice'] = Field('choice', alias='type')
    # Indicate if fragment can be "activated", for choices, allow the choice to be selected, etc.
    activatable: Optional[bool] = False
    # For activatable fragments, is this fragment _currently_ active.
    active: Optional[bool] = True
    # Params to be included with the cb if the fragment is "activated", i.e., a choice, link, button, input, rollover hint, custom ui event trigger
    activation_payload: Optional[Any] = None


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
    fragment_type: Literal['dialog'] = Field('dialog', alias='type')
    content: list[AttributedFragment]


