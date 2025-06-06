from __future__ import annotations
import logging
import re
from typing import Optional, ClassVar, Self

from PIL.Image import Image
from pydantic import BaseModel, Field, field_validator, model_validator
import yaml
import webuiapi

from tangl.compilers.story_script import BaseScriptItem
from tangl.core.entity import Node
from tangl.media import MediaResourceInventoryTag as MediaRIT
from .forge_utils import basic_info, dims_given_max, DEFAULT_MAX_DIM
from .stable_spec import StableSpec

logger = logging.getLogger(__name__)

re_spaces = re.compile(r" +")

class Auto1111Spec(StableSpec):

    restore_faces: bool = False

    class HighResFix(BaseModel):
        scale: float = Field(alias="hr_scale", default=1.5)
        upscaler: str = Field(alias="hr_upscaler", default=None)
        sampler: str = Field(alias="hr_sampler", default=None)
        # "hr_prompt": ""
        # "hr_negative_prompt": ""
        # "hr_checkpoint_name": "string"

    hr_fix: HighResFix = Field(default_factory=HighResFix)

    class Img2ImgSpec(BaseModel, arbitrary_types_allowed=True):
        img_src: Image | MediaRIT

        @field_validator('img_src')
        @classmethod
        def _convert_rit(cls, value):
            if isinstance(value, MediaRIT):
                return value.image
            return value

        denoise: float = Field(alias="denoising_strength", default=None)
        resize_mode: int = 1  # 0 = just resize, 1 = crop and resize

        @model_validator(mode='before')
        @classmethod
        def _alias_denoise(cls, data):
            if 'denoise' in data:
                data['denoising_strength'] = data.pop('denoise')
            return data

        # class Config:
        #     arbitrary_types_allowed = True

        def new_dims(self, max_dim=DEFAULT_MAX_DIM):
            return dims_given_max(self.img_src, max_dim)

    img2img: Img2ImgSpec = None

    class CtrlNetSpec(BaseModel, arbitrary_types_allowed = True):
        img_src: Optional[Image | ImageFileRIT] = None

        @field_validator('img_src')
        @classmethod
        def _convert_rit(cls, value):
            if isinstance(value, ImageFileRIT):
                return value.image
            return value

        preprocessor: str = Field("canny", alias='module')

        @model_validator(mode='before')
        @classmethod
        def _alias_preprocessor(cls, data):
            if 'preprocessor' in data:
                data['module'] = data.pop('preprocessor')
            return data

        model: str = "control_v11p_sd15_canny [d14c016b]"
        # dims: tuple[int, int] = None
        weight: float = 1.0

        # class Config:
        #     arbitrary_types_allowed = True

        def new_dims(self, max_dim=DEFAULT_MAX_DIM):
            return dims_given_max(self.img_src, max_dim)

    ctrlnet: list[CtrlNetSpec] = None

    def __init__(self, *args, width=None, height=None, **kwargs):
        if width and height:
            kwargs['dims'] = (width, height)
        super().__init__(*args, **kwargs)
        if not self.initial_digest:
            self.initial_digest = self.digest()

    # metadata for info
    actors: set[str] = Field(default_factory=set)
    nsfw: bool = Field(default=False)
    initial_digest: Optional[bytes] = Field(exclude=True, default=None)

    locals: dict = None
    # vars that need to be included in template string renders

    def _render_prompts(self, ref: Node = None, world: 'World' = None, **kwargs):
        if ref and hasattr(ref, 'look'):
            from .adapters import CharacterLook
            look = CharacterLook.from_look(ref.look)
            logger.debug("ref look ----->")
            logger.debug( ref.look )
            logger.debug("look ------>")
            logger.debug( look )
            kwargs = kwargs | look.dict()

        if world and hasattr('world', 'art_style_desc'):
            kwargs['art_style_desc'] = world.art_style_desc()
        else:
            kwargs['art_style_desc'] = "perfect anime masterpiece"

        if self.locals:
            from copy import deepcopy
            from tangl.utils.deep_merge import deep_merge
            vars = deepcopy( self.locals )
            deep_merge( vars, kwargs )
        else:
            vars = kwargs

        if self.prompt and self.prompt.find( r"{{" ) >= 0:
            s = self.prompt
            # vars = self.locals | kwargs
            s = RenderHandler.render_str(s, vars)
            s = re_spaces.sub(" ", s)
            self.prompt = s
        if self.n_prompt and self.n_prompt.find( r"{{" ) >= 0:
            s = self.n_prompt
            # vars = self.locals | kwargs
            s = RenderHandler.render_str(s, vars)
            s = re_spaces.sub(" ", s)
            self.n_prompt = s

    def realize(self, ref: Node = None, **overrides) -> Self:
        res = super().realize(**overrides)  # type=Self
        res._render_prompts(ref=ref)
        return res

    @classmethod
    def from_info(cls, info: str):
        kwargs = parse_info(info)
        return cls(**kwargs)

    def to_request(self) -> dict:
        """Returns a dict suitable for sending to an Auto1111 API endpoint as json"""
        res = self.model_dump(exclude_none=True,
                              exclude={'label',
                                       'data',
                                       'metadata',
                                       'tags',
                                       'media_type',
                                       'dims',
                                       'actors',
                                       'nsfw',
                                       'initial_digest',
                                       'locals',
                                       'hr_fix',
                                       'img2img',
                                       'ctrlnet'},
                              by_alias=True)
        if self.dims:
            res['width'], res['height'] = self.dims

        if self.img2img:
            img2img_res = self.img2img.model_dump(exclude_none=True,
                                                  exclude={'img_src'},
                                                  by_alias=True)
            img2img_res['images'] = [ self.img2img.img_src ]
            img2img_res['width'], img2img_res['height'] = self.img2img.new_dims()

            res |= img2img_res

        elif self.hr_fix:
            # img2img doesn't use hr_fix
            hr_res = self.hr_fix.model_dump(exclude_none=True,
                                            by_alias=True)
            hr_res['enable_hr'] = True
            res |= hr_res

        if self.ctrlnet:
            ctrlnet_res = []
            for unit in self.ctrlnet:
                unit_res = unit.model_dump(exclude_none=True,
                                           by_alias=True,
                                           exclude={'img_src'})
                if unit.img_src:
                    unit_res['input_image'] = unit.img_src
                    res['width'], res['height'] = self.ctrlnet[0].new_dims()
                if unit.preprocessor == "canny":
                    unit_res |= {
                        'threshold_a': 100, 'threshold_b': 200
                    }
                ctrlnet_unit = webuiapi.ControlNetUnit( **unit_res )
                ctrlnet_res.append( ctrlnet_unit )
            res['controlnet_units'] = ctrlnet_res

        return res

    def to_info(self):
        res = self.model_dump(exclude_none=True,
                              exclude_unset=True,
                              exclude={"initial_digest"})
        res.update(basic_info())
        res['uid'] = self.uid
        digest = self.digest()
        res['digest'] = digest
        if self.initial_digest != digest:
            # We should still track the original digest even if it has changed, so the
            # resulting output can be registered under the realized creation-id
            res['initial_digest'] = self.initial_digest
        res['source'] += "-Auto1111Api"
        return res

    class Config:
        # resolves a warning about "model_hash" conflicting with protected "model_"
        protected_namespaces = ()



# with importlib.resources.open_text("tangl.media.stableforge.resources", "shot_templates.yaml") as f:
#     templates = yaml.safe_load(f)
# Auto1111Spec.templates = templates
#
