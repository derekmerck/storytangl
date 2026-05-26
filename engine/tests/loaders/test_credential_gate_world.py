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


def _choose(ledger: Ledger, label: str) -> None:
    # Story-authored actions surface their display string as ``text``;
    # game-provisioned actions surface it as ``label`` (from get_move_label).
    action = next(
        a
        for a in _actions(ledger)
        if a.label == label or getattr(a, "text", None) == label
    )
    ledger.resolve_choice(action.uid, choice_payload=action.payload)


class TestCredentialGateWorld:
    """Tests for the staged credentials demo world."""

    def test_world_registry_discovers_credential_gate(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "credential_gate" in registry.bundles
        bundle = registry.bundles["credential_gate"]
        assert bundle.manifest.label == "credential_gate"
        assert bundle.manifest.metadata["title"] == "Credential Gate"

    def test_scheduled_shift_routes_to_victory(self) -> None:
        bundle = WorldBundle.load(_credential_gate_root())
        world = WorldCompiler().compile(bundle)

        assert "CredentialGateBlock" in world.class_registry

        result = world.create_story("credential_gate_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"
        _choose(ledger, "Work the scheduled shift")
        assert ledger.cursor.label == "standard_challenge"

        # The authored roster: Tomas (pass), Edda (deny), Goran (arrest).
        _choose(ledger, "Inspect passport")
        _choose(ledger, "Choose pass")
        assert ledger.cursor.label == "standard_challenge"  # still mid-shift

        _choose(ledger, "Inspect passport")
        _choose(ledger, "Choose deny")
        assert ledger.cursor.label == "standard_challenge"

        _choose(ledger, "Inspect passport")
        _choose(ledger, "Choose arrest")

        assert ledger.cursor.label == "victory"
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "shift complete" in content.lower()

    def test_randomized_shift_materializes_lazily_and_routes_to_victory(self) -> None:
        """The sampled path materializes each candidate on arrival and, played
        correctly, routes to the same victory ending."""

        bundle = WorldBundle.load(_credential_gate_root())
        world = WorldCompiler().compile(bundle)

        assert "SampledGateBlock" in world.class_registry

        result = world.create_story("credential_gate_demo", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        _choose(ledger, "Work a randomized shift")
        assert ledger.cursor.label == "sampled_challenge"

        game = ledger.cursor.game
        total = game._total_cases()
        assert total > 1
        # Lazy: only the active arrival has materialized; the rest still pending.
        assert len(game.materialized) == 1

        for _ in range(total):
            target = game.expected_disposition(game.active_case).value
            inspect = next(
                a for a in _actions(ledger) if a.label.startswith(("Inspect", "Review"))
            )
            ledger.resolve_choice(inspect.uid, choice_payload=inspect.payload)
            _choose(ledger, f"Choose {target}")

        assert ledger.cursor.label == "victory"
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "shift complete" in content.lower()
        assert f"of {total}" in content
