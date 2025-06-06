from pydantic import BaseModel, Field

from tangl.media import MediaResourceInventoryTag as MediaRIT
from ...media_spec import MediaSpec

class StableSpec(MediaSpec):
    prompt: str = None
    n_prompt: str = None
    model: str = None
    seed: int = None
    sampler: str = None
    iterations: int = None
    dims: tuple[int, int] = None
    ref_ims: MediaRIT | dict[str, MediaRIT] | list[MediaRIT] = None

    @classmethod
    def get_creator_service(cls):
        from .stable_forge import StableForge
        return StableForge()
