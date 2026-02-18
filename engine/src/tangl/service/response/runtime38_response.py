"""Service38 runtime response schema.

The service38 transport contract is an envelope around an ordered fragment
stream. Clients may filter and recompose fragments however they want, but the
service layer does not split content/choices/media into separate top-level
lists.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RuntimeEnvelope38(BaseModel):
    """Ordered-fragment runtime payload for vm38/story38 clients."""

    cursor_id: UUID | None = None
    step: int | None = None
    fragments: list[dict[str, Any]] = Field(default_factory=list)
    last_redirect: dict[str, Any] | None = None
    redirect_trace: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
