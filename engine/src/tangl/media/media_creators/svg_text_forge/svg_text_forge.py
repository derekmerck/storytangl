"""Deterministic local SVG creation for fixed printable text."""

from __future__ import annotations

from lxml import etree

from .svg_text_spec import SvgTextSpec


class SvgTextForge:
    """Render resolved printable text layout into a standalone SVG document."""

    def create_media(self, spec: SvgTextSpec) -> tuple[str, SvgTextSpec]:
        """Return XML-safe SVG text and the realized backend spec."""
        root = etree.Element(
            "{http://www.w3.org/2000/svg}svg",
            nsmap={None: "http://www.w3.org/2000/svg"},
            width=str(spec.canvas_width),
            height=str(spec.canvas_height),
            viewBox=f"0 0 {spec.canvas_width} {spec.canvas_height}",
        )
        etree.SubElement(
            root,
            "{http://www.w3.org/2000/svg}rect",
            x="0",
            y="0",
            width=str(spec.canvas_width),
            height=str(spec.canvas_height),
            fill=spec.background,
        )
        for index, line in enumerate(spec.lines):
            text = etree.SubElement(
                root,
                "{http://www.w3.org/2000/svg}text",
                x=str(spec.padding),
                y=str(spec.padding + spec.font_size + index * spec.line_height),
                fill=spec.foreground,
                **{
                    "font-family": spec.font_family,
                    "font-size": str(spec.font_size),
                    "{http://www.w3.org/XML/1998/namespace}space": "preserve",
                },
            )
            text.text = line
        return etree.tostring(root, encoding="unicode"), spec.model_copy(
            update={
                "renderer_name": "svg-text-forge",
                "renderer_version": spec.adapter_version,
            }
        )
