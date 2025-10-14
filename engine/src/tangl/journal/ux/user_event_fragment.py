from typing import Optional, Literal

from pydantic import Field

from tangl.core import BaseFragment

class UserEventFragment(BaseFragment, extra='allow'):
    # - ui indicator, like a user achievement notification
    # - ui trigger, like req a client-side save
    fragment_type: Literal["user_event"] = Field("user_event")
    event_type: Optional[str] = None
