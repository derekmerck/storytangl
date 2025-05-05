
from tangl.media import MediaSpec

class VoxSpec(MediaSpec):
    """
    Spec for voice-over dialog and narration
    """

    text: str = None           # text to read
    voice_kws: str = None      # baseline enthusiasm etc.
    passage_kws: str = None

    vocal_accent: str = None
    apparent_age: str = None
    apparent_gender: str = None
    speaker_model: str = None  # character voice in api namespace

    @classmethod
    def get_forge(cls):
        from .voxforge import VoxForge
        return VoxForge()
