from tangl.media.type_hints import Audio
from .voxforge_spec import VoxSpec

class ElevenLabsApi:

    url: str
    token: str

    def generate_audio(self, spec: VoxSpec) -> Audio:
        pass
