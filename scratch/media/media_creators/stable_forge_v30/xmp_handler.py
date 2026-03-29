from uuid import UUID
import re
from pathlib import Path
from typing import *
from datetime import datetime
import logging

import pyexiv2
from PIL.Image import Image
from pydantic import BaseModel, Field, validator

from tangl.info import __title__, __author__, __author_email__, __url__
from . import __version__ as __sf_version__, __title__ as __sf_title__

logger = logging.getLogger(__name__)

pyexiv2.registerNs("http://xmp.gettyimages.com/gift/1.0", "GettyImagesGIFT")

class XmpDataModel(BaseModel):

    XMP_KEY_MAP: ClassVar[dict] = {
        "tool":       "Xmp.tiff.Software",
        "creator":    "Xmp.dc.creator",
        "email":      "Xmp.Iptc4xmpCore.CreatorContactInfo/Iptc4xmpCore:CiEmailWork",
        "url":        "Xmp.Iptc4xmpCore.CreatorContactInfo/Iptc4xmpCore:CiUrlWork",
        "collection": "Xmp.photoshop.Category",
        "source":     "Xmp.photoshop.Source",

        "guid":       "Xmp.photoshop.TransmissionReference",  # "job", should be pre-digest?
        "prompt":     "Xmp.dc.description",                   # "caption"
        "model":      "Xmp.tiff.Model",                       # "model name"
        "spec":       "Xmp.photoshop.Instructions",           # "instructions"
        "digest":     "Xmp.iptcExt.DigImageGUID",             # "guid"
        "kws":        "Xmp.dc.subject",                       # "keywords"
        "actors":     "Xmp.iptcExt.PersonInImage",            # Used by Lrc
        "actors_alt": "Xmp.GettyImagesGIFT.Personality",      # Used by Cap1

        "timestamp":  "Xmp.tiff.DateTime",                    # Capture time

        # unused
        "title":      "Xmp.dc.title",
    }

    tool: str = "StableDiffusion"
    creator: str = __author__
    email: str = __author_email__
    url: str = __url__
    collection: str = __title__
    source: str = f"{__sf_title__} v{__sf_version__}"

    guid: UUID
    prompt: str
    model: str
    spec: dict[str, Any]
    digest: str
    actors: list[str] = Field(default_factory=list)
    actors_alt: str = None
    kws: set[str] = Field(default_factory=set)
    timestamp: datetime = Field(default_factory=datetime.now)

    # unused
    title: str = None

    def __init__(self, actors=None, nsfw=False, kws=None, **kwargs):
        if not 'spec' in kwargs:
            kwargs['spec'] = {**kwargs}
        if 'n_prompt' in kwargs:
            kwargs['prompt'] += " NOT " + kwargs['n_prompt']
        if ts := kwargs.get('ts'):
            kwargs['timestamp'] = ts

        print( kws )
        kws = kws or set()
        print( kws )
        if actors:
            kwargs['actors_alt'] = ";".join(actors)
            for actor in actors:
                kws.add( f"actor|{actor}" )
        if nsfw:
            kws.add('nsfw')
        print( kws )
        super().__init__(kws=kws, actors=actors, **kwargs)

    @property
    def xmp_tags(self):
        data = self.model_dump()
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat()
            elif isinstance(v, UUID):
                data[k] = str(v)
            elif isinstance(v, set | list):
                data[k] = [ str(item) for item in v ]
        # transform keys
        xmp_tags = { self.XMP_KEY_MAP[k]: v for k, v in data.items() }
        return xmp_tags

    def write_xmp( self, fp: Path, clear_all=True ):
        target = pyexiv2.Image(str(fp))
        if clear_all:
            target.clear_xmp()
        target.modify_xmp( self.xmp_tags )

    XMP_TEMPLATE_BYTES: ClassVar[str] = """<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.5.0"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/></x:xmpmeta>""".encode('utf8')

    def write_xmp_sidecar( self, fp: Optional[Path], clear_all=True ):
        if not fp or clear_all:
            target = pyexiv2.ImageData(self.XMP_TEMPLATE_BYTES)
        else:
            with open(fp, 'rb') as f:
                target = pyexiv2.ImageData(f.read())
        target.modify_xmp( self.xmp_tags )

        im_bytes = target.get_bytes()
        im_str = im_bytes.decode('utf8', errors="ignore")
        m = re.match(r".*?(<x:xmpmeta.*</x:xmpmeta>)", im_str, re.DOTALL)
        xmp_str = m.groups(1)[0]

        if fp:
            xmp_fp = fp.with_suffix('.xmp')
            with open(xmp_fp, 'w') as f:
                f.write(xmp_str)
        else:
            logger.debug( xmp_str )

    @classmethod
    def read_xmp( cls, fp: Path ) -> dict:
        target = pyexiv2.Image(str(fp))
        res = target.read_xmp()
        logger.debug( res )
        return res

    @classmethod
    def read_xmp_sidecar( cls, fp: Path ) -> str:
        with open(fp, 'rb') as f:
            target = pyexiv2.ImageData(f.read())
        logger.debug( target.read_xmp() )
        im_bytes = target.get_bytes()
        im_str = im_bytes.decode('utf8', errors="ignore")
        m = re.match(r".*?(<x:xmpmeta.*</x:xmpmeta>)", im_str, re.DOTALL)
        xmp_str = m.groups(1)[0]
        logger.debug(xmp_str)
        return xmp_str
