from enum import Enum

class Stat3(Enum):
    # A minimal stat framework, power is strength * leverage over time of endurance
    BODY   = "body"    # strength/health
    MIND   = "mind"    # leverage/cleverness
    WILL   = "will"    # endurance/spirit
    # consider charm as average of mind/will
    # consider hidden as average of body/mind

class Stat5(Enum):
    # Somewhat more nuanced, power may be applied at range and under various
    # conditions, like before opponents can act
    BODY   = "body"    # strength/health, club
    MIND   = "mind"    # leverage/cleverness, lamp
    WILL   = "will"    # endurance/spirit/light
    CHARM  = "charm"   # range/influence, cup
    HIDDEN = "hidden"  # speed/cunning/dark, key

class Stat10(Enum):
    # Intrinsics
    BODY   = "body"    # strength/health
    MIND   = "mind"    # leverage/cleverness
    WILL   = "will"    # endurance/spirit/light
    CHARM  = "charm"   # range/influence
    HIDDEN = "hidden"  # speed/cunning/dark

    # Extrinsics
    LOOKS = "looks"            # body
    FIGHT = "fight"
    PRINCESS = "princess"      # charm/etiquette
    COMFORT = "comfort"        # charm/skill
    CORRUPTION = "corruption"  # hidden

    PRESTIGE = "prestige"      # background
