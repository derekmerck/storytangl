from datetime import datetime
import logging

from webuiapi import WebUIApi, WebUIApiResult
from PIL.Image import Image

from tangl.utils.pixel_avg_hash import pix_avg_hash
from .auto1111_spec import Auto1111Spec

logger = logging.getLogger(__name__)

class Auto1111Api(WebUIApi):
    """
    Wraps WebUIApi and provides simple im2im and txt2im workflows for MediaSpec objects
    """

    # def __init__(self, *args, **kwargs):
    #     # Have to call this manually
    #     super().__init__(*args, **kwargs)

    def generate_image(self, spec: Auto1111Spec) -> tuple[Image, Auto1111Spec]:
        # todo: add call to change the mode

        kwargs = spec.to_request()
        if 'images' in kwargs:
            result = self.img2img(**kwargs)
        else:
            result = self.txt2img(**kwargs)

        kwargs.update(result.info)
        updated_spec = Auto1111Spec(**kwargs)
        im = result.image
        im.info.update( updated_spec.to_info() )
        # Auto1111 returns the parameters as a string in im.info['parameters'],
        # we can preserve that; see 'parse_auto1111_params' for details
        im.info['px_hash'] = pix_avg_hash(result.image)
        im.info['timestamp'] = datetime.now()

        return im, updated_spec
