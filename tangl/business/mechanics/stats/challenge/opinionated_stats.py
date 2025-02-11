from enum import Enum

class Stat3(Enum):
    # A minimal stat framework, power is strength * leverage over time of endurance
    BODY   = "body"    # strength/health
    MIND   = "mind"    # leverage/cleverness
    WILL   = "will"    # endurance/spirit
    # consider hidden as average of body/mind
    # consider charm as average of mind/will

class Stat5(Enum):
    # Somewhat more nuanced, power may be applied at range and under various
    # conditions, like before opponents can act
    BODY   = "body"    # strength/health
    MIND   = "mind"    # leverage/cleverness
    WILL   = "will"    # endurance/spirit/light
    CHARM  = "charm"   # range/influence
    HIDDEN = "hidden"  # speed/cunning/dark
