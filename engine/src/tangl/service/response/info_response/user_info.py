"""Native user metadata response."""

from __future__ import annotations

from collections import namedtuple
from datetime import datetime
from typing import Optional, Self
from uuid import UUID

from tangl.service.response.native_response import InfoModel
from tangl.service.user import User
from tangl.type_hints import UniqueLabel


class UserInfo(InfoModel):
    user_id: UUID
    user_secret: str
    created_dt: datetime
    last_played_dt: Optional[datetime] = None
    worlds_played: set[UniqueLabel]
    stories_finished: int = 0
    turns_played: int = 0
    achievements: Optional[set[str]] = None

    @classmethod
    def from_user(cls, user: User, **kwargs: object) -> Self:
        return cls(
            user_id=user.uid,
            user_secret=getattr(user, "secret", ""),
            created_dt=user.created_dt,
            last_played_dt=user.last_played_dt,
            worlds_played=set(getattr(user, "worlds_played", set())),
            stories_finished=getattr(user, "stories_finished", 0),
            turns_played=getattr(user, "turns_played", 0),
            achievements=set(getattr(user, "achievements", set())) or None,
            **kwargs,
        )


UserSecret = namedtuple("UserSecret", ["api_key", "user_secret"])
