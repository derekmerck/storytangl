"""
Winding Metric Rock-Paper-Scissors

- Each Throw has a type/bin and a power-multiplier
- A Hand may contain multiple throws
- Hands are compared by determining a relative strategy error
  and comparing error-weighted total power.
- In a multi-round match, each Hand is then randomly decimated
  by removing throws equal to the error-weighted total power
  of the opponent and repeating until one hand is exhausted.

Terminology is slightly motivated by the principles of
barycentric coordinates (weights on a vertex to balance a
triangle at a particular point) and vertex winding.

Pseudo-barycentric weights are compared to the next (and
next and so on) to compute an overall strategic multiplier
for the absolute power of the throws available.

Because strategy is computed as ratios, it is important to
_leave out_ non-contributing throws, or the bad strategy may
counteract the added power benefit.

There is a special case for unbinned throws: these throws will
be added piecewise to any bin to optimize overall strategic power.
Each unbinned throw is greedily tested in every bin against
a given strategy and then added to the one that provides the
greatest overall benefit.
"""

import math
import typing as typ
import random
import attr


MIN_POWER = 0.1       # Even a perfectly bad strategy can exert a minimal match influence
POWER_OFFSET = -0.15  # Reduces impact of all windings
POW_EXP = 1.8         # Power exponent (shrinks values near 0)
NUM_BINS = 3

def vdist(this, that):
    diff_v = [(x-y)**2 for x, y in zip(this, that)]  # root square error
    dist = math.sqrt( sum(diff_v) )
    return dist

@attr.s(auto_attribs=True, hash=True)
class Throw(object):
    _bin: int = 0
    power: float = 1.0


