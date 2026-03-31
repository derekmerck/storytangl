from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from importlib.resources import files
from typing import Any, Self

from pydantic import model_validator

from tangl.core import Priority
from tangl.media.media_creators.media_shot_plan import MediaShotPlan
from tangl.media.media_creators.media_spec import MediaResolutionClass, on_adapt_media_spec
from tangl.media.media_data_type import MediaDataType

from ..stable_forge.stable_spec import StableSpec
from .comfy_api import ComfyWorkflow

_REQUIRED_TEMPLATE_TITLES = (
    "checkpoint_loader",
    "positive_prompt",
    "negative_prompt",
    "latent_image",
    "ksampler",
    "save_image",
)

_COMFY_SHOT_DEFAULTS = {
    "portrait": {
        "visual_workflow": "portrait_txt2img",
        "visual_dims": (512, 768),
        "visual_prompt_open": "portrait of a character",
    },
    "establishing": {
        "visual_workflow": "establishing_txt2img",
        "visual_dims": (896, 512),
        "visual_prompt_open": "wide establishing shot",
    },
}


class ComfySpec(StableSpec):
    """Workflow-templated ComfyUI image spec for Comfy sync or async generation."""

    resolution_class: MediaResolutionClass = MediaResolutionClass.ASYNC
    data_type: MediaDataType = MediaDataType.IMAGE

    workflow_template: str | None = None
    workflow: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _validate_workflow_source(self) -> Self:
        if not self.workflow and not self.workflow_template and not self.shot_type:
            raise ValueError(
                "ComfySpec requires workflow, workflow_template, or shot_type"
            )
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

    @classmethod
    def _apply_shot_defaults(cls, spec: "ComfySpec", ctx: dict[str, Any]) -> None:
        shot_type = spec.shot_type
        if not isinstance(shot_type, str) or not shot_type:
            return
        defaults = _COMFY_SHOT_DEFAULTS.get(shot_type)
        if defaults is None:
            return
        ctx.setdefault("visual_shot_type", shot_type)
        for key, value in defaults.items():
            ctx.setdefault(key, value)

    def build_shot_plan(self, *, ctx: Mapping[str, Any] | None = None) -> MediaShotPlan:
        scratch = dict(ctx) if isinstance(ctx, Mapping) else {}
        self._apply_shot_defaults(self, scratch)
        return MediaShotPlan.from_ctx_and_spec(spec=self, ctx=scratch)

    def apply_shot_plan(self, plan: MediaShotPlan) -> None:
        if plan.workflow_template is not None:
            self.workflow_template = plan.workflow_template
        if plan.dims is not None:
            self.dims = plan.dims
        if plan.checkpoint is not None:
            self.model = plan.checkpoint
        self.prompt = plan.render_prompt(base_prompt=self.prompt)
        self.n_prompt = plan.render_negative_prompt(base_prompt=self.n_prompt)

    def materialize_workflow(self) -> dict[str, Any]:
        if self.workflow is None and self.workflow_template is None and self.shot_type is not None:
            self.apply_shot_plan(self.build_shot_plan())

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
    def apply_shot_defaults(self, ctx: dict[str, Any] | None = None):
        if ctx is None:
            return self
        self._apply_shot_defaults(self, ctx)
        return self

    @on_adapt_media_spec.register(priority=Priority.LATE)
    def apply_media_shot_plan(self, ctx: Mapping[str, Any] | None = None):
        self.apply_shot_plan(self.build_shot_plan(ctx=ctx))
        return self


ComfySpec.apply_shot_defaults._behavior.wants_caller_kind = ComfySpec
ComfySpec.apply_media_shot_plan._behavior.wants_caller_kind = ComfySpec
