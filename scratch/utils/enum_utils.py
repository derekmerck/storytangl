from __future__ import annotations
from typing import *
import random
from enum import IntEnum, EnumMeta

# type checking for mixins
if TYPE_CHECKING:  # pragma: no cover
    from enum import Enum
    Enum_ = Enum
else:
    Enum_ = object


class EnumUtils(Enum_):
    """
    This is a utility mixin for Enums.

    It adds a robust 'missing' function with aliases, and utilities
    for dictionary key conversion, random picking, and ordering.

    Create class methods 'alias' and/or 'rev_alias' to support casting
    additional values to the Enum.

    Note that Enums cannot have mixins except non-Enum's _before_ the
    Enum class and no additional base classes _after_ the Enum class.

    Usage:
    >>> class MyEnum(EnumUtils, Enum):
    ...   FOO = 'foobar'
    ...
    >>> assert MyEnum('_fOoBaR') == MyEnum.FOO
    """

    @classmethod
    def aliases(cls) -> dict[str, EnumUtils]:
        """Map of alternative names to value, ie, { alias: value }"""
        return {}

    @classmethod
    def rev_aliases(cls) -> dict[EnumUtils, list[str]]:
        """Map of values to lists of alternative names, ie, { value: [ alias1, alias2, ...] }"""
        return {}

    def __repr__(self):
        return f"<{self.name}>"

    @classmethod
    def _missing_(cls, value, *args, **kwargs):
        """
        Looks in a more places to try to decode enums.

        - Clamps out of range ints for IntEnum
        - Cast types by value, ie, This.MAX -> That.MAX
        - Case-invariant, ignores-underscores in member-map lookup
        - Checks for substring values in member-map names, ie, diamond -> This.BLUE_DIAMOND
        - Checks 'aliases' and 'rev_aliases' class vars, if they exist

        Note, substring matching may not always be desirable.
        """
        if isinstance( value, int) and issubclass(cls, IntEnum):
            # ints out of range
            if value > max( cls.__members__.values() ):
                value = max( cls.__members__.values() )
                return cls( value )
            elif value < min(cls.__members__.values()):
                value = min(cls.__members__.values())
                return cls( value )

        # cast types by value
        if isinstance( value, EnumUtils ):
            value = value.value
            return cls( value )

        # figure out key and member_map
        elif isinstance(value, str):
            # names with leading underscores indicate reserved
            value = cls._lower(value)
            member_map = { cls._lower(v.name): v for v in cls.__members__.values() }
            member_map |= { cls._lower(v.value): v for v in cls.__members__.values() if isinstance(v.value, str) }
            if value in member_map:
                return member_map[value]
            # check if we can _find_ value in any of the member names
            for k, v in member_map.items():
                if value in k:
                    return v

        # check for value in the keys of the 'aliases' map
        if value in cls.aliases():
            return cls( cls.aliases()[value] )

        # check for value in the values of the 'reverse alias' map
        for k, v in cls.rev_aliases().items():
            if value in v:
                return cls(k)

    @classmethod
    def pick(cls) -> Enum:
        return random.choice( list(cls) )

    @classmethod
    def _lower(cls, s: str):
        if isinstance(s, cls):
            s = s.name
        s = s.lower().lstrip("_")  # get rid of leading underscore
        s = s.replace("_", " ")
        return s

    def lower(self):
        return self._lower(self.name)

    @classmethod
    def typed_keys(cls, value_dict: dict) -> dict:
        # Convert a dictionary to use enum'd _keys_
        res = {}
        for k, v in value_dict.items():
            res[ cls(k) ] = v
        return res

    @classmethod
    def typed_list(cls, value_list: list) -> list:
        # Convert a list to enum'd values
        res = [ cls(v) for v in value_list ]
        return res

    def __int__(self):
        if hasattr(self, "_int_map"):
            return self._int_map[self.value]
        elif isinstance(self.value, int):
            return self.value
        raise TypeError(f'Cannot cast {self} to int')

    def __gt__(self, other: int):
        """
        Can decorate with @functools.totalordering if it is int-like
        """
        return int(self) > int(other)
