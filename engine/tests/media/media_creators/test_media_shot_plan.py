"""Tests for the transient media shot-plan microconcept.

Organized by functionality:
- Construction: normalize spec fields and media-private scratch context
- Rendering: build prompt strings without duplicating fragments
"""

from __future__ import annotations

import pytest

from tangl.media.media_creators.comfy_forge import ComfySpec
from tangl.media.media_creators.media_shot_plan import MediaShotPlan


class TestMediaShotPlanConstruction:
    """Tests for building shot plans from authored spec state and scratch context."""

    def test_from_ctx_and_spec_normalizes_shot_defaults_and_fragments(self) -> None:
        spec = ComfySpec(shot_type="portrait")

        plan = MediaShotPlan.from_ctx_and_spec(
            spec=spec,
            ctx={
                "visual_workflow": "portrait_txt2img",
                "visual_dims": (512, 768),
                "visual_prompt_open": "portrait of a character",
                "look_media_payload": {"description": "with navy hair and shaved sides"},
                "style_description": "painted storybook illustration",
            },
        )

        assert plan.shot_type == "portrait"
        assert plan.workflow_template == "portrait_txt2img"
        assert plan.dims == (512, 768)
        assert plan.prompt_open == "portrait of a character"
        assert plan.subject_fragments == ["with navy hair and shaved sides"]
        assert plan.style_fragments == ["painted storybook illustration"]

    def test_from_ctx_and_spec_rejects_unsupported_shot_type(self) -> None:
        spec = ComfySpec(
            workflow_template="portrait_txt2img",
            shot_type="closeup",
        )

        with pytest.raises(ValueError, match="Unsupported media shot_type"):
            MediaShotPlan.from_ctx_and_spec(spec=spec, ctx={})


class TestMediaShotPlanRendering:
    """Tests for prompt assembly from shot-plan fragments."""

    def test_render_prompt_uses_prompt_open_when_base_prompt_missing(self) -> None:
        plan = MediaShotPlan(
            prompt_open="portrait of a character",
            subject_fragments=["with navy hair and shaved sides"],
            style_fragments=["painted storybook illustration"],
        )

        assert plan.render_prompt() == (
            "portrait of a character, "
            "with navy hair and shaved sides, painted storybook illustration"
        )

    def test_render_prompt_appends_only_missing_fragments(self) -> None:
        plan = MediaShotPlan(
            prompt_open="portrait of a character",
            subject_fragments=["with navy hair and shaved sides"],
            style_fragments=["painted storybook illustration"],
        )

        rendered = plan.render_prompt(
            base_prompt="portrait of a character with navy hair and shaved sides"
        )

        assert rendered == (
            "portrait of a character with navy hair and shaved sides, "
            "painted storybook illustration"
        )

    def test_render_negative_prompt_avoids_duplicate_suffixes(self) -> None:
        plan = MediaShotPlan(negative_prompt="low quality, blurry")

        assert plan.render_negative_prompt(base_prompt="low quality, blurry") == "low quality, blurry"
        assert plan.render_negative_prompt(base_prompt="bad anatomy") == "bad anatomy, low quality, blurry"
