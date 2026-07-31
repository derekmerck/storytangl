"""Small local SVG compositor with no graph or provisioning knowledge."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from lxml import etree

from tangl.core import Priority
from tangl.media.media_creators.media_spec import on_create_media

from .composition_inputs import COMPOSITION_INPUTS_CONTEXT_KEY, ResolvedCompositionInput
from .composition_spec import CompositionSpec

_URL_REFERENCE = re.compile(r"url\(#([A-Za-z_][\w:.-]*)\)")
_REFERENCE_VALUE_ATTRIBUTES = {
    "clip-path",
    "cursor",
    "fill",
    "filter",
    "marker-end",
    "marker-mid",
    "marker-start",
    "mask",
    "stroke",
    "style",
}


def _namespace_svg_ids(root: etree._Element, *, prefix: str) -> None:
    """Make one child document's local fragment references unique in its parent."""
    identifiers = {
        identifier: f"{prefix}{identifier}"
        for element in root.iter()
        if (identifier := element.get("id"))
    }
    if not identifiers:
        return

    def rewrite_url_references(value: str) -> str:
        def replace(match: re.Match[str]) -> str:
            identifier = match.group(1)
            replacement = identifiers.get(identifier)
            if replacement is None:
                return match.group(0)
            return f"url(#{replacement})"

        return _URL_REFERENCE.sub(replace, value)

    for element in root.iter():
        if identifier := element.get("id"):
            element.set("id", identifiers[identifier])
        for name, value in element.attrib.items():
            local_name = etree.QName(name).localname
            if local_name == "href" and value.startswith("#"):
                identifier = value[1:]
                if replacement := identifiers.get(identifier):
                    element.set(name, f"#{replacement}")
            elif local_name in _REFERENCE_VALUE_ATTRIBUTES:
                element.set(name, rewrite_url_references(value))


class CompositionForge:
    """Place resolved child SVG roots on one parent SVG canvas."""

    def create_media(
        self,
        spec: CompositionSpec,
        *,
        inputs: list[ResolvedCompositionInput],
    ) -> tuple[str, CompositionSpec]:
        """Compose one concrete SVG from already-resolved child SVG data."""
        width, height = spec.canvas_size
        root = etree.Element(
            "{http://www.w3.org/2000/svg}svg",
            nsmap={None: "http://www.w3.org/2000/svg"},
            width=str(width),
            height=str(height),
        )
        if spec.background != "transparent":
            etree.SubElement(
                root,
                "{http://www.w3.org/2000/svg}rect",
                x="0",
                y="0",
                width=str(width),
                height=str(height),
                fill=spec.background,
            )
        for index, item in enumerate(inputs):
            child_root = etree.fromstring(item.svg.encode("utf-8"))
            _namespace_svg_ids(child_root, prefix=f"input-{index}-")
            x, y = item.ref.offset
            group = etree.SubElement(
                root,
                "{http://www.w3.org/2000/svg}g",
                transform=f"translate({x},{y})",
            )
            group.append(deepcopy(child_root))
        svg = etree.tostring(root, encoding="unicode")
        return svg, spec.model_copy(
            update={
                "renderer_name": "svg-compositor",
                "renderer_version": spec.compositor_version,
                "resolved_input_hashes": [item.ref.content_hash for item in inputs],
            }
        )


@on_create_media.register(priority=Priority.NORMAL)
def create_composition_media(
    spec: CompositionSpec,
    ctx: dict[str, Any] | None = None,
) -> tuple[str, CompositionSpec]:
    """Create a composition from the render plan prepared by media provisioning."""
    if ctx is None or COMPOSITION_INPUTS_CONTEXT_KEY not in ctx:
        raise ValueError("Composition creation requires resolved composition inputs")
    inputs = ctx[COMPOSITION_INPUTS_CONTEXT_KEY]
    if not isinstance(inputs, list) or not all(
        isinstance(item, ResolvedCompositionInput) for item in inputs
    ):
        raise TypeError("Composition creation requires resolved composition inputs")
    return CompositionForge().create_media(spec, inputs=inputs)


create_composition_media._behavior.wants_caller_kind = CompositionSpec
