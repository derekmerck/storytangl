from __future__ import annotations
from tangl.journal.content import ContentFragment, PresentationHints

# this is just something like 'attributed fragment' now
# its the same format as a 'card', I think, with inline content and a group roles record for related fragments like media

class DialogFragment(ContentFragment):
    speaker_hints: SpeakerHints = None

class SpeakerHints(PresentationHints):

    speaker_label: str = None
    speaker_attitude: dict = None
    speaker_media: dict = None
