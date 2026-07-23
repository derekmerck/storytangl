"""Compiled-story proof that one world can host two credentials scenario types."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Graph, Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.mechanics.credentials import (
    CREDENTIAL_ID_SLOT,
    CREDENTIAL_PACKET_SLOT,
    CredentialDefinition,
    CredentialDefectKind,
    FailureMode,
)
from tangl.mechanics.games.credentials_game import (
    CredentialDisposition,
    CredentialsGame,
    CredentialsGameHandler,
    derive_defects,
)
from tangl.story import Action, InitMode, World
from tangl.vm import Ledger


def _actions(ledger: Ledger) -> list[Action]:
    return list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


def _action(ledger: Ledger, label: str) -> Action:
    """Return an authored or game-provisioned action by its player-facing label."""

    actions = _actions(ledger)
    for action in actions:
        if action.label == label or action.text == label:
            return action
    available = [(action.label, action.text) for action in actions]
    raise AssertionError(f"Action {label!r} not found; available: {available!r}")


def _choose(ledger: Ledger, label: str) -> None:
    ledger.resolve_choice(_action(ledger, label).uid)


def _inspect(ledger: Ledger, target: str) -> None:
    game = ledger.cursor.game
    ledger.resolve_choice(
        _action(ledger, "Inspect a document").uid,
        choice_payload={"piece_ids": [f"{game.case_index}:{target}"]},
    )


def _compile_combined_world(root: Path) -> World:
    """Compile the two-catalog conformance world once for both story branches."""

    root = root / "combined_credentials"
    root.mkdir()
    package = root / "combined_credentials"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "domain.py").write_text(
        '''from __future__ import annotations

from uuid import UUID

from pydantic import Field

from tangl.mechanics.credentials import (
    CredentialDefinition,
    CredentialStatus,
    FailureMode,
    Restrictions,
    RestrictionLevel,
)
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.credentials_game import (
    CredentialDisposition,
    CredentialPresentationProfile,
    CredentialsGame,
    CredentialsGameHandler,
)
from tangl.mechanics.games.credentials_roster import ScenarioOffer
from tangl.story import Block


BORDER_RULES = {"border": {"work": RestrictionLevel.WITH_PERMIT}}
SCHOOL_RULES = {"school": {"activity": RestrictionLevel.WITH_PERMIT}}

BORDER_PRESENTATION = CredentialPresentationProfile(
    indication_labels={"work": "work"},
    document_labels={"work": "work permit"},
    identity_label="passport",
    identity_description="A border identity document.",
    document_description="A {document}.",
    status_text={
        CredentialStatus.MISSING_SEAL: "The issuing stamp is missing.",
        CredentialStatus.BAD_DATE: "The issue date is wrong.",
        CredentialStatus.EXPIRED: "The credential has expired.",
        CredentialStatus.FORGED: "The seal is a forgery.",
        CredentialStatus.WRONG_HOLDER: "The holder does not match this document.",
    },
    holder_mismatch_text="The passport does not name this bearer.",
    decision_labels={"pass": "Clear the checkpoint", "deny": "Turn away", "arrest": "Detain"},
)

SCHOOL_PRESENTATION = CredentialPresentationProfile(
    indication_labels={"activity": "activity"},
    document_labels={"activity": "activity pass"},
    identity_label="student ID",
    identity_description="A laminated student identification card.",
    document_description="A {document}.",
    status_text={
        CredentialStatus.MISSING_SEAL: "The required teacher signature is missing.",
        CredentialStatus.BAD_DATE: "The date on the pass is wrong.",
        CredentialStatus.EXPIRED: "The pass has expired.",
        CredentialStatus.FORGED: "The teacher signature is forged.",
        CredentialStatus.WRONG_HOLDER: "The student ID does not match this document.",
    },
    holder_mismatch_text="The student ID does not name this student.",
    decision_labels={
        "pass": "Allow onward",
        "deny": "Send back to class",
        "arrest": "Send to office",
    },
)


class CombinedBorderGame(CredentialsGame):
    restriction_map: Restrictions = Field(
        default_factory=lambda: Restrictions.from_map(BORDER_RULES)
    )
    catalog_ref: str = "border"
    presentation: CredentialPresentationProfile = Field(
        default_factory=lambda: BORDER_PRESENTATION.model_copy(deep=True)
    )
    offers: list[ScenarioOffer] = Field(
        default_factory=lambda: [
            ScenarioOffer(
                target_disposition=CredentialDisposition.DENY,
                region="border",
                purpose="work",
                candidate_name="Tomas Vey",
                failure_modes=[FailureMode.UNSEALED_PERMIT],
            )
        ]
    )


class CombinedSchoolGame(CredentialsGame):
    restriction_map: Restrictions = Field(
        default_factory=lambda: Restrictions.from_map(SCHOOL_RULES)
    )
    catalog_ref: str = "school"
    presentation: CredentialPresentationProfile = Field(
        default_factory=lambda: SCHOOL_PRESENTATION.model_copy(deep=True)
    )
    offers: list[ScenarioOffer] = Field(
        default_factory=lambda: [
            ScenarioOffer(
                target_disposition=CredentialDisposition.DENY,
                region="school",
                purpose="activity",
                candidate_name="Mira Quill",
                failure_modes=[FailureMode.UNSEALED_PERMIT],
            )
        ]
    )


class CombinedBorderBlock(HasGame, Block):
    _game_class = CombinedBorderGame
    _game_handler_class = CredentialsGameHandler


class CombinedSchoolBlock(HasGame, Block):
    _game_class = CombinedSchoolGame
    _game_handler_class = CredentialsGameHandler


CombinedBorderBlock.model_rebuild(_types_namespace={"UUID": UUID})
CombinedSchoolBlock.model_rebuild(_types_namespace={"UUID": UUID})
''',
        encoding="utf-8",
    )
    (root / "world.yaml").write_text(
        '''label: combined_credentials
scripts: script.yaml
domain_module: combined_credentials.domain
assets:
  - asset_kind: CredentialDefinition
    catalog: border
    source: border_credentials.yaml
  - asset_kind: CredentialDefinition
    catalog: school
    source: school_credentials.yaml
''',
        encoding="utf-8",
    )
    (root / "border_credentials.yaml").write_text(
        '''identity_card:
  name: Border Identity Card
  origin_ids: [border]
  indication: work
  document_kind: id
  requires_id: false
activity_pass:
  name: Work Permit
  origin_ids: [border]
  indication: work
  document_kind: document
  requires_id: true
  facets:
    - channel: choice
      facet_type: giver
      payload: request_document
''',
        encoding="utf-8",
    )
    (root / "school_credentials.yaml").write_text(
        '''identity_card:
  name: Student ID
  origin_ids: [school]
  indication: activity
  document_kind: id
  requires_id: false
activity_pass:
  name: Activity Pass
  origin_ids: [school]
  indication: activity
  document_kind: document
  requires_id: true
  facets:
    - channel: choice
      facet_type: giver
      payload: request_document
''',
        encoding="utf-8",
    )
    (root / "script.yaml").write_text(
        '''label: combined_credentials
metadata:
  title: Combined Credentials
  start_at: activity.entrance
scenes:
  activity:
    blocks:
      entrance:
        content: Choose an inspection assignment.
        actions:
          - text: Work the border checkpoint
            successor: border_shift
          - text: Monitor the school halls
            successor: school_shift
      border_shift:
        kind: combined_credentials.domain.CombinedBorderBlock
        content: Check a traveler at the border.
        continues:
          - successor: victory
            trigger: last
            predicate: game_won
          - successor: defeat
            trigger: last
            predicate: game_lost
      school_shift:
        kind: combined_credentials.domain.CombinedSchoolBlock
        content: Check a student in the hall.
        continues:
          - successor: victory
            trigger: last
            predicate: game_won
          - successor: defeat
            trigger: last
            predicate: game_lost
      victory:
        content: The assignment ends correctly.
      defeat:
        content: The assignment ends with the wrong call.
''',
        encoding="utf-8",
    )
    return WorldCompiler().compile(WorldBundle.load(root))


def test_compiled_story_selects_its_local_credentials_scenarios(tmp_path: Path) -> None:
    """One compiled world yields fresh, catalog-isolated stories for both activities."""

    combined_world = _compile_combined_world(tmp_path)
    assert set(combined_world.assets.values) == {"border", "school"}
    assert CredentialDefinition.get_instance("combined_credentials:border:activity_pass") in (
        combined_world.assets.values["border"].members
    )
    assert CredentialDefinition.get_instance("combined_credentials:school:activity_pass") in (
        combined_world.assets.values["school"].members
    )

    for choice, block_label, catalog_ref, prefix, identity_label, finding, decision in (
        (
            "Work the border checkpoint",
            "border_shift",
            "border",
            "combined_credentials:border:",
            "passport",
            "The issuing stamp is missing.",
            "Turn away",
        ),
        (
            "Monitor the school halls",
            "school_shift",
            "school",
            "combined_credentials:school:",
            "student ID",
            "The required teacher signature is missing.",
            "Send back to class",
        ),
    ):
        result = combined_world.create_story("combined_credentials", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert {action.text for action in _actions(ledger)} == {
            "Work the border checkpoint",
            "Monitor the school halls",
        }
        _choose(ledger, choice)

        block = result.graph.find_one(Selector(label=block_label))
        assert ledger.cursor is block
        game = ledger.cursor.game
        assert isinstance(game, CredentialsGame)
        assert isinstance(ledger.cursor.game_handler, CredentialsGameHandler)
        assert game.catalog_ref == catalog_ref

        first = ledger.cursor.game_handler.get_provisioned_moves(game)
        second = ledger.cursor.game_handler.get_provisioned_moves(game)
        assert first == second
        assert len(game.materialized) == 1
        assert [move.kind for move in first] == ["inspect"]

        case = game.active_case
        assert identity_label in case.presented_documents
        assert finding in case.hidden_facts.values()
        manager = case.packet_manager
        assert manager is not None
        component_ids = {
            component.uid
            for slot_name in (CREDENTIAL_ID_SLOT, CREDENTIAL_PACKET_SLOT)
            for component in manager.get_slot(slot_name)
        }
        packet_components = manager.get_slot(CREDENTIAL_PACKET_SLOT)
        assert packet_components
        assert all(
            component.reference_singleton.label.startswith(prefix)
            for component in packet_components
        )

        restored = Graph.structure(result.graph.unstructure())
        restored_block = restored.find_one(Selector(label=block_label))
        restored_manager = restored_block.game.active_case.packet_manager
        assert restored_manager is not None
        restored_components = [
            component
            for slot_name in (CREDENTIAL_ID_SLOT, CREDENTIAL_PACKET_SLOT)
            for component in restored_manager.get_slot(slot_name)
        ]
        assert {component.uid for component in restored_components} == component_ids
        assert all(
            component.reference_singleton.label.startswith(prefix)
            for component in restored_components
        )
        assert (
            sum(item.uid in component_ids for item in restored.members.values())
            == len(component_ids)
        )

        _inspect(ledger, identity_label)
        _choose(ledger, decision)
        assert ledger.cursor.label == "victory"


def test_combined_world_profiles_one_subject_mismatch_per_skin(tmp_path: Path) -> None:
    combined_world = _compile_combined_world(tmp_path)

    for choice, block_label, identity_label, finding in (
        (
            "Work the border checkpoint",
            "border_shift",
            "passport",
            "The passport does not name this bearer.",
        ),
        (
            "Monitor the school halls",
            "school_shift",
            "student ID",
            "The student ID does not name this student.",
        ),
    ):
        result = combined_world.create_story("combined_credentials", init_mode=InitMode.EAGER)
        block = result.graph.find_one(Selector(label=block_label))
        offer = block.game.offers[0].model_copy(
            update={
                "failure_modes": [FailureMode.FAKE_ID],
                "target_disposition": CredentialDisposition.ARREST,
            }
        )
        block.game.offers = [offer]
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        _choose(ledger, choice)

        case = block.game.active_case
        id_card = case.packet_manager.get_slot(CREDENTIAL_ID_SLOT)[0]
        defects = derive_defects(case.packet_manager, block.game.restriction_map)
        assert [(defect.kind, defect.source_id) for defect in defects] == [
            (CredentialDefectKind.SUBJECT_MISMATCH, id_card.uid),
        ]
        assert case.hidden_facts == {identity_label: finding}
