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


def _run_world_script(world_id: str) -> str:
    """Run one world-owned command script through cmd2's script command."""

    manager = build_service_manager(PersistenceManagerFactory.native_in_mem())
    app = StoryTanglCLI(service_manager=manager, terminal_style="plain")
    app.stdout = io.StringIO()
    app.onecmd_plus_hooks("create_user world-witness")
    app.stdout.seek(0)
    app.stdout.truncate(0)

    script = WORLDS_DIR / world_id / "cli_witness.txt"
    app.onecmd_plus_hooks(f"run_script {script}")
    return app.stdout.getvalue()


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


def test_adventure_sandbox_cli_witness_remains_open_and_coherent() -> None:
    transcript = _run_world_script("adventure_sandbox_slice")

    assert _proof_class("adventure_sandbox_slice") == "open-ended"
    assert "You are inside a building, a well house for a large spring." in transcript
    assert transcript.count("You are standing at the end of a road") >= 2
    assert "Choices:" in transcript
    assert transcript.rstrip().endswith("5. Wait")
