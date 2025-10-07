"""
## Attacker/Defender Game Scenario

Defender commits units (num, type)
  - creates a posture + total pow, rock=dig in, iron=draw out, glass=flank
  - signal: type, number

Attacker selects units (num, type)
  - creates a posture + total pow, rock=assault, iron=draw out, glass=lightning

resolution - payout * total pow decimates opponent forces, payouts = 1, 0.5, 0.2

defender reinforces
  - may change posture
  - change effective pow
  - signal: type, number

attacker reinforces
  - may change posture
  - change effective pow

resolution - payout * total pow decimates opponent forces

continues until time limit or one player has no units left

upgrades include better signals, force multipliers, leader units w adaptive types
"""
from typing import Protocol

from tangl.core import Singleton
from .abs_game import Payout, Strategy
from .rps import RpsGame_, GamePlayer, RpsMove


class BagRpsMove(Protocol):
    uid: str
    move_typ: RpsMove
    power: float
    last_down: bool


@attr.define(init=False, slots=False, eq=False, hash=False)
class BagRpsItem(Singletons, BagRpsMove):

    move_typ: RpsMove = attr.ib(default=None,
                                converter=RpsMove,
                                validator=attr.validators.instance_of(RpsMove))
    power: float = 1.0
    last_down: bool = False  # Heroes are always last down in bag

    uid: str = attr.ib()
    @uid.default
    def mk_uid(self):
        """ :meta private: """
        s = f"{repr(self.move_typ)[1].capitalize()}{int(self.power)}"
        return s

    # def __attrs_post_init__(self):
    #     self._instances[self.uid] = self


# Has power and affiliation
# @attr.define(slots=False)
class BagRpsCollection(collections.Counter, BagRpsMove):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_cls = BagRpsItem

    def _pow_by_move_typ(self) -> collections.Counter[RpsMove, float]:
        tmp = collections.Counter()
        for k, v in self.items():
            print( self.item_cls )
            item_typ = self.item_cls.instance(k)
            tmp[item_typ.move_typ] += item_typ.power * v
        return tmp

    @property
    def move_typ(self) -> RpsMove:
        tmp = self._pow_by_move_typ()
        cand = tmp.most_common()
        # sort by total power desc (10 > 5 > 1) then
        #      by move typ asc (Rock > Scissors > Paper)
        cand.sort(key=lambda x: (x[1], -x[0]), reverse=True)
        return cand[0][0]

    @property
    def power(self) -> float:
        res = 0
        for k, v in self.items():
            item_typ = self.item_cls.instance(k)
            res += item_typ.power * v
        return res

    @property
    def count(self) -> int:
        return len(self)

    def __len__(self):
        return sum(self.values())

    def __bool__(self):
        return bool(len(self))

    def decimate(self, damage: numbers.Number) -> collections.Counter:
        reduced_power = self.power - damage
        res = self.__class__()
        if reduced_power < 0:
            return +self
        while self.power > reduced_power:
            print(list(self.elements()))
            key = random.choice( list(self.elements()) )
            # todo, if you are going to go negative, [6->-2] then
            #    you have a 2/8 chance to save unit and break
            self[key] -= 1
            res[key] += 1
        return res

    def __floordiv__(self, other: int):
        res_ = {k: math.ceil( v / other ) for k, v in self.items() }
        cls = self.__class__
        res = cls(res_)
        return res

    def __pos__(self):
        return self.__class__( super().__pos__() )

    def __neg__(self):
        return self.__class__( super().__neg__() )


class BagRpsStrategy(Strategy):

    @classmethod
    def commit_half(cls, bag: BagRpsCollection) -> BagRpsCollection:
        return bag // 2  # half of remaining

    @classmethod
    def all_in(cls, bag: BagRpsCollection) -> BagRpsCollection:
        print("Going all in")
        return bag


@attr.define
class BagRpsPlayer(GamePlayer):

    forces: BagRpsCollection = attr.ib(default=None,
                                       converter=BagRpsCollection)
    reserve: BagRpsCollection = attr.ib(init=False)
    @reserve.default
    def mk_reserve(self):
        """ :meta private: """
        return +self.forces
    committed: BagRpsCollection = attr.ib(factory=BagRpsCollection, init=False)
    defeated: BagRpsCollection = attr.ib(factory=BagRpsCollection, init=False)

    strategy: Callable = BagRpsStrategy.all_in

    _move: BagRpsCollection = attr.ib(default=None, init=False)
    def make_move(self, game: 'BagRpsGame'):
        if self._move:
            try:
                self.reserve -= self._move
                self.committed += self._move
                self._move = None
            except ValueError:
                raise "Failed to commit units"
        else:
            _committing = self.strategy( self.reserve )
            self.committed += _committing
            self.reserve = -_committing

            # raise RuntimeError("Need a default move")

        return self.committed.move_typ, self.committed.power

    def decimate(self, impact: float):
        defeated = self.committed.decimate(impact)
        self.committed -= defeated
        self.defeated += defeated


# 4x, 1x, 1/4x
rps3_graded_payout = [
    [1, 4, 0.25],
    [0.25, 1, 4],
    [4, 0.25, 4]
]


@attr.define(slots=False, init=False, eq=False, hash=False)
class BagRpsGame_(RpsGame_):

    payout: Payout = attr.ib( factory=lambda: Payout(rps3_graded_payout) )
    player1: BagRpsPlayer = attr.ib( factory=BagRpsPlayer )
    player2: BagRpsPlayer = attr.ib( factory=BagRpsPlayer )

    # decimation-type turn
    def do_round(self, *args, **kwargs) -> int:
        p1_mv, p1_pow = self.player1.make_move(self)
        p2_mv, p2_pow = self.player2.make_move(self)

        p1_payout = self.payout.get(p1_mv, p2_mv)
        p2_payout = self.payout.get(p2_mv, p1_mv)

        p1_impact = p1_pow * p1_payout
        p2_impact = p2_pow * p2_payout

        print(p1_impact, 'v', p2_impact, "impact")

        self.player1.decimate(p2_impact)
        self.player2.decimate(p1_impact)

        self.score[0] += p1_impact
        self.score[1] += p2_impact

        if p1_payout > p2_payout:
            self.round_winner = 1
        elif p2_payout > p1_payout:
            self.round_winner = 2
        else:
            self.round_winner = -1

        self.history.append( (p1_mv, p1_pow, p2_mv, p2_pow) )
        return self.has_winner()

    def has_winner(self, *args, **kwargs):
        # or could check defeated power == initial forces power
        if not self.player2.reserve + self.player2.committed + \
               self.player1.reserve + self.player1.committed:
            # Everyone down
            return self.draw_goes_to
        if not self.player2.reserve + self.player2.committed:
            return 1
        elif not self.player1.reserve + self.player1.committed:
            return 2
        elif self.round > self.draw_at:
            return self.draw_goes_to
        else:
            return 0


@attr.define
class BagRpsGame(BagRpsGame_):
    pass