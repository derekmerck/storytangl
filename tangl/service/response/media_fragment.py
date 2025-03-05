from typing import Literal, Optional
from base64 import b64encode

from pydantic import Field, field_serializer

from tangl.type_hints import StringMap, UniqueLabel, Label, Identifier, Tag, Pathlike

from .base_fragment import BaseFragment, ContentUpdateFragment
from .presentation_hints import PresentationHints

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

class MediaPresentationHints(PresentationHints, extra="allow"):
    shape: Optional[ShapeName | float] = None  # aspect ratio
    size: Optional[SizeName | tuple[int, int] | tuple[float, float] | float] = None  # dims or scale
    position: Optional[PositionName | tuple[int, int] | tuple[float, float]] = None  # pixel or ndc coords
    transition: Optional[TransitionName] = None
    duration: Optional[DurationName | float] = None  # secs
    timing: Optional[TimingName] = None

MediaFragmentType = Literal['media', 'image', 'vo', 'music', 'sfx', 'anim', 'mov']
DataContentFormatType = Literal['url', 'data', 'xml', 'json']

class MediaFragment(BaseFragment, extra='allow'):
    fragment_type: MediaFragmentType = Field("media", alias='type')
    content: Pathlike | bytes
    content_format: DataContentFormatType = Field(..., alias='format')
    presentation_hints: Optional[MediaPresentationHints] = None

    @field_serializer("content")
    def _encode_data_content(self, content):
        if self.content_format is "data":
            return b64encode(content)
        return str(content)

class MediaUpdateFragment(ContentUpdateFragment, extra='allow'):
    presentation_hints: Optional[MediaPresentationHints] = None  # Only req if updating pres
