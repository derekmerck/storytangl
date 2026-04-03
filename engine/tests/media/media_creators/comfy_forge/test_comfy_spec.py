"""Tests for the Comfy workflow-backed media spec.

Organized by functionality:
- Authoring: alias resolution and required workflow/shot sources
- Workflow materialization: template loading and node parameterization
- Adaptation: shot defaults, authored overrides, and namespace-driven prompt assembly
"""

from __future__ import annotations

import pytest

from tangl.lang.body_parts import BodyPart, BodyRegion
from tangl.mechanics.presence.look import EyeColor, HairColor, HairStyle, HasSimpleLook, Look
from tangl.mechanics.presence.look.look import HasLook
from tangl.mechanics.presence.ornaments import Ornament, OrnamentType
from tangl.mechanics.presence.wearable import Wearable, WearableLayer, WearableType
from tangl.media.media_creators.comfy_forge import ComfySpec
from tangl.media.media_creators.media_spec import MediaSpec
from tangl.story.concepts import Actor as StoryActor


@pytest.fixture(autouse=True)
def reset_wearable_types():
    WearableType.clear_instances()
    yield
    WearableType.clear_instances()


def _build_outfit(actor: HasLook) -> None:
    shirt_type = WearableType(
        label="look_shirt",
        noun="shirt",
        covers={BodyRegion.TOP},
        layer=WearableLayer.OUTER,
    )
    coat_type = WearableType(
        label="look_coat",
        noun="coat",
        covers={BodyRegion.TOP},
        layer=WearableLayer.OVER,
    )

    actor.outfit.assign("top_60", Wearable(token_from=shirt_type.label))
    actor.outfit.assign("top_80", Wearable(token_from=coat_type.label))


def _build_ornaments(actor: HasLook) -> None:
    actor.ornamentation.add_ornament(
        Ornament(
            body_part=BodyPart.LEFT_ARM,
            ornament_type=OrnamentType.TATTOO,
            text="a dragon",
        )
    )


class DemoLookOnlyActor(StoryActor, HasSimpleLook):
    """Story actor exposing the direct look facet only."""


class DemoActor(StoryActor, HasLook):
    """Story actor exposing bundled look, outfit, and ornament facets."""


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

    def test_from_authoring_accepts_shot_type_without_explicit_template(self) -> None:
        spec = MediaSpec.from_authoring(
            {
                "kind": "comfy",
                "shot_type": "portrait",
            }
        )

        assert isinstance(spec, ComfySpec)
        assert spec.shot_type == "portrait"
        assert spec.workflow_template is None


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

    def test_materialize_workflow_uses_shot_type_defaults_when_template_not_authored(self) -> None:
        spec = ComfySpec(
            shot_type="portrait",
            prompt="portrait of Katya",
        )

        workflow = spec.materialize_workflow()

        assert spec.workflow_template == "portrait_txt2img"
        assert workflow["2"]["inputs"]["text"] == "portrait of Katya"
        assert workflow["4"]["inputs"]["width"] == 512
        assert workflow["4"]["inputs"]["height"] == 768

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
    """Tests for namespace-driven prompt and shot-plan adaptation."""

    def test_prompt_rendering_applies_to_comfy_subclass(self) -> None:
        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            prompt="portrait of {name}",
        )

        adapted = spec.adapt_spec(ctx={"name": "Katya"})

        assert adapted.prompt == "portrait of Katya"

    def test_missing_shot_type_preserves_explicit_prompt_behavior(self) -> None:
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
        assert adapted.workflow_template == "portrait_txt2img"

    def test_shot_type_portrait_applies_defaults_and_context_fragments(self) -> None:
        spec = ComfySpec(shot_type="portrait")

        adapted = spec.adapt_spec(
            ctx={
                "look_media_payload": {"description": "with navy hair and shaved sides"},
                "style_description": "painted storybook illustration",
            }
        )

        assert adapted.workflow_template == "portrait_txt2img"
        assert adapted.dims == (512, 768)
        assert adapted.prompt == (
            "portrait of a character, "
            "with navy hair and shaved sides, painted storybook illustration"
        )

    def test_shot_type_establishing_applies_landscape_defaults(self) -> None:
        spec = ComfySpec(shot_type="establishing")

        adapted = spec.adapt_spec(ctx={"style_description": "painted storybook illustration"})

        assert adapted.workflow_template == "establishing_txt2img"
        assert adapted.dims == (896, 512)
        assert adapted.prompt == "wide establishing shot, painted storybook illustration"

    def test_authored_fields_override_shot_defaults(self) -> None:
        spec = ComfySpec(
            shot_type="portrait",
            workflow_template="establishing_txt2img",
            dims=(1024, 256),
            model="custom-model.safetensors",
        )

        adapted = spec.adapt_spec(ctx={})

        assert adapted.workflow_template == "establishing_txt2img"
        assert adapted.dims == (1024, 256)
        assert adapted.model == "custom-model.safetensors"

    def test_adapt_spec_does_not_mutate_external_context(self) -> None:
        ctx = {"style_description": "painted storybook illustration"}
        spec = ComfySpec(shot_type="portrait")

        adapted = spec.adapt_spec(ctx=ctx)

        assert adapted.workflow_template == "portrait_txt2img"
        assert "visual_workflow" not in ctx
        assert "visual_dims" not in ctx
        assert "visual_prompt_open" not in ctx

    def test_build_shot_plan_exposes_debuggable_intermediate_state(self) -> None:
        spec = ComfySpec(shot_type="portrait")

        plan = spec.build_shot_plan(
            ctx={
                "look_media_payload": {"description": "with navy hair and shaved sides"},
                "style_description": "painted storybook illustration",
            }
        )

        assert plan.to_dict() == {
            "shot_type": "portrait",
            "workflow_template": "portrait_txt2img",
            "dims": (512, 768),
            "prompt_open": "portrait of a character",
            "subject_fragments": ["with navy hair and shaved sides"],
            "style_fragments": ["painted storybook illustration"],
            "extras": {},
        }

    def test_build_shot_plan_rejects_unsupported_shot_type(self) -> None:
        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            shot_type="closeup",
        )

        with pytest.raises(ValueError, match="Unsupported media shot_type"):
            spec.build_shot_plan(ctx={})

    def test_actor_with_simple_look_contributes_subject_fragments(self) -> None:
        actor = DemoLookOnlyActor(
            label="guide",
            look=Look(
                hair_color=HairColor.AUBURN,
                hair_style=HairStyle.BRAID,
                eye_color=EyeColor.GRAY,
            ),
        )
        spec = ComfySpec(shot_type="portrait")

        plan = spec.build_shot_plan(ctx=actor.get_ns())

        subject_text = " ".join(plan.subject_fragments)
        assert plan.workflow_template == "portrait_txt2img"
        assert "gray eyes" in subject_text
        assert "auburn braid hair" in subject_text

    def test_actor_with_haslook_flows_outfit_and_ornaments_into_prompt(self) -> None:
        actor = DemoActor(
            label="guide",
            look=Look(
                hair_color=HairColor.AUBURN,
                hair_style=HairStyle.BRAID,
                eye_color=EyeColor.GRAY,
            ),
        )
        _build_outfit(actor)
        _build_ornaments(actor)
        spec = ComfySpec(shot_type="portrait")

        adapted = spec.adapt_spec(ctx=actor.get_ns())

        assert adapted.workflow_template == "portrait_txt2img"
        assert "shirt and coat" in adapted.prompt
        assert "a dragon tattoo on their left arm" in adapted.prompt
