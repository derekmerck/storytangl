from types import SimpleNamespace

class Domain(SimpleNamespace):
    """Holds world-level singletons that must survive graph reloads."""
    def __init__(self):
        super().__init__(
            globals_layer = {},          # context globals
            templates = {},              # name → Template
        )

    def get_templates(self) -> dict:
        return self.templates

    def get_globals(self) -> dict:
        return self.globals_layer
