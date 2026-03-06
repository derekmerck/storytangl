"""Choice metadata response."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from tangl.service.response.native_response import InfoModel


class ChoiceInfo(InfoModel):
    """Metadata describing an available choice for the current cursor."""

    uid: UUID = Field(..., alias="id")
    """Unique identifier for the choice edge."""

    label: str
    """Human-readable label for the choice."""

    active: bool = True
    """Whether the choice can currently be selected."""

    reason: str | None = None
    """Explanation for inactive choices."""

    class Config:
        populate_by_name = True
        """Allow field population via ``uid`` or alias ``id``."""
