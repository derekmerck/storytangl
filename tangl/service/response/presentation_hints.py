from __future__ import annotations
from typing import Optional, Any
import functools

from pydantic import BaseModel, Field

from tangl.type_hints import Label, Tag, StyleId, StyleClass, StyleDict

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
    label: Optional[Label | StyleId] = None
    tags: Optional[list[Tag | StyleClass]] = Field(default_factory=list)
    icon: Optional[str] = None
    style_dict: Optional[StyleDict] = Field(default_factory=dict)

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('by_alias', True)
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(*args, **kwargs)
