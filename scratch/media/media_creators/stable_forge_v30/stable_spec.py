from __future__ import annotations
from typing import Optional
import datetime
from pathlib import Path
import random
import hashlib
import sys
import uuid

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from hashlib import _Hash

import attr
from PIL import Image

from tangl.media.media_spec import MediaSpec
from tangl.utils.pixel_avg_hash import pix_avg_hash
import tangl.utils.attrs_ext as attrs_ext
from .hash2model import ModelHashes

from .resources import celebs, embeddings

@attr.define
class StableForgeSpec(MediaSpec):
    """
    Uid's and meta are excluded from equivalence.
    digests/guids will be unique and identical for the same parameters.

    Depends on the `pixel_avg_hash` module from tangl.
    """
    uid: str = attr.ib(metadata={"digest": False}, eq=False)

    prompt: str = attr.ib(default="a sailboat")
    neg_prompt: Optional[str] = attr.ib(default="lowres blur anime cg 3d")

    model_hash: str = attr.ib(default="sd15")
    seed: int = attr.ib(default=-1)
    cfg_scale: float = attr.ib(default=4.5)
    sampler: str = attr.ib(default="Euler a")
    steps: int = attr.ib(default=20)

    dims: tuple[int, int] = attr.ib(default=(320, 320))

    @attr.s
    class HiresFixSpec:
        scale: float = attr.ib(default=1.0)
        denoise: float = attr.ib(default=0.6)

    hires_fix: HiresFixSpec = attr.ib(default=None)

    @attr.s
    class Img2ImgSpec:
        image: Image = attr.ib(metadata={"digest": pix_avg_hash})
        # scale: float = 2.0    # probably crop and scale and dims?
        denoise: float = attr.ib(default=0.6)

        def __post_init__(self):
            if isinstance(self.image, str | Path):
                self.image = Image.open(self.image)

    img2img: Img2ImgSpec = attr.ib(default=None)

    @attr.s
    class CtrlNetSpec:
        image: Image = attr.ib(default = None, metadata={"digest": pix_avg_hash})
        processor: str = attr.ib(default='canny')
        model_name: str = attr.ib(default='canny')
        weight: float = attr.ib(default=1.0)
        guidance: float = attr.ib(default=1.0)
        guidance_start: float = attr.ib(default=0.0)
        guidance_end: float = attr.ib(default=1.0)
        processor_res: int = attr.ib(default=512)

        def __post_init__(self):
            if isinstance(self.image, str | Path):
                self.image = Image.open(self.image)

    ctrlnet: CtrlNetSpec = attr.ib(default=None)

    meta: dict = attr.ib(factory=dict, metadata={'digest': False}, eq=False)

    def __attrs_post_init__(self):

        if not self.seed or self.seed < 0:
            self.seed = random.randint(0, sys.maxsize)

        try:
            self.model_hash = ModelHashes.model_to_hash(self.model_hash)
        except KeyError:
            pass

        if self.hires_fix and isinstance(self.hires_fix, dict):
            self.hires_fix = self.HiresFixSpec(**self.hires_fix)

        if self.img2img and isinstance(self.img2img, dict):
            self.img2img = self.Img2ImgSpec(**self.img2img)

        if self.ctrlnet and isinstance(self.ctrlnet, dict):
            self.ctrlnet = self.CtrlNetSpec(**self.ctrlnet)

        if "post" in self.meta:
            kwargs = attr.asdict(self)
            kwargs['meta'].pop('post')
            kwargs |= self.meta['post']
            self.meta['post'] = self.__class__(**kwargs)

        # find celebrity prompts and note them in 'actors' metadata field
        for a in celebs:
            if a.lower() in self.prompt.lower():
                self.meta['actors'] = self.meta.get('actors', []) + [a]

        for k, v in embeddings.items():
            if k.lower() in self.prompt.lower():
                self.meta['actors'] = self.meta.get('actors', []) + [v]

        # check and tag nsfw
        nsfw_toks = ['cock', 'pussy', 'cum']
        nsfw_found = [t in self.prompt for t in nsfw_toks]
        if any(nsfw_found):
            self.meta['nsfw'] = True

    @property
    def model_name(self) -> str:
        return ModelHashes.hash_to_model(self.model_hash) or 'unknown'

    # Unique ID

    @property
    def _hash(self) -> _Hash:
        d = self.as_tuple(digest=True)
        # ignore uid and meta
        bytes_ = str(d).encode('utf8')
        h = hashlib.sha224(bytes_)
        return h

    @property
    def digest(self) -> str:
        return self._hash.hexdigest()

    @property
    def guid(self) -> uuid.UUID:
        h = self._hash()
        return uuid.UUID( bytes=h.digest()[0:16] )  # 16 bytes in a uuid

    # Representers

    def as_dict(self) -> dict:
        d = attrs_ext.as_dict(self)
        d['digest'] = self.digest[0:8]
        return d

    as_tuple = attrs_ext.as_tuple
    as_yaml = attrs_ext.as_yaml

    def as_xmp(self, ts: datetime.datetime = None) -> dict:
        """
        If using the spec to convert an image to xmp, you have to pass a
        timestamp explicitly if you want to include it.  The spec does not
        track timestamp for any particular image.
        """
        from .xmp_handler import XmpHandler
        return XmpHandler.spec2xmp(self, ts=ts)

    def as_sd_api_params(self) -> dict:
        raise NotImplementedError

    # Factories

    @classmethod
    def from_xmp(cls, xmp_data: dict, uid: str = None) -> 'StableforgeSpec':
        """Convert xmp data to a spec"""
        raise NotImplementedError
        # from .xmp_handler import XmpHandler
        # return XmpHandler.xmp2spec(xmp_data, uid)

    @classmethod
    def from_info(cls, info: str, uid: str = None) -> 'StableforgeSpec':
        """Convert auto1111 image gen info string to a spec"""
        from tangl.media.illustrated.stableforge.parse_info import info2spec
        return info2spec(info, uid)
