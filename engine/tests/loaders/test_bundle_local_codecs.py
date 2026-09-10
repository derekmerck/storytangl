"""Bundle-local codec contributions through ordinary world loading."""

from __future__ import annotations

import importlib
from pathlib import Path

from pytest import MonkeyPatch

from tangl.loaders import DecodeResult, EncodeResult
from tangl.loaders.compiler import WorldCompiler
from tangl.service.service_manager import ServiceManager
from tangl.service.world_registry import (
    WorldRegistry,
    clear_discovered_world_registries,
)
from tangl.story import World


def _write_codec_bundle(
    root: Path,
    *,
    label: str,
    variant: str,
    anthology: bool = False,
    codec_key: str = "local_codec",
) -> str:
    """Write one trusted world domain that contributes a private codec."""

    bundle_root = root / label
    bundle_root.mkdir()
    module_name = f"{label}_domain"
    if anthology:
        manifest = "\n".join(
            [
                f"label: {label}",
                f"domain_module: {module_name}",
                "stories:",
                "  first:",
                f"    codec: {codec_key}",
                "    scripts: first.local",
                "  second:",
                f"    codec: {codec_key}",
                "    scripts: second.local",
            ]
        )
        script_names = ["first.local", "second.local"]
    else:
        manifest = "\n".join(
            [
                f"label: {label}",
                f"domain_module: {module_name}",
                f"codec: {codec_key}",
                "scripts: story.local",
            ]
        )
        script_names = ["story.local"]

    (bundle_root / "world.yaml").write_text(manifest, encoding="utf-8")
    for script_name in script_names:
        (bundle_root / script_name).write_text("local source", encoding="utf-8")

    (bundle_root / f"{module_name}.py").write_text(
        f'''\
from __future__ import annotations

from pathlib import Path
from typing import Any

from tangl.loaders import DecodeResult, EncodeResult, LossKind, LossRecord, WorldBundle

CODEC_CONTRIBUTION_CALLS = 0


class LocalCodec:
    codec_id = "local_codec"

    def decode(
        self,
        *,
        bundle: WorldBundle,
        script_paths: list[Path],
        story_key: str | None,
    ) -> DecodeResult:
        _ = script_paths
        title = "{variant}" if story_key is None else f"{variant}:{{story_key}}"
        return DecodeResult(
            story_data={{
                "label": bundle.manifest.label,
                "metadata": {{"title": title, "start_at": "intro.start"}},
                "scenes": {{
                    "intro": {{"blocks": {{"start": {{"content": title}}}}}},
                }},
            }},
            codec_state={{"codec_id": self.codec_id, "variant": "{variant}"}},
            loss_records=[
                LossRecord(
                    kind=LossKind.AUTHORING_DEBT,
                    feature="local:{variant}",
                    passage="intro.start",
                    excerpt="local source",
                )
            ],
        )

    def encode(
        self,
        *,
        bundle: WorldBundle,
        runtime_data: dict[str, Any],
        story_key: str | None,
        codec_state: dict[str, Any] | None = None,
    ) -> EncodeResult:
        _ = bundle, story_key, codec_state
        return EncodeResult(artifacts={{"local.story": runtime_data["label"]}})


def get_story_codecs() -> dict[str, LocalCodec]:
    global CODEC_CONTRIBUTION_CALLS
    CODEC_CONTRIBUTION_CALLS += 1
    return {{"{codec_key}": LocalCodec()}}
''',
        encoding="utf-8",
    )
    return module_name


