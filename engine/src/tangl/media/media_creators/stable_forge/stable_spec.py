from tangl.type_hints import StringMap
from tangl.core import Priority
from tangl.media import MediaResourceInventoryTag as MediaRIT, MediaSpec, on_adapt_media_spec


def _render_str(template: str | None, ctx: StringMap | None) -> str | None:
    if template is None or not ctx:
        return template
    try:
        return template.format(**ctx)
    except Exception:
        return template

class StableSpec(MediaSpec):
    # txt2im
    prompt: str = None
    n_prompt: str = None

    # im2im
    ref_image: MediaRIT = None
    ref_image_rescale: float = None
    ref_image_blur: float = None

    # sampler
    model: str = None
    seed: int = None
    sampler: str = None
    iterations: int = None
    dims: tuple[int, int] = None

    @classmethod
    def get_creator_service(cls):
        from .stable_forge import StableForge
        return StableForge()

    @on_adapt_media_spec.register(priority=Priority.EARLY)
    def render_prompts(self, ctx: StringMap):
        self.prompt = _render_str(self.prompt, ctx)
        self.n_prompt = _render_str(self.n_prompt, ctx)
