"""Production encode orchestration for canonical near-native story data."""

from __future__ import annotations

from pathlib import Path

from pytest import raises

from tangl.loaders import NearNativeYamlCodec, WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.story import World


def _write_bundle(root: Path, *, label: str) -> WorldBundle:
    root.mkdir()
    scripts_dir = root / "scripts"
    scripts_dir.mkdir()
    (root / "world.yaml").write_text(
        f"label: {label}\nscripts: scripts/story.yaml\n",
        encoding="utf-8",
    )
    (scripts_dir / "story.yaml").write_text(
        f"label: {label}\nscenes: {{}}\n",
        encoding="utf-8",
    )
    return WorldBundle.load(root)


def test_reference_world_encodes_to_a_canonical_near_native_fixed_point(tmp_path: Path) -> None:
    reference_root = Path("worlds/reference")
    bundle = WorldBundle.load(reference_root)
    compiler = WorldCompiler()
    world = compiler.compile(bundle)
    canonical = compiler.story_compiler.decompile(world.bundle)
    original_source = (reference_root / "script.yaml").read_text(encoding="utf-8")

    emitted = compiler.encode(bundle, world.bundle)

    output_root = tmp_path / "reference"
    output_root.mkdir()
    (output_root / "world.yaml").write_text(
        (reference_root / "world.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    for relative_path, content in emitted.items():
        target = output_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    World.clear_instances()
    recompiled = WorldCompiler().compile(WorldBundle.load(output_root))

    assert emitted.keys() == {"script.yaml"}
    assert (reference_root / "script.yaml").read_text(encoding="utf-8") == original_source
    assert compiler.story_compiler.decompile(world.bundle) == canonical
    assert compiler.story_compiler.decompile(recompiled.bundle) == canonical


def test_near_native_encode_uses_only_safe_relative_output_paths(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path / "safe_paths", label="safe_paths")
    codec = NearNativeYamlCodec()
    runtime_data = {"label": "safe_paths", "scenes": {}}

    in_bundle = codec.encode(
        bundle=bundle,
        runtime_data=runtime_data,
        story_key=None,
        codec_state={"script_paths": [str(bundle.bundle_root / "scripts/story.yaml")]},
    )
    unsafe = codec.encode(
        bundle=bundle,
        runtime_data=runtime_data,
        story_key=None,
        codec_state={"script_paths": [str(tmp_path / "foreign.yaml")]},
    )
    escaped = codec.encode(
        bundle=bundle,
        runtime_data=runtime_data,
        story_key=None,
        codec_state={"script_paths": ["../foreign.yaml"]},
    )
    absent = codec.encode(
        bundle=bundle,
        runtime_data=runtime_data,
        story_key=None,
    )

    assert in_bundle.keys() == {"scripts/story.yaml"}
    assert unsafe.keys() == {"script.yaml"}
    assert escaped.keys() == {"script.yaml"}
    assert absent.keys() == {"script.yaml"}
    assert runtime_data == {"label": "safe_paths", "scenes": {}}


def test_encode_rejects_a_compiled_codec_that_disagrees_with_the_manifest(
    tmp_path: Path,
) -> None:
    bundle = _write_bundle(tmp_path / "codec_mismatch", label="codec_mismatch")
    compiler = WorldCompiler()
    world = compiler.compile(bundle)
    world.bundle.codec_id = "twine"

    with raises(ValueError, match="disagrees with manifest codec"):
        compiler.encode(bundle, world.bundle)
