from __future__ import annotations
from typing import Optional, Any
import functools

from pydantic import BaseModel, Field, ConfigDict

from tangl.type_hints import StyleId, StyleClass, StyleDict

class PresentationHints(BaseModel, extra="allow"):
    """
    Presentation hints can include anything that the front-end and
    back-end can agree on.

    Presentation hints are _not_ guaranteed to be respected by a client,
    although `style_dict['color']` is usually pretty easy to implement

    These are some basic suggestions.

    - style_name (str): Optional suggested presentation-style label or html-entity #id
    - style_tags (list[str]): Optional list of tags or html-classes
    - style_dict (dict[str, Any]): Optional suggested html style params (color, etc.)
    - icon (str): Optional suggested icon (arrow, emoji, etc.)

    The tags field can be abused for free-form, fragment-type-specific tags like
    ["portrait", "from_right", "2.0s"] for an image.  Or, use the dedicated
    MediaPresentationHints model for type checking.
    """
    model_config = ConfigDict(frozen=True)

    style_name: Optional[StyleId] = None
    style_tags: Optional[list[StyleClass]] = Field(default_factory=list)
    style_dict: Optional[StyleDict] = Field(default_factory=dict)
    icon: Optional[str] = None

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('by_alias', True)
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(*args, **kwargs)

    # todo: should have an inference from tags like ["color=blue", ...] -> {'color': 'blue'}
