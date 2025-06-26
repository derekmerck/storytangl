from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

from pydantic import Field

from tangl.type_hints import UniqueLabel
from tangl.service.response import BaseResponse

class UserInfo(BaseResponse):
    fragment_type: Literal["user_info"] = Field("user_info", alias="type")
    user_id: UUID
    user_secret: str
    created_dt: datetime
    last_played_dt: Optional[datetime] = None
    worlds_played: set[UniqueLabel]
    stories_finished: int = 0
    turns_played: int = 0
    achievements: Optional[set[str]]

# todo: should probably just return a full user info object for consistency
import collections
UserSecret = collections.namedtuple("UserSecret", ["user_id", "user_secret"])
