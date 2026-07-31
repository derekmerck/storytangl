"""Presence-side projection from look payloads to renderer-neutral portraits."""

from __future__ import annotations

from tangl.media.media_creators.portrait_spec import PortraitSpec

from .look import LookMediaPayload


def portrait_spec_from_look(
    payload: LookMediaPayload,
    *,
    identity_key: str,
    explicit_seed: str | int | None = None,
    style_profile: str | None = None,
) -> PortraitSpec:
    """Project one structured look payload without importing a renderer into presence."""
    return PortraitSpec(
        media_role=payload.media_role,
        identity_key=identity_key,
        explicit_seed=explicit_seed,
        description=payload.description,
        traits=dict(payload.traits),
        style_profile=style_profile,
    )
