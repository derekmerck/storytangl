from __future__ import annotations
import itertools
from enum import Enum
from typing import TYPE_CHECKING

from .pov import PoV
from .gens import Gens, IsGendered

if TYPE_CHECKING:
    import jinja2


class Pronoun:
    """Standardized nomenclature for representing pronoun pov and type."""

    @classmethod
    def pov_of(cls, which: str) -> PoV:
        if not which:
            return
        match which.lower():
            case "i" | "me" | "myself" | "my" | "mine":
                return PoV._1s
            case "you" | "yourself" | "your" | "yours":
                return PoV._2s
            case "he" | "she" | "it" | "himself" | "herself" | "itself" | \
                 "his" | "her" | "hers" | "its" | "he;she;it" | "he/she/it":
                return PoV._3s
            case "we" | "us" | "ourselves" | "our" | "ours":
                return PoV._1p
            case "yall" | "yalls" | "yallselves":
                return PoV._2p
            case "they" | "them" | "themselves" | "their" | "theirs":
                return PoV._3p
        raise ValueError(f"Not a valid pronoun: {which}")

    @classmethod
    def gender_of(cls, which: str) -> Gens:
        if not which:
            return
        match which.lower():
            case "she" | "her" | "herself" | "hers":
                return Gens.XX
            case "he" | "him" | "himself" | "his":
                return Gens.XY
            case "it" | "its" | "itself":
                return Gens.X_
        raise ValueError(f"Not a valid pronoun: {which}")

    class PT(Enum):
        # Pronoun type
        S = 'subject'
        O = 'object'
        OR = 'object_reflexive'
        P = 'possessive'
        PA = 'possessive_adjective'

        @classmethod
        def _missing_(cls, value: str):
            for member in cls:
                if member.name.lower() == value.lower():
                    return member

    @classmethod
    def type_of(cls, which: str) -> Pronoun.PT:
        if not which:
            return
        match which.lower():
            case "i" | "you" | "he" | "she" | "it" | "we" | "yall" | "they":
                return Pronoun.PT.S
            case "me" | "_you" | "him" | "her" | "_it" | "us" | "_yall" | "them":
                return Pronoun.PT.O
            case "myself" | "yourself" | "himself" | "herself" | "ourselves" | "yallselves" | "themselves":
                return Pronoun.PT.OR
            case "my" | "your" | "his_" | "her_" | "our" | "yalls_" | "their":
                return Pronoun.PT.PA
            case "mine" | "yours" | "his" | "hers" | "ours" | "yalls" | "theirs":
                return Pronoun.PT.P
        raise ValueError(f"Not a valid pronoun: {which}")

    @classmethod
    def pov_and_type_of(cls, which: str) -> tuple[PoV, Pronoun.PT]:
        return cls.pov_of(which), cls.type_of(which)

    @classmethod
    def pronoun(cls, pt: PT, pov: PoV, gens: Gens):
        pt = Pronoun.PT(pt)
        match pt:
            case Pronoun.PT.S:
                return cls.subjective(pov, gens)
            case Pronoun.PT.O:
                return cls.objective(pov, gens)
            case Pronoun.PT.OR:
                return cls.objective(pov, gens, reflexive=True)
            case Pronoun.PT.P:
                return cls.possessive(pov, gens)
            case Pronoun.PT.PA:
                return cls.possessive(pov, gens, adjective=True)

    @classmethod
    def pronoun_map(cls):
        res = {}
        for pt, pov, gens in itertools.product( Pronoun.PT, PoV, reversed(Gens) ):
            res[ cls.pronoun(pt, pov, gens) ] = pt, pov, gens
        return res

    @classmethod
    def subjective(cls, pov: PoV, gens: Gens):
        pov = PoV(pov)
        gens = Gens(gens)
        match pov, gens:
            case PoV._1s, _:
                return "I"
            case PoV._2s, _:
                return "you"
            case PoV._3s, Gens.XY:
                return "he"
            case PoV._3s, Gens.X_:
                return "it"
            case PoV._3s, _:
                return "she"
            case PoV._1p, _:
                return "we"
            case PoV._2p, _:
                return "you"
            case PoV._3p, _:
                return "they"
        raise ValueError

    @classmethod
    def possessive(cls, pov: PoV, gens: Gens, adjective=False):
        pov = PoV(pov)
        gens = Gens(gens)
        if adjective:
            match pov, gens:
                case PoV._1s, _:
                    return "my"
                case PoV._2s, _:
                    return "your"
                case PoV._3s, Gens.XY:
                    return "his"
                case PoV._3s, Gens.X_:
                    return "its"
                case PoV._3s, _:
                    return "her"
                case PoV._1p, _:
                    return "our"
                case PoV._2p, _:
                    return "your"
                case PoV._3p, _:
                    return "their"

        match pov, gens:
            case PoV._1s, _:
                return "mine"
            case PoV._2s, _:
                return "yours"
            case PoV._3s, Gens.XY:
                return "his"
            case PoV._3s, Gens.X_:
                return "its"
            case PoV._3s, _:
                return "hers"
            case PoV._1p, _:
                return "ours"
            case PoV._2p, _:
                return "yours"
            case PoV._3p, _:
                return "theirs"

        raise ValueError

    @classmethod
    def objective(cls, pov: PoV, gens: Gens, reflexive=False):
        pov = PoV(pov)
        gens = Gens(gens)
        if reflexive:
            match pov, gens:
                case PoV._1s, _:
                    return "myself"
                case PoV._2s, _:
                    return "yourself"
                case PoV._3s, Gens.XY:
                    return "himself"
                case PoV._3s, Gens.X_:
                    return "itself"
                case PoV._3s, _:
                    return "herself"
                case PoV._1p, _:
                    return "ourselves"
                case PoV._2p, _:
                    return "yourselves"
                case PoV._3p, _:
                    return "themselves"

        match pov, gens:
            case PoV._1s, _:
                return "me"
            case PoV._2s, _:
                return "you"
            case PoV._3s, Gens.XY:
                return "him"
            case PoV._3s, Gens.X_:
                return "it"
            case PoV._3s, _:
                return "her"
            case PoV._1p, _:
                return "us"
            case PoV._2p, _:
                return "you"
            case PoV._3p, _:
                return "them"

        raise ValueError

    @classmethod
    def register_pronoun_filters(cls, env: jinja2.Environment):
        """
        Provides jinja filters like {{ ref | her }} and {{ ref | Her }}
        for IsGendered refs.
        """

        def get_func(pt: PT, pov: PoV, cap: bool = False):

            def get_pronoun_for(obj: IsGendered):
                gens = Gens.XX if obj.is_xx else Gens.XY
                pronoun = Pronoun.pronoun(pt, pov, gens)
                if cap:
                    pronoun = pronoun.capitalize()
                return pronoun

            return get_pronoun_for

        all_pronoun_params = itertools.product(PT, PoV, Gens)

        for pt, pov, gens in all_pronoun_params:
            s = cls.pronoun(pt, pov, gens)
            s_cap = s.capitalize()
            if pt is PT.O and s in ["you", "it", "yall"]:
                s = "_" + s
                s_cap = "_" + s_cap
            if pt is PT.PA and s in ["his", "her", "yalls"]:
                s = s + "_"
                s_cap = s_cap + "_"
            if s not in env.filters:
                env.filters[s] = get_func(pt, pov)
                env.filters[s_cap] = get_func(pt, pov, cap=True)


# Useful aliases
PT = Pronoun.PT
