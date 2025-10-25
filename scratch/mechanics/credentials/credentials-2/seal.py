from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Flag, auto, Enum

from tangl.utils.enum_utils import EnumUtils

from .enums import Region, Indication
if TYPE_CHECKING:
    from .credential import CS

# todo: this could also be implemented as singletons for more flexibility?

class Seal(EnumUtils, Enum):
    # Various legitimizing or fake seals for credentials
    LOCAL = auto()

    LOCAL_TRAVEL = auto()
    LOCAL_WORK = auto()
    LOCAL_EMIGRATION = auto()

    LOCAL_WEAPONS = auto()
    LOCAL_DRUGS = auto()
    LOCAL_SECRETS = auto()

    FOREIGN_EAST = auto()
    FOREIGN_EAST_SECRETS = auto()

    FOREIGN_WEST = auto()
    FOREIGN_WEST_SECRETS = auto()

    # errors
    NONE = auto()
    FAKE_LOCAL = auto()
    FAKE_FOREIGN_EAST = auto()
    FAKE_FOREIGN_WEST = auto()

    @classmethod
    def type_for(cls,
                 region: Region,
                 indication: Indication,
                 credential_status: CS) -> Seal:
        from .credential import CS
        # which seal to use for a given region and indication, both legitimate and invalid
        match region, indication, credential_status:
            case _, _, CS.MISSING_SEAL:
                return Seal.NONE
            case Region.LOCAL, _, CS.BAD_SEAL:
                return Seal.FAKE_LOCAL
            case Region.LOCAL, Indication.TRAVEL, _:
                return Seal.LOCAL_TRAVEL
            case Region.LOCAL, Indication.WORK, _:
                return Seal.LOCAL_WORK
            case Region.LOCAL, Indication.EMIGRATE, _:
                return Seal.LOCAL_EMIGRATION
            case Region.LOCAL, Indication.WEAPON, _:
                return Seal.LOCAL_WEAPONS
            case Region.LOCAL, Indication.DRUGS, _:
                return Seal.LOCAL_DRUGS
            case Region.LOCAL, Indication.SECRETS, _:
                return Seal.LOCAL_SECRETS
            case Region.LOCAL, _, _:
                return Seal.LOCAL

            case Region.FOREIGN_EAST, _, CS.BAD_SEAL:
                return Seal.FAKE_FOREIGN_EAST
            case Region.FOREIGN_EAST, Indication.SECRETS, _:
                return Seal.FOREIGN_EAST_SECRETS
            case Region.FOREIGN_EAST, _, _:
                return Seal.FOREIGN_EAST

            case Region.FOREIGN_WEST, _, CS.BAD_SEAL:
                return Seal.FAKE_FOREIGN_WEST
            case Region.FOREIGN_WEST, Indication.SECRETS, _:
                return Seal.FOREIGN_WEST_SECRETS
            case Region.FOREIGN_WEST, _, _:
                return Seal.FOREIGN_WEST
        raise TypeError(f"No seal could be determined for {region}, {indication}, {credential_status}")

