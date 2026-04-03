"""Tests for the credential gate demo world bundle."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode
from tangl.vm import Ledger


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _credential_gate_root() -> Path:
    return _repo_worlds_dir() / "credential_gate"


def _actions(ledger: Ledger) -> list[Action]:
    return list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


class TestCredentialGateWorld:
    """Tests for the staged credentials demo world."""

    def test_world_registry_discovers_credential_gate(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "credential_gate" in registry.bundles
        bundle = registry.bundles["credential_gate"]
        assert bundle.manifest.label == "credential_gate"
        assert bundle.manifest.metadata["title"] == "Credential Gate"

    def test_credential_gate_compiles_and_routes_to_victory(self) -> None:
        bundle = WorldBundle.load(_credential_gate_root())
        world = WorldCompiler().compile(bundle)

        assert "CredentialGateBlock" in world.class_registry

        result = world.create_story("credential_gate_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"

        ledger.resolve_choice(_actions(ledger)[0].uid)

        assert ledger.cursor.label == "challenge"
        inspect = next(action for action in _actions(ledger) if action.label == "Inspect passport")
        ledger.resolve_choice(inspect.uid, choice_payload=inspect.payload)

        packet = next(action for action in _actions(ledger) if action.label == "Review packet consistency")
        ledger.resolve_choice(packet.uid, choice_payload=packet.payload)

        deny = next(action for action in _actions(ledger) if action.label == "Choose deny")
        ledger.resolve_choice(deny.uid, choice_payload=deny.payload)

        assert ledger.cursor.label == "victory"
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "choose to deny" in content.lower()
