from __future__ import annotations

from enum import Enum


class CanonicalSlot(Enum):
    """
    Universal semantic slots for cross-genre portability.

    A world may map its concrete stats onto these to enable
    generic reasoning across different themes.
    """

    PHYSICAL = "physical"
    MENTAL = "mental"
    SPIRITUAL = "spiritual"
    SOCIAL = "social"
    COVERT = "covert"

    def __str__(self) -> str:
        return self.value
