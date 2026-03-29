import functools
import logging
logger = logging.getLogger("tangl.media")

import attr
from webuiapi import WebUIApi as WebUIApi_, WebUIApiResult, ControlNetInterface, ControlNetUnit
from PIL import Image

from .hash2model import ModelHashes, CtrlNetModelNames
from .stable_spec import StableForgeSpec
from tangl.utils.pixel_avg_hash import pix_avg_hash


@attr.s(init=False)
class WebUIApi(WebUIApi_):
    """
    Wraps WebUIApi to allow it to accept a StableForgeSpec for generation

    Vocab:
    - model_hash: canonical, automatic 8-char version
    - model_name: checkpoint name as reported by automatic
    - model_key: shorthand model key like "sd15", as indicated in SD_MODEL_HASHES
    """

    def __init__(self, *args, **kwargs):
        # Have to call this manually
        super().__init__(*args, **kwargs)
        self.__attrs_init__()

    model_names: dict = attr.ib(init=False)
    @model_names.default
    def _mk_model_titles(self):
        models_ = self.get_sd_models()
        # plogger.debug( models_ )
        return { v['hash']: v['title'] for v in models_ }

    @property
    def model_hashes(self):
        return {v: k for k, v in self.model_names.items()}

    @property
    def models(self) -> list:
        return list(self.model_names.keys())

    _current_model_hash: str = attr.ib(default=None, init=False)

    @property
    def current_model_hash(self):
        if self._current_model_hash is None:
            # store as its hash
            options = self.get_options()
            # plogger.debug(options)
            model_title = options['sd_model_checkpoint']
            _current_model_hash = self.model_hashes[model_title]
        return self._current_model_hash

    @property
    def current_model_name(self):
        return self.model_names[self.current_model_hash]

    def using_model(self, hash_or_key_or_name) -> bool:
        try:
            model_hash = ModelHashes.model_hash_for(hash_or_key_or_name)
            return self.current_model_hash == model_hash
        except KeyError:
            return self.current_model_name == hash_or_key_or_name

    def set_model(self, hash_or_key_or_name: str):
        if not self.using_model(hash_or_key_or_name):
            if hash_or_key_or_name in self.model_names.values():
                model_name = hash_or_key_or_name
                model_hash = self.model_hashes[model_name]
            else:
                model_hash = ModelHashes.model_hash_for(hash_or_key_or_name)
                try:
                    model_name = self.model_names[model_hash]
                except KeyError:
                    raise ValueError(f"No such model {hash_or_key_or_name} available on this api")
            logger.debug(f"Changing out sd model to {model_name}")
            options_ = {'sd_model_checkpoint': model_name}
            self.set_options(options_)
            self._current_model_hash = model_hash

    @functools.cached_property
    def ctrlnet(self) -> ControlNetInterface:
        return ControlNetInterface(self)

    cn_names: dict = attr.ib(init=False)
    @cn_names.default
    def _mk_cn_names(self):
        try:
            models_ = self.ctrlnet.model_list()
            # discard V10 models
            return { v.split("_")[-1].split()[0]: v for v in models_ if "V10" not in v }
        except KeyError:
            return {}

    @classmethod
    def _result2img(cls, result: WebUIApiResult, spec: StableForgeSpec, show_discarded_images: bool = False) -> Image:
        """Addend digests the result of a StableForge generation"""

        if len(result.images) > 1:
            logger.debug("Multiple images were returned, and all but the first were discarded")
            if show_discarded_images:
                for im_ in result.images[1:]:
                    im_.show()

        im = result.image
        im.info |= result.info

        if spec.seed != im.info['seed']:
            # Revise the spec seed if necessary
            logger.debug(f"Revising spec hash: seed {spec.seed} -> {result.info['seed']}")
            spec.seed = im.info['seed']

        # Include the spec digest in the image info
        im.info['spec_digest'] = spec.digest

        # Include the pixel hash in the image info
        pixel_h = pix_avg_hash(result.image)
        im.info['pixel_hash'] = pixel_h

        return im

    def txt2img(self, spec: StableForgeSpec = None, **kwargs) -> Image:

        if not spec:
            result = super().txt2img(**kwargs)
            return self._result2img(result, spec)

        kwargs = kwargs | {}

        if spec.hires_fix:
            kwargs |= {"enable_hr": True,
                       "hr_scale": spec.hires_fix.scale,
                       "denoising_strength": spec.hires_fix.denoise}

        if spec.ctrlnet:

            unit1 = ControlNetUnit(
                input_image=spec.ctrlnet.image,
                weight=spec.ctrlnet.weight,
                guidance=spec.ctrlnet.guidance,
                guidance_start=spec.ctrlnet.guidance_start,
                guidance_end=spec.ctrlnet.guidance_end,
                # This _must_ be "none" lowercase for None
                module=spec.ctrlnet.processor or "none",
                processor_res=spec.ctrlnet.processor_res,
                model=self.cn_names[spec.ctrlnet.model_name])

            kwargs['controlnet_units'] = [unit1]

        result = super().txt2img(
            prompt=spec.prompt,
            negative_prompt=spec.neg_prompt,
            seed=spec.seed,
            cfg_scale=spec.cfg_scale,
            sampler_index=spec.sampler,
            steps=spec.steps,
            width=spec.dims[0],
            height=spec.dims[1],
            **kwargs)

        im = self._result2img(result, spec)
        return im

    def img2img( self, spec: StableForgeSpec = None, **kwargs ) -> Image:

        if not spec:
            result = super().txt2img(**kwargs)
            return self._result2img(result, spec)

        kwargs = kwargs | {}

        if spec.hires_fix:
            raise ValueError("Hires fix is not supported for img2img")

        if spec.ctrlnet:

            unit1 = ControlNetUnit(
                input_image=spec.ctrlnet.image,
                weight=spec.ctrlnet.weight,
                guidance=spec.ctrlnet.guidance,
                guidance_start=spec.ctrlnet.guidance_start,
                guidance_end=spec.ctrlnet.guidance_end,
                # This _must_ be "none" lowercase for None
                module=spec.ctrlnet.processor or "none",
                processor_res=spec.ctrlnet.processor_res,
                model=self.cn_names[spec.ctrlnet.model_name])

            kwargs['controlnet_units'] = [unit1]

        result = super().img2img(
            images=[spec.img2img.image],
            prompt=spec.prompt,
            negative_prompt=spec.neg_prompt,
            seed=spec.seed,
            sampler_index=spec.sampler,
            steps=spec.steps,
            width=spec.dims[0],
            height=spec.dims[1],
            denoising_strength=spec.img2img.denoise,
            **kwargs
        )

        im = self._result2img(result, spec)
        return im
