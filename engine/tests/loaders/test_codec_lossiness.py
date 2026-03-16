"""Tests for loader codec loss-reporting contracts.

Organized by behavior:
- Loss-reporting types: public loader surface and defaults.
- WorldCompiler propagation: structured loss records survive compile plumbing.
"""
from __future__ import annotations

import json
from pathlib import Path

from tangl.loaders import CodecRegistry, LossKind, LossRecord, WorldBundle
from tangl.loaders.codec import DecodeResult, NearNativeYamlCodec
from tangl.loaders.compiler import WorldCompiler


class _LossyCodec:
    """Minimal test codec that emits structured loss records."""

    codec_id = "lossy_test"

    def decode(self, *, bundle: WorldBundle, script_paths: list[Path], story_key: str | None) -> DecodeResult:
        _ = bundle, script_paths, story_key
        return DecodeResult(
            story_data={
                "label": "lossy_world",
                "metadata": {
                    "title": "Lossy World",
                    "start_at": "world.start",
                },
                "scenes": {
                    "world": {
                        "blocks": {
                            "start": {
                                "content": "Hello",
                                "actions": [],
                            }
                        }
                    }
                },
            },
            codec_state={"codec_id": self.codec_id},
            loss_records=[
                LossRecord(
                    kind=LossKind.UNSUPPORTED_FEATURE,
                    feature="macros:if",
                    passage="Start",
                    excerpt="<<if $torch>>",
                ),
                LossRecord(
                    kind=LossKind.AUTHORING_DEBT,
                    feature="source:dangling_link",
                    passage="Start",
                    excerpt="Missing",
                ),
            ],
        )

    def encode(
        self,
        *,
        bundle: WorldBundle,
        runtime_data: dict,
        story_key: str | None,
        codec_state: dict | None = None,
    ) -> dict[str, str]:
        _ = bundle, runtime_data, story_key, codec_state
        raise NotImplementedError


def _write_world(tmp_path: Path, *, label: str, world_yaml: str, script_name: str, script_text: str) -> WorldBundle:
    root = tmp_path / label
    root.mkdir()
    (root / "world.yaml").write_text(world_yaml.strip(), encoding="utf-8")
    (root / script_name).write_text(script_text, encoding="utf-8")
    return WorldBundle.load(root)


class TestLossReportingTypes:
    """Tests for structured loader loss-reporting primitives."""

    def test_loss_kind_values_are_strings(self) -> None:
        assert LossKind.UNSUPPORTED_FEATURE.value == "unsupported_feature"
        assert LossKind.SOURCE_INTEGRITY.value == "source_integrity"
        assert LossKind.AUTHORING_DEBT.value == "authoring_debt"

    def test_loss_record_defaults_note_to_none(self) -> None:
        record = LossRecord(
            kind=LossKind.SOURCE_INTEGRITY,
            feature="source:duplicate_passage",
            passage="Start",
            excerpt="Start",
        )

        assert record.note is None

    def test_decode_result_defaults_loss_records_to_empty(self) -> None:
        result = DecodeResult(story_data={})

        assert result.loss_records == []

    def test_near_native_yaml_codec_emits_no_loss_records(self, tmp_path: Path) -> None:
        bundle = _write_world(
            tmp_path,
            label="lossless_world",
            world_yaml="""
label: lossless_world
scripts: script.yaml
            """,
            script_name="script.yaml",
            script_text="""
label: lossless_world
metadata:
  title: Lossless World
scenes:
  world:
    blocks:
      start:
        content: Hello
            """.strip(),
        )

        result = NearNativeYamlCodec().decode(
            bundle=bundle,
            script_paths=bundle.get_script_paths(),
            story_key=None,
        )

        assert result.loss_records == []


class TestWorldCompilerLossPropagation:
    """Tests for propagating structured decode losses into compiled worlds."""

    def test_compiler_serializes_loss_records_into_codec_state(self, tmp_path: Path) -> None:
        bundle = _write_world(
            tmp_path,
            label="lossy_bundle",
            world_yaml="""
label: lossy_bundle
codec: lossy_test
scripts: story.fake
            """,
            script_name="story.fake",
            script_text="placeholder",
        )
        registry = CodecRegistry()
        registry.register("lossy_test", _LossyCodec())

        world = WorldCompiler(codec_registry=registry).compile(bundle)

        assert world.bundle.codec_state["loss_record_count"] == 2
        assert world.bundle.codec_state["loss_records"] == [
            {
                "kind": "unsupported_feature",
                "feature": "macros:if",
                "passage": "Start",
                "excerpt": "<<if $torch>>",
                "note": None,
            },
            {
                "kind": "authoring_debt",
                "feature": "source:dangling_link",
                "passage": "Start",
                "excerpt": "Missing",
                "note": None,
            },
        ]
        json.dumps(world.bundle.codec_state)

