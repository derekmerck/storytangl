"""Native response types for the StoryTangl service layer."""

from __future__ import annotations

"""Native response types for the service layer."""

from typing import Any, Literal, Mapping, TypeAlias
from uuid import UUID

from pydantic import BaseModel

from tangl.core import BaseFragment
from tangl.journal.media import MediaFragment

# ============================================================================
# Fragment Streams (ResponseType.CONTENT)
# ============================================================================

FragmentStream: TypeAlias = list[BaseFragment]
"""
Ordered sequence of journal fragments.

Used by CONTENT endpoints to return narrative discourse. Fragments may be
specialized (ContentFragment, MediaFragment, etc.) but the type is kept
generic at this layer.
"""


# ============================================================================
# Info Models (ResponseType.INFO)
# ============================================================================

class InfoModel(BaseModel):
    """
    Marker base for orchestrator-native information models.

    InfoModel subclasses return metadata about system state without side
    effects. They contain no HTTP-specific fields—just domain data.
    """

    class Config:
        arbitrary_types_allowed = True


# ============================================================================
# Runtime Models (ResponseType.RUNTIME)
# ============================================================================

class RuntimeInfo(InfoModel):
    """Native acknowledgment for state-mutating operations."""

    status: Literal["ok", "error"]
    code: str | None = None
    message: str | None = None
    cursor_id: UUID | None = None
    step: int | None = None
    details: Mapping[str, Any] | None = None

    @classmethod
    def ok(
        cls,
        *,
        cursor_id: UUID | None = None,
        step: int | None = None,
        message: str | None = None,
        **details: Any,
    ) -> "RuntimeInfo":
        """Return a success response with optional metadata."""

        return cls(
            status="ok",
            cursor_id=cursor_id,
            step=step,
            message=message,
            details=details or None,
        )

    @classmethod
    def error(
        cls,
        code: str,
        message: str,
        *,
        cursor_id: UUID | None = None,
        step: int | None = None,
        **details: Any,
    ) -> "RuntimeInfo":
        """Return an error response with optional metadata."""

        return cls(
            status="error",
            code=code,
            message=message,
            cursor_id=cursor_id,
            step=step,
            details=details or None,
        )


# ============================================================================
# Media Natives (ResponseType.MEDIA)
# ============================================================================

MediaNative: TypeAlias = MediaFragment
"""Native media representation at orchestrator level."""


# ============================================================================
# Union Type for Orchestrator Return
# ============================================================================

NativeResponse: TypeAlias = FragmentStream | InfoModel | RuntimeInfo | MediaNative
"""Union of all native response types."""
