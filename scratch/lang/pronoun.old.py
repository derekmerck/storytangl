
from enum import Enum

from tangl.utils.enum_plus import EnumPlusMixin
from tangl.narrative.lang.gens import Gens

class Pronoun(EnumPlusMixin, Enum):

    I = "i"
    YOU = "you"
    SHE = "she"
    WE = "we"
    YALL = "yall"
    THEY = "they"

    __aliases__ = {
        I:    ["1",  "first", "i"],
        YOU:  ["2",  "second", "you"],
        SHE:  ["3",  "third", "he;she;it", "he", "she", "it"],
        WE:   ["1+", "first_plural", "we"],
        YALL: ["2+", "second_plural", "yall"],
        THEY: ["3+", "third_plural", "they"]
    }

    def short_key(self) -> str:
        if self is self.YALL:
            return "2"  # There isn't a "yall" in the conjugate dictionary
        return self.__aliases__[self.value][0]

    def subjective( self, gens, **kwargs ):
        match ( self, gens ):
            case ( Pronoun.I, _ ):
                return "I"
            case ( Pronoun.YOU, _ ):
                return "you"
            case ( Pronoun.SHE, Gens.XY ):
                return "he"
            case ( Pronoun.SHE, Gens.X_ ):
                return "it"
            case ( Pronoun.SHE, _ ):
                return "she"
            case ( Pronoun.WE, _ ):
                return "we"
            case ( Pronoun.YALL, _ ):
                return "yall"
            case ( Pronoun.THEY, _ ):
                return "they"

    def objective( self, gens, refl: bool = False, **kwargs ):
        if refl:
            return self.objective_reflexive( gens, **kwargs )
        match ( self, gens ):
            case ( Pronoun.I, _ ):
                return "me"
            case ( Pronoun.YOU, _ ):
                return "you"
            case ( Pronoun.SHE, Gens.XY ):
                return "him"
            case ( Pronoun.SHE, Gens.X_ ):
                return "it"
            case ( Pronoun.SHE, _ ):
                return "her"
            case ( Pronoun.WE, _ ):
                return "us"
            case ( Pronoun.YALL, _ ):
                return "yall"
            case ( Pronoun.THEY, _ ):
                return "them"

    def objective_reflexive( self, gens, **kwargs ):
        match ( self, gens ):
            case ( Pronoun.I, _ ):
                return "myself"
            case ( Pronoun.YOU, _ ):
                return "yourself"
            case ( Pronoun.SHE, Gens.XY ):
                return "himself"
            case ( Pronoun.SHE, Gens.X_ ):
                return "itself"
            case ( Pronoun.SHE, _ ):
                return "herself"
            case ( Pronoun.WE, _ ):
                return "ourselves"
            case ( Pronoun.YALL, _ ):
                return "yallselves"
            case ( Pronoun.THEY, _ ):
                return "themselves"

    def possessive( self, gens, **kwargs ):
        match ( self, gens ):
            case ( Pronoun.I, _ ):
                return "mine"
            case ( Pronoun.YOU, _ ):
                return "yours"
            case ( Pronoun.SHE, Gens.XY ):
                return "his"
            case ( Pronoun.SHE, Gens.X_ ):
                return "its"
            case ( Pronoun.SHE, _ ):
                return "hers"
            case ( Pronoun.WE, _ ):
                return "ours"
            case ( Pronoun.YALL, _ ):
                return "yalls"
            case ( Pronoun.THEY, _ ):
                return "theirs"

    def possessive_adjective( self, gens, **kwargs ):
        match ( self, gens ):
            case ( Pronoun.I, _ ):
                return "my"
            case ( Pronoun.YOU, _ ):
                return "your"
            case ( Pronoun.SHE, Gens.XY ):
                return "his"
            case ( Pronoun.SHE, Gens.X_ ):
                return "its"
            case ( Pronoun.SHE, _ ):
                return "her"
            case ( Pronoun.WE, _ ):
                return "our"
            case ( Pronoun.YALL, _ ):
                return "yalls"
            case ( Pronoun.THEY, _ ):
                return "their"
