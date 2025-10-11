from enum import Enum, auto

import attr
from PIL import Image

from tangl.utils.png_dims import get_png_dimensions
from .media_resource import StaticMediaFileSpec, MediaType
from .media_handler import MediaHandler

@attr.s
class ImageHandler(MediaHandler):

    media_format: ImageFormat = attr.ib(default=ImageFormat.PNG)
    image_shape: ImageShape = attr.ib(init=False)

    @image_shape.default
    def _mk_image_shape(self):
        if isinstance(self.spec, StaticImageFileSpec):
            if self.spec.fp.is_file():
                width, height = get_png_dimensions(self.spec.fp)
                aspect_ratio = width / height
                if aspect_ratio < 0.8:
                    return ImageShape.PORTRAIT
                elif aspect_ratio > 1.2:
                    return ImageShape.LANDSCAPE
                else:
                    return ImageShape.SQUARE

    def get_media(self, **kwargs) -> Image:
        if isinstance(self.spec, StaticImageFileSpec):
            if self.spec.fp.is_file():
                self.media = Image.open(self.spec.fp)
            raise FileNotFoundError
        return super().get_media(**kwargs)
