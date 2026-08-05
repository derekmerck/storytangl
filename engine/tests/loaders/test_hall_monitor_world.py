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


def _started_shift(*, pinned_candidate_name: str | None = None) -> tuple[StoryGraph, Ledger]:
    world = WorldCompiler().compile(WorldBundle.load(_hall_monitor_root()))
    result = world.create_story("hall_monitor", init_mode=InitMode.EAGER)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    if pinned_candidate_name is not None:
        block = result.graph.find_one(Selector(label="morning_shift"))
        assert block is not None
        block.game.offers[0].candidate_name = pinned_candidate_name
    _choose(ledger, "Monitor the morning halls")
    return result.graph, ledger


def _journal_text(ledger: Ledger) -> str:
    return " ".join(
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment.content, str)
    )


def _finish_shift_correctly(ledger: Ledger) -> None:
    while ledger.cursor.label == "morning_shift":
        game = ledger.cursor.game
        _inspect(ledger, next(iter(game.presented_documents)))
        decision = game.expected_disposition(game.active_case).value
        _choose(ledger, game.presentation.decision_labels[decision])


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

    def test_script_configures_a_seeded_shift_with_an_authored_student_offer(self) -> None:
        graph, ledger = _started_shift()
        block = graph.find_one(Selector(label="morning_shift"))
        game = ledger.cursor.game

        assert block is ledger.cursor
        assert block.encounters == 5
        assert block.seed == 20260719
        assert block.inhaler_case_index == 0
        assert block.disposition_distribution == {
            CredentialDisposition.PASS: 0.5,
            CredentialDisposition.DENY: 0.3,
            CredentialDisposition.ARREST: 0.2,
        }
        assert len(game.offers) == 5
        assert any(offer.candidate_name == "Mira Quill" for offer in game.offers)
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
                owner=object(),
                catalog=game._credential_catalog(ledger.cursor),
                narrative_renderer=game.presentation.render_case,
            )
            assert derive_disposition(case.packet_manager, game.restriction_map) is offer.target_disposition

    def test_school_projection_and_full_shift_keep_the_shared_loop(self) -> None:
        _, ledger = _started_shift()
        first_case = ledger.cursor.game.active_case

        assert "student ID" in first_case.presented_documents
        assert "doctor's note" in first_case.presented_documents
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

    def test_repeated_move_reads_do_not_expand_the_prepared_frontier(self) -> None:
        _, ledger = _started_shift()
        game = ledger.cursor.game
        handler = ledger.cursor.game_handler
        prepared = tuple(game.materialized)

        first = handler.get_provisioned_moves(game)
        second = handler.get_provisioned_moves(game)

        assert first == second
        assert game.materialized == list(prepared)
        assert len(prepared) == 2
        assert game.active_case is prepared[0]

    def test_hall_monitor_records_and_later_reveals_harsh_inhaler_outcome(self) -> None:
        graph, ledger = _started_shift(pinned_candidate_name="Ren Ito")
        block = ledger.cursor
        game = block.game
        bearer_id = game.active_case.packet_manager.bearer_id

        _inspect(ledger, "doctor's note")
        _choose(ledger, "Send back to class")

        assert game.case_results[0].correct is True
        assert game.score["player"] == 1
        assert game.score["opponent"] == 0
        assert len(block.consequences) == 1
        consequence = block.consequences[0]
        assert consequence.bearer_id == bearer_id
        assert consequence.candidate_name == "Ren Ito"
        assert consequence.outcome == "inhaler_withheld"
        assert "remained at the hall desk" not in _journal_text(ledger)

        _finish_shift_correctly(ledger)
        assert ledger.cursor.label == "victory"
        assert block.consequences == [consequence]
        _choose(ledger, "Read the attendance note")

        assert ledger.cursor.label == "attendance_note"
        assert "Ren Ito was sent back to class" in _journal_text(ledger)

        restored = Graph.structure(graph.unstructure())
        restored_block = restored.find_one(Selector(label="morning_shift"))
        assert restored_block is not None
        assert restored_block.consequences == [consequence]
        restored_result = restored_block.game.case_results[0]
        assert restored_result.case_index == consequence.source_case_index
        assert restored_result.bearer_id == consequence.bearer_id
        assert restored.get(restored_result.bearer_id) is not None

    def test_hall_monitor_records_compassionate_inhaler_outcome_without_changing_score(
        self,
    ) -> None:
        _, ledger = _started_shift()
        block = ledger.cursor
        game = block.game

        _inspect(ledger, "doctor's note")
        _choose(ledger, "Allow onward")

        assert game.case_results[0].correct is False
        assert game.score["opponent"] == 1
        assert game.score["player"] == 0
        assert [fact.outcome for fact in block.consequences] == ["inhaler_allowed"]
        assert "reached the nurse's office" not in _journal_text(ledger)

        _finish_shift_correctly(ledger)
        assert ledger.cursor.label == "defeat"
        _choose(ledger, "Read the attendance note")
        assert "Mira Quill reached the nurse's office" in _journal_text(ledger)

        ledger.get_journal()
        ledger.get_journal()
        assert len(block.consequences) == 1