@attr.s(auto_attribs=True, repr=False)
class Hand(object):

    contents: typ.List[Throw] = attr.ib( init=False, factory=list )

    def add(self, p: Throw):
        self.contents.append(p)

    def add_items(self, count, _bin, power):
        for i in range(count):
            p = Throw(_bin, power)
            self.contents.append(p)

    _init_items: typ.Tuple = None

    def __attrs_post_init__(self):
        if self._init_items:
            for item in self._init_items:
                self.add_items(*item)

    def total_weight(self) -> float:
        weight = sum([x.power for x in self.contents if x._bin is not None])
        # print(weight)
        weight = round(weight, 2)
        return weight

    norm = total_weight

    def weight_by_bin(self, _bin: int) -> float:
        weight = sum([x.power for x in self.contents if x._bin == _bin])
        return weight

    def count_by_bin(self, _bin) -> float:
        count = len([x.power for x in self.contents if x._bin == _bin])
        return count

    def counts(self, num_bins=NUM_BINS):
        counts = []
        for _bin in range(num_bins):
            counts.append(self.count_by_bin(_bin))
        return counts

    def pseudobary(self, num_bins = NUM_BINS) -> typ.List[float]:
        weights = []
        total_weight = self.total_weight()
        if total_weight == 0:
            v = 1.0 / num_bins
            return [v] * num_bins
        for bin in range(num_bins):
            this = round( self.weight_by_bin(bin) / total_weight, 2 )
            weights.append(this)
        return weights

    def winding_dist(self, other: "Hand") -> float:
        """Yields normalized winding distance from 0 to 1 (max diff)"""
        return self._winding_dist(self.pseudobary(), other.pseudobary())

    def adaptive_winding_dist(self, other: "Hand", num_bins = NUM_BINS) -> float:
        if None in [x._bin for x in self.contents]:
            # print('found adaptive elements')
            adaptive = [x for x in self.contents if x._bin is None]
            best_d = 1.0
            for unit in adaptive:
                for test_bin in range(num_bins):
                    curr_bin  = unit._bin
                    unit._bin = test_bin
                    d = Hand.winding_dist(self, other)
                    # print( f"{test_bin}: {d}" )
                    if d > best_d:
                        unit._bin = curr_bin
                    else:
                        best_d = d
            # Put them back
            for unit in adaptive:
                # print( f"Using {unit._bin}" )
                unit._bin = None
            return best_d

        return Hand.winding_dist(self, other)

    @classmethod
    def _winding_dist(cls, this, that) -> float:
        _this = [*this]
        min_dist = 2
        num_winds = len(this) // 2
        for i in range( num_winds ):
            _this.insert(0, _this.pop(-1))  # wind
            # print(_this, that, vdist( _this, that ))
            dist = vdist(_this, that) / math.sqrt(2)    # length of a tringle side = sqrt(2)
            # todo: need min of each bin and sum/norm of that
            min_dist = min([min_dist, dist])
        return min_dist

    def wound_power(self, other: "Hand") -> float:
        # complement winding distance (lower is more powerful)
        # add min offset
        # multiply by total weight of hand
        wf = (1 - self.winding_dist(other) )**POW_EXP
        wf = max([wf + POWER_OFFSET, MIN_POWER])
        return wf * self.norm()

    def decimate(self, _weight: float):
        removed = []
        while _weight > 0 and self.contents:
            choice = self.contents.pop(random.randrange(len(self.contents)))

            if (_weight - choice.power) < 0:
                # This is a final marginal pull, like only 1 weight left vs a 10 weight loss
                win_chance = abs(_weight - choice.power) / choice.power   # i.e. 1/10
                # print(f"Marginal pull: {_weight} v {choice.power} = {win_chance}")
                if random.random() > win_chance:
                    # print("Yes")
                    removed.append(choice)
                else:
                    # print("Put back")
                    self.contents.append(choice)
            _weight -= choice.power
        return removed

    @classmethod
    def match(cls, this: "Hand", that: "Hand"):
        # Inflict random losses up to the wound power
        that_dam = this.wound_power(that) * ( random.random() )
        this_dam = that.wound_power(this) * ( random.random() )
        # that_dam = this.wound_power(that) * ( 0.5 + 0.5 * random.random() )
        # this_dam = that.wound_power(this) * ( 0.5 + 0.5 * random.random() )
        # that_dam = this.wound_power(that) * ( 1.0 )
        # this_dam = that.wound_power(this) * ( 1.0 )

        removed_that = that.decimate(that_dam)
        removed_this = this.decimate(this_dam)

        return removed_this, removed_that

    @classmethod
    def play(cls, this: 'Hand', that: 'Hand'):

        this_init_power = this.total_weight()
        that_init_power = that.total_weight()

        this_init_wound_power = this.wound_power(that)
        that_init_wound_power = that.wound_power(this)

        # this_losses = []
        # that_losses = []
        round_counter = 0
        rounds = []
        while (this.total_weight() > 0) and (that.total_weight() > 0):
            round_counter += 1
            this_losses_, that_losses_ = Hand.match(this, that)
            # this_losses += this_losses_
            # that_losses += that_losses_
            rounds.append((this_losses_, that_losses_))
            # print(f"Round {round_}")
            # print(this_losses)
            # print(this.total_weight())
            # print(that_losses)
            # print(that.total_weight())

        return {
            "init_pow": (this_init_power, that_init_power),
            "init_wpow": (this_init_wound_power, that_init_wound_power),
            "outcome": this.total_weight() > that.total_weight(),
            "rounds": rounds,
        }

    def __repr__(self):
        s =  f"counts: {self.counts()}\n"
        s += f"weight: {self.total_weight()}\n"
        s += f"pb:     {self.pseudobary()}\n"
        return s


@attr.s(auto_attribs=True, repr=False)
class Player(object):
    reserve: Hand = None
    active: Hand = None

    def select_hand(self):
        """Move throws from reserve to active tp build pow and strategy"""
        raise NotImplementedError

    def revise_hand(self):
        """Move throws from reserve to active or vice versa to revise pow and strategy"""
        raise NotImplementedError

