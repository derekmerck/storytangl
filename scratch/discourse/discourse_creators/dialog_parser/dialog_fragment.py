from tangl.core.solver import ContentFragment

class DialogFragment(ContentFragment):
    style_hints: DialogStyleHints = None

class DialogStyleHints:

    speaker_label: str = None
    speaker_style_hints: dict = None
    speaker_attitude: dict = None
