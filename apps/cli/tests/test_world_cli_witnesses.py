"""World-owned command scripts exercised through the real CLI adapter."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from tangl.cli.app import StoryTanglCLI
from tangl.loaders import WorldBundle
from tangl.persistence import PersistenceManagerFactory
from tangl.service import build_service_manager
from tangl.service.world_registry import clear_discovered_world_registries
from tangl.story import World


WORLDS_DIR = Path(__file__).resolve().parents[3] / "worlds"


@pytest.fixture(autouse=True)
def reset_worlds() -> None:
    clear_discovered_world_registries()
    World.clear_instances()
    yield
    World.clear_instances()
    clear_discovered_world_registries()


def _run_script(script: Path) -> str:
    """Run one command script and fail on errors reported through cmd2."""

    errors: list[str] = []

    def record_error(message: object = "", **_kw: object) -> None:
        errors.append(str(message))

    manager = build_service_manager(PersistenceManagerFactory.native_in_mem())
    app = StoryTanglCLI(service_manager=manager, terminal_style="plain")
    app.stdout = io.StringIO()
    app.perror = record_error  # type: ignore[method-assign]
    app.onecmd_plus_hooks("create_user world-witness")
    app.stdout.seek(0)
    app.stdout.truncate(0)

    app.onecmd_plus_hooks(f"run_script {script}")
    if errors:
        pytest.fail(f"cmd2 errors while running {script}:\n" + "\n".join(errors))
    return app.stdout.getvalue()


def _run_world_script(world_id: str) -> str:
    """Run one world-owned command script through cmd2's script command."""

    return _run_script(WORLDS_DIR / world_id / "cli_witness.txt")


def _proof_class(world_id: str) -> str:
    bundle = WorldBundle.load(WORLDS_DIR / world_id)
    return str(bundle.manifest.metadata["proof_class"])


def test_credential_gate_cli_witness_reaches_declared_ending() -> None:
    transcript = _run_world_script("credential_gate")

    assert _proof_class("credential_gate") == "finite"
    assert "Tomas Vey steps forward." in transcript
    assert "Shift complete: 3 of 3 calls correct." in transcript
    assert "The last traveler clears the counter." in transcript
    assert transcript.rstrip().endswith("No available choices.")


def test_world_script_runner_surfaces_cmd2_errors(tmp_path: Path) -> None:
    script = tmp_path / "invalid-cli-witness.txt"
    script.write_text("not_a_storytangl_command\n", encoding="utf-8")

    with pytest.raises(pytest.fail.Exception, match="not a recognized command"):
        _run_script(script)


def test_adventure_sandbox_cli_witness_remains_open_and_coherent() -> None:
    transcript = _run_world_script("adventure_sandbox_slice")

    assert _proof_class("adventure_sandbox_slice") == "open-ended"
    assert "You are inside a building, a well house for a large spring." in transcript
    assert transcript.count("You are standing at the end of a road") >= 3
    final_road = transcript.rsplit("You are standing at the end of a road", 1)[1]
    assert "Choices:" in final_road
    assert "5. Wait" in final_road
    assert "Info: /t Watch" in final_road
