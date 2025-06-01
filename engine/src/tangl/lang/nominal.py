from __future__ import annotations
from random import choice, random
from enum import Enum, auto
from typing import Optional, ClassVar

from pydantic import BaseModel, field_validator, Field, ValidationInfo

from .helpers.pattern import is_plural

class DeterminativeType(Enum):

    INDEFINITE = IDET = auto()     # a/n
    DEFINITE   = DDET = auto()     # the
    POSSESSIVE = PPDET = auto()    # his/hers
    DEMONSTRATIVE = auto()         # this/these, that/those

    @classmethod
    def use_an(cls, value: str = None):
        if not value:
            return False
        if value[0] in 'aieouy':
            return True
        if any( value.startswith(x) for x in ['hour', 'honest', 'honor'] ):
            return True
        return False

    @classmethod
    def get_det(cls, dt: DT, plural=False, next_word: str = None, is_xx=True):
        match dt, plural:

            case DT.IDET, False if cls.use_an(next_word):
                return "an"
            case DT.IDET, False:
                return "a"       # a pair of blue pants
            case DT.IDET, True:
                return "some"    # some blue pants

            case DT.DDET, _:
                return "the"     # the blue pants, the pair of blue pants

            case DT.PPDET, _ if is_xx:
                return "her"     # her blue pants, her pair of blue pants
            case DT.PPDET, _:
                return "his"

            case DT.DEMONSTRATIVE, False:
                return "this"    # or that, this pair of blue pants
            case DT.DEMONSTRATIVE, True:
                return "these"   # or those, these blue pants

DT = DeterminativeType

class DetHandler:
    # todo: could make these class methods to match other handler patterns

    @classmethod
    def get_quantifier(cls, nominal: Nominal) -> Optional[str]:
        # For now, let's assume:
        # - plural Nominals are countable and can be qualified
        # - all qualifiers change plurality of the phrase to singular
        # - quantifiers are optional with a 50% probability
        if not nominal.plural or not nominal.quantifiers or random() < 0.5:
            return
        if len( nominal.quantifiers ) == 1:
            return nominal.quantifiers[0]
        return choice( nominal.quantifiers )

    @classmethod
    def get_det(cls, nominal: Nominal, dt: DT, np: str = None, is_xx: bool = True):
        """
        May return an article (a/n, the) or pronoun, optionally followed by an quantifier.
        """
        # if it's not plural, we don't need to worry about a quant
        if not nominal.plural:
            return DT.get_det( dt, plural=False, next_word=np, is_xx=is_xx )

        # otherwise we have to figure out if we want to use a quantifier and if
        # that changes the plurality of the noun.
        quant = cls.get_quantifier(nominal)
        if quant:
            # new next word, assume always singular now
            det = DT.get_det( dt, plural=False, next_word=quant, is_xx=is_xx )
            return f"{det} {quant}"

        return DT.get_det( dt, plural=True, next_word=np, is_xx=is_xx )

    @classmethod
    def determinative(cls, nominal: Nominal, dt: DT, np: str = None, is_xx: bool = True):
        det = cls.get_det( nominal, dt, np, is_xx )
        res = f"{det} {np}"
        # todo: also need to report plurality of returned determinative nominal
        return res

class Nominal(BaseModel):
    """
    >>> pants = Nominal(
    ...  nouns = [ 'pants', 'trousers' ],
    ...  plural = True,
    ...  adjective_groups = [ { 'blue' } ]
    ...  quantifiers = [ 'pair of' ] )

    >>> pants.idet()
    "a pair of blue pants"    # This pattern is IDET/s QUANT/s ADJ NN
    "some blue pants"         # This pattern is IDET/p ADJ NN

    >>> pants.ddet()
    "the pair of blue pants"  # This pattern is DDET ADJ NN
    "the blue pants"          # This pattern is DDET ADJ NN

    >>> pants.ppdet( is_xx=True )
    "her pair of blue pants"  # This pattern is PDET/f QUANT/s AJD NN
    "her blue pants"          # This pattern is PDET/f ADJ NN
    """

    nouns: list[str] = Field( default_factory=list )
    adjectives: list[str] = Field( default_factory=list )             #: default adjectives (blue, soft)
    adjective_groups: list[set[str]] = Field( default_factory=list )  #: groups of adjective synonyms [{damp, moist}, ... ]
    plural: bool = Field(None, validate_default=True)

    @field_validator('plural', mode='before')
    @classmethod
    def _determine_plurality(cls, data, info: ValidationInfo):
        if data is None:
            noun = info.data['nouns'][0]
            return is_plural(noun)
        return data

    quantifiers: list[str] = Field( default_factory=list )

    def get_adjective(self, tags: list[str]):
        # look for something specific
        tags = tags or []
        for tag in tags:
            for group in self.adjective_groups:
                if tag in group:
                    return choice(list(group))

        # fall back on a default
        if self.adjectives:
            if len(self.adjectives) == 1:
                return self.adjectives[0]
            return choice(self.adjectives)

        return ""

    def get_bare_noun_phrase(self, tags: list[str] = None ):
        noun_phrase = choice(list(self.nouns))
        adjective = self.get_adjective(tags)
        if adjective:
            noun_phrase = f"{adjective} {noun_phrase}"
        # assumes np keeps base plurality
        return noun_phrase
    np = get_bare_noun_phrase

    # Delegate determinative forms to handler
    det_handler: ClassVar[type[DetHandler]] = DetHandler

    def determinative(self, dt: DT, tags: list[str] = None, is_xx = True):
        np = self.get_bare_noun_phrase( tags )
        return self.det_handler.determinative( self, dt, np, is_xx )

    def idet(self, tags: list[str] = None, **kwargs ):
        return self.determinative( DT.INDEFINITE, tags )

    def ddet(self, tags: list[str] = None, **kwargs ):
        return self.determinative( DT.DEFINITE, tags )

    def ppdet(self, tags: list[str] = None, is_xx = True, **kwargs):
        return self.determinative(DT.POSSESSIVE, tags, is_xx=is_xx)

    def demonstrative(self, tags: list[str] = None, **kwargs):
        return self.determinative(DT.DEMONSTRATIVE, tags)
