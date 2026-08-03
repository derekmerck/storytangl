"""Deterministic SVG backend for printable text."""

from . import svg_text_adapter as _svg_text_adapter  # noqa: F401
from .svg_text_forge import SvgTextForge
from .svg_text_spec import SvgTextSpec

__all__ = ["SvgTextForge", "SvgTextSpec"]
