"""Offline SVG generation through the official DiceBear Python implementation."""

from __future__ import annotations

from importlib.metadata import version

from dicebear import Avatar

from .dicebear_spec import DiceBearSpec, lorelei_style


class DiceBearForge:
    """Render one Lorelei ``DiceBearSpec`` and retain DiceBear's resolved options."""

    def create_media(self, spec: DiceBearSpec) -> tuple[str, DiceBearSpec]:
        result = Avatar(lorelei_style(), spec.options).to_json()
        return result["svg"], spec.model_copy(
            update={
                "renderer_name": "dicebear-core",
                "renderer_version": version("dicebear-core"),
                "resolved_options": result["options"],
            }
        )
