# A frozen fragment of the collapsing graph projected onto 1-d journal-space

from typing import Optional, Any

from pydantic import Field, BaseModel, ConfigDict, model_validator
import yaml

import tangl.utils.setup_yaml
from tangl.type_hints import Identifier
from tangl.core.solver.journal import JournalFragment, ControlFragment
from .presentation_hints import PresentationHints

class DiscourseFragment(JournalFragment, extra='allow'):
    """
    A chunk of text content and metadata annotations.

    Presentation hint fields are optional and may not be respected by the client.
    """
    # base features
    presentation_hints: Optional[PresentationHints] = Field(None, alias='hints')

    # If not wrapped in a response, can be used with batches to assemble a response on client end
    # response_id: Optional[Identifier] = None
    # sequence: Optional[int] = None

class ActiveFragment(DiscourseFragment, extra='allow'):
    # Indicate if fragment can be "activated", for choices, allow the choice to be selected, etc.
    activatable: Optional[bool] = False
    # For activatable fragments, is this fragment _currently_ active.
    active: Optional[bool] = True
    # Params to be included with the cb if the fragment is "activated", i.e., a choice, link, button, input, rollover hint, custom ui event trigger
    activation_payload: Optional[Any] = None

# DialogBite is a group of annotated DialogFragments
