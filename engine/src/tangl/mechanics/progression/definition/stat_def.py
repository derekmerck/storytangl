from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

from .canonical_slots import CanonicalSlot


class StatDef(BaseModel):
    """
    Definition of a single stat in a stat system.

    Examples:
        - "body" as an intrinsic physical stat
        - "swordsmanship" as a domain governed by "body"
    """

    model_config = ConfigDict(frozen=True)

    name: str
    description: str = ""
    is_intrinsic: bool = False

    currency_name: Optional[str] = None
    governed_by: Optional[str] = None
    canonical_slot: Optional[CanonicalSlot] = None
