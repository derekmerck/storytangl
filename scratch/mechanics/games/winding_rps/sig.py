"""
Stone, iron, glass

A homologue of extended rps with enumerated types, units, and forces
"""
from enum import Enum
from tangl.core.entity import Entity, Renderable_
from tangl.lang.helpers import plural as pl, oxford_join as ox


# 3-element SigType matches RPS exactly
SIG_TYPES = ["STONE", "IRON", "GLASS"]


class SigPrimary(Enum):
    """This is an ABC for an Enum of integer bins of arbitrary length"""

    @property
    def _bin(self) -> int:
        return self.value - 1

    @classmethod
    def of_bin(cls, value: int):
        if value is None:
            return None
        return cls(value + 1)

    def pseudobary(self) -> Tuple[float, ...]:
        result = [0] * len(self.__class__)
        result[self._bin] = 1.0
        return tuple(result)

    def dist(self, coord: Union[Tuple[float, ...], List[float]]) -> float:
        return math.sqrt( sum( [(x-y)**2 for x, y in zip(self.pseudobary(), coord) ] ) )

    @classmethod
    def primaries(cls):
        result = {}
        for el in cls:
            result[el.name] = el.pseudobary()
        return result

    @classmethod
    def secondaries(cls):
        result = {}
        r = list(range(len(cls)))
        rr = r[1:] + r[0:1]
        for i, j in zip(r, rr):
            loc = [0,] * len(cls)
            loc[i] = loc[j] = 0.5
            name = cls(i+1).name + cls(j+1).name
            result[name] = tuple(loc)
        return result

    @classmethod
    def extended_members(cls):
        result = {**cls.primaries(), **cls.secondaries()}
        val = 1.0 / len(cls)
        result["BALANCED"] = [val] * len(cls)
        return result

    @classmethod
    def closest(cls, coord: Union[Tuple[float, ...], List[float]]) -> Optional["SigClass"]:
        closest_dist = 2  # Max dist is 1
        closest = None
        for k, v in cls.extended_members().items():
            d = vdist(coord, v)
            # print(coord, el, d)
            if d < closest_dist:
                closest_dist = d
                closest = k
        return closest

    def __str__(self) -> str:
        return self.name

    @classmethod
    def from_str(cls, s) -> Optional["SigType"]:
        # print(f"s {s} is a {type(s)}")
        if s is None:
            return
        elif isinstance(s, SigPrimary):
            return s
        elif s in cls._member_names_:
            return cls[s]
        elif s == "ADAPTIVE":
            return None
        raise ValueError


SigType = Enum("SigType", SIG_TYPES, type=SigPrimary)


@attr.s(auto_attribs=True)
class Unit(Throw, Entity, Renderable_):

    sig_typ: SigType = attr.ib(converter=SigType.from_str, default=None)
    last_down: bool = False  # todo: Unit cannot be defeated until no other units remain

    @property
    def _bin(self) -> Optional[int]:
        if self.sig_typ is None:
            return None
        return self.sig__bin

    @_bin.setter
    def _bin(self, value: int):
        self.sig_typ = SigType.of_bin(value)

    @classmethod
    def summarize(cls, units: List["Unit"]) -> Optional[Dict]:
        if len(units) == 0:
            return
        result = defaultdict(int)
        for u in units:
            result[u.uid] += 1
        return {**result}

    @classmethod
    def join_str(cls,
                 units: List["Unit"] = None,
                 summary: Dict["Unit", int] = None,
                 label_map: Dict = None) -> Optional[str]:
        if not summary:
            if not units:
                return
            summary = cls.summarize(units)
        items = []
        for k, v in summary.items():
            if label_map and k in label_map:
                k_ = label_map[k]
            else:
                k_ = k
            items.append(f"{v} {k_ if v == 1 else pl(k_)}")
        item_str = ox(items)
        return item_str


@attr.s(auto_attribs=True, repr=False)
class Force(Hand):

    def sig_typ(self) -> str:
        return SigType.closest(self.pseudobary())

    def winding_dist(self, other: "Force"):
        return self.adaptive_winding_dist(other, num_bins=len(SigType))
        # # This is a special winding dist that rebins adaptive
        # if None in [x.sig_typ for x in self.contents]:
        #     # print('found adaptive elements')
        #     adaptive = [x for x in self.contents if x.sig_typ == None]
        #     best_d = 1.0
        #     for unit in adaptive:
        #         for _typ in SigType:
        #             curr_sig_typ = unit.sig_typ
        #             unit.sig_typ = _typ
        #             d = Hand.winding_dist(self, other)
        #             print( f"{_typ}: {d}" )
        #             if d > best_d:
        #                 unit.sig_typ = curr_sig_typ
        #             else:
        #                 best_d = d
        #     # Put them back
        #     for unit in adaptive:
        #         print( f"Using {unit.sig_typ}" )
        #         unit.sig_typ = None
        #     return best_d

        # return Hand.winding_dist(self, other)

    def add_units(self, count: int, unit_spec):
        for i in range(count):
            p = Unit(**unit_spec)
            self.contents.append(p)

    def summarize(self) -> Dict:
        result = {
            'strategy': self.sig_typ().__str__(),
            'power': self.total_weight(),
            'units': Unit.summarize(self.contents)
        }
        return result

    @classmethod
    def losses_str(cls, units=None, summary=None, who="Account", label_map: Dict = None):
        s = f"{who.capitalize()} lost {Unit.join_str(units=units, summary=summary, label_map=label_map)}."
        return s
