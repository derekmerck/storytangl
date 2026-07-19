"""Conformance tests for the Hall Monitor credentials world."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Graph, Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.mechanics.credentials import (
    CREDENTIAL_PACKET_SLOT,
    CredentialDefinition,
    FailureMode,
)
from tangl.mechanics.games.credentials_game import CredentialDisposition, derive_disposition
from tangl.mechanics.games.credentials_roster import materialize
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode, StoryGraph
from tangl.vm import Ledger


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _hall_monitor_root() -> Path:
    return _repo_worlds_dir() / "hall_monitor"


def _actions(ledger: Ledger) -> list[Action]:
    return list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


def _choose(ledger: Ledger, label: str) -> None:
    action = next(action for action in _actions(ledger) if action.label == label or action.text == label)
    ledger.resolve_choice(action.uid)


def _inspect(ledger: Ledger, target: str) -> None:
    action = next(action for action in _actions(ledger) if action.label == "Inspect a document")
    game = ledger.cursor.game
    ledger.resolve_choice(
        action.uid,
        choice_payload={"piece_ids": [f"{game.case_index}:{target}"]},
    )


def _started_shift() -> tuple[StoryGraph, Ledger]:
    world = WorldCompiler().compile(WorldBundle.load(_hall_monitor_root()))
    result = world.create_story("hall_monitor", init_mode=InitMode.EAGER)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    _choose(ledger, "Monitor the morning halls")
    return result.graph, ledger


class TestHallMonitorWorld:
    """The school skin exercises the shared credentials lifecycle."""

    def test_registry_discovers_hall_monitor(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert registry.bundles["hall_monitor"].manifest.metadata["title"] == "Hall Monitor"

    def test_compiles_school_catalog_without_checkpoint_definitions(self) -> None:
        world = WorldCompiler().compile(WorldBundle.load(_hall_monitor_root()))
        catalog = world.assets.values["school"]

        assert catalog.label == "school"
        assert CredentialDefinition.get_instance("hall_monitor:school:activity_pass") in catalog.members
        assert all("credential_gate" not in definition.label for definition in catalog.members)
        assert {definition.indication for definition in catalog.members} >= {
            "academic",
            "activity",
            "off_campus",
            "uniform",
            "medicine",
            "records",
        }

    def test_script_configures_a_seeded_shift_with_a_pinned_student(self) -> None:
        graph, ledger = _started_shift()
        block = graph.find_one(Selector(label="morning_shift"))
        game = ledger.cursor.game

        assert block is ledger.cursor
        assert block.encounters == 5
        assert block.seed == 20260719
        assert block.disposition_distribution == {
            CredentialDisposition.PASS: 0.5,
            CredentialDisposition.DENY: 0.3,
            CredentialDisposition.ARREST: 0.2,
        }
        assert len(game.offers) == 5
        assert any(offer.pinned_case is not None for offer in game.offers)
        assert all(
            set(offer.failure_modes).isdisjoint(
                {FailureMode.UNPERMITTED_CONTRABAND, FailureMode.CONCEALED_CONTRABAND}
            )
            for offer in game.offers
        )

        for offer in game.offers:
            case = materialize(
                offer,
                game.restriction_map,
                narrative_renderer=game.presentation.render_case,
            )
            assert derive_disposition(case, game.restriction_map) is offer.target_disposition

    def test_school_projection_and_full_shift_keep_the_shared_loop(self) -> None:
        _, ledger = _started_shift()
        first_case = ledger.cursor.game.active_case

        assert "student ID" in first_case.presented_documents
        assert "activity pass" in first_case.presented_documents
        assert "passport" not in first_case.presented_documents

        while ledger.cursor.label == "morning_shift":
            game = ledger.cursor.game
            target = next(iter(game.presented_documents))
            _inspect(ledger, target)
            decision = game.expected_disposition(game.active_case).value
            _choose(ledger, game.presentation.decision_labels[decision])

        assert ledger.cursor.label == "victory"

    def test_active_school_packet_round_trips_with_bound_catalog_components(self) -> None:
        graph, ledger = _started_shift()
        game = ledger.cursor.game
        manager = game.active_case.packet_manager
        assert manager is not None

        restored = Graph.structure(graph.unstructure())
        block = restored.find_one(Selector(label="morning_shift"))
        assert block is not None
        restored_manager = block.game.active_case.packet_manager
        assert restored_manager is not None
        assert restored_manager.get_slot(CREDENTIAL_PACKET_SLOT)
        assert all(
            component.reference_singleton.label.startswith("hall_monitor:school:")
            for component in restored_manager.get_slot(CREDENTIAL_PACKET_SLOT)
        )

    def test_repeated_provisioning_does_not_materialize_another_case(self) -> None:
        _, ledger = _started_shift()
        game = ledger.cursor.game
        handler = ledger.cursor.game_handler

        first = handler.get_provisioned_moves(game)
        second = handler.get_provisioned_moves(game)

        assert first == second
        assert len(game.materialized) == 1
