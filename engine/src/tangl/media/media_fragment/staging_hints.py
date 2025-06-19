from typing import Literal, Optional
from pydantic import BaseModel

ShapeName = Literal['landscape', 'portrait', 'square', 'avatar', 'banner', 'bg']
PositionName = Literal['top', 'bottom', 'left', 'right', 'cover', 'inline']
SizeName = Literal['small', 'medium', 'large']
TransitionName = Literal['fade_in', 'fade_out', 'remove',
                         'from_right', 'from_left', 'from_top', 'from_bottom',
                         'to_right', 'to_left', 'to_top', 'to_bottom',
                         'update', 'scale', 'rotate']
DurationName = Literal['short', 'medium', 'long']
TimingName = Literal['start', 'stop', 'pause', 'restart', 'loop']

class StagingHints(BaseModel, extra="allow"):
    """
    Media StagingHints are similar to dialog StyleHint annotations -- they provide
    additional client-side suggestions for client staging, position, arrival, and
    departure transitions.
    """
    media_shape: Optional[ShapeName | float] = None  # aspect ratio
    media_size: Optional[SizeName | tuple[int, int] | tuple[float, float] | float] = None  # dims or scale
    media_position: Optional[PositionName | tuple[int, int] | tuple[float, float]] = None  # pixel or ndc coords
    media_transition: Optional[TransitionName] = None
    media_duration: Optional[DurationName | float] = None  # secs
    media_timing: Optional[TimingName] = None
