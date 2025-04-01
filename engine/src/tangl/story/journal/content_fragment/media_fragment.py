from typing import Literal, Optional
from base64 import b64encode

from pydantic import Field, field_serializer, BaseModel

from tangl.type_hints import Pathlike
from tangl.media import MediaRecord
from .content_fragment import ContentFragment, UpdateFragment

# Media Presentation Hints
ShapeName = Literal['landscape', 'portrait', 'square', 'avatar', 'banner', 'bg']
PositionName = Literal['top', 'bottom', 'left', 'right', 'cover', 'inline']
SizeName = Literal['small', 'medium', 'large']
TransitionName = Literal['fade_in', 'fade_out', 'remove',
                         'from_right', 'from_left', 'from_top', 'from_bottom',
                         'to_right', 'to_left', 'to_top', 'to_bottom',
                         'update', 'scale', 'rotate']
DurationName = Literal['short', 'medium', 'long']
TimingName = Literal['start', 'stop', 'pause', 'restart', 'loop']

class MediaPresentationHints(BaseModel, extra="allow"):
    media_shape: Optional[ShapeName | float] = None  # aspect ratio
    media_size: Optional[SizeName | tuple[int, int] | tuple[float, float] | float] = None  # dims or scale
    media_position: Optional[PositionName | tuple[int, int] | tuple[float, float]] = None  # pixel or ndc coords
    media_transition: Optional[TransitionName] = None
    media_duration: Optional[DurationName | float] = None  # secs
    media_timing: Optional[TimingName] = None

MediaFragmentType = Literal['media', 'image', 'vo', 'music', 'sfx', 'anim', 'mov']
DataContentFormatType = Literal['url', 'data', 'xml', 'json']

class MediaFragment(ContentFragment, extra='allow'):
    fragment_type: MediaFragmentType = Field("media", alias='type')
    content: Pathlike | bytes
    content_format: DataContentFormatType = Field(..., alias='format')
    media_hints: Optional[MediaPresentationHints] = None

    @field_serializer("content")
    def _encode_data_content(self, content):
        if self.content_format == "data":
            return b64encode(content)
        return str(content)

    @classmethod
    def from_media_record(cls, media_record: MediaRecord, **kwargs) -> 'MediaFragment':
        ...

class MediaUpdateFragment(MediaFragment, UpdateFragment, extra='allow'):
    fragment_type: Literal['media_update'] = Field("media_update", alias='type')
    reference_type: MediaFragmentType = "media"
