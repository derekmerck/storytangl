# keeps tracks of all variables used by a template

from jinja2 import Environment

class TrackingEnvironment(Environment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.used_variables = set()

    def resolve(self, key):
        self.used_variables.add(key)
        return super().resolve(key)
