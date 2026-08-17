"""Bundle-local codec contributions through ordinary world loading."""

from __future__ import annotations

import importlib
from pathlib import Path

from pytest import MonkeyPatch

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
                "    codec: local_codec",
                "    scripts: first.local",
                "  second:",
                "    codec: local_codec",
                "    scripts: second.local",
            ]
        )
        script_names = ["first.local", "second.local"]
    else:
        manifest = "\n".join(
            [
                f"label: {label}",
                f"domain_module: {module_name}",
                "codec: local_codec",
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

from tangl.loaders import DecodeResult, LossKind, LossRecord, WorldBundle

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
    ) -> dict[str, str]:
        _ = bundle, runtime_data, story_key, codec_state
        raise NotImplementedError


def get_story_codecs() -> dict[str, LocalCodec]:
    global CODEC_CONTRIBUTION_CALLS
    CODEC_CONTRIBUTION_CALLS += 1
    return {{"local_codec": LocalCodec()}}
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
