from typing import Literal, Optional, Any, Tuple, Union, Annotated
from uuid import UUID, uuid4
import functools
from datetime import datetime

from pydantic import BaseModel, Field
import yaml

from tangl.info import __name__, __version__
from tangl.type_hints import StringMap, UniqueLabel, Label, Identifier, Tag
import tangl.utils.setup_yaml

minor_version = ".".join(__version__.split(".")[0:1])

RESPONSE_SCHEMA_VERSION = f"{__name__}-response-v{minor_version}"

class ResponseMetadata(BaseModel):
    response_id: Identifier = Field(default_factory=uuid4)
    version: str = Field(RESPONSE_SCHEMA_VERSION, init=False)
    timestamp: datetime = Field(default_factory=datetime.now, init=False)

class FragmentMetadata(BaseModel):
    fragment_id: Identifier = Field(default_factory=uuid4)
    response_id: Optional[Identifier] = None  # If not wrapped in a response
    sequence: int

ShapeName = Literal['landscape', 'portrait', 'square', 'avatar', 'banner', 'bg']
PositionName = Literal['top', 'bottom', 'left', 'right', 'cover', 'inline']
SizeName = Literal['small', 'medium', 'large']
TransitionName = Literal['fade_in', 'fade_out', 'remove',
                         'from_right', 'from_left', 'from_top', 'from_bottom',
                         'to_right', 'to_left', 'to_top', 'to_bottom',
                         'update', 'scale', 'rotate']
TimingName = Literal['start', 'stop', 'pause', 'restart', 'loop']
DurationName = Literal['short', 'medium', 'long']

PresentationTag = Union[ShapeName, PositionName, SizeName, TransitionName, TimingName, DurationName]

class PresentationHints(BaseModel, extra="allow"):
    """
    Presentation hints can include anything that the client and server can
    agree on.

    Presentation hints are _not_ guaranteed to be respected by a client,
    although `style_dict['color']` is usually pretty easy to implement

    These are some basic suggestions.

    - label (str): Optional suggested presentation-style label or html-entity #id
    - tags (list[str]): Optional list of tags or html-classes
    - icon (str): Optional suggested icon (arrow, emoji, etc.)
    - style_dict (dict[str, Any]): Optional suggested html style params (color, etc.)

    The tags or hints fields can be abused for free-form, fragment-type-specific
    tags like ["portrait", "from_right", "2.0s"] for an image.  Or, use the
    dedicated MediaPresentationHints model for type checking.
    """
    label: Optional[Label] = None
    tags: Optional[list[str | PresentationTag]] = Field(default_factory=list)
    icon: Optional[str] = None
    style_dict: Optional[StringMap] = Field(default_factory=dict)

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('by_alias', True)
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(*args, **kwargs)

class MediaPresentationHints(PresentationHints, extra="allow"):
    shape: Optional[ShapeName] = None
    size: Optional[SizeName | tuple[int, int] | tuple[float, float] | float] = None
    position: Optional[PositionName | tuple[int, int] | tuple[float, float]] = None
    transition: Optional[TransitionName] = None
    duration: Optional[DurationName | float] = None
    timing: Optional[TimingName] = None

KvFragmentType = Literal["kv"]
TextFragmentType = Literal['text', 'title', 'narrative', 'paragraph', 'dialog', 'choice']
MediaFragmentType = Literal['media', 'image', 'vo', 'music', 'sfx', 'anim', 'mov']
UpdateFragmentType = Literal['update', 'update_text', 'update_media', 'discard']
FragmentType = Union[KvFragmentType, TextFragmentType, MediaFragmentType, UpdateFragmentType]

DataContentFormatType = Literal['url', 'data', 'svg', 'json']
TextContentFormatType = Literal['plain', 'html', 'markdown']
ContentFormatType = Union[DataContentFormatType, TextContentFormatType]

class ResponseFragment(BaseModel, extra='allow'):
    """
    Represents a basic content element in any response and the core
    schema for communicating story-content and info-content to the front-end.

    Presentation hints need not be respected by the client.

    Attributes:
    - fragment_type: General type of fragment, i.e., text, media, kv
    - label (str): Optional name/key for the fragment
    - content (str): Optional value/text/media for the fragment
    - content_format: Instruction for how to parse content field, ie, markdown or encoded data
    - presentation_hints: Optional suggestions for icon, html styling, and staging for presentation
    """
    # base features
    fragment_id: UUID = Field(init=False, default_factory=uuid4)
    fragment_type: FragmentType = Field(..., alias='type')
    label: UniqueLabel = None
    content: Any
    content_format: Optional[ContentFormatType] = Field(None, alias='format')
    presentation_hints: Optional[PresentationHints] = None

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(*args, **kwargs)

    def __str__(self):
        data = self.model_dump()
        s = yaml.dump(data, default_flow_style=False)
        return s

class KvResponseFragment(ResponseFragment, extra='allow'):
    fragment_type: KvFragmentType = Field("kv", alias='type')
    label: str = Field(None, alias='key')
    content: Any = Field(..., alias='value')

class TextResponseFragment(ResponseFragment, extra='allow'):
    fragment_type: TextFragmentType = Field("text", alias='type')
    content: str
    content_format: TextContentFormatType = Field("plain", alias='format')

class MediaResponseFragment(ResponseFragment, extra='allow'):
    fragment_type: MediaFragmentType = Field("media", alias='type')
    content: str
    content_format: DataContentFormatType = Field(..., alias='format')
    presentation_hints: Optional[MediaPresentationHints] = None

class ResponseFragmentUpdate(ResponseFragment, extra='allow'):
    fragment_type: UpdateFragmentType = Field("update", alias='type')
    reference_id: Identifier = Field(..., alias='ref_id')
    # identifier (uid or label) for the fragment we want to update

class BaseResponse(BaseModel):
    schema_version: str = RESPONSE_SCHEMA_VERSION
    response_id: Identifier = Field(default_factory=uuid4)

class InfoResponse(BaseResponse):
    # Any info response is an ordered dict of (potentially styled) kv fragments interpreted as key/value pairs
    data: list[KvResponseFragment]

AnyFragment = Annotated[
    Union[KvResponseFragment, TextResponseFragment, MediaResponseFragment, ResponseFragmentUpdate],
    Field(discriminator='type')
]

class ContentResponse(BaseResponse):
    data: list[AnyFragment]  # This will automatically cast to proper model
