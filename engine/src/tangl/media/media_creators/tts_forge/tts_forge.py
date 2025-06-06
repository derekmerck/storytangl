from typing import TYPE_CHECKING

from ...type_hints import Media
from .tts_spec import TtsSpec
from .eleven_api import ElevenLabsApi

if TYPE_CHECKING:
    from tangl.media.type_hints import Audio

class TtsForge:
    """
    Implements MediaForge
    """

    @classmethod
    def create_media(cls, spec: TtsSpec) -> tuple[Audio, TtsSpec]:
        api = cls.get_11labs_api()
        audio, updated_spec = api.generate_audio(spec)  # type: Audio, TtsSpec
        return audio, updated_spec

    @staticmethod
    def get_11labs_api() -> ElevenLabsApi:
        return ElevenLabsApi()

