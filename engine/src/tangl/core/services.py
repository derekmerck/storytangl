from __future__ import annotations

"""Minimal service-layer protocol definitions used by legacy models."""

from typing import Any, Mapping

from tangl.core.dispatch import DispatchRegistry


class HasContext:
    """Mixin providing a rendering context namespace."""

    def get_context(self) -> Mapping[str, Any]:  # pragma: no cover - trivial shim
        return {}


class Renderable(HasContext):
    """Placeholder base class for renderable entities."""

    def render(self, **_: Any) -> str:  # pragma: no cover - trivial shim
        return ""


on_gather_context = DispatchRegistry(label="on_gather_context")
on_render_content = DispatchRegistry(label="on_render_content")
