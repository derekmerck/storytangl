from __future__ import annotations
import re
from typing import *
import functools
from collections import defaultdict

import attr
import jinja2

from tangl.actor.enums import Gens
from scratch.old.regex_voice.pronoun_old2 import Pronoun
from tangl.lang import LexRef
PT = Pronoun.PronounType


@attr.define( hash=True )
class Voice:
    """
    A Narrative Voice can convert pronouns, conjugate verbs, and make gender- or
    context-specific text substitutions in a text passage.  Voices are passed into
    the jinja template render and accessed with language like this:

    '{{ him.subject() }} {{ him.conjugate('puts') {{ his.possessive() }} coins into
     {{ her.possessive() }} hand.

    During rendering, 'him' and 'her', are passed through a _Voice_ filter that
    provides pronouns, common gendered word replacements such as Mr. -> Ms., and
    verb conjugation.

    The Voice class itself also implements a set of expansion macros that provide
    shortcuts for easy-to-read notation.  The same example phrase in simplified
    notation:

    'He puts his_ coins into her_ hand.'

    By default, feminine 3rd person pronouns (she/her) are mapped to a voice 'her',
    masculine 3rd person (he/him) and 2nd person (you) are mapped to a voice 'him'.
    Any pronoun or verb can be passed to a specific voice by appending @<voice> to
    it.  Affixing only '@' without a <voice> directs the class to attempt to infer
    a Voice at render-time.  A set of common verbs and pronouns is searched by default
    and only needs annotation if the inference fails.

    The benefit of using voice filters is that text passages can be easily updated
    to another point-of-view simply by altering the voices.  For example, swapping
    voice perspectives could change the output from the sample phrase to this:

    'You put your coins into his hand.'

    Simple and full notation can be mixed and matched as useful and reserved keywords
    with new behaviors can be added in subclasses.
    """

    pov: Pronoun = attr.ib( default="3", converter=Pronoun )
    gens: str = attr.ib( default="XX", converter=Gens )
    proper: str = None

    # Substitution Handlers

    @jinja2.pass_context
    def pronoun(self, ctx, which: str):
        match PT.type_of( which ):
            case PT.SUBJECTIVE:
                res = self.subject( ctx )
            case PT.OBJECTIVE | PT.OBJECTIVE_REFLEXIVE:
                res = self.object_( ctx )
            case PT.POSSESSIVE:
                res = self.possessive(ctx)
            case PT.POSSESSIVE_ADJECTIVE:
                res = self.possessive(ctx, adjective=True)
            case _:
                raise ValueError

        if which[0].isupper() and res[0].islower():  # Ignore if returning Capitalized Result
            res = res.capitalize()

        return res

    @jinja2.pass_context
    def subject(self, ctx, proper=True):
        ctx['enc']['subject'] = self
        ctx['enc']['prior_noun'] = self
        if self.pov is Pronoun.HER and proper and self.proper and self not in ctx['enc']['proper']:
            ctx['enc']['proper'].add( self )
            return self.proper
        return self.pov.subjective( self.gens )

    @jinja2.pass_context
    def object_(self, ctx, proper=True, reflexive=False):
        ctx['enc']['prior_noun'] = self
        if self.pov is Pronoun.HER and proper and self.proper and self not in ctx['enc']['proper']:
            ctx['enc']['proper'].add( self )
            return self.proper
        if ctx['enc']['subject'] == self:
            reflexive = True
        return self.pov.objective( self.gens, reflexive=reflexive )

    @jinja2.pass_context
    def possessive(self, ctx, proper=True, adjective=False):
        ctx['enc']['prior_noun'] = self
        if self.pov is Pronoun.HER and proper and self.proper and self not in ctx['enc']['proper']:
            ctx['enc']['proper'].add( self )
            return self.proper + "'s"
        return self.pov.possessive( self.gens, adjective=adjective )

    @jinja2.pass_context
    def conjugate(self, ctx, verb: str, gerund: bool = False):
        ctx['enc']['subject'] = self
        ctx['enc']['prior_noun'] = self
        res = LexRef.conjugate( verb, self.pov, gerund=gerund )
        return res

    @jinja2.pass_context
    def handle_substitution(self, ctx, word, *args, **kwargs):
        try:
            res = self.pronoun( ctx, word )
        except ValueError:
            res = self.conjugate( ctx, word )

        if word[0].isupper() and res[0].islower():  # Ignore if returning Capitalized Result
            res = res.capitalize()

        return res

    @classmethod
    @jinja2.pass_context
    def _infer_voice(cls, ctx, word, *args, **kwargs ):
        voice = ctx['enc']['prior_noun']  # type=Voice
        if not voice:
            raise ValueError("No prior noun referent set!")
        return voice.handle_substitution( ctx, word, *args, **kwargs )

    # Pre-rendering handlers

    @classmethod
    def _explicit_voice(cls, match, **voice_kwargs: dict[str, Voice]):
        # What got tagged?
        word = match[1]
        voice = None
        voice_name = None
        for k, v in voice_kwargs.items():
            if k.lower().startswith(match[2].lower()):
                voice_name = k
                voice = v
                break
        if not voice:
            raise KeyError(f"Unclear voice assignment for {match[2]} in {voice_kwargs.keys()}")
        return r"{{" + fr" {voice_name}.handle_substitution( '{word}' ) " + r"}}"

    @classmethod
    def _explicit_subject(cls, match):
        subj = match[1].lower()
        if match[1][0].isupper():
            return r"{{" + fr" {subj}.subject().capitalize() " + r"}}"
        return r"{{" + fr" {subj}.subject() " + r"}}"

    @classmethod
    def render(cls, s: str, **voice_kwargs ) -> str:
        templ = jinja2.Environment().from_string(s)
        templ.globals['enc'] = defaultdict( set )
        res = templ.render( **voice_kwargs, Voice=cls )
        return res

    # 20ish most common verbs
    _untagged_patterns: ClassVar[list[str]] = [
        "is", "am", "are",
        "have", "has",
        "do(es)?",
        "says?",
        "gets?",
        "makes?",
        "go(es)?",
        "knows?",
        "takes?",
        "sees?",
        "comes?",
        "thinks?",
        "looks?",
        "wants?",
        "gives?",
        "uses?",
        "finds?",
        "tells?",
        "asks?",
        "works?",
        "seems?",
        "feels?",
        "tr(y|ies)",
        "leaves?",
        "calls?",
        "likes?",
        "puts?",
        "begins?",
    ]

    @classmethod
    def preprocess( cls, s: str, default="him", **voice_kwargs ) -> str:

        repls = {
            r"(?<![@'])\b(i|you_|me|_you|myself|yourself|my|your|mine|yours)\b(?!\.\w|@)":
                r"{{" + fr" {default}.pronoun( '\1' )" + r"}}",
            r"(?<!['@])\b(he|him|himself|his_|_his)\b(?!\.\w|@)": r"{{ him.pronoun( '\1' ) }}",
            r"(?<!['@])\b(she|_her|herself|her_|hers)\b(?!\.\w|@)": r"{{ her.pronoun( '\1' ) }}",
            r'\b(\w+)@(\w+)\b': functools.partial( cls._explicit_voice, **voice_kwargs ),
            r'\b(\w+)@(?=\W)': r"{{ Voice._infer_voice( '\1' ) }}",
            r"(?<!')(?<!to )(?<!can )\b(" + r"|".join(cls._untagged_patterns) + r")\b(?!')":
                r"{{ Voice._infer_voice( '\1' ) }}",
        }
        explicit_voices = [k for k in voice_kwargs.keys() if k not in ['him', 'her']]
        if explicit_voices:
            repls[r"\b(" + r"|".join( explicit_voices ) + r")\b(?=[^\.\w])"] = cls._explicit_subject

        # print( r"\b(" + r"|".join( [k for k in voice_kwargs.keys() if k not in ['him', 'her']] ) + r")\b(?=[^\.\w])" )

        for pat, repl in repls.items():
            s = re.sub( pat, repl, s, flags=re.IGNORECASE )

        return s
