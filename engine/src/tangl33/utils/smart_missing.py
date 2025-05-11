from typing import Any
from enum import Enum

class SmartMissing:

    @classmethod
    def _missing_(cls, value: Any):
        if isinstance(value, str):
            # Try to match by name or value, case-insensitive
            match_value = value.lower().replace(" ", "_")
            if isinstance(value, str):
                for member in cls:
                    if value.lower() == member.name.lower():
                        return member
            elif isinstance(value, int):
                for member in cls:
                    if value == member.value:
                        return member
            elif isinstance(value, Enum):
                # If it's another Enum, try to match by value
                return cls._missing_(value.value)
        raise ValueError(f"{value} is not a valid {cls.__name__}")

