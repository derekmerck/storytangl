"""Conformance tests for the Hall Monitor credentials world."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from tangl.core import Graph, Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.mechanics.credentials import (
    CREDENTIAL_ID_SLOT,
    CREDENTIAL_PACKET_SLOT,
    CREDENTIAL_UNPRESENTED_SLOT,
    CredentialDefinition,
    CredentialStatus,
    FailureMode,
)
from tangl.mechanics.presence.look import HairColor, HasSimpleLook
from tangl.mechanics.transaction import (
    CallbackCommitment,
    TransactionOffer,
    TransactionReceipt,
)
from tangl.mechanics.games.credentials_game import CredentialDisposition, derive_disposition
from tangl.mechanics.games.credentials_roster import materialize
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode, StoryGraph
from tangl.vm import Ledger
from tangl.vm.dispatch import do_provision
from tangl.vm.resolution_phase import ResolutionPhase
from tangl.vm.runtime.frame import PhaseCtx


_DESK_CUSTODY_SLOT = "retained_documents"


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


def _advance_to_inhaler_case(ledger: Ledger) -> None:
    """Settle earlier authored encounters without taking their custody actions."""

    while ledger.cursor.game.case_index < ledger.cursor.game.inhaler_case_index:
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
        assert block.inhaler_case_index == 2
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

    def test_hall_monitor_requires_all_three_authored_encounters(self) -> None:
        graph, _ = _started_shift()
        block = graph.find_one(Selector(label="morning_shift"))

        with pytest.raises(ValueError, match="requires waiver, media, and Mira"):
            type(block)(encounters=2)

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

    def test_retained_waiver_is_completed_and_issued_to_mira(self) -> None:
        """One graph-owned waiver moves through custody into a fresh packet."""

        graph, ledger = _started_shift()
        game = ledger.cursor.game
        waiver = game.active_case.packet_manager.get_slot(CREDENTIAL_PACKET_SLOT)[0]
        waiver_id = waiver.uid

        _inspect(ledger, "doctor's note")
        assert "Retain the medical waiver" in [
            action.label for action in _actions(ledger)
        ]
        _choose(ledger, "Retain the medical waiver")
        assert game.desk_custody.get_slot(_DESK_CUSTODY_SLOT) == [waiver]
        assert not game.active_case.packet_manager.get_slot(CREDENTIAL_PACKET_SLOT)
        assert len(game.transaction_receipts) == 1

        _choose(ledger, "Send back to class")
        tess_result = game.case_results[0].model_dump(mode="python")
        _advance_to_inhaler_case(ledger)
        mira_packet = game.active_case.packet_manager
        assert not mira_packet.get_slot(CREDENTIAL_PACKET_SLOT)

        _inspect(ledger, "inhaler")
        assert "Complete and issue the medical waiver" in [
            action.label for action in _actions(ledger)
        ]
        _choose(ledger, "Complete and issue the medical waiver")

        completed = mira_packet.get_slot(CREDENTIAL_PACKET_SLOT)
        assert completed == [waiver]
        assert completed[0].uid == waiver_id
        assert completed[0].status is CredentialStatus.VALID
        assert completed[0].subject_id == mira_packet.bearer_id
        assert not game.desk_custody.get_slot(_DESK_CUSTODY_SLOT)
        assert game.expected_disposition(game.active_case) is CredentialDisposition.DENY
        assert len(game.transaction_receipts) == 2
        move_detail = game.transaction_receipts[1].details[0]
        assert isinstance(move_detail, dict)
        assert str(move_detail["asset_id"]) == str(waiver_id)

        before_response = Graph.structure(graph.unstructure())
        pre_response_game = before_response.find_one(
            Selector(label="morning_shift")
        ).game
        pre_response_packet = pre_response_game.active_case.packet_manager
        assert not pre_response_packet.get_slot(CREDENTIAL_ID_SLOT)
        assert len(pre_response_packet.get_slot(CREDENTIAL_UNPRESENTED_SLOT)) == 1

        _choose(ledger, "Request student ID")
        assert game.expected_disposition(game.active_case) is CredentialDisposition.PASS
        _inspect(ledger, "doctor's note")
        reissued_text = _journal_text(ledger)
        assert "Valid for this period" in reissued_text
        assert "signature line is blank" not in reissued_text
        assert game.case_results[0].model_dump(mode="python") == tess_result

        restored = Graph.structure(graph.unstructure())
        restored_game = restored.find_one(Selector(label="morning_shift")).game
        restored_packet = restored_game.active_case.packet_manager
        restored_waiver = restored_packet.get_slot(CREDENTIAL_PACKET_SLOT)[0]
        assert restored_waiver.uid == waiver_id
        assert restored_waiver.status is CredentialStatus.VALID
        assert restored_waiver.subject_id == restored_packet.bearer_id
        restored_id = restored_packet.get_slot(CREDENTIAL_ID_SLOT)[0]
        assert restored_id.subject_id == restored_packet.bearer_id
        assert not restored_packet.get_slot(CREDENTIAL_UNPRESENTED_SLOT)
        assert restored_game.finding_status["id"] == "verified"
        assert len(restored_game.transaction_receipts) == 2
        assert restored_game.case_results[0].model_dump(mode="python") == tess_result

    def test_mira_has_no_reissue_action_without_the_retained_waiver(self) -> None:
        _, ledger = _started_shift()
        _advance_to_inhaler_case(ledger)

        _inspect(ledger, "inhaler")

        assert "Complete and issue the medical waiver" not in [
            action.label for action in _actions(ledger)
        ]

    def test_waiver_retention_rejects_stale_or_duplicate_component_ids(self) -> None:
        _, ledger = _started_shift()
        game = ledger.cursor.game
        handler = ledger.cursor.game_handler

        with pytest.raises(ValueError, match="not visible"):
            handler._retain_waiver(game, str(uuid4()), {})

        _inspect(ledger, "doctor's note")
        _choose(ledger, "Retain the medical waiver")

        with pytest.raises(ValueError, match="not visible"):
            handler._retain_waiver(game, str(uuid4()), {})

    def test_late_reissue_failure_rolls_back_completion_and_custody_move(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The transaction rail reverses both legs when a later commitment fails."""

        _, ledger = _started_shift()
        game = ledger.cursor.game
        waiver = game.active_case.packet_manager.get_slot(CREDENTIAL_PACKET_SLOT)[0]
        original_status = waiver.status
        original_subject_id = waiver.subject_id

        _inspect(ledger, "doctor's note")
        _choose(ledger, "Retain the medical waiver")
        _choose(ledger, "Send back to class")
        _advance_to_inhaler_case(ledger)
        packet = game.active_case.packet_manager
        _inspect(ledger, "inhaler")

        def fail_late() -> None:
            raise RuntimeError("late failure")

        original_accept = TransactionOffer.accept

        def accept_with_late_failure(offer: TransactionOffer) -> TransactionReceipt:
            if offer.label == "complete medical waiver":
                offer.commitments.append(CallbackCommitment(label="fail late", apply=fail_late))
            return original_accept(offer)

        monkeypatch.setattr(TransactionOffer, "accept", accept_with_late_failure)

        with pytest.raises(RuntimeError, match="late failure"):
            _choose(ledger, "Complete and issue the medical waiver")

        assert game.desk_custody.get_slot(_DESK_CUSTODY_SLOT) == [waiver]
        assert not packet.get_slot(CREDENTIAL_PACKET_SLOT)
        assert waiver.status is original_status
        assert waiver.subject_id == original_subject_id

    def test_hall_monitor_records_and_later_reveals_harsh_inhaler_outcome(self) -> None:
        graph, ledger = _started_shift()
        _advance_to_inhaler_case(ledger)
        block = ledger.cursor
        game = block.game
        bearer_id = game.active_case.packet_manager.bearer_id

        _inspect(ledger, next(iter(game.presented_documents)))
        _choose(ledger, "Send back to class")

        assert game.case_results[2].correct is True
        assert game.score["player"] == 3
        assert game.score["opponent"] == 0
        assert len(block.consequences) == 1
        consequence = block.consequences[0]
        assert consequence.bearer_id == bearer_id
        assert consequence.outcome == "inhaler_withheld"
        assert "remained at the hall desk" not in _journal_text(ledger)

        bearer = graph.get(bearer_id)
        assert isinstance(bearer, HasSimpleLook)
        bearer.label = "Zapp"
        bearer.look.hair_color = HairColor.BLUE

        _finish_shift_correctly(ledger)
        assert ledger.cursor.label == "victory"
        assert block.consequences == [consequence]
        _choose(ledger, "Read the attendance note")

        assert ledger.cursor.label == "attendance_note"
        assert "Zapp, with blue hair, was sent back to class" in _journal_text(ledger)

        restored = Graph.structure(graph.unstructure())
        restored_block = restored.find_one(Selector(label="morning_shift"))
        assert restored_block is not None
        assert restored_block.consequences == [consequence]
        restored_result = restored_block.game.case_results[2]
        assert restored_result.case_index == consequence.source_case_index
        assert restored_result.bearer_id == consequence.bearer_id
        assert restored.get(restored_result.bearer_id) is not None

    def test_hall_monitor_records_compassionate_inhaler_outcome_without_changing_score(
        self,
    ) -> None:
        _, ledger = _started_shift()
        _advance_to_inhaler_case(ledger)
        block = ledger.cursor
        game = block.game

        _inspect(ledger, next(iter(game.presented_documents)))
        _choose(ledger, "Allow onward")

        assert game.case_results[2].correct is False
        assert game.score["opponent"] == 1
        assert game.score["player"] == 2
        assert [fact.outcome for fact in block.consequences] == ["inhaler_allowed"]
        assert "reached the nurse's office" not in _journal_text(ledger)

        _finish_shift_correctly(ledger)
        assert ledger.cursor.label == "defeat"
        _choose(ledger, "Read the attendance note")
        assert "reached the nurse's office with their inhaler" in _journal_text(ledger)

        ledger.get_journal()
        ledger.get_journal()
        assert len(block.consequences) == 1

    def test_attendance_note_prepares_a_returning_bearer_with_prior_receipt(self) -> None:
        graph, ledger = _started_shift()
        _advance_to_inhaler_case(ledger)
        source = ledger.cursor
        source_game = source.game
        first_packet = source_game.active_case.packet_manager
        bearer_id = first_packet.bearer_id

        _inspect(ledger, next(iter(source_game.presented_documents)))
        _choose(ledger, "Send back to class")
        first_result = source_game.case_results[2].model_dump(mode="python")
        _finish_shift_correctly(ledger)
        assert ledger.cursor.label == "victory"

        subjects_before_return = sum(
            isinstance(item, HasSimpleLook)
            for item in graph.members.values()
        )
        _choose(ledger, "Read the attendance note")
        assert ledger.cursor.label == "attendance_note"
        assert any(action.text == "Meet the returning student" for action in _actions(ledger))

        returning = graph.find_one(Selector(label="returning_student"))
        assert returning is not None
        returning_game = returning.game
        returning_case = returning_game.active_case
        returning_packet = returning_case.packet_manager
        assert returning_packet is not first_packet
        assert returning_packet.bearer_id == bearer_id
        assert returning_case.prior_case_results == [source_game.case_results[2]]
        assert not any(case.prior_case_results for case in source_game.materialized[1:])
        assert sum(isinstance(item, HasSimpleLook) for item in graph.members.values()) == (
            subjects_before_return
        )
        assert {
            component.uid for component in returning_packet.document_components()
        }.isdisjoint(component.uid for component in first_packet.document_components())

        restored = StoryGraph.structure(graph.unstructure())
        restored_source = restored.find_one(Selector(label="morning_shift"))
        restored_attendance = restored.find_one(Selector(label="attendance_note"))
        restored_returning = restored.find_one(Selector(label="returning_student"))
        assert restored_source is not None
        assert restored_attendance is not None
        assert restored_returning is not None
        assert restored_source.consequences
        restored_case = restored_returning.game.active_case
        assert restored_case.packet_manager.bearer_id == bearer_id
        assert restored_case.prior_case_results[0].model_dump(mode="python") == first_result

        restored_subject_count = sum(
            isinstance(item, HasSimpleLook)
            for item in restored.members.values()
        )

        bearer = restored.get(bearer_id)
        assert isinstance(bearer, HasSimpleLook)
        bearer.label = "Zapp"
        bearer.look.hair_color = HairColor.BLUE

        restored_ledger = Ledger.from_graph(restored, entry_id=restored_attendance.uid)
        planning_ctx = PhaseCtx(
            graph=restored,
            cursor_id=restored_attendance.uid,
            current_phase=ResolutionPhase.PLANNING,
        )
        do_provision(restored_attendance, ctx=planning_ctx)
        do_provision(restored_attendance, ctx=planning_ctx)
        returning_actions = [
            action
            for action in _actions(restored_ledger)
            if action.text == "Meet the returning student"
        ]
        assert len(returning_actions) == 1
        assert sum(isinstance(item, HasSimpleLook) for item in restored.members.values()) == (
            restored_subject_count
        )
        _choose(restored_ledger, "Meet the returning student")
        assert restored_ledger.cursor is restored_returning
        assert "Zapp, with blue hair, returns" in _journal_text(restored_ledger)

        _inspect(restored_ledger, "doctor's note")
        _choose(restored_ledger, "Allow onward")
        assert restored_returning.game.case_results[0].correct is True
        assert len(restored_returning.game.case_results) == 1
        assert restored_source.game.case_results[2].model_dump(mode="python") == first_result

    def test_arrest_does_not_offer_or_prepare_a_returning_student(self) -> None:
        graph, ledger = _started_shift()

        _advance_to_inhaler_case(ledger)

        _inspect(ledger, next(iter(ledger.cursor.game.presented_documents)))
        _choose(ledger, "Send to the office")
        _finish_shift_correctly(ledger)
        assert ledger.cursor.label == "defeat"

        _choose(ledger, "Read the attendance note")
        assert ledger.cursor.label == "attendance_note"
        assert all(action.text != "Meet the returning student" for action in _actions(ledger))

        returning = graph.find_one(Selector(label="returning_student"))
        assert returning is not None
        assert returning.game_state is None
