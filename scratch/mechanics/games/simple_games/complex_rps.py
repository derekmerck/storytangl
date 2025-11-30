
import typing as typ
from enum import Enum
import attr


class Rps(Enum):
    R = ROCK = 0
    P = PAPER = 1
    S = SCISSORS = 2

    def beats(self, other) -> typ.Optional[bool]:
        ahead = (self.value - other.value) % 3
        if ahead == 0:
            return None  # draw
        if ahead == 1:
            return True
        if ahead == 2:
            return False


@attr.s(auto_attribs=True)
class Move(object):
    label: str = "Little scissors"
    rps_typ: Rps = Rps.SCISSORS

    aggro: int = 10
    heat: int = 10         # how much heat is raised


# mutable, values can go up/down, posture can change
@attr.s(auto_attribs=True)
class Target(object):
    label: str = "Little Paper"
    rps_typ: Rps = Rps.PAPER    # susceptible to sharp

    max_defiance: int = 100     # this is external, sus
    defiance: int = 0
    defiance_cool: int = -5

    max_heat: int = 100
    heat: int = 0
    heat_cool: int = -5

    def apply_move(self, move: Move, sus_mult = 1.0):
        self.defiance += self.defiance_cool
        self.heat += self.heat_cool
        self.defiance = max([self.defiance, 0])
        self.heat = max([self.heat, 0])

        outcome = move.rps_typ.beats(self.rps_typ)
        if outcome:
            d_mult = 0.5
            h_mult = 1.0
        elif outcome is None:
            d_mult = 1.0
            h_mult = 0.5
        else:
            d_mult = 1.5
            h_mult = 0.0

        self.defiance += sus_mult * d_mult * move.aggro
        self.heat += h_mult * move.heat

        self.defiance = max([self.defiance, 0])
        self.heat = max([self.heat, 0])

        if self.defiance > self.max_defiance:
            print("You lost")
        elif self.heat > self.max_heat:
            print("You win")


if __name__ == "__main__":

    m = Move()
    t = Target()
    print(t)

    t.apply_move(m, sus_mult=1.0)
    t.apply_move(m, sus_mult=1.0)
    t.apply_move(m, sus_mult=1.0)
    print(t)


