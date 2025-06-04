from __future__ import annotations
import abc
from typing import Self

from pydantic import Field, model_validator, BaseModel

# from tangl.media.protocols import MediaForgeProtocol
# from tangl.media.media_spec import MediaSpecification
# from tangl.script.script_models import BaseScriptItem
# from tangl.utils.response_models import StyleHints
from tangl.type_hints import StyleDict, UniqueLabel
# from tangl.core import Node, PresentationHints
# from ...media_spec import MediaSpec
from .svg_source_manager import SvgSourceManager
from .svg_group import SvgGroup
from .svg_transform import SvgTransform

from tangl.media.media_spec import MediaSpec
from tangl.media.media_fragment import PresentationHints

class VectorScriptItem(BaseModel, extra="allow", arbitrary_types_allowed=True):
    """
    This could be marked in two ways, as a direct call to named groups,
    or as an indirect call to build up appropriate groups from a reference
    node.

    ```yaml
    media:
      - obj_cls: SvgSpec
        label: scene1/block1
        shapes: xxx
        style_dict: { override_style_info: foo }
        style_cls: override_style_cls.dark_bg

    vector:
      ref: my_actor / my_role
      # override kwargs
      outfit: override_outfit_name
      attitude: override_expr
    ```
    """
    label: UniqueLabel = None
    ref: UniqueLabel = None

    style_hints: PresentationHints = None

    @model_validator(mode='after')
    def _check_exactly_one(self):
        if not any([self.label, self.ref]) or all([self.label, self.ref]):
            raise ValueError("Exactly one of `label` or `ref` must be provided")
        return self


class VectorSpec(MediaSpec, arbitrary_types_allowed=True):

    #: registry of shapes and styles
    source_manager: SvgSourceManager = None

    transform: SvgTransform = Field(default_factory=list)   # transform for the entire scene
    shapes: list[ SvgGroup ] = Field(default_factory=list)  # each group can have its own transform
    styles: dict[ str, str ] = Field(default_factory=dict)

    # may be relevant to track the labels of the shape and style collections loaded to create this??

    @classmethod
    def get_creation_service(cls) -> Self:
        from .vector_forge import VectorForge
        return VectorForge(source_manager=cls.source_manager)
