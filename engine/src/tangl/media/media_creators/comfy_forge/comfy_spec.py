from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from importlib.resources import files
from typing import Any, Self

from pydantic import model_validator

from tangl.core import Priority
from tangl.media.media_creators.media_spec import MediaResolutionClass, on_adapt_media_spec
from tangl.media.media_data_type import MediaDataType

from ..stable_forge.stable_spec import StableSpec
from .comfy_api import ComfyWorkflow

_STYLE_KEYS = (
    "art_style",
    "art_style_desc",
    "style",
    "style_description",
    "visual_style",
    "world_style",
)

_REQUIRED_TEMPLATE_TITLES = (
    "checkpoint_loader",
    "positive_prompt",
    "negative_prompt",
    "latent_image",
    "ksampler",
    "save_image",
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
    description = value.get("description")
    return _string_value(description)


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


def _merge_prompt(prompt: str | None, *, ctx: Mapping[str, Any] | None) -> str | None:
    if not isinstance(ctx, Mapping):
        return _string_value(prompt)

    look_payload = _mapping_description(ctx.get("look_media_payload"))
    look_description = _string_value(ctx.get("look_description"))
    outfit_description = _string_value(ctx.get("outfit_description"))
    style_fragments = [_string_value(ctx.get(key)) for key in _STYLE_KEYS]
    fragments = _unique_fragments(
        look_payload,
        look_description,
        outfit_description,
        *style_fragments,
    )

    base_prompt = _string_value(prompt)
    if base_prompt is None:
        return ", ".join(fragments) or None

    extra = [item for item in fragments if item.casefold() not in base_prompt.casefold()]
    if not extra:
        return base_prompt
    return f"{base_prompt}, {', '.join(extra)}"


class ComfySpec(StableSpec):
    """Workflow-templated ComfyUI image spec for Comfy sync or async generation."""

    resolution_class: MediaResolutionClass = MediaResolutionClass.ASYNC
    data_type: MediaDataType = MediaDataType.IMAGE

    workflow_template: str | None = None
    workflow: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _validate_workflow_source(self) -> Self:
        if not self.workflow and not self.workflow_template:
            raise ValueError("ComfySpec requires either workflow or workflow_template")
        return self

    @classmethod
    def _load_packaged_workflow(cls, template_name: str) -> dict[str, Any]:
        filename = template_name if template_name.endswith(".json") else f"{template_name}.json"
        try:
            data = files(__package__).joinpath("workflows", filename).read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ValueError(f"Unknown packaged Comfy workflow template {template_name!r}") from exc
        payload = json.loads(data)
        if not isinstance(payload, dict):
            raise TypeError("Comfy workflow template must decode to a dict")
        return payload

    @classmethod
    def get_creation_service(cls):
        from .comfy_forge import ComfyForge

        return ComfyForge.from_settings() or ComfyForge()

    @staticmethod
    def _set_workflow_value(
        workflow: ComfyWorkflow,
        *,
        field_name: str,
        value: Any,
        title: str,
        key: str,
        source_name: str,
    ) -> None:
        if value is None:
            return
        try:
            workflow.set_input_value(title, value, key=key)
        except KeyError as exc:
            raise ValueError(
                f"Comfy workflow {source_name!r} cannot apply field {field_name!r}: {exc}"
            ) from exc

    @staticmethod
    def _validate_template_contract(workflow: ComfyWorkflow, *, template_name: str) -> None:
        for title in _REQUIRED_TEMPLATE_TITLES:
            try:
                workflow.get_node(title)
            except KeyError as exc:
                raise ValueError(
                    f"Comfy workflow template {template_name!r} is missing required node {title!r}"
                ) from exc

    def materialize_workflow(self) -> dict[str, Any]:
        loaded_from_template = self.workflow is None
        source = self.workflow or self._load_packaged_workflow(str(self.workflow_template))
        workflow = ComfyWorkflow(spec=deepcopy(source))
        source_name = str(self.workflow_template) if loaded_from_template else "inline workflow"

        if loaded_from_template:
            self._validate_template_contract(workflow, template_name=source_name)

        self._set_workflow_value(
            workflow,
            field_name="prompt",
            value=self.prompt,
            title="positive_prompt",
            key="text",
            source_name=source_name,
        )
        self._set_workflow_value(
            workflow,
            field_name="n_prompt",
            value=self.n_prompt,
            title="negative_prompt",
            key="text",
            source_name=source_name,
        )
        self._set_workflow_value(
            workflow,
            field_name="model",
            value=self.model,
            title="checkpoint_loader",
            key="ckpt_name",
            source_name=source_name,
        )
        self._set_workflow_value(
            workflow,
            field_name="seed",
            value=self.seed,
            title="ksampler",
            key="seed",
            source_name=source_name,
        )
        self._set_workflow_value(
            workflow,
            field_name="iterations",
            value=self.iterations,
            title="ksampler",
            key="steps",
            source_name=source_name,
        )
        self._set_workflow_value(
            workflow,
            field_name="sampler",
            value=self.sampler,
            title="ksampler",
            key="sampler_name",
            source_name=source_name,
        )
        if self.dims is not None:
            width, height = self.dims
            self._set_workflow_value(
                workflow,
                field_name="dims",
                value=width,
                title="latent_image",
                key="width",
                source_name=source_name,
            )
            self._set_workflow_value(
                workflow,
                field_name="dims",
                value=height,
                title="latent_image",
                key="height",
                source_name=source_name,
            )

        return workflow.spec

    def normalized_spec_payload(
        self,
        *,
        exclude: set[str] | None = None,
    ) -> dict[str, Any]:
        self.workflow = self.materialize_workflow()
        excluded = set(exclude or ())
        if self.workflow is not None:
            excluded.add("workflow_template")
        return super().normalized_spec_payload(exclude=excluded)

    @on_adapt_media_spec.register(priority=Priority.NORMAL)
    def apply_context_prompt_fragments(self, ctx: Mapping[str, Any] | None = None):
        self.prompt = _merge_prompt(self.prompt, ctx=ctx)
        if self.n_prompt is None and isinstance(ctx, Mapping):
            self.n_prompt = _string_value(ctx.get("negative_prompt") or ctx.get("n_prompt"))
        return self


ComfySpec.apply_context_prompt_fragments._behavior.wants_caller_kind = ComfySpec
