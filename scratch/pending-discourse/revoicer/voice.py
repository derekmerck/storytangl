"""
A 'Voice' is a custom jinja2 environment that supports narrative pre-processors.

Voices can can be attached to individual Actors or the story Narrator to add
features for rendered text output.

- Singleton text objects: initialize it with a string-map of strings by resource
  path and alleviate the need to duplicate text passages in every story instance.
- Localization: provide multiple string-maps for localization and reference a
  global 'locale' setting to provide translation
- Discrete overrides: provide a string-map with 'override' values that supersede
  and replace default string-map entries
- Template preprocessing: it can do pre- and post-processing on template renders,
  including regex's for simple translation and recursive rendering, these can come
  from Actors or the Narrator, using word-banks or link to an LLM, for example.
- Recursive template rendering

Note that Voices are managed by the world, so they are effectively story-independent
Singletons.
"""
from typing import Callable
import re

from jinja2 import Environment as BaseEnvironment, Template

from tangl.type_hints import StringMap  # string or UUID
from tangl.utils.rejinja import RecursiveTemplate  # recursively evaluates content in {{ text expansions }}

RegexSub = tuple[str, str | Callable]

class Voice(BaseEnvironment):
    def __init__(self, *args,
                 strings_map: StringMap = None,
                 strings_overrides: StringMap = None,
                 string_preprocessors: list[Callable] = None,
                 regex_substitutions: list[RegexSub] = None,
                 default_template_class: type[Template] = None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.strings_map = strings_map or {}
        self.strings_overrides = strings_overrides or {}
        self.string_preprocessors = string_preprocessors or []
        self.regex_substitutions: list[ tuple[re.Pattern, str] ] = []
        for pattern, replacement in regex_substitutions or []:
            # precompile since we are going to be using these a lot
            compiled = re.compile( pattern )
            self.regex_substitutions.append( (compiled, replacement) )
        self.default_template_class = default_template_class or RecursiveTemplate

    def from_id(self, string_id: Uid, globals: dict = None,
                template_class: type[Template] = None) -> Template:
        if not self.strings_map:
            raise ValueError("No strings map available")
        if string_id in self.strings_overrides:
            source = self.strings_overrides[string_id]
        else:
            source = self.strings_map.get(string_id, "")
        source = self.preprocess_string(source)
        return super().from_string(source,
                                   globals=globals,
                                   template_class=template_class or self.default_template_class)

    def from_string(self, source: str, globals: dict = None,
                    template_class: type[Template] = None) -> Template:
        source = self.preprocess_string(source)
        return super().from_string(source, globals=globals,
                                   template_class=template_class or self.default_template_class)

    def process_regex_substitutions(self, source):
        for pattern, replacement in self.regex_substitutions:
            source = pattern.sub(replacement, source)

    def preprocess_string(self, source: str) -> str:
        if self.regex_substitutions:
            source = self.process_regex_substitutions(source)
        for func in self.string_preprocessors:
            source = func(source)
        return source
