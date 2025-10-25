from typing import TypeVar, Optional

from PIL.Image import Image

from tangl.config import settings
from .stable_spec import StableSpec
from .auto1111_spec import Auto1111Spec
from .auto1111_api import Auto1111Api

StableSpecT = TypeVar('StableSpecT', bound=StableSpec)

class StableForge:
    """
    Implements MediaForgeP
    """

    def create_media(self, spec: StableSpecT) -> tuple[Image, Optional[StableSpecT]]:

        if isinstance(spec, Auto1111Spec):
            api = self.get_auto1111_api()
            im, updated_spec = api.generate_image( spec )  # type: Image, StableSpecT
            return im, updated_spec

        # elif isinstance(spec, ComfySpec):
        #     api = self.get_comfy_api()
        #     im, updated_spec = api.generate_image( spec )
        #     return im, updated_spec

        else:
            raise TypeError

    # The preprocessing should actually be in the spec.realize() function
    # def create_media(self, spec: MediaSpec, adapters: list[str] = None, **context) -> tuple[Auto1111Spec, Image]:
    #     adapters = adapters or ['render_prompts']
    #     for adapter in adapters:
    #         if x := adapter_handlers.get(adapter).execute(spec, **context):
    #             spec = x
    #     api = self.get_auto1111_api()
    #     im, spec = api.handle_spec(spec)
    #     return im, spec

    @classmethod
    def get_auto1111_api(cls):
        """
        Get an auto1111 worker from config
        """
        if not settings.media.apis.stableforge.enabled:
            raise RuntimeError("StableForge disabled!")
        if not settings.media.apis.stableforge.auto1111_workers:
            raise RuntimeError('No auto1111 workers in config')
        url = settings.media.apis.stableforge.auto1111_workers[0]
        return Auto1111Api(url)

    # @classmethod
    # def get_comfy_api(cls):
    #     """
    #     Get a comfy worker from config
    #     """
    #     if not settings.media.apis.stableforge.enabled:
    #         raise RuntimeError("StableForge disabled!")
    #     if not settings.media.apis.stableforge.comfy_workers:
    #         raise RuntimeError('No comfy workers in config')
    #     url = settings.media.apis.stableforge.comfy_workers[0]
    #     return ComfyApi(url)
