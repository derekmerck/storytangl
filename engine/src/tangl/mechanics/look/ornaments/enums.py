from enum import Enum, auto

# todo: should ornament type be AssetType and ornament be an asset-instance class
#       with a loc and specific description?

class OrnamentType(Enum):

    SCAR = auto()
    TATTOO = auto()
    PIERCING = auto()
    BRAND = auto()
    MARKER = auto()
    BURN = auto()
