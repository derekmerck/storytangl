from __future__ import annotations

import base64
from typing import TYPE_CHECKING
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, computed_field

from tangl.type_hints import Identifier, Hash
from tangl.service.api_endpoint import ApiEndpoint, AccessLevel, HasApiEndpoints
from tangl.media import MediaResourceInventoryTag as MediaRIT, MediaDataType
from .user import User
from .user_info import UserInfo

if TYPE_CHECKING:
    from tangl.story.story import Story
else:
    # Fallbacks for endpoint type hinting
    class Story: pass

class ApiKeyInfo(BaseModel):
    secret: str

    @computed_field()
    @property
    def api_key(self) -> str:
        return base64.urlsafe_b64encode(self.secret.encode('utf-8')).decode('utf-8')

class UserController(HasApiEndpoints):
    """
    client:
    - create new user (rw)
    - create new story from a world (rw) **currently in world controller
    - update user api key or current_story (rw)
    - get info about user (achievements, global story stats) (ro)
    - get media related to this user (avatar) (possibly rw if new media is generated?)
    - drop this user (rw)
    - drop a story (rw)

    Wrapping the methods with ApiEndpoint provides the ServiceManager
    class with hints for creating appropriate service-layer endpoints
    with context.
    """

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def create_user(self, **kwargs) -> User:
        return User(**kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def update_user(self, user: User, **kwargs) -> ApiKeyInfo:
        user.update(**kwargs)
        return ApiKeyInfo(secret=user.secret)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def get_user_info(self, user: User, **kwargs) -> UserInfo:
        return UserInfo.from_user(user, **kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def get_user_media(self, user: User, media: MediaRIT | Identifier, **kwargs) -> MediaDataType:
        if isinstance(media, Identifier):
            media = user.find_one(alias=media)
        return media.get_content(**kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def drop_user(self, user: User, **kwargs):
        # returns a list of uids to drop from service context
        story_ids = user.get_story_ids()
        for story_id in story_ids:
            user.unlink_story(story_id)
        return user.uid, *story_ids

    @ApiEndpoint.annotate(access_level=AccessLevel.USER, group="user")
    def drop_story(self, story: Story, **kwargs):
        # returns a list of uids to drop from service context, user is written back
        story.user.unlink_story(story)
        return (story.uid,)

    @ApiEndpoint.annotate(access_level=AccessLevel.PUBLIC, group="system", response_type="info")
    def get_key_for_secret(self, secret: str, **kwargs) -> ApiKeyInfo:
        return ApiKeyInfo(secret=secret)
