"""Compile semantic printable text into fixed SVG layout instructions."""

from __future__ import annotations

from typing import Any

from tangl.core import Priority
from tangl.media.media_creators.media_spec import on_adapt_media_spec
from tangl.media.media_creators.printable_text_spec import PrintableTextSpec

from .svg_text_spec import SvgTextSpec

_DEFAULT_STYLE_PROFILE = "default"
_CANVAS_WIDTH = 320
_PADDING = 16
_FONT_FAMILY = "sans-serif"
_FONT_SIZE = 16
_LINE_HEIGHT = 24
_FOREGROUND = "#111111"
_BACKGROUND = "#ffffff"
_ADAPTER_VERSION = "1"


@on_adapt_media_spec.register(priority=Priority.NORMAL)
def adapt_printable_text_spec(
    spec: PrintableTextSpec,
    ctx: dict[str, Any] | None = None,
) -> SvgTextSpec:
    """Resolve the single supported printable-text profile into fixed SVG layout."""
    _ = ctx
    if spec.style_profile != _DEFAULT_STYLE_PROFILE:
        raise ValueError(f"Unsupported printable text style profile {spec.style_profile!r}")
    return SvgTextSpec(
        label=spec.label,
        lines=spec.lines,
        canvas_width=_CANVAS_WIDTH,
        canvas_height=_PADDING * 2 + _LINE_HEIGHT * max(1, len(spec.lines)),
        padding=_PADDING,
        font_family=_FONT_FAMILY,
        font_size=_FONT_SIZE,
        line_height=_LINE_HEIGHT,
        foreground=_FOREGROUND,
        background=_BACKGROUND,
        adapter_version=_ADAPTER_VERSION,
    )


adapt_printable_text_spec._behavior.wants_caller_kind = PrintableTextSpec
