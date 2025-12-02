
from tangl.story.concepts import Concept
from .enums import *


class Vocals(Concept):
    # This is analogous to a _look_ for a vo creator/adapter

    accent: VocalAccent = VocalAccent.US
    general_attitude: Attitude = None
    reference_model: str = None
    voice_kws: str = None

    @property
    def apparent_gender(self):
        return self.parent.look.apparent_gender

    @property
    def apparent_age(self):
        return self.parent.look.apparent_age
