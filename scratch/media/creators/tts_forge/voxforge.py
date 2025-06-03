from typing import TYPE_CHECKING

from tangl.entity import SingletonEntity
from tangl.media.type_hints import MediaResource
from .voxforge_spec import VoxSpec
from .elevenlabs_api import ElevenLabsApi

if TYPE_CHECKING:
    from tangl.media.type_hints import Audio

class VoxForge(SingletonEntity):
    """
    Implements MediaForge
    """

    @classmethod
    def create_media(cls, spec: VoxSpec) -> tuple[MediaResource, VoxSpec]:

        api = cls.get_11labs_api()
        audio = api.generate_audio(spec)  # type: Audio
        updated_spec = VoxSpec(**audio[1])
        return audio[0], updated_spec

    @staticmethod
    def get_11labs_api() -> ElevenLabsApi:
        return ElevenLabsApi()

