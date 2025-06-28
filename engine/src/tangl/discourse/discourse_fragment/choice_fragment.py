from typing import Optional, Any, Literal, Tuple, Union

from pydantic import Field, BaseModel, ConfigDict, model_validator

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
