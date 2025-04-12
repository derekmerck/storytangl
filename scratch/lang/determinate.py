"""
Determiners are composed of two components:
- the article (a, the, these, her, etc.)
- a quantifier (many, pair of, etc.)

Common quantifiers are provided in the definition of a nominal phrase.
"""
from __future__ import annotations

import yaml
from enum import Enum, auto

# language=YAML
quantifiers_data_ = """
either:        # -- No determiner --
  - some       # some books, some water
  - any        # any books, any water
  - enough     # enough books, enough water
  - lots of    # lots of books, lots of water
  - plenty of  # plenty of books, plenty of water
  - bottle of  # bottle of books (legit but makes no sense), bottle of water

either_s:      # -- Any determiner -- (the lack of books, a lack of water)
  - lack of    # a lack of books, a lack of water

uncountable:   # -- Only indefinite determiner -- (not his little water)
  - little     # a little water
  - bit of     # a bit of water

countable:     # -- Any determiner -- (a, the, his, this/these pair of...)
  - pair of    # a pair of pants, the pair of pants
  - lot of     # a lot of pants
  - few        # a few books

countable_pl:  # -- Not indefinite determiner --- (not a many books, but these several books ok)
  - many       # many books
  - several    # several books
"""

quantifiers_data = yaml.safe_load( quantifiers_data_ )
quantifiers_map = {vv: k for k, v in quantifiers_data.item() for vv in v}


class QuantifierType(Enum):
    """
    Quantifiers can be used for both countable and uncountable nouns.

    Uncountable quantifiers usually convert the subordinate noun phrase to
    plural, if it's not already, and don't get an additional article, like
    "some pants" or "some water"

    Countable quantifiers usually convert the subordinate noun phrase to
    singular if it's not already, and get an additional article, like
    "the pair of pants" or "a lot of water"
    """

    EITHER = auto()  # forces plural, disallows determinate
    EITHER_S = auto()  # forces singular, requires any determinate
    UNCOUNTABLE = auto()  # forces singular, requires indefinite determinate
    COUNTABLE = auto()  # forces singular, requires any determinate
    COUNTABLE_P = auto()  # forces plural,  forbids indefinite determinate

    @classmethod
    def quantifier_for(cls, value):
        if value in quantifiers_map:
            return QT( quantifiers_map[value] )

QT = QuantifierType

class DeterminerType(Enum):

    DIRECT = auto()         # blue pants, some blue pants, some walnuts, no article, no quant
    INDEFINITE = auto()     # a pair of blue pants, a bunch of walnuts, a + quant if quant
    DEFINITE = auto()       # the blue pants, the pair of blue pants, the walnuts, the + optional quant
    POSSESSIVE = auto()     # his blue pants, his pair of blue pants, his walnuts, his + optional quant
    DEMONSTRATIVE = auto()  # these blue pants, this pair of blue pants, this bunch of walnuts, these walnuts

    # this + single or this + quant + plural or these + plural

    def article(cls,
                dt: DeterminerType,
                noun_phrase: str,
                plural: bool = False):
        match dt:
            case DT.DIRECT:
                return ""
            case DT.INDEFINITE if noun_phrase[0].lower() in ['aeiouy']:
                return "an"
            case DT.INDEFINITE:
                return "a"
            case DT.DEFINITE:
                return "the"
            case DT.POSSESSIVE:
                return "their"  # todo: select appropriate pronoun
            case DT.DEMONSTRATIVE if plural:
                return "these"
            case DT.DEMONSTRATIVE:
                return "this"
        raise ValueError

    @classmethod
    def determinate(cls,
                    dt: DeterminerType,
                    noun_phrase: str,
                    plural: False,
                    quantifiers: list[str] = None) -> tuple[str, str, str]:
        """
        Accepts a noun phrase, plural flag, and optional list of quantifiers
        Returns an article (singular) or quantified article (plural), the noun phrase,
        and the updated plurality flag for the determinative form.

        Usage:

        >> determinative( INDEFINITE, "blue pants", plural=True, quantifiers=['pair of']
        a, pair of blue pants, singular
        >> determinative( DEMONSTRATIVE, "blue pants", plural=True)
        these, blue pants, plural

        _noun_phrase_ includes adj like "blue pants", we just need the first letter for a/an for
        the indefinite form.

        _quantifiers_ are optional for plurals or singular uncountables, but will be used if provided.
        If required but not provided, it just defaults to "some".

        For example,

        >> determinative( INDEFINITE, "blue pants", True )
        some, blue pants, plural

        but

        >> determinative( INDEFINITE, "blue pants", True, [ 'pair of' ] )
        a pair of, blue pants, singular

        """
        pass

DT = DeterminerType
