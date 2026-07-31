"""Small local SVG compositor with no graph or provisioning knowledge."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from lxml import etree

from tangl.core import Priority
from tangl.media.media_creators.media_spec import on_create_media

from .composition_inputs import COMPOSITION_INPUTS_CONTEXT_KEY, ResolvedCompositionInput
from .composition_spec import CompositionSpec


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
        for item in inputs:
            child_root = etree.fromstring(item.svg.encode("utf-8"))
            x, y = item.ref.offset
            group = etree.SubElement(
                root,
                "{http://www.w3.org/2000/svg}g",
                id=item.ref.role,
                transform=f"translate({x},{y})",
            )
            for child in child_root:
                group.append(deepcopy(child))
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
