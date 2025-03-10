
from typing import Literal, Any, Optional

from pydantic import Field

from .content_fragment import ContentFragment

class UserEventFragment(ContentFragment, extra='allow'):
    # - ui indicator, like a user achievement notification
    # - ui trigger, like req a client-side save
    fragment_type: Literal["event"] = Field("event", alias='type')
    event_type: Optional[str] = None
