from __future__ import annotations
from typing import *
import random
import functools

import attr

from lang import Pronoun, Gens, ParseTree
from utils import attrs_cast as cast



@attr.define( hash=True )
class Word:

    _synonyms: list[str] = attr.ib( default="<NONE>", converter=lambda x: cast(list, x), hash=False )

    def render(self, **kwargs):
        return random.choice( self._synonyms )

    @classmethod
    def expand(cls, *words, ctx: dict = None):

        _words = []
        ctx = ctx or { 'proper': set(),
                       'subject': None,
                       'prior_noun': None,
                       'words': _words }

        for word in words:

            if not word:
                continue

            if isinstance( word, Callable ):
                word = word( ctx=ctx )

            if isinstance( word, tuple ):
                word = cls.expand( *word, ctx=ctx )
                _words += word
            else:
                # update determiner if necessary
                if _words and _words[-1] == "a" and word[0].lower() in "aeiouy":
                    _words[-1] = "an"
                _words.append( word )

        return _words

    @classmethod
    def render(cls, *words):
        _words = cls.expand( words )
        _words = [str(word) for word in _words if word]
        res = " ".join( _words )
        return res

@attr.define( hash=True )
class Noun(Word):

    pov: Pronoun.PoV = attr.ib( default=Pronoun.PoV._3, converter=Pronoun.PoV )  # singular (_3) or plural (_3s)
    gens: Gens = attr.ib( default=None, converter=lambda x: cast(Gens, x) )
    definite: bool = True
    proper: str = None
    owner: Voice = attr.ib( default=None, hash=False )
    friends: dict[str, Word] = attr.ib( factory=dict, hash=False )

    @property
    def _obj_pronoun(self):
        if not self.gens:
            return "it"
        return Pronoun.pronoun( Pronoun.PT.O, self.pov, self.gens )

    def determiner(self, ctx: dict = None):
        if self.owner:
            return self.owner.possessive(adjective=True, ctx=ctx)
        elif self.definite:
            return "the"
        else:
            return "a"

    def possessive(self, adjective=False, ctx: dict = None):
        if adjective:
            pt = Pronoun.PT.PA
        else:
            pt = Pronoun.PT.P
        is_referent = ctx.get( ('prior_noun', self._obj_pronoun) ) == self or ctx['subject'] == self
        ctx['prior_noun', self._obj_pronoun] = self
        if self.pov in [Pronoun.PoV._3]:
            if self.proper and self not in ctx['proper']:
                ctx['proper'].add( self )
                return self.proper + "'s"
            elif is_referent:
                return Pronoun.pronoun( pt, self.pov, self.gens )
            return self.determiner, str( self ) + "'s"

        return Pronoun.pronoun( pt, self.pov, self.gens)

    possessive_adjective = functools.partial( possessive, adjective=True )

    adjective: Word = attr.ib( default=None, converter=lambda x: cast(Word, x))

    def subject(self, ctx: dict = None, **kwargs):
        is_referent = ctx.get( ('prior_noun', self._obj_pronoun) ) == self or ctx['subject'] == self
        ctx['subject'] = self
        ctx['prior_noun', self._obj_pronoun] = self

        if self.pov in [Pronoun.PoV._3]:
            if self.proper and self not in ctx['proper']:
                ctx['proper'].add( self )
                return self.proper
            elif is_referent:
                return Pronoun.pronoun(Pronoun.PT.S, self.pov, self.gens)
            else:
                return self.determiner, self.adjective, str( self )

        return Pronoun.pronoun(Pronoun.PT.S, self.pov, self.gens)

    def object(self, proper: bool = True, ctx: dict = None, **kwargs):
        if ctx['subject'] == self:
            pt = Pronoun.PT.OR
        else:
            pt = Pronoun.PT.O
        is_referent = ctx.get( ('prior_noun', self._obj_pronoun) ) == self or ctx['subject'] == self
        ctx['prior_noun', self._obj_pronoun] = self
        if self.pov in [Pronoun.PoV._3]:
            if proper and self.proper and self not in ctx['proper']:
                ctx['proper'].add( self )
                return self.proper
            elif is_referent:
                return Pronoun.pronoun( pt, self.pov, self.gens )
            else:
                return self.determiner, self.adjective, str( self )

        return Pronoun.pronoun( pt, self.pov, self.gens )


