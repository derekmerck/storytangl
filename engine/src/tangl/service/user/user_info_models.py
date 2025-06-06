import collections
from typing import Optional
from datetime import datetime
from uuid import UUID

from tangl.type_hints import UniqueLabel
from tangl.utils.response_models import BaseResponse

class UserInfo(BaseResponse):
    user_id: UUID
    user_secret: str
    created_dt: datetime
    last_played_dt: Optional[datetime] = None
    worlds_played: set[UniqueLabel]
    stories_finished: int = 0
    turns_played: int = 0
    achievements: Optional[set[str]]


UserSecret = collections.namedtuple("UserSecret", ["user_id", "user_secret"])
