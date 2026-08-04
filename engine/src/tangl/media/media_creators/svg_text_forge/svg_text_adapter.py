"""Compile semantic printable text into fixed SVG layout instructions."""

from __future__ import annotations

from textwrap import TextWrapper

from tangl.core import Priority
from tangl.media.media_creators.media_spec import on_adapt_media_spec
from tangl.media.media_creators.printable_text_spec import PrintableTextSpec
from tangl.type_hints import StringMap

from .svg_text_spec import SvgTextSpec

_DEFAULT_STYLE_PROFILE = "default"
_CREDENTIAL_CARD_STYLE_PROFILE = "credential_card"
_CANVAS_WIDTH = 320
_PADDING = 16
_FONT_FAMILY = "sans-serif"
_FONT_SIZE = 16
_LINE_HEIGHT = 24
_FOREGROUND = "#111111"
_BACKGROUND = "#ffffff"
_ADAPTER_VERSION = "1"
_CREDENTIAL_CARD_FONT_FAMILY = "monospace"
_CREDENTIAL_CARD_FONT_SIZE = 14
_CREDENTIAL_CARD_LINE_HEIGHT = 20
_CREDENTIAL_CARD_LINE_WIDTH = 34
_CREDENTIAL_CARD_MAX_LINES = 7


def _credential_card_lines(lines: tuple[str, ...]) -> tuple[str, ...]:
    """Wrap source lines to the fixed-width credential-card text contract."""
    wrapper = TextWrapper(
        width=_CREDENTIAL_CARD_LINE_WIDTH,
        break_long_words=True,
        break_on_hyphens=False,
    )
    wrapped_lines = tuple(
        wrapped
        for line in lines
        for wrapped in (wrapper.wrap(line) or [""])
    )
    if len(wrapped_lines) <= _CREDENTIAL_CARD_MAX_LINES:
        return wrapped_lines
    return (*wrapped_lines[: _CREDENTIAL_CARD_MAX_LINES - 1], "…")


@on_adapt_media_spec.register(priority=Priority.NORMAL)
def adapt_printable_text_spec(
    spec: PrintableTextSpec,
    ctx: StringMap | None = None,
) -> SvgTextSpec:
    """Resolve a named printable-text profile into deterministic SVG layout."""
    _ = ctx
    if spec.style_profile == _DEFAULT_STYLE_PROFILE:
        lines = spec.lines
        font_family = _FONT_FAMILY
        font_size = _FONT_SIZE
        line_height = _LINE_HEIGHT
    elif spec.style_profile == _CREDENTIAL_CARD_STYLE_PROFILE:
        lines = _credential_card_lines(spec.lines)
        font_family = _CREDENTIAL_CARD_FONT_FAMILY
        font_size = _CREDENTIAL_CARD_FONT_SIZE
        line_height = _CREDENTIAL_CARD_LINE_HEIGHT
    else:
        raise ValueError(f"Unsupported printable text style profile {spec.style_profile!r}")
    return SvgTextSpec(
        label=spec.label,
        lines=lines,
        style_profile=spec.style_profile,
        canvas_width=_CANVAS_WIDTH,
        canvas_height=_PADDING * 2 + line_height * max(1, len(lines)),
        padding=_PADDING,
        font_family=font_family,
        font_size=font_size,
        line_height=line_height,
        foreground=_FOREGROUND,
        background=_BACKGROUND,
        adapter_version=_ADAPTER_VERSION,
    )


adapt_printable_text_spec._behavior.wants_caller_kind = PrintableTextSpec
