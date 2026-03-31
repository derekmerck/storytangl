from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

SUPPORTED_MEDIA_SHOT_TYPES = {"portrait", "establishing"}
STYLE_KEYS = (
    "art_style",
    "art_style_desc",
    "style",
    "style_description",
    "visual_style",
    "world_style",
)


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _mapping_description(value: Any) -> str | None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python", exclude_none=True)
    if not isinstance(value, Mapping):
        return None
    return _string_value(value.get("description"))


def _normalized_dims(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    width, height = value
    if not isinstance(width, int) or not isinstance(height, int):
        return None
    return width, height


def _unique_fragments(*values: str | None) -> list[str]:
    fragments: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _string_value(value)
        if text is None:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        fragments.append(text)
    return fragments


class MediaShotPlanSpec(Protocol):
    shot_type: str | None
    prompt: str | None
    n_prompt: str | None
    dims: tuple[int, int] | None
    model: str | None
    workflow_template: str | None


@dataclass(slots=True)
class MediaShotPlan:
    """Transient backend-agnostic visual shot assembly artifact."""

    shot_type: str | None = None
    workflow_template: str | None = None
    dims: tuple[int, int] | None = None
    checkpoint: str | None = None
    prompt_open: str | None = None
    negative_prompt: str | None = None
    subject_fragments: list[str] = field(default_factory=list)
    style_fragments: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_ctx_and_spec(
        cls,
        *,
        spec: MediaShotPlanSpec,
        ctx: Mapping[str, Any] | None = None,
    ) -> "MediaShotPlan":
        shot_type = _string_value(spec.shot_type)
        if shot_type is None and isinstance(ctx, Mapping):
            shot_type = _string_value(ctx.get("visual_shot_type") or ctx.get("shot_type"))
        if shot_type is not None and shot_type not in SUPPORTED_MEDIA_SHOT_TYPES:
            raise ValueError(
                f"Unsupported media shot_type {shot_type!r}; "
                f"expected one of {sorted(SUPPORTED_MEDIA_SHOT_TYPES)!r}"
            )

        subject_fragments: list[str] = []
        style_fragments: list[str] = []
        prompt_open = None
        negative_prompt = None
        workflow_template = _string_value(spec.workflow_template)
        dims = _normalized_dims(spec.dims)
        checkpoint = _string_value(spec.model)

        if isinstance(ctx, Mapping):
            subject_fragments = _unique_fragments(
                _mapping_description(ctx.get("look_media_payload")),
                _string_value(ctx.get("look_description")),
                _string_value(ctx.get("outfit_description")),
                _string_value(ctx.get("ornament_description")),
            )
            style_fragments = _unique_fragments(*[_string_value(ctx.get(key)) for key in STYLE_KEYS])
            prompt_open = _string_value(ctx.get("visual_prompt_open"))
            negative_prompt = _string_value(
                ctx.get("visual_negative") or ctx.get("negative_prompt") or ctx.get("n_prompt")
            )
            workflow_template = workflow_template or _string_value(ctx.get("visual_workflow"))
            dims = dims or _normalized_dims(ctx.get("visual_dims"))
            checkpoint = checkpoint or _string_value(ctx.get("visual_checkpoint"))

        return cls(
            shot_type=shot_type,
            workflow_template=workflow_template,
            dims=dims,
            checkpoint=checkpoint,
            prompt_open=prompt_open,
            negative_prompt=negative_prompt,
            subject_fragments=subject_fragments,
            style_fragments=style_fragments,
        )

    def prompt_fragments(self, *, include_open: bool = True) -> list[str]:
        opening = [self.prompt_open] if include_open else []
        return _unique_fragments(
            *opening,
            *self.subject_fragments,
            *self.style_fragments,
        )

    def render_prompt(self, *, base_prompt: str | None = None) -> str | None:
        base = _string_value(base_prompt)
        if base is None:
            fragments = self.prompt_fragments(include_open=True)
            return ", ".join(fragments) or None

        fragments = self.prompt_fragments(include_open=False)
        extra = [item for item in fragments if item.casefold() not in base.casefold()]
        if not extra:
            return base
        return f"{base}, {', '.join(extra)}"

    def render_negative_prompt(self, *, base_prompt: str | None = None) -> str | None:
        base = _string_value(base_prompt)
        if self.negative_prompt is None:
            return base
        if base is None:
            return self.negative_prompt
        if self.negative_prompt.casefold() in base.casefold():
            return base
        return f"{base}, {self.negative_prompt}"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "subject_fragments": list(self.subject_fragments),
            "style_fragments": list(self.style_fragments),
            "extras": dict(self.extras),
        }
        if self.shot_type is not None:
            payload["shot_type"] = self.shot_type
        if self.workflow_template is not None:
            payload["workflow_template"] = self.workflow_template
        if self.dims is not None:
            payload["dims"] = self.dims
        if self.checkpoint is not None:
            payload["checkpoint"] = self.checkpoint
        if self.prompt_open is not None:
            payload["prompt_open"] = self.prompt_open
        if self.negative_prompt is not None:
            payload["negative_prompt"] = self.negative_prompt
        return payload
