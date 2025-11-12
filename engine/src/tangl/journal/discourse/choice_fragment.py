from typing import Optional, Any, Literal

from pydantic import Field

from tangl.journal.content import ContentFragment, PresentationHints

class ChoiceFragment(ContentFragment, extra='allow'):
    fragment_type: Literal['choice'] = Field('choice')

    # For activatable fragments, is this fragment _currently_ active.
    #   None  -> not activatable (or field not present)
    #   True  -> activatable and enabled
    #   False -> activatable but disabled
    active: Optional[bool] = True
    # todo: could provide a reason it is inactive as well in message

    # Params to be included with the cb if the fragment is "activated", i.e., a choice, link, button, input, rollover hint, custom ui event trigger
    activation_payload: Optional[Any] = None
