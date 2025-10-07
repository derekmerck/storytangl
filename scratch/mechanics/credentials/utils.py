from enum import Enum
from uuid import UUID


# format internal value representations for rendered output
def turn2date( turn: int ) -> str:
    return f"Day {turn}"


def uid2credential( uid: UUID ) -> str:
    return str(uid)


def seal2image( seal: Enum ) -> str:
    return repr(seal)
