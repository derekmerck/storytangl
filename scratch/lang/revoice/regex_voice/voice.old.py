import re
import functools
from typing import *

import jinja2

from tangl.lang import LexRef, Pronoun
from tangl.actor.enums import Gens


class Voice:
    """
    A Voice can convert pronouns, conjugate verbs, and make gender- or context-
    specific edits to a text passage.  Voices are passed into the jinja template
    render and accessed with language like this:

    '{{ a.She }} {{ a.verb('pleases') {{ b.him }} and {{ b.his }} {{ c.King }}
    with {{ a.her_ }} hands'

    During rendering, a, b, and c are passed through a _voice_ filter that provides
    pronouns, common gendered word replacements e.g. (Mr. -> Ms.), and verb conjugation.

    The Voice class itself also implements some expansion macros that provide shortcuts
    for easy-to-read notation.  The same example phrase in simplified notation:

    'She pleases@a him and his King@c with her_ hands.'
    or
    'She pleases@a you and your King@c with her_ hands.'

    By default, feminine 3rd person pronouns (she/her) are mapped to a voice 'a',
    masculine 3rd person (he/him) and 2nd person (you) are mapped to a voice 'b'.
    Any pronoun or verb can be passed to a specific voice by appending @a,b,c etc.
    to it.

    The benefit of using voice filters is that text passages can be easily updated
    to another point of view by altering the voices.  For example, swapping voices
    could change the output from the sample phrase to this:

    'You please her and her Queen with your hands'

    Simple and full notation can be mixed and matched as useful.
    """

    common_verbs = {
        'is': 'be',
        'has': 'have',
        'says': 'say',
        'wants': 'want',
        'tries': 'try'
    }
    common_replacement_words = {
        'mr': 'ms',
        'king': 'queen',
    }

    def __init__(self, gens=Gens.XX, pronoun=Pronoun.SHE):
        self.gens = Gens(gens)
        self.pronoun = Pronoun(pronoun)
        # self.tense = None   # skip this for now

    @property
    def subjective(self) -> str:
        return self.pronoun.subjective( self.gens )
    he = she = i = you_ = subjective
    He = She = I = You_ = property( lambda self: self.subjective.capitalize() )

    @property
    def objective(self) -> str:
        return self.pronoun.objective( self.gens )
    him = _her = me = _you = objective
    Him = _Her = Me = _You = property( lambda self: self.objective.capitalize() )

    @property
    def objective_reflexive(self) -> str:
        return self.pronoun.objective_reflexive( self.gens )
    himself = herself = myself = yourself = objective_reflexive

    @property
    def possessive(self) -> str:
        return self.pronoun.possessive( self.gens )
    _his = hers = mine = yours = possessive

    @property
    def possessive_adjective(self) -> str:
        return self.pronoun.possessive_adjective( self.gens )
    his_ = her_ = my = your = possessive_adjective
    His_ = Her_ = My = Your = property( lambda self: self.possessive_adjective.capitalize() )

    def verb(self, verb) -> str:
        res = LexRef.conjugate( verb, self.pronoun )
        if verb[0].isupper():
            return res.capitalize()
        return res

    inv_common_replacement_words = { v: k for k, v in common_replacement_words.items() }

    def replace_word(self, word) -> str:
        caps = False
        if word[0].isupper():
            caps = True
        word = word.lower()
        if word in self.common_replacement_words:
            xy = word
            xx = self.common_replacement_words[word]
        elif word in self.inv_common_replacement_words:
            xx = word
            xy = self.inv_common_replacement_words[word]
        else:
            raise KeyError

        if self.gens == Gens.XY:
            res = xy
        else:
            res = xx

        if caps:
            res = res.capitalize()

        return res

    _replacement_map: ClassVar = dict()
    @classmethod
    def replacement_map(cls):

        if not cls._replacement_map:
            her_pronouns = r"[Ss]he|[Hh]er_|[Hh]ers|_[Hh]er|[Hh]erself"
            him_pronouns = r"[Hh]e|[Hh]is_|_[Hh]is|[Hh]im|[Hh]imself"
            you_pronouns = r"[Yy]ou_|_[Yy]ou|[Yy]our|[Yy]ours|[Yy]ourself"

            props_patterns = []
            for k in cls.common_verbs | cls.common_replacement_words | cls.inv_common_replacement_words:
                props_patterns.append(f'[{k[0].upper()}{k[0].lower()}]{k[1:]}')

            props_patterns = "|".join(props_patterns)
            not_period = r"(?<!\.)\b"
            optional_at = r"(@(\w+)?)?\b"  # any known pronoun will be derefed to the default if no ref given
            VERB_ = r"(\w+)@(\w+)?"  # verb _must_ have an @ to consider dereferencing
            PROP_ = not_period + "(" + props_patterns + r")@(\w+)?"
            HER_ = not_period + "(" + her_pronouns + ")" + optional_at
            HIM_ = not_period + "(" + him_pronouns + ")" + optional_at
            YOU_ = not_period + "(" + you_pronouns + ")" + optional_at

            VERB = re.compile(VERB_)
            PROP = re.compile(PROP_)
            HER = re.compile(HER_)
            HIM = re.compile(HIM_)
            YOU = re.compile(YOU_)

            def replace_pronoun(match, who=None):
                who = match.groups()[2] or who
                if not who:
                    raise KeyError(f"No subject for replacement {match}")
                return "{{ " + f"{who}.{match.groups()[0]}" + " }}"

            def replace_word(match, who=None):
                who = match.groups()[1] or who
                if not who:
                    raise KeyError(f"No subject for replacement {match}")
                return "{{ " + f"{who}.{match.groups()[0]}" + " }}"

            def replace_verb(match, who=None):
                who = match.groups()[1] or who
                if not who:
                    raise KeyError(f"No subject for replacement {match}")
                return "{{ " + f"{who}.verb('{match.groups()[0]}')" + " }}"

            cls._replacement_map = {
                PROP: lambda match: replace_word(match, who="b"),
                HER: lambda match: replace_pronoun(match, who="a"),
                HIM: lambda match: replace_pronoun(match, who="b"),
                YOU: lambda match: replace_pronoun(match, who="b"),
                VERB: lambda match: replace_verb(match, who="b")
            }
        return cls._replacement_map

    @classmethod
    def pre_render(cls, s: str, repl_map: dict = None, default_refs={'her': 'a', 'him': 'b'} ):

        repl_map = cls.replacement_map() | ( repl_map or {} )

        for k, v in repl_map.items():
            s = k.sub( v, s)
        return s

    @classmethod
    def _render(cls, s: str, **kwargs):
        # Convenience function for objects not inheriting from Renderable
        templ = jinja2.Environment().from_string( s )
        res = templ.render( **kwargs )
        return res

    def __repr__(self) -> str:
        s = f"{self.__class__.__name__}(gens={self.gens}, pronoun={self.pronoun})"
        return s



for k, v in Voice.common_verbs.items():
    setattr( Voice, k, property( functools.partial( Voice.verb, verb=v ) ) )
    setattr( Voice, k.capitalize(), property( functools.partial( Voice.verb, verb=v.capitalize() ) ) )

for k, v in (Voice.common_replacement_words | Voice.inv_common_replacement_words).items():
    setattr( Voice, k, property( functools.partial( Voice.replace_word, word=v ) ) )
    setattr( Voice, k.capitalize(), property( functools.partial( Voice.replace_word, word=v.capitalize() ) ) )

