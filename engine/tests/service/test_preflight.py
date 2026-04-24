"""Service preflight diagnostics tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tangl.service.response import PreflightReport
from tangl.service.service_manager import ServiceManager


def _write_clean_world(root: Path) -> str:
    world_dir = root / "clean_world"
    world_dir.mkdir()
    (world_dir / "world.yaml").write_text(
        "\n".join(
            [
                "label: clean_world",
                "scripts: script.yaml",
            ]
        ),
        encoding="utf-8",
    )
    (world_dir / "script.yaml").write_text(
        "\n".join(
            [
                "label: clean_world",
                "metadata:",
                "  start_at: intro.start",
                "scenes:",
                "  intro:",
                "    blocks:",
                "      start:",
                "        content: Start",
            ]
        ),
        encoding="utf-8",
    )
    return "clean_world"


def _write_compile_diagnostic_world(root: Path) -> str:
    world_dir = root / "compile_diagnostic_world"
    world_dir.mkdir()
    (world_dir / "world.yaml").write_text(
        "\n".join(
            [
                "label: compile_diagnostic_world",
                "scripts: script.yaml",
            ]
        ),
        encoding="utf-8",
    )
    (world_dir / "script.yaml").write_text(
        "\n".join(
            [
                "label: compile_diagnostic_world",
                "metadata:",
                "  start_at: intro.start",
                "scenes:",
                "  intro:",
                "    blocks:",
                "      start:",
                "        content: Start",
                "        roles:",
                "          - label: host",
                "            actor_ref: missing_actor",
            ]
        ),
        encoding="utf-8",
    )
    return "compile_diagnostic_world"


def _write_lossy_world(root: Path) -> str:
    world_dir = root / "lossy_world"
    world_dir.mkdir()
    (world_dir / "world.yaml").write_text(
        "\n".join(
            [
                "label: lossy_world",
                "codec: twine",
                "scripts: story.twee",
            ]
        ),
        encoding="utf-8",
    )
    (world_dir / "story.twee").write_text(
        "\n".join(
            [
                ":: StoryTitle",
                "Lossy World",
                "",
                ":: StoryData",
                '{"start":"Begin","format":"Twine 2","format-version":"2.0"}',
                "",
                ":: Begin",
                '<<display "End">>',
                "<<if $torch>>Lit<<endif>>",
                "[[Go->End]]",
                "",
                ":: End",
                "Done.",
            ]
        ),
        encoding="utf-8",
    )
    return "lossy_world"


def test_preflight_world_returns_clean_report(tmp_path: Path, monkeypatch) -> None:
    world_id = _write_clean_world(tmp_path)
    monkeypatch.setattr("tangl.service.world_registry.get_world_dirs", lambda: [tmp_path])

    report = ServiceManager().preflight_world(world_id=world_id)

    assert isinstance(report, PreflightReport)
    assert report.world_id == world_id
    assert report.status == "ok"
    assert report.diagnostics == []


def test_preflight_world_normalizes_compile_diagnostics(tmp_path: Path, monkeypatch) -> None:
    world_id = _write_compile_diagnostic_world(tmp_path)
    monkeypatch.setattr("tangl.service.world_registry.get_world_dirs", lambda: [tmp_path])

    report = ServiceManager().preflight_world(world_id=world_id)

    assert report.status == "error"
    assert [(item.phase, item.severity, item.code) for item in report.diagnostics] == [
        ("compile", "error", "compile:dangling_actor_ref")
    ]
    diagnostic = report.diagnostics[0]
    assert diagnostic.source is not None
    assert diagnostic.source["authored_path"] == "scenes[0].intro.blocks[0].start.roles[0]"
    assert diagnostic.subject_label == "intro.start.host"
    assert diagnostic.details["missing_ref"] == "missing_actor"


def test_preflight_world_normalizes_decode_losses(tmp_path: Path, monkeypatch) -> None:
    world_id = _write_lossy_world(tmp_path)
    monkeypatch.setattr("tangl.service.world_registry.get_world_dirs", lambda: [tmp_path])

    report = ServiceManager().preflight_world(world_id=world_id)

    assert report.status == "ok"
    decode_diagnostics = [item for item in report.diagnostics if item.phase == "decode"]
    assert decode_diagnostics
    assert {item.severity for item in decode_diagnostics} == {"warning"}
    assert any(item.code.startswith("decode:unsupported_feature") for item in decode_diagnostics)
    assert all("feature" in item.details for item in decode_diagnostics)


def test_preflight_world_rejects_unknown_world(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("tangl.service.world_registry.get_world_dirs", lambda: [tmp_path])

    with pytest.raises(ValueError, match="Unknown world: missing"):
        ServiceManager().preflight_world(world_id="missing")
