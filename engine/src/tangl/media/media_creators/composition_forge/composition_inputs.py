"""Resolve persisted composition inputs before local SVG rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tangl.core import Graph
from tangl.media.media_resource.media_resource_inv_tag import (
    MediaRITStatus,
    MediaResourceInventoryTag as MediaRIT,
)

from .composition_spec import CompositionInputRef, CompositionSpec

COMPOSITION_INPUTS_CONTEXT_KEY = "composition_inputs"


class CompositionInputUnavailable(ValueError):
    """Raised when a referenced child cannot safely contribute to composition."""


@dataclass(frozen=True)
class ResolvedCompositionInput:
    """One validated child SVG passed to the compositor."""

    ref: CompositionInputRef
    svg: str


def with_composition_inputs(
    ctx: dict[str, Any] | None,
    inputs: list[ResolvedCompositionInput],
) -> dict[str, Any]:
    """Return a creation context carrying a resolved composition render plan."""
    result = dict(ctx or {})
    result[COMPOSITION_INPUTS_CONTEXT_KEY] = inputs
    return result


def resolve_composition_inputs(
    spec: CompositionSpec,
    *,
    graph: Graph,
) -> list[ResolvedCompositionInput]:
    """Return graph-owned, resolved child SVGs matching their persisted hashes."""
    resolved: list[ResolvedCompositionInput] = []
    for ref in spec.inputs:
        rit = graph.get(ref.rit_id)
        if not isinstance(rit, MediaRIT):
            raise CompositionInputUnavailable(
                f"Composition input {ref.role!r} is not a media RIT"
            )
        if rit.status is not MediaRITStatus.RESOLVED:
            raise CompositionInputUnavailable(f"Composition input {ref.role!r} is not resolved")
        if rit.get_content_hash() != ref.content_hash:
            raise CompositionInputUnavailable(f"Composition input {ref.role!r} content hash changed")
        if rit.path is not None:
            try:
                svg = rit.path.read_text(encoding="utf-8")
            except OSError as exc:
                raise CompositionInputUnavailable(
                    f"Composition input {ref.role!r} could not be read"
                ) from exc
        elif isinstance(rit.data, str):
            svg = rit.data
        else:
            raise CompositionInputUnavailable(f"Composition input {ref.role!r} has no SVG source")
        resolved.append(ResolvedCompositionInput(ref=ref, svg=svg))
    return resolved
