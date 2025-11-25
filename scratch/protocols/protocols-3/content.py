from typing import Callable, Any, Literal
from pathlib import Path

from PIL.Image import Image
from pydantic import AnyUrl, BaseModel

from tangl.type_hints import StringMap
from .entity import DataSingleton, Tags, EntityMixin, Registry, TaskHandler

# ---------------
# Media type hints
# ---------------
VectorImage = str  # svg/xml
Audio = bin
MediaData = Audio | Image | VectorImage


# ---------------
# Media Fragment
# ---------------
class MediaFragment(BaseModel):
    media_type: Literal["audio", "image", "video", "animation"]
    media_role: Literal["narrative", "portrait", "avatar", "vo", "effect"]
    data: MediaData = None
    url: AnyUrl = None


# ------------------
# Media Content
# ------------------
MediaContentSpec = StringMap  # generation spec, path, or tag criteria

class HasMedia(EntityMixin):
    media_specs: list[MediaContentSpec]

RIT = DataSingleton
# media resource inventory tag, converted to MediaInfo by ServiceResponseHandler
FilePathTaggingStrategy = Callable[[str], Tags]

class MediaResourceRegistry(Registry[RIT]):

    def add_file_source(self, path: Path, recurse: bool = True, tagging_strategy: FilePathTaggingStrategy = None): ...
    # creates tagged rits for each object on path

class MediaHandler(TaskHandler):
    # multiple dispatch for various media aspects

    def render_media(self, **kwargs) -> MediaData: ...
    def realize_spec(self, spec: MediaContentSpec, **kwargs: Any) -> RIT: ...
    # find in registry or call render

ImageContentSpec = MediaContentSpec

class ImageHandler(MediaHandler):
    # files, svg/png assembly, gen ai

    def render_media(self, **kwargs) -> Image | VectorImage: ...
    def realize_spec(self, spec: ImageContentSpec, **kwargs: Any) -> RIT: ...

AudioContentSpec = StringMap

class AudioHandler(MediaHandler):
    # files, gen ai

    def render_media(self, **kwargs) -> Audio: ...
    def realize_spec(self, spec: AudioContentSpec, **kwargs: Any) -> RIT: ...

ContentStagingSpec = StringMap  # dialog timing for vox, transitions for media
StagingHints = StringMap        # journal fragment additions with media, timing, and transitions

class StagingHandler(MediaHandler):
    # todo: I'm not sure what this should actually look like

    def render_staging(self, **kwargs) -> StagingHints: ...
    def realize_spec(self, spec: ContentStagingSpec, **kwargs) -> StagingHints: ...

# ------------------
# Narrative Content
# ------------------
NarrativeContentSpec = StringMap
# convert a section of marked up dialog to multiple segments assigned to different roles

class NarrativeVoiceHandler(TaskHandler):
    # This is a wrapper for parsing and re-writing textual narrative and dialog based on the current story state

    def render_narrative(self, **kwargs) -> str: ...
    def realize_spec(self, spec: NarrativeContentSpec, **kwargs: Any) -> StringMap: ...


# ---------------
# Narrative Fragment
# ---------------
class StyledContent(BaseModel):
    style_id: str = None
    style_cls: set[str] = None
    style_hints: dict[str, str] = None

class NarrativeFragment(StyledContent):
    text: str = None
    media: list[MediaFragment] = None

class DialogFragment(NarrativeFragment):
    speaker_name: str = None
    speaker_attitude: str = None
    speaker_avatar: str = MediaFragment
