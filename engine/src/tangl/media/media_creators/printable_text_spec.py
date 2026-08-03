"""Renderer-neutral request for ordered printable text."""

from __future__ import annotations

from tangl.media.media_creators.media_spec import MediaSpec


class PrintableTextSpec(MediaSpec):
    """Semantic request for an ordered sequence of printable text.

    Why:
        Preserve authored text and its presentation intent independently from a
        concrete vector renderer.

    Key Features:
        Carries ordered source lines and a named style profile without making
        layout or backend choices.

    API:
        ``adapt_spec()`` resolves this request into an ``SvgTextSpec``.

    Notes:
        The default profile preserves one source line per SVG text element;
        other named profiles may define their own deterministic layout rules.

    See also:
        ``SvgTextSpec`` for resolved SVG instructions.
    """

    lines: tuple[str, ...]
    style_profile: str = "default"
