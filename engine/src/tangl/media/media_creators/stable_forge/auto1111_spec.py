from __future__ import annotations

from pydantic import Field

from tangl.media import MediaResourceInventoryTag as MediaRIT, MediaSpec
from .stable_spec import StableSpec


class Auto1111Spec(StableSpec):

    control_nets: list = Field(default_factory=list)  # settings, ref ims
    ip_adapter: dict = Field(default_factory=dict)    # settings, ref ims

    image_ref: MediaRIT = None
    image_rescale: float = 0.5
    image_blur: float = 0.5


class Auto1111MultiSpec(MediaSpec):

    phases: list[Auto1111Spec] = Field(default_factory=list)
