# tangl/service/controllers/user_controller.py
"""User controller exposing account-oriented endpoints."""

from __future__ import annotations
import base64
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, computed_field

from tangl.media import MediaDataType, MediaResourceInventoryTag as MediaRIT
from tangl.service.api_endpoint import AccessLevel, ApiEndpoint, HasApiEndpoints
from tangl.type_hints import Hash, Identifier

if TYPE_CHECKING:
    from tangl.service.user.user import User
    from tangl.service.response.info_response import UserInfo
else:  # pragma: no cover - runtime imports to avoid circulars
    class User:  # type: ignore[dead-code]
        ...

    class UserInfo:  # type: ignore[dead-code]
        ...


class ApiKeyInfo(BaseModel):
    """Encoded API key metadata returned after user updates."""

    secret: str

    @computed_field  # type: ignore[misc]
    @property
    def api_key(self) -> str:
        """Return the URL-safe base64 encoded secret."""

        raw = self.secret.encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8")


class UserController(HasApiEndpoints):
    """Operations that mutate or inspect :class:`~tangl.service.user.user.User`."""

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def create_user(self, **kwargs: Hash) -> User:
        """Instantiate a new user model from keyword arguments."""

        from tangl.service.user.user import User  # imported lazily to avoid cycles

        return User(**kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def update_user(self, user: User, **kwargs: Hash) -> ApiKeyInfo:
        """Update mutable user fields and surface the secret metadata."""

        user.update(**kwargs)
        return ApiKeyInfo(secret=user.secret)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def get_user_info(self, user: User, **kwargs: Hash) -> "UserInfo":
        """Build a :class:`UserInfo` snapshot from the provided user."""

        from tangl.service.response.info_response import UserInfo  # lazy import to avoid cycles

        return UserInfo.from_user(user, **kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def get_user_media(
        self,
        user: User,
        media: MediaRIT | Identifier,
        **kwargs: Hash,
    ) -> MediaDataType:
        """Resolve media for the user, dereferencing identifiers if necessary."""

        if isinstance(media, Identifier):
            media = user.find_one(alias=media)
        return media.get_content(**kwargs)

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def drop_user(self, user: User, **kwargs: Hash) -> tuple[UUID, ...]:
        """Unlink all stories from the user and return identifiers to purge."""

        story_ids = tuple(user.get_story_ids())
        for story_id in story_ids:
            user.unlink_story(story_id)
        return (user.uid, *story_ids)

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        group="system",
        response_type="info",
    )
    def get_key_for_secret(self, secret: str, **_: Hash) -> ApiKeyInfo:
        """Utility endpoint that encodes ``secret`` for API clients."""

        return ApiKeyInfo(secret=secret)


__all__ = ["ApiKeyInfo", "UserController"]
