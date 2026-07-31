"""Persisted request types for one-level SVG composition."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from tangl.core.bases import BaseModelPlus
from tangl.media.media_creators.media_spec import MediaResolutionClass, MediaSpec
from tangl.media.media_data_type import MediaDataType


class CompositionInputRef(BaseModelPlus):
    """A persisted reference to one already-realized child media resource."""

    role: str
    rit_id: UUID
    content_hash: bytes
    offset: tuple[int, int] = (0, 0)

    def fingerprint_payload(self) -> dict[str, Any]:
        """Return the child identity relevant to its parent rendering."""
        return {
            "role": self.role,
            "content_hash": self.content_hash,
            "offset": self.offset,
        }


class CompositionSpec(MediaSpec):
    """One SVG canvas composed from explicitly resolved child resources."""

    resolution_class: MediaResolutionClass = MediaResolutionClass.FAST_SYNC
    data_type: MediaDataType = MediaDataType.VECTOR

    inputs: list[CompositionInputRef]
    canvas_size: tuple[int, int] = (128, 128)
    background: str = "transparent"
    treatment: str = "overlay"
    compositor_version: str = "1"
    renderer_name: str | None = None
    renderer_version: str | None = None
    resolved_input_hashes: list[bytes] | None = Field(default=None)

    def fingerprint_payload(self) -> dict[str, Any]:
        """Project child content, layout, and treatment while retaining RIT provenance."""
        payload = self.normalized_spec_payload()
        payload["inputs"] = [item.fingerprint_payload() for item in self.inputs]
        return payload
