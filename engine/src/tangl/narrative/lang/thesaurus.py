from __future__ import annotations
import functools
import importlib.resources
from typing import *
import re
import random
import logging
from pprint import pprint, pformat

import jinja2
import pydantic
import yaml

from tangl.core.entity import Singleton
from .pos import PartOfSpeach
from .pov import PoV
from .helpers.pattern import conjugate
from .helpers.adjective_to_adverb import adjective_to_adverb

logger = logging.getLogger("tangl.narrative.lang.thesaurus")

class Synset(Singleton):
    """
    Cardinal representation is as singular nouns (NN), adjectives (JJ), or verb
    base forms (VB).  Other common forms (NNS, RB, VBG/N/P/Z) can be created
    from these.
    """

    # _instances: ClassVar[dict[str, Synset]]

    pos: PartOfSpeach  # in general, this should be NN/S, JJ, or VB

    synonyms: set[str] = pydantic.Field(default_factory=set)
    @pydantic.field_validator('synonyms', mode='before')
    @classmethod
    def _convert_to_set(cls, value):
        if value and not isinstance(value, set):
            value = set(value)
        return value

    @property
    def synonyms_(self):
        return self.synonyms.union({ self.label })

    def synonyms_conjugated(self,
                            pov: PoV = PoV._3s,
                            tense: str = "present",
                            aspect: str = "imperfective"):

        if self.pos is not PartOfSpeach.VB:
            raise TypeError(f"{self.label} is not a verb!")

        return {
            conjugate(s, pov, tense=tense, aspect=aspect)
            for s in self.synonyms_
        }

    def synonyms_vbp(self):
        # past participles from verbs
        return self.synonyms_conjugated(tense="past")

    def synonyms_vbg(self):
        # gerunds or present participles from verbs
        return self.synonyms_conjugated(aspect="progressive")

    def synonyms_rb(self):
        # adverbs from adjectives
        if self.pos is PartOfSpeach.RB:
            return self.synonyms_
        elif self.pos is PartOfSpeach.JJ:
            return {adverb for adverb in (adjective_to_adverb(s) for s in self.synonyms_) if adverb is not None}
            # return { adjective_to_adverb(s) for s in self.synonyms_ } - {None}
        raise TypeError(f"{self.label} is not an adjective or adverb")

    @functools.cached_property
    def re_pattern(self) -> re.Pattern:
        # pattern = r"(?<=\W)({k})(?=\W|$)".format( k=k )
        rex = fr"(?<=\W)({['|'.join(self.synonyms)]})(?=\W|$)"
        return re.compile(rex)

    def substitution(self, match: re.Match):
        return "{{" + f"Synset[{self.label}].replace({match[0]})" + "}}"

    def re_sub(self, s: str) -> str:
        s = self.re_pattern.sub(self.re_sub, s)
        return str(s)

    def replace(self, match: str):
        return random.choice(list(self.synonyms_))


class Thesaurus(Singleton):

    synsets: list[Synset]

    @classmethod
    def from_resources(cls, label: str, resource_module: str, resource_fn: str) -> Thesaurus:
        synsets = cls.load_resources(resource_module, resource_fn)
        from pprint import pprint

        pprint( [ s.model_dump() for s in synsets ] )
        return cls(label=label, synsets=synsets)

    @classmethod
    def load_resources(cls, resource_module: str, resource_fn: str) -> list[Synset]:
        with open( importlib.resources.files(resource_module) / resource_fn ) as f:
            data = yaml.safe_load(f)
        res = []
        for pos, _data in data.items():
            for k, v in _data.items():
                if k not in Synset._instances:
                    syn = Synset(label=k, pos=pos, synonyms=v)
                    res.append( syn )
                else:
                    logger.warning(f"redeclared a synset {k}")
                    logger.warning(pformat( v ))

        return res

    def nouns(self):
        for s in self.synsets:
            if s.pos in [ PartOfSpeach.NN, PartOfSpeach.NNS ]:
                yield s

    def verbs(self):
        for s in self.synsets:
            if s.pos is PartOfSpeach.VB:
                yield s

    def adjectives(self):
        for s in self.synsets:
            if s.pos is PartOfSpeach.JJ:
                yield s

    def adverbs(self):
        for s in self.synsets:
            if s.pos in [PartOfSpeach.RB, PartOfSpeach.JJ]:
                yield s

    @classmethod
    def prepare(cls, s: str):
        for syn in cls.synsets:
            s = syn.re_sub(s)
        print(s)
        return s

    # todo: Need to inject this as a post-processor in rejinja/render_str and then render again


# legacy code is clever, it uses a reverse search through the text.

# language=python
"""
import random
cls = object
pat, repl, s = "my_regex", "my_repl", "my string"
for match in reversed( list( pat.finditer( s ) ) ):
    if random.random() < cls.replacement_prob:
        if isinstance( repl, list ) and len( repl ) > 1:
            repl_ = ""
            for repl_el in repl:
                repl_ += random.choice( list( repl_el ) ) + " "
            repl_ = repl_[:-1]
        else:
            repl_ = random.choice( list(repl) )
        s = s[:match.start()] + repl_ + s[match.end():]
"""