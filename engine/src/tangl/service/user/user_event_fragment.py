from typing import Optional, Literal

from pydantic import Field

from tangl.core.fragment import BaseFragment

class UserEventFragment(BaseFragment, extra='allow'):
    # - ui indicator, like a user achievement notification
    # - ui trigger, like req a client-side save
    fragment_type: Literal["user_event"] = Field("user_event", alias='type')
    event_type: Optional[str] = None
