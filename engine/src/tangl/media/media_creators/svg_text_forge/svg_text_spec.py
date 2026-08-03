"""Concrete SVG layout for one printable-text request."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tangl.media.media_creators.media_spec import MediaResolutionClass, MediaSpec
from tangl.media.media_data_type import MediaDataType

if TYPE_CHECKING:
    from .svg_text_forge import SvgTextForge


class SvgTextSpec(MediaSpec):
    """Resolved fixed-layout SVG instructions for ordered text lines."""

    resolution_class: MediaResolutionClass = MediaResolutionClass.FAST_SYNC
    data_type: MediaDataType = MediaDataType.VECTOR

    lines: tuple[str, ...]
    canvas_width: int
    canvas_height: int
    padding: int
    font_family: str
    font_size: int
    line_height: int
    foreground: str
    background: str
    adapter_version: str = "1"
    renderer_name: str | None = None
    renderer_version: str | None = None

    @classmethod
    def get_creation_service(cls) -> SvgTextForge:
        from .svg_text_forge import SvgTextForge

        return SvgTextForge()
