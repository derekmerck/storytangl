from tangl.media.type_hints import Audio
from .tts_spec import TtsSpec

class ElevenLabsApi:

    url: str
    token: str

    def generate_audio(self, spec: TtsSpec) -> tuple[Audio, TtsSpec]:
        pass
