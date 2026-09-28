"""Typed authored policy for presenting unavailable Story choices."""

from __future__ import annotations

from enum import Enum

from tangl.utils.enum_plus import EnumPlusMixin


class UnavailableChoiceDisclosure(EnumPlusMixin, Enum):
    """Whether an unavailable Story choice is emitted to the reader."""

    DISCLOSE = "disclose"
    HIDE = "hide"
