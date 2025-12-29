from enum import Enum

import attr

from tangl.story.asset import Asset
from tangl.world.narrator.lang import RefLex, Pronoun, PoV, Gens
from tangl.world.narrator.prereader.treebank_symbols import TreeBankSymbols as TBS

from tangl.utils.cast_collection import wrap_cast_to as cast_to
from .eurynym import Eurynym

@attr.define
class Voice:

    name: str = "tangldev"
    surname: str = "v211"
    @property
    def full_name(self):
        return f"{self.name} {self.surname}"

    def proper(self):
        return self.name

    aliases: list[str] = attr.ib( factory=list )

    pov: PoV = attr.ib( default=PoV._3s, converter=PoV )
    gens: Gens = attr.ib( default=Gens.XY,
                          converter=Gens,
                          validator=attr.validators.instance_of(Gens))
    # vocabulary: dict[str, Word] = None
    assets: dict[str, Asset] = None

    def render_verb(self, word: Eurynym):
        if word.plural:
            pov = self.pov.plural()
        else:
            pov = self.pov
        return RefLex.conjugate(word.lemma, pov)

    def render_pronoun(self, word: Eurynym):
        if word.plural:
            pov = self.pov.plural()
        else:
            pov = self.pov
        return Pronoun.pronoun(word.pt, pov, self.gens)

    def render_word(self, word: Eurynym, ctx: dict):
        if word.symbol.is_verb():
            return self.render_verb(word)
        elif word.symbol == TBS.PRP5:
            return self.render_pronoun(word)
        elif word.symbol == TBS.NNP:
            return self.proper()
        elif word.symbol.is_noun():
            return self.render_pronoun(word)
            # todo: this should be proper() and sometimes pronoun
        return word.text

    def described_by(self, tag: str | Enum ):
        pass

    @attr.define
    class AdoptionRules:
        aliases: list = attr.ib( factory=list )
        povs: list = attr.ib( factory=list, converter=cast_to(list[PoV]) )
        gens: list = attr.ib( factory=list, converter=cast_to(list[Gens]))

        def adopts_word(self, word: Eurynym, **kwargs) -> bool:
            """Test word for adoption, kwargs for extra rules, exclusions"""
            if word.ner == "S-PERSON" and word.text in self.aliases:
                return True
            elif word.pov in self.povs:
                return True
            elif word.gens in self.gens:
                return True

            # print( f"ignoring {word.text}, {word.pov}")

            return False

    adopts: AdoptionRules = attr.ib( factory=dict, converter=cast_to(AdoptionRules) )
    #: Rules for word adoption
