"""Renderer-neutral request for ordered printable text."""

from __future__ import annotations

from tangl.media.media_creators.media_spec import MediaSpec


class PrintableTextSpec(MediaSpec):
    """Semantic request for a fixed ordered sequence of printed text lines."""

    lines: tuple[str, ...]
    style_profile: str = "default"
