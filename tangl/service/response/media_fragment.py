from typing import Literal, Optional

from pydantic import Field

from tangl.type_hints import StringMap, UniqueLabel, Label, Identifier, Tag

from .base_fragment import ResponseFragment, ResponseFragmentUpdate
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
DataContentFormatType = Literal['url', 'data', 'svg', 'json']

class MediaResponseFragment(ResponseFragment, extra='allow'):
    fragment_type: MediaFragmentType = Field("media", alias='type')
    content: str
    content_format: DataContentFormatType = Field(..., alias='format')
    presentation_hints: Optional[MediaPresentationHints] = None

class MediaResponseFragmentUpdate(ResponseFragmentUpdate, extra='allow'):
    presentation_hints: Optional[MediaPresentationHints] = None  # Only req if updating pres
