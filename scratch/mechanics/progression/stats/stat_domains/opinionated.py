import typing as typ
from enum import Enum, auto

from tangl.utils.enum_utils import EnumUtils


class OpinionatedDomains( EnumUtils, Enum ):
    """Default domains for a simple progression system"""

    # Intrinsics
    BODY = auto()                 # stamina, fatigue
    MIND = auto()                 # wit, focus
    SPIRIT = auto()               # will, temper/stress
    CHARM = COMFORT = auto()      # lewd, heat
    PRESTIGE = PRINCESS = auto()  # influence/cash, presence
    CORRUPTION = CRIME = auto()   # hidden, peril

    FACE = BEAUTY = auto()        # composure, makeup

    ANY = auto()

    @classmethod
    def stat_currency(cls): return {
        cls.BODY:       "stamina",    # cost: fatigue
        cls.MIND:       "wit",        # cost: focus
        cls.SPIRIT:     "will",       # cost: temper, stress

        cls.CHARM:      "cheer",
        cls.COMFORT:    "heat",

        cls.PRESTIGE:   "influence",  # cost: cash, favors
        cls.PRINCESS:   "presence",

        cls.CRIME:      "hidden",     # cost: peril
        cls.CORRUPTION: "darkness",

        cls.BEAUTY:     "composure",

    }
    # Objects associated with a particular domain may try to use domain flavor text.

    @classmethod
    def actor_traits(cls): return {
        cls.BODY:       "healthy",
        cls.MIND:       "clever",
        cls.SPIRIT:     "faithful",

        cls.CHARM:      "friendly",
        cls.COMFORT:    "worldly",

        cls.PRESTIGE:   "influential",
        cls.PRINCESS:   "royal",

        cls.CRIME:      "cunning",
        cls.CORRUPTION: "foul",

        cls.BEAUTY:     "stunning"
    }

    @classmethod
    def asset_traits(cls): return {
        cls.BODY:       "tactical",
        cls.MIND:       "scholarly",
        cls.SPIRIT:     "ritual",

        cls.CHARM:      "familiar",
        cls.COMFORT:    "risque",

        cls.PRESTIGE:   "formal",
        cls.PRINCESS:   "elegant",

        cls.CRIME:      "discreet",
        cls.CORRUPTION: "cruel",

        cls.BEAUTY:     "fashionable"
    }

    @classmethod
    def asset_affiliations(cls): return {
        cls.BODY:       "earth",   # heavy
        cls.MIND:       "light",   # sharp
        cls.SPIRIT:     "wind",    # fast

        cls.CHARM:      "fire",    # hot
        cls.COMFORT:    "fire",    # alt hot

        cls.PRESTIGE:   "water",   # cold
        cls.PRINCESS:   "water",   # alt cold

        cls.CRIME:      "dark",    # hidden
        cls.CORRUPTION: "dark",    # alt hidden

        cls.BEAUTY:     None
    }

    @classmethod
    def create_currencies(cls):
        from tangl.mechanics.progression.stat_currency import StatCurrency
        for k, v in cls.stat_currency().items():
            StatCurrency(label=v, base_stat=k)

OpinionatedDomains.create_currencies()
