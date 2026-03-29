"""Tests for the Comfy workflow-backed media spec.

Organized by functionality:
- Authoring: alias resolution and required workflow source validation
- Workflow materialization: template loading and node parameterization
- Adaptation: prompt rendering and namespace-driven prompt enrichment
"""

from __future__ import annotations

import pytest

from tangl.media.media_creators.comfy_forge import ComfySpec
from tangl.media.media_creators.media_spec import MediaSpec


class TestComfySpecAuthoring:
    """Tests for authoring-time spec construction."""

    def test_from_authoring_resolves_comfy_alias(self) -> None:
        spec = MediaSpec.from_authoring(
            {
                "kind": "comfy",
                "workflow_template": "portrait_txt2img",
                "prompt": "portrait of a hero",
            }
        )

        assert isinstance(spec, ComfySpec)
        assert spec.workflow_template == "portrait_txt2img"


class TestComfySpecWorkflowMaterialization:
    """Tests for template loading and workflow payload generation."""

    def test_materialize_workflow_populates_standard_titles(self) -> None:
        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of Katya",
            n_prompt="low quality",
            model="realistic.safetensors",
            seed=42,
            sampler="euler_ancestral",
            iterations=28,
            dims=(768, 1024),
        )

        workflow = spec.materialize_workflow()

        assert workflow["1"]["inputs"]["ckpt_name"] == "realistic.safetensors"
        assert workflow["2"]["inputs"]["text"] == "portrait of Katya"
        assert workflow["3"]["inputs"]["text"] == "low quality"
        assert workflow["4"]["inputs"]["width"] == 768
        assert workflow["4"]["inputs"]["height"] == 1024
        assert workflow["5"]["inputs"]["seed"] == 42
        assert workflow["5"]["inputs"]["steps"] == 28
        assert workflow["5"]["inputs"]["sampler_name"] == "euler_ancestral"

    def test_spec_fingerprint_is_deterministic_after_seed_commit(self) -> None:
        first = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of a hero",
        )
        second = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of a hero",
        )

        assert first.spec_fingerprint() == second.spec_fingerprint()
        assert first.workflow is not None
        assert second.workflow is not None

    def test_unknown_packaged_template_raises_clear_error(self) -> None:
        spec = ComfySpec(
            workflow_template="missing_template",
            prompt="portrait of a hero",
        )

        with pytest.raises(ValueError, match="Unknown packaged Comfy workflow template"):
            spec.materialize_workflow()

    def test_missing_node_raises_clear_error_when_field_is_supplied(self) -> None:
        spec = ComfySpec(
            workflow={
                "1": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": ""},
                    "_meta": {"title": "negative_prompt"},
                }
            },
            prompt="portrait of Katya",
        )

        with pytest.raises(ValueError, match="field 'prompt'.*positive_prompt"):
            spec.materialize_workflow()

    def test_missing_input_raises_clear_error_when_field_is_supplied(self) -> None:
        spec = ComfySpec(
            workflow={
                "1": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {"height": 512, "batch_size": 1},
                    "_meta": {"title": "latent_image"},
                }
            },
            dims=(768, 1024),
        )

        with pytest.raises(ValueError, match="field 'dims'.*width"):
            spec.materialize_workflow()

    def test_normalized_payload_includes_workflow_and_omits_template_once_materialized(self) -> None:
        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of Katya",
        )

        payload = spec.normalized_spec_payload()

        assert isinstance(payload["workflow"], dict)
        assert "workflow_template" not in payload


class TestComfySpecAdaptation:
    """Tests for namespace-driven prompt adaptation."""

    def test_prompt_rendering_applies_to_comfy_subclass(self) -> None:
        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of {name}",
        )

        adapted = spec.adapt_spec(ctx={"name": "Katya"})

        assert adapted.prompt == "portrait of Katya"

    def test_namespace_visual_payloads_extend_prompt(self) -> None:
        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of a young woman",
        )

        adapted = spec.adapt_spec(
            ctx={
                "look_media_payload": {"description": "with navy hair and shaved sides"},
                "style_description": "painted storybook illustration",
            }
        )

        assert adapted.prompt == (
            "portrait of a young woman, "
            "with navy hair and shaved sides, painted storybook illustration"
        )
