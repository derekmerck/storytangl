"""
eurynym -- a 'broad word', collection of senses covering an application of a concept

identify the eurynym lemmas:  "she eagerly ate the delicious sandwich"
- eager -> enthusiastic, hesitant, ...
- eat -> devour, nibble, ...
- delicious -> tasty, nasty, ...
- sandwich -> snack, meal, ...

check referent and select replacements from possible senses:
- eager -> hesitant
- eat -> nibble
- delicious -> nasty
- sandwich -> gruel

linguistic transforms for each pos:
- hesitant (ADV) -> hesitantly
- nibble (VERB, pp) -> nibbled
- nasty (ADJ) -> nasty
- gruel (NOUN) -> gruel

"she hesitantly nibbled the nasty gruel"
"""
import dataclasses
import functools
import re
from typing import Protocol
from enum import Enum
from abc import ABC
import random

import jinja2

Uid = str

class Referent(Protocol):
    def qualified_by(self, tag: str): ...

class EurynymException(Exception):
    pass

class PoS(Enum):
    """Part of speach"""
    NOUN = "noun"
    ADJ = "adjective"
    VERB = "verb"
    ADV = "adverb"

from tangl.world.narrator.lang import PoV, PT
from tangl.world.narrator.prereader import PoS

@dataclasses.dataclass
class AbstractSemiote(ABC):
    """Abstract contrastative element of meaning"""
    uid: str
    pos: PoS
    gloss: str = None
    examples: list = dataclasses.field(default_factory=list)

    def __call__(self, referent: Referent = None) -> str: ...

@dataclasses.dataclass
class Word(AbstractSemiote):
    """Primitive semiote for lexical token"""
    lemma: str = None
    ner: str = None
    pov: Pronoun.PoV = 3


@dataclasses.dataclass
class Sense(AbstractSemiote):
    """Primitive semiote with lexemes covering a single 'sense'"""
    synset: set[str] = dataclasses.field(default_factory=set)
    lemmas: list = dataclasses.field(default_factory=list)

    def __call__(self, *args, **kwargs):
        return random.choice( list(self.synset) )

@dataclasses.dataclass
class Eurynym(AbstractSemiote):
    """
    Dynamic semiote that maps qualifiers to senses (a 'senseset')

    Two types of default senses can be represented.

    - '_':  generic sens, included in all variants
    - '__': ambiguous sense, ONLY invoked if no generic or variant
            is available.

    Can find/sub with either a regex or a semex (and spaCy)
    """
    senseset: dict[str, Sense] = dataclasses.field(default_factory=dict)
    regex: str = None
    plural: bool = False  # noun members are plural by default

    @functools.cached_property
    def _regex(self) -> re.Pattern:
        if self.regex:
            return re.compile(self.regex)

    def __call__(self, referent: Referent = None) -> str:
        sense = None
        for tag, candidate_sense in self.senseset.items():
            if referent.qualified_by(tag):
                sense = candidate_sense
                break

        if not sense:
            raise EurynymException(f"No suited sense for {self} with referent {referent}")

        return sense()

    def find(self, source: str):
        if self._regex:
            return len( self._regex.findall( source ) ) > 0



@dataclasses.dataclass
class Euryphrase(AbstractSemiote):
    """Extended dynamic semiote that organizes multiple senses into phrase patterns"""
    eurysets: dict[str, Eurynym] = dataclasses.field(default_factory=dict)
    template: str = "{{ _() }}"
    semex: list = dataclasses.field(default_factory=list)
    regex: str = None

    # def __post_init__(self):
    #     self.regex = "xyz"

    def __call__(self, referent: Referent = None) -> str:
        senses = {}
        for k, eurynym in self.eurysets:
            for tag, candidate_sense in eurynym.senseset.items():
                if referent.qualified_by(tag):
                    senses[k] = candidate_sense
                    continue

        templ = jinja2.Environment().get_template(self.template)
        return templ.render( **senses )

    # def find(self, source: str) -> bool:
    #     if self.regex:

