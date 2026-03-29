from __future__ import annotations
from typing import Self
from io import TextIOWrapper

from PIL import Image
from pydantic import Field

from tangl.media.media_spec import MediaSpecification
from .comfy_api import ComfyWorkflow


class ComfySpec(MediaSpecification, arbitrary_types_allowed = True):
    # implements media spec

    workflow: ComfyWorkflow | dict   # loaded from template
    ims: dict[str, Image] = Field(default_factory=list)

    # model: str = Field(alias="sd_model_name", default=None)
    # sampler: str = Field(alias="sampler_name", default=None)
    # steps: Optional[int] = None
    # dims: tuple[int, int] = None
    # seed: int = None
    # # batch_size: int = 1
    # # clip_skip: int = 2
    # cfg_scale: float = 4.5

    @classmethod
    def from_json(cls, data: str | TextIOWrapper):
        workflow = ComfyWorkflow.from_json(data)
        return cls(workflow=workflow)

    def to_request(self) -> dict:
        """Returns a dict suitable for sending to a Comfy API endpoint as json"""
        return self.workflow.spec

    @classmethod
    def get_forge(cls) -> Self:
        from .stableforge import StableForge
        return StableForge.get_instance()
