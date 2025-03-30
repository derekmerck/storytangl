from typing import Any
from enum import Enum

class EnumPlusMixin:
    """
    Adds robust missing funcs and aliases for casting.
    """

    @classmethod
    def aliases(cls):
        return { k: v for k, v in cls.__dict__.items() if isinstance(v, cls)}

    @classmethod
    def _missing_(cls, value: Any):
        if isinstance(value, str):
            # Try to match by name or value, case-insensitive
            match_value = value.lower().replace(" ", "_")
            for member in cls:
                if (match_value == member.name.lower() or
                        isinstance(member.value, str) and match_value == member.value.lower()):
                    return member
            for alias, member in cls.aliases().items():
                if match_value == alias.lower():
                    return member

        if isinstance(value, int):
            # Try to match by value
            for member in cls:
                if value == member.value:
                    return member
        elif isinstance(value, Enum):
            # If it's another Enum, try to match by value
            return cls._missing_(value.value)
        raise ValueError(f"{value} is not a valid {cls.__name__}")

    def lower(self: Enum):
        return self.name.lower()
