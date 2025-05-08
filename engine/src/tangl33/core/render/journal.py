from .fragment import Fragment

class Journal(list[Fragment]):
    def append_fragments(self, frags, bookmark: str = None): ...