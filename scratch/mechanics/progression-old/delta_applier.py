from __future__ import annotations
from enum import Enum
from typing import Union

from scratch.progression.measured_value import MeasuredValue

Keylike = Union[str, Enum]
Valuelike = Union[int, float, MeasuredValue]
Delta = tuple[Valuelike, Valuelike]  # (absolute change, relative change)
ValueMap = dict[Keylike, Valuelike]
DeltaMap = dict[Keylike, Delta]


class DeltaMapHandler:
    """
    Provides interface to add and scale dictionaries of numbers or other types that
    implement "apply_delta" and "accumulate_delta".
    """

    @classmethod
    def apply_delta(cls, value: Valuelike, delta: Delta) -> Valuelike:
        """
        Apply a delta to a given value. If the value supports apply_delta, use it.
        Otherwise, apply the delta as an absolute and relative change.
        """
        try:
            return value.apply_delta(delta)
        except AttributeError:
            pass
        absolute, relative = delta
        return value * relative + value + absolute

    @classmethod
    def accumulate_delta(cls, base_delta: Delta, update_delta: Delta) -> Delta:
        """
        Accumulate an update delta into a base delta. If the values support
        accumulate_delta, use it. Otherwise, accumulate by addition.
        """
        res = []
        for base, update in zip(base_delta, update_delta):
            try:
                res.append(base.accumulate_delta(update))
            except AttributeError:
                res.append(base + update)
        return tuple(res)

    @classmethod
    def accumulate_delta_maps(cls, *delta_maps: DeltaMap) -> DeltaMap:
        """
        Accumulate multiple delta maps into a single delta map.
        """
        res = {}
        for delta_map in delta_maps:
            for k, v in delta_map.items():
                res[k] = cls.accumulate_delta(res.get(k, (0, 0)), v)
        return res

    @classmethod
    def apply_delta_maps(cls, values: ValueMap, *delta_maps: DeltaMap) -> ValueMap:
        """
        Apply accumulated deltas from multiple delta maps to the values.
        """
        delta_map = cls.accumulate_delta_maps(*delta_maps)
        result = values.__class__()
        for key, value in values.items():
            delta = delta_map.get(key, (0, 0))
            new_value = cls.apply_delta(value, delta)
            result[key] = new_value
        return result

    @classmethod
    def delta_from_tag(cls, tag: str):
        """
        Parse a string like "@abc:easier", "@abc,def:cost+x.wealth,-cash-y.time,*z
        """
        applies_to, modifier = tag.split(":")

# Example usage and testing
if __name__ == "__main__":
    # Example MeasuredValue class
    class MeasuredValue:
        def __init__(self, value: float):
            self.value = value

        def apply_delta(self, delta: Delta) -> MeasuredValue:
            absolute, relative = delta
            new_value = self.value * relative + self.value + absolute
            return MeasuredValue(new_value)

        def accumulate_delta(self, delta: Valuelike) -> MeasuredValue:
            return MeasuredValue(self.value + delta)

        def __repr__(self):
            return f"MeasuredValue({self.value})"

    # Example usage
    value_map = {
        "hp": 100,
        "mp": 50,
        "strength": MeasuredValue(10),
        "agility": MeasuredValue(8)
    }

    delta_map_1 = {
        "hp": (10, 0.1),  # +10 absolute, +10% relative
        "strength": (2, 0.05)  # +2 absolute, +5% relative
    }

    delta_map_2 = {
        "hp": (5, 0.05),  # +5 absolute, +5% relative
        "agility": (1, 0.1)  # +1 absolute, +10% relative
    }

    updated_values = DeltaMapHandler.apply_delta_maps(value_map, delta_map_1, delta_map_2)
    print(updated_values)
    # Output: {'hp': 125.5, 'mp': 50, 'strength': MeasuredValue(12.5), 'agility': MeasuredValue(9.8)}
