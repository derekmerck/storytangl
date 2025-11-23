from __future__ import annotations

from enum import IntEnum


class Quality(IntEnum):
    """
    Five-tier quality scale for stat “qv” representation.

    Values:
        1: VERY_POOR
        2: POOR
        3: MID
        4: HIGH
        5: VERY_HIGH
    """

    VERY_POOR = 1
    POOR = 2
    MID = 3
    HIGH = 4
    VERY_HIGH = 5

    # Aliases
    OK = MID
    GOOD = HIGH
    VERY_GOOD = VERY_HIGH

    @classmethod
    def from_name(cls, name: str) -> "Quality":
        """Resolve a case-insensitive name or alias to a Quality."""
        key = name.strip().upper()
        # Optional simple synonyms
        aliases = {
            "AVERAGE": "MID",
            "MEDIUM": "MID",
        }
        key = aliases.get(key, key)
        return cls[key]
