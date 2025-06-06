from __future__ import annotations
from typing import Optional

from pydantic import Field
from PIL import Image

from tangl.type_hints import StringMap
from tangl.core.handler import HandlerRegistry, HandlerPriority as Priority
from tangl.core.solver.journal import Renderable
from tangl.media import MediaResourceInventoryTag as MediaRIT

from tangl.media.media_spec import on_adapt_media_spec
from .stable_spec import StableSpec


class Auto1111Spec(StableSpec):

    control_nets: list  # settings, ref ims
    ip_adapter: None    # settings, ref ims

    @on_adapt_media_spec.register(priority=Priority.EARLY)
    def render_prompts(self, ctx: StringMap):
        self.prompt = Renderable.render_str(self.prompt, **ctx)
        self.n_prompt = Renderable.render_str(self.n_prompt, **ctx)

    i2i_ref: MediaRIT = None
    i2i_blur: float = 0.5
