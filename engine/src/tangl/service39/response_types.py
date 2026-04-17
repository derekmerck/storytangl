import base64
from typing import Literal, Any, Optional, TypeAlias, Self
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, field_serializer

from tangl.type_hints import Identifier
from .job_type import JobType

##############################
# RESPONSES
##############################

ResponseType: TypeAlias = Literal["info", "runtime", "content", "media"]

class Response(BaseModel):
    # discriminated union key for automatic typed-response generation
    response_type: ResponseType

##############################
# CONTENT RESPONSES
##############################

ContentFormat: TypeAlias = Literal["native", "json", "xml", "md"]

class ContentResponse(Response):
    content: Any
    content_format: ContentFormat
    response_type: Literal["content"] = "content"

MediaFormat: TypeAlias = Literal["native", "b64", "xml", "url", "path"]
MediaType: TypeAlias = Literal["png", "svg", "mp3", "mp4"]

class InlineMedia(BaseModel):
    media: Any
    media_format: MediaFormat
    media_type: MediaType

    @field_serializer("media")
    @classmethod
    def _flatten_media(cls, media: Any) -> str:
        if isinstance(media, bytes):
            # an inline raster image
            return base64.b64encode(media).decode("utf-8")
        elif isinstance(media, str):
            # path or already json/xml
            return media
        raise TypeError(f"Unsupported media type {type(media)}")

class MediaResponse(Response, InlineMedia):
    response_type: Literal["media"] = "media"


##############################
# RUNTIME RESPONSES
##############################

class RuntimeStatus(Enum):
    OK = "ok"
    NOT_OK = "not_ok"


class RuntimeResponse(Response):
    response_type: Literal["runtime"] = "runtime"
    job: str
    job_type: JobType
    status: RuntimeStatus
    result: Optional[Any] = None
    error: Optional[Any] = None

    @classmethod
    def Ok(cls, job_type: JobType, job: str, result: Any = None) -> Self:
        return cls(
            status = RuntimeStatus.OK,
            job = job,
            job_type = job_type,
            result = result
        )

    @classmethod
    def Nok(cls, job_type: JobType, job: str, error: Any) -> Self:
        return cls(
            status = RuntimeStatus.NOT_OK,
            job = job,
            job_type = job_type,
            error = error
        )

##############################
# INFO RESPONSES
##############################

InfoType: TypeAlias = Literal["user", "story", "world", "system"]

class InfoResponse(Response):
    response_type: Literal["info"] = "info"
    info_type: InfoType
    entity_id: int

class InlineAchievement(BaseModel):
    # These are references to system-level token catalogs defined by loaded worlds
    world_id: str
    achievement_id: str
    world_name: str
    achievement_name: str
    achievement_media: InlineMedia

class UserAchievement(InlineAchievement):
    when: datetime

class UserInfoResponse(InfoResponse):
    info_type: Literal["user"] = "user"

    # metadata
    name: str
    creation_time: datetime
    last_seen: datetime

    current_story: str  # user.current_story.world.get_title()
    current_story_turn: int

    total_num_stories: int
    total_num_turns: int
    # By world id
    achievements: dict[Identifier, list[UserAchievement]]

class StoryInfoResponse(InfoResponse):
    info_type: Literal["story"] = "story"
    # This is determined by world, but has some basic formatting cues

class WorldInfoResponse(InfoResponse):
    info_type: Literal["world"] = "world"

    # metadata
    world_id: str
    version: str
    title: str
    author: str
    genre: str
    desc: str
    copyright: str
    info_media: InlineMedia

    # computed from bundle
    node_count: int
    complexity: int
    media_types: list[MediaType]

    # derived from usage patterns
    num_world_users: int
    num_world_stories: int
    num_world_completed_stories: int
    total_num_world_turns: int
    user_discovered_world_achievements: list[InlineAchievement]  # with earliest and count of each

    earliest_story: datetime
    latest_story: datetime

class SystemInfoResponse(InfoResponse):
    info_type: Literal["system"] = "system"

    engine: str
    version: str
    api_url: str
    doc_url: str
    info_media: InlineMedia

    # computed from bundles
    num_worlds: int
    world_ids: list[str]   # call world/get_info(world_id) for details on each
    default_world: str     # default for new user

    # derived from usage patterns
    num_users: int
    num_stories: int
    num_completed_stories: int
    total_num_turns: int
    all_user_discovered_achievements: list[InlineAchievement]  # with earliest and count of each

    earliest_story: datetime
    latest_story: datetime


