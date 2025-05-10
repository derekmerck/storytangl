from .fragment import Fragment

class Journal(list[Fragment]):

    def append_fragments(self, frags: list[Fragment], bookmark: str = None):
        self.extend(frags)