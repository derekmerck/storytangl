"""An explicit PNG derivative of a graph-owned SVG resource."""
from __future__ import annotations

from hashlib import sha256
import math
from typing import Any, Literal
from uuid import UUID

from pydantic import Field
from lxml import etree

from tangl.core import Priority
from tangl.media.media_creators.media_spec import MediaResolutionClass, MediaSpec, on_create_media
from tangl.media.media_data_type import MediaDataType

MASK_REVISION = "2"


class SvgPngSpec(MediaSpec):
    resolution_class: MediaResolutionClass = MediaResolutionClass.FAST_SYNC
    data_type: MediaDataType = MediaDataType.IMAGE
    source_id: UUID
    source_hash: bytes
    source_sha256: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    background: Literal["transparent", "white"] = "transparent"
    aspect: Literal["contain"] = "contain"
    renderer: Literal["chromium"] = "chromium"
    renderer_version: str = ""
    mask_region: str | None = None
    mask_regions: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    mask_occluders: tuple[str, ...] = ()
    mask_revision: str = MASK_REVISION

    def fingerprint_payload(self) -> dict[str, Any]:
        data = self.normalized_spec_payload()
        for field in ("source_id", "label", "tags", "resolution_class", "persistence_policy"):
            data.pop(field, None)
        if self.mask_region is None:
            data.pop("mask_regions", None)
            data.pop("mask_occluders", None)
            data.pop("mask_revision", None)
        return data


class SvgPngInputError(ValueError):
    """A PNG request cannot use its referenced SVG source."""


@on_create_media.register(priority=Priority.NORMAL)
def create_svg_png(spec: SvgPngSpec, ctx: dict[str, Any] | None = None) -> tuple[bytes, SvgPngSpec]:
    from .render_playwright import render_svg

    if ctx is None or "vector_source" not in ctx:
        raise SvgPngInputError("PNG creation requires a resolved SVG source")
    if not spec.renderer_version:
        raise SvgPngInputError("PNG creation requires a resolved renderer version")
    source = ctx["vector_source"]
    if sha256(source.encode()).hexdigest() != spec.source_sha256:
        raise SvgPngInputError("PNG source content changed")
    try:
        root = etree.fromstring(source.encode(), etree.XMLParser(resolve_entities=False, no_network=True))
    except etree.XMLSyntaxError as exc:
        raise SvgPngInputError("PNG source must be valid SVG") from exc
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise SvgPngInputError("PNG source must be SVG")
    try:
        box = tuple(float(item) for item in root.get("viewBox", "").replace(",", " ").split())
    except ValueError as exc:
        raise SvgPngInputError("PNG source requires a valid viewBox") from exc
    if len(box) != 4 or not all(math.isfinite(item) for item in box) or box[2] <= 0 or box[3] <= 0:
        raise SvgPngInputError("PNG source requires a valid viewBox")
    if spec.mask_region is not None:
        from .region_mask import region_mask_svg
        try:
            source = region_mask_svg(source, regions=spec.mask_regions,
                                     occluders=spec.mask_occluders, region=spec.mask_region)
        except ValueError as exc:
            raise SvgPngInputError(str(exc)) from exc
    return render_svg(source, (spec.width, spec.height), background=spec.background,
                      identity=spec.renderer_version), spec


create_svg_png._behavior.wants_caller_kind = SvgPngSpec
