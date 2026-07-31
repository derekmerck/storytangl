"""Renderer-neutral semantic request for one generated portrait."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.media.media_creators.media_spec import MediaSpec


class PortraitSpec(MediaSpec):
    """Semantic portrait request independent of a particular avatar renderer."""

    media_role: str | None = None
    identity_key: str
    explicit_seed: str | int | None = None
    description: str = ""
    traits: dict[str, Any] = Field(default_factory=dict)
    style_profile: str | None = None
