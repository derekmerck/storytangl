import re
from typing import Any, TYPE_CHECKING, Self
from enum import Enum
from random import Random
import warnings

# type checking for mixins
if TYPE_CHECKING:  # pragma: no cover
    Enum_ = Enum
else:
    Enum_ = object


class EnumPlusMixin(Enum_):
    """
    This is a utility mixin for Enums.

    It adds a robust 'missing' function with aliases, and utilities
    for dictionary key conversion, random picking, and ordering.

    Create class methods 'alias' and/or 'rev_alias' to support casting
    additional values to the Enum.

    Note that Enums cannot have mixins except non-Enum's _before_ the
    Enum class and no additional base classes _after_ the Enum class.

    Usage:
    >>> class MyEnum(EnumPlusMixin, Enum):
    ...   FOO = 'foobar'
    ...
    >>> assert MyEnum('fOoBaR') == MyEnum.FOO
    """

    @classmethod
    def aliases(cls):
        return {k: v for k, v in cls.__dict__.items() if isinstance(v, cls)}

    @classmethod
    def rev_aliases(cls) -> dict[Self, list[str]]:
        """Map of values to lists of alternative names, ie, { value: [ alias1, alias2, ...] }"""
        return {}

    @classmethod
    def _missing_(cls, value: Any):
        # If it's another Enum, normalize to its value first.
        if isinstance(value, Enum):
            return cls._missing_(value.name) or cls._missing_(value.value)

        if isinstance(value, str):
            # Handle "ClassName:foo" or "classname/foo"
            if m := re.match(fr"{re.escape(cls.__name__)}\W(.*)", value, re.IGNORECASE):
                return cls._missing_(m.group(1))

            # If this looks numeric and the enum uses int values, treat it as such.
            if value.isdigit():
                iv = int(value)
                for member in cls:
                    if isinstance(member.value, int) and member.value == iv:
                        return member

            # Try to match by name or string value, case-insensitive
            match_value = value.lower().replace(" ", "_")
            for member in cls:
                if (match_value == member.name.lower() or
                        isinstance(member.value, str)
                        and match_value == member.value.lower()):
                    return member

            # check for value in the keys of the 'aliases' map
            for alias, member in cls.aliases().items():
                if isinstance(alias, str) and match_value == alias.lower():
                    return member

            # check for value in the values of the 'reverse alias' map
            for member, aliases in cls.rev_aliases().items():
                for alias in aliases:
                    if match_value == alias.lower().replace(" ", "_"):
                        return member

            # for alias, member in cls.aliases().items():
            #     if match_value == alias.lower():
            #         return member

        if isinstance(value, int):
            # Try to match by int value
            for member in cls:
                if value == member.value:
                    return member

        # raise ValueError(f"{value} is not a valid {cls.__name__}")

    # For parsing configs mostly
    @classmethod
    def typed_keys(cls, value_dict: dict) -> dict:
        return {cls(k): v for k, v in value_dict.items()}

    @classmethod
    def typed_list(cls, value_list: list) -> list:
        return [cls(v) for v in value_list]

    @classmethod
    def pick(cls, rand: Random = None):
        if rand is None:
            warnings.warn(f"{cls.__name__}.pick() can be useful for testing, but always pass in `rand` if you need reproducible results", RuntimeWarning)
            rand = Random()
        return rand.choice(list(cls))

    def lower(self: Enum):
        return self.name.lower()

    def __repr__(self):
        return f"<{self.name}>"