@attr.define( hash=True )
class Voice(Noun):

    part: Noun = attr.ib( default="part", converter=lambda x: cast(Noun, x) )
    adverb: Word = attr.ib( default="happily", converter=lambda x: cast(Word, x) )

    def __attrs_post_init__(self):
        if self.part:
            self.part.owner = self

    def complement(self):
        return "with", self.possessive, self.part


@attr.define( hash=True )
class Action:

    verb: Word = attr.ib( default="eats", converter=lambda x: cast(Word, x) )
    prep: str = None

    inv_verb: str = attr.ib( default="feeds", converter=lambda x: cast(Word, x) )
    inv_prep: str = "to"

    def direct(self, subject_pov: Pronoun.PoV):
        return self.conjugate( str(self.verb), subject_pov )

    def passive(self, subject_pov: Pronoun.PoV):
        helper = self.conjugate( "is", subject_pov )
        verb = str( self.verb ) + "ed"
        return helper, verb

    def inverse(self, subject_pov: Pronoun.PoV):
        return self.conjugate( str(self.inv_verb), subject_pov )

    def inverse_passive(self, subject_pov: Pronoun.PoV):
        helper = self.conjugate( "is", subject_pov )
        verb = str( self.inv_verb ) + "ed"
        return helper, verb

    @classmethod
    def conjugate(cls, verb: str, subject_pov: Pronoun.PoV ):
        return verb


@attr.define( hash=True )
class Context:

    him: Voice = attr.ib( converter=lambda x: cast(Voice, x) )
    her: Voice = attr.ib( converter=lambda x: cast(Voice, x) )
    action: Action = attr.ib( converter=lambda x: cast(Action, x) )

    def rephrase(self, templ=ParseTree):
        pass



    def _structure(self, case: int = 1) -> list[Callable | str]:
        """
        6 Cases
        --------
        direct, top
          - (He/his_ mouth) eats (_her/her_ sandwich) (with (his mouth))?
        inv on him, top
          - (He) feeds (himself/his_mouth) with (_her/her_ sandwich)
        inv passive, bottom
          - (He/His_ mouth) is fed with (_her/her_ sandwich)

        inv, bottom
          - (She) feeds (herself/her_ sandwich) to (him/his_ mouth)
        direct on her, bottom
          - (She) eats (herself / her_ sandwich) with (him/his_ mouth)
        direct passive, top
          - (She/Her_ sandwich) is eaten with (him/his_ mouth)
        """

        res = None
        match case:
            case 1:
                res = [ self.him.subject,
                        self.him.adverb,
                        self.action.direct( self.him.pov ),
                        self.action.prep,
                        self.her.part.object,
                        "with",
                        self.him.part.object]

            case 2:
                res = [ self.him.subject,
                        self.him.adverb,
                        self.action.inverse( self.him.pov ),
                        self.him.part.object,
                        "with",
                        self.her.part.object ]

            case 3:
                res = [ self.him.part.subject,
                        # self.object.adverb,
                        self.action.inverse_passive( self.him.part.pov ),
                        "with",
                        self.her.part.object ]

            case 4:
                res = [ self.her.subject,
                        self.her.adverb,
                        self.action.inverse( self.her.pov ),
                        self.her.part.object,
                        self.action.inv_prep,
                        self.him.part.object ]

            case 5:
                res = [ self.her.subject,
                        self.her.adverb,
                        self.action.direct( self.her.pov ),
                        self.her.part.object,
                        "with",
                        self.him.part.object ]

            case 6:
                res = [ self.her.part.subject,
                        # self.subject.adverb,
                        self.action.passive(self.her.part.pov),
                        "with",
                        self.him.part.object ]

        res = [ self.him.subject, Action.conjugate("moans", self.him.pov), "as" ] + res

        return res
