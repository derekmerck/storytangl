from typing import Optional, Literal, Self
from datetime import datetime
from uuid import UUID

from pydantic import Field

from tangl.type_hints import UniqueLabel
from tangl.service.response import BaseResponse
from tangl.service.user import User

class UserInfo(BaseResponse):
    fragment_type: Literal["user_info"] = Field("user_info")
    user_id: UUID
    user_secret: str
    created_dt: datetime
    last_played_dt: Optional[datetime] = None
    worlds_played: set[UniqueLabel]
    stories_finished: int = 0
    turns_played: int = 0
    achievements: Optional[set[str]]

    @classmethod
    def from_user(cls, user: User, **kwargs) -> Self:
        ...

# todo: should probably just return a full user info object for consistency
import collections
UserSecret = collections.namedtuple("UserSecret", ["user_id", "user_secret"])
