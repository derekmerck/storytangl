"""Reference world loading and raw-dict compiler contract tests.

Organized by behavior:
- Reference world pipeline: bundle -> codec -> compiler -> world -> story.
- IR decoupling: raw dict compilation remains valid without IR gating.
- Loader integration: world registry preserves codec provenance.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tangl.core import Selector
from tangl.loaders.bundle import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.service.world_registry import WorldRegistry
from tangl.story import World
from tangl.story.concepts import Actor
from tangl.story.fabula import StoryCompiler


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def reference_root() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds" / "reference"


@pytest.fixture(scope="module")
def reference_bundle(reference_root: Path) -> WorldBundle:
    return WorldBundle.load(reference_root)


@pytest.fixture()
def reference_world(reference_bundle: WorldBundle) -> World:
    return WorldCompiler().compile(reference_bundle)


@pytest.fixture(scope="module")
def reference_script_data(reference_root: Path) -> dict[str, Any]:
    return yaml.safe_load((reference_root / "script.yaml").read_text(encoding="utf-8"))


# ============================================================================
# Reference World Pipeline
# ============================================================================

class TestReferenceWorldLoads:
    """Tests for the end-to-end reference world loading path."""

    def test_bundle_loads(self, reference_bundle: WorldBundle) -> None:
        assert reference_bundle.manifest.label == "reference"
        assert reference_bundle.get_story_codec() == "near_native"
        assert reference_bundle.script_paths == [reference_bundle.bundle_root / "script.yaml"]

    def test_world_compiles(self, reference_world: World) -> None:
        assert reference_world.label == "reference"
        assert reference_world.metadata["title"] == "The Crossroads Inn"

    def test_template_tree_is_complete(self, reference_world: World) -> None:
        labels = {template.get_label() for template in reference_world.find_templates()}

        assert "crossroads_inn" in labels
        assert {"prologue", "chapter1", "epilogue"} <= labels
        assert {
            "prologue.start",
            "prologue.meet_aria",
            "prologue.request_help",
            "prologue.innkeeper",
            "prologue.rumors",
            "chapter1.trail_start",
            "chapter1.forest_encounter",
            "epilogue.left_path",
            "epilogue.right_path",
            "epilogue.end",
        } <= labels

    def test_scene_level_templates_compile(self, reference_world: World) -> None:
        aria_template = next(
            (
                template
                for template in reference_world.find_templates()
                if template.get_label() == "prologue.aria"
            ),
            None,
        )

        assert aria_template is not None
        assert isinstance(aria_template.payload, Actor)
        assert aria_template.payload.name == "Aria"

    def test_entry_template_resolves(self, reference_world: World) -> None:
        assert reference_world.bundle.entry_template_ids == ["prologue.start"]

    def test_story_materializes(self, reference_world: World) -> None:
        result = reference_world.create_story("crossroads")

        assert result.graph is not None
        assert result.graph.label == "crossroads"
        assert len(result.entry_ids) == 1
        assert result.report.materialized_counts.get("Scene") == 3
        assert result.report.materialized_counts.get("Block") == 10
        assert result.report.materialized_counts.get("Actor") == 1
        assert not result.report.unresolved_hard


# ============================================================================
# IR Decoupling
# ============================================================================

class TestCompilerIRDecoupling:
    """Tests for compiling runtime-ready dicts without IR gating."""

    def test_compile_from_raw_dict(self, reference_script_data: dict[str, Any]) -> None:
        bundle = StoryCompiler().compile(reference_script_data)

        assert bundle.template_registry is not None
        assert bundle.entry_template_ids == ["prologue.start"]
        assert bundle.metadata["title"] == "The Crossroads Inn"

    def test_compile_from_raw_dict_with_locals_key(self) -> None:
        bundle = StoryCompiler().compile(
            {
                "label": "locals_test",
                "locals": {"mood": "cheerful"},
                "scenes": {},
            }
        )

        assert bundle.locals == {"mood": "cheerful"}

    def test_compile_from_raw_dict_with_globals_key(self) -> None:
        bundle = StoryCompiler().compile(
            {
                "label": "globals_test",
                "globals": {"mood": "gloomy"},
                "scenes": {},
            }
        )

        assert bundle.locals == {"mood": "gloomy"}

    def test_compile_from_raw_dict_unknown_media_role_survives(self) -> None:
        bundle = StoryCompiler().compile(
            {
                "label": "custom_media",
                "scenes": {
                    "s1": {
                        "blocks": {
                            "b1": {
                                "content": "Hello",
                                "media": [{"name": "pic.png", "media_role": "hologram_3d"}],
                                "actions": [],
                            }
                        }
                    }
                },
            }
        )

        block_template = bundle.template_registry.find_one(Selector(has_identifier="s1.b1"))

        assert block_template is not None
        assert block_template.payload.media == [
            {"name": "pic.png", "media_role": "hologram_3d"}
        ]

    def test_compile_from_validated_storyscript_still_works(
        self,
        reference_script_data: dict[str, Any],
    ) -> None:
        script = StoryCompiler.validate_ir(reference_script_data)
        bundle = StoryCompiler().compile(script)

        assert bundle.entry_template_ids == ["prologue.start"]

    def test_validate_ir_catches_schema_errors(self) -> None:
        with pytest.raises(ValidationError):
            StoryCompiler.validate_ir(
                {
                    "label": "bad",
                    "scenes": "not_a_dict_or_list",
                }
            )

    def test_raw_dict_with_successor_field_variants(self) -> None:
        for field_name in ("successor", "target_ref", "successor_ref"):
            bundle = StoryCompiler().compile(
                {
                    "label": f"succ_test_{field_name}",
                    "scenes": {
                        "main": {
                            "blocks": {
                                "a": {
                                    "content": "start",
                                    "actions": [{"text": "Go", field_name: "b"}],
                                },
                                "b": {
                                    "content": "end",
                                    "actions": [],
                                },
                            }
                        }
                    },
                }
            )

            block_a = bundle.template_registry.find_one(Selector(has_identifier="main.a"))
            assert block_a is not None
            assert len(block_a.payload.actions) == 1
            assert block_a.payload.actions[0].get("successor_ref") == "main.b"


# ============================================================================
# WorldCompiler Integration
# ============================================================================

class TestWorldCompilerCodecIntegration:
    """Tests for bundle loading through the codec and world registry path."""

    def test_near_native_codec_produces_world(self, reference_bundle: WorldBundle) -> None:
        world = WorldCompiler().compile(reference_bundle)

        assert isinstance(world, World)
        assert world.bundle.codec_id == "near_native_yaml"
        assert world.bundle.codec_state["codec_id"] == "near_native_yaml"

    def test_codec_state_preserves_source_provenance(
        self,
        reference_bundle: WorldBundle,
    ) -> None:
        world = WorldCompiler().compile(reference_bundle)
        state = world.bundle.codec_state

        assert "script_paths" in state
        assert any("script.yaml" in path for path in state["script_paths"])
        assert state["world_label"] == "reference"

    def test_world_registry_loads_reference(self, reference_root: Path) -> None:
        registry = WorldRegistry([reference_root.parent])
        world = registry.get_world("reference")

        assert world.label == "reference"
        assert world.metadata["title"] == "The Crossroads Inn"