def test_world_registry_uses_bundle_local_codec_and_preflight_reports_loss(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    _write_codec_bundle(tmp_path, label="local_alpha", variant="alpha")
    _write_codec_bundle(tmp_path, label="local_beta", variant="beta")

    registry = WorldRegistry([tmp_path])
    alpha = registry.get_world("local_alpha")
    beta = registry.get_world("local_beta")

    assert alpha.metadata["title"] == "alpha"
    assert beta.metadata["title"] == "beta"
    assert alpha.bundle.codec_state["variant"] == "alpha"
    assert beta.bundle.codec_state["variant"] == "beta"
    assert alpha.bundle.codec_state["loss_records"] == [
        {
            "kind": "authoring_debt",
            "feature": "local:alpha",
            "passage": "intro.start",
            "excerpt": "local source",
            "note": None,
        }
    ]

    World.clear_instances()
    clear_discovered_world_registries()
    monkeypatch.setattr("tangl.service.world_registry.get_world_dirs", lambda: [tmp_path])
    try:
        report = ServiceManager().preflight_world(world_id="local_alpha")
    finally:
        clear_discovered_world_registries()

    assert [diagnostic.code for diagnostic in report.diagnostics] == [
        "decode:authoring_debt:local:alpha"
    ]


def test_anthology_reuses_one_domain_codec_contribution(tmp_path: Path) -> None:
    module_name = _write_codec_bundle(
        tmp_path,
        label="local_anthology",
        variant="anthology",
        anthology=True,
    )
    bundle = WorldRegistry([tmp_path]).bundles["local_anthology"]

    anthology = WorldCompiler().compile_anthology(bundle)
    domain_module = importlib.import_module(module_name)

    assert anthology["first"].metadata["title"] == "anthology:first"
    assert anthology["second"].metadata["title"] == "anthology:second"
    assert domain_module.CODEC_CONTRIBUTION_CALLS == 1


def test_world_compiler_encodes_with_bundle_local_codec(tmp_path: Path) -> None:
    _write_codec_bundle(
        tmp_path,
        label="local_encode",
        variant="encode",
        codec_key="local_alias",
    )
    bundle = WorldRegistry([tmp_path]).bundles["local_encode"]
    compiler = WorldCompiler()
    world = compiler.compile(bundle)

    assert compiler.encode(bundle, world.bundle).artifacts == {"local.story": "local_encode"}


class _ApplicationCodec:
    """An application-supplied codec claiming the same id as a bundle's."""

    codec_id = "local_codec"

    def decode(self, *, bundle, script_paths, story_key):
        _ = script_paths, story_key
        return DecodeResult(
            story_data={
                "label": bundle.manifest.label,
                "metadata": {"title": "application", "start_at": "intro.start"},
                "scenes": {"intro": {"blocks": {"start": {"content": "application"}}}},
            },
            codec_state={"codec_id": self.codec_id, "variant": "application"},
        )

    def encode(self, *, bundle, runtime_data, story_key, codec_state=None):
        _ = bundle, story_key, codec_state
        return EncodeResult(artifacts={"local.story": runtime_data["label"]})


def test_bundle_contribution_outranks_a_same_id_application_codec(
    tmp_path: Path,
) -> None:
    """Specificity decides, not who registered first.

    A contribution from a world's own domain module is scoped to that world, so
    it outranks a generic registration for the codec type. This is the rule an
    application relies on when a world ships a better reader for its own source
    than the one core provides, and it is documented in STORY_DESIGN.md as
    intended rather than incidental - so it is pinned here.
    """
    _write_codec_bundle(tmp_path, label="local_precedence", variant="bundle")

    compiler = WorldCompiler()
    compiler.codec_registry.register("local_codec", _ApplicationCodec())

    World.clear_instances()
    try:
        bundle = WorldRegistry([tmp_path]).bundles["local_precedence"]
        world = compiler.compile(bundle)
    finally:
        World.clear_instances()

    assert world.metadata["title"] == "bundle"
    assert world.bundle.codec_state["variant"] == "bundle"


def test_application_codec_is_used_when_the_bundle_contributes_none(
    tmp_path: Path,
) -> None:
    """The application registry is the fallback, not dead weight.

    Without this the previous test would pass even if bundle contributions were
    the only path that ever worked.
    """
    _write_codec_bundle(tmp_path, label="local_fallback", variant="bundle")
    module_name = "local_fallback_domain"
    # Strip the contribution hook, keeping the module importable.
    (tmp_path / "local_fallback" / f"{module_name}.py").write_text(
        "from __future__ import annotations\n", encoding="utf-8"
    )

    compiler = WorldCompiler()
    compiler.codec_registry.register("local_codec", _ApplicationCodec())

    World.clear_instances()
    try:
        bundle = WorldRegistry([tmp_path]).bundles["local_fallback"]
        world = compiler.compile(bundle)
    finally:
        World.clear_instances()

    assert world.metadata["title"] == "application"
