from typing import *

from aenum import Enum
import yaml

from tangl.utils.dyn_enum import DynamicEnumMeta


# language=YAML
pronoun_spec_ = """
---
me:
  pov: '1'
  subj: I
  obj: me
  obj_refl: myself
  poss_adj: my
  poss: mine
you:  [ '2', you, you, yourself, your, yours ]
her:  [ '3', she/he, her/him, herself/himself, her/his, hers/his ]
us:   [ '1+', we, us, ourselves, our, ours ]
yall: [ '2+', yall, yall, yallselves, yalls, yalls ]
they: [ '3+', they, them, themselves, their, theirs ]
"""

pronoun_spec = yaml.safe_load(pronoun_spec_)  # type: dict

# Pronouns1 = DynamicEnumMeta('Pronouns1', (), {"_fields": ('pov', 'subj', 'obj'), "_values": pronoun_spec})

class Pronoun(metaclass=DynamicEnumMeta, module=__name__):

    _fields = ('pov', 'subj', 'obj', 'obj_refl', 'poss_adj', 'poss')
    _values = pronoun_spec

    __aliases__: ClassVar[dict] = {
        "her": ["he;she;it", "she"],
    }

    class PronounType(Enum):
        SUBJECTIVE = "subjective"
        OBJECTIVE = "objective"
        OBJECTIVE_REFLEXIVE = "objective_reflexive"
        POSSESSIVE = "possessive"
        POSSESSIVE_ADJECTIVE = "possessive_adjective"

        @classmethod
        def type_of(cls, which: str) -> 'PronounType':
            match which.lower():
                case "i" | "you_" | "he" | "she" | "we" | "yall_" | "they":
                    return cls.SUBJECTIVE
                case "me" | "_you" | "him" | "_her" | "us" | "_yall" | "them":
                    return cls.OBJECTIVE
                case "myself" | "yourself" | "himself" | "herself" | "ourselves" | "yallselves" | "themselves":
                    return cls.OBJECTIVE_REFLEXIVE
                case "my" | "your" | "his_" | "her_" | "our" | "yalls_" | "their":
                    return cls.POSSESSIVE_ADJECTIVE
                case "mine" | "yours" | "_his" | "hers" | "ours" | "_yalls" | "theirs":
                    return cls.POSSESSIVE
            raise ValueError

    def subjective(self, gender: str | Enum = None) -> str:
        if hasattr( gender, "value" ):
            gender = gender.value.lower()
        if self is Pronoun.HER:
            if gender in ["xy"]:
                return self.subj.split("/")[1]
            return self.subj.split("/")[0]
        return self.subj

    def objective(self, gender: str | Enum = None, reflexive: bool = False) -> str:
        if hasattr( gender, "value" ):
            gender = gender.value.lower()
        if reflexive:
            if self is Pronoun.HER:
                if gender in ["xy"]:
                    return self.obj_refl.split("/")[1]
                return self.obj_refl.split("/")[0]
            return self.obj_refl

        if self is Pronoun.HER:
            if gender in ["xy"]:
                return self.obj.split("/")[1]
            return self.obj.split("/")[0]
        return self.obj

    def possessive(self, gender: str | Enum = None, adjective: bool = False) -> str:
        if hasattr( gender, "value" ):
            gender = gender.value.lower()
        if adjective:
            if self is Pronoun.HER:
                if gender in ["xy"]:
                    return self.poss_adj.split("/")[1]
                return self.poss_adj.split("/")[0]
            return self.poss_adj

        if self is Pronoun.HER:
            if gender in ["xy"]:
                return self.poss.split("/")[1]
            return self.poss.split("/")[0]
        return self.poss

    def transform_pronoun(self, which: str, gender: Enum | str) -> str:
        PT = Pronoun.PronounType
        match PT.type_of( which ):
            case PT.SUBJECTIVE:
                return self.subjective(gender)
            case PT.OBJECTIVE:
                return self.objective(gender)
            case PT.OBJECTIVE_REFLEXIVE:
                return self.objective(gender, reflexive=True)
            case PT.POSSESSIVE:
                return self.possessive(gender)
            case PT.POSSESSIVE_ADJECTIVE:
                return self.possessive(gender, adjective=True)
        raise ValueError( which )
