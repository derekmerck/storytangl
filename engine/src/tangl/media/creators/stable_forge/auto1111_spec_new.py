from __future__ import annotations
from typing import Optional

from PIL import Image

from tangl.core import ResourceInventoryTag as MediaRIT, HandlerRegistry, Renderable
from ...media_spec import MediaSpec

class Auto1111ScriptItem(BaseScriptItem, extra="allow"):
    ...

class StableStage:
    model: str
    seed: int
    sampler: str
    iterations: int
    control_nets: list  # settings, ref ims
    ip_adapter: None    # settings, ref ims

class Auto1111Spec(MediaSpec):

    prompt: str
    n_prompt: str
    stages: list[StableStage]
    ref_ims: list[MediaRIT]

adapter_handlers = HandlerRegistry(label="auto1111_adapters")

@adapter_handlers.register(caller_cls=Auto1111Spec)
def render_prompts(spec: Auto1111Spec, **context) -> Optional[Auto1111Spec]:

    prompt = Renderable.render_str(spec.prompt, **context)
    n_prompt = Renderable.render_str(spec.n_prompt, **context)

    if prompt != spec.prompt or n_prompt != spec.n_prompt:
        return spec.model_copy(update={'prompt': prompt, 'n_prompt': n_prompt})


