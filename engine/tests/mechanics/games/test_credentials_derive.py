"""Tests for rules-based disposition derivation (Phase A.1)."""

from __future__ import annotations

from tangl.mechanics.credentials import CREDENTIAL_ID_SLOT, CREDENTIAL_PACKET_SLOT
from tangl.mechanics.games import (
    ContrabandItem,
    CredentialDefectKind,
    CredentialDisposition,
    CredentialStatus,
    CredentialToken,
    CredentialsGame,
    DEFAULT_RESTRICTIONS,
    FailureClass,
    Indication,
    Region,
    Restrictions,
    RestrictionLevel,
    derive_disposition,
    derive_defects,
)
from engine.tests.mechanics.games.credentials_helpers import make_credential_case as CredentialCase

D = CredentialDisposition
S = CredentialStatus
IND = Indication
L = RestrictionLevel

# A compact local rule set used across the matrix tests.
LOCAL_RULES = Restrictions.from_map(
    {
        Region.LOCAL: {
            IND.TRAVEL: L.WITH_ID,
            IND.WORK: L.WITH_PERMIT,
            IND.EMIGRATE: L.ANONYMOUS,
            IND.WEAPON: L.WITH_PERMIT,
            IND.DRUGS: L.FORBIDDEN,
            IND.SECRETS: L.FORBIDDEN,
        }
    }
)


def _id(status: S) -> CredentialToken:
    return CredentialToken(indication=IND.TRAVEL, status=status)


def _permit(indication: IND, status: S = S.VALID, holder_matches: bool = True) -> CredentialToken:
    return CredentialToken(
        indication=indication, status=status, requires_id=True, holder_matches=holder_matches
    )


def _derive(case: CredentialCase) -> CredentialDisposition:
    return derive_disposition(case.packet_manager, LOCAL_RULES)


class TestPacketManager:
    def test_case_delegates_to_its_single_packet_manager(self) -> None:
        case = CredentialCase(
            region=Region.FOREIGN_EAST,
            purpose=IND.WORK,
            id_card=_id(S.VALID),
            packet=[_permit(IND.WORK)],
            possessions=[ContrabandItem(indication=IND.WEAPON, concealed=False)],
        )

        packet = case.packet_manager
        assert packet.get_region() is case.get_region()
        assert packet.get_purpose() is case.get_purpose()
        assert packet.id_status() is case.id_status()
        assert packet.credential_for(IND.WORK) == case.credential_for(IND.WORK)
        assert packet.get_contraband() == case.get_contraband()
        assert packet.all_credentials() == case.all_credentials()

    def test_derive_disposition_reads_the_concrete_manager(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK,
            id_card=_id(S.VALID),
            packet=[_permit(IND.WORK, S.MISSING_SEAL)],
        )

        assert derive_disposition(case.packet_manager, LOCAL_RULES) is D.DENY
        assert (
            derive_disposition(case.packet_manager, LOCAL_RULES, {IND.WORK.value: "cleared"})
            is D.PASS
        )


class TestStructuredDefects:
    def test_defect_records_document_cause_and_component_source(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK,
            id_card=_id(S.VALID),
            packet=[_permit(IND.WORK, S.MISSING_SEAL)],
        )
        component = case.packet_manager.get_slot(CREDENTIAL_PACKET_SLOT)[0]

        defects = derive_defects(case.packet_manager, LOCAL_RULES)
        assert [
            (
                defect.kind,
                defect.failure_class,
                defect.subject,
                defect.indication,
                defect.source_id,
                defect.cause,
            )
            for defect in defects
        ] == [
            (
                CredentialDefectKind.INVALID_EVIDENCE,
                FailureClass.MITIGATABLE,
                "authorization",
                IND.WORK,
                component.uid,
                S.MISSING_SEAL,
            )
        ]

    def test_mediation_suppresses_the_remediable_defect_not_packet_truth(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK,
            id_card=_id(S.VALID),
            packet=[_permit(IND.WORK, S.MISSING_SEAL)],
        )

        assert derive_defects(case.packet_manager, LOCAL_RULES)
        assert derive_defects(
            case.packet_manager,
            LOCAL_RULES,
            {IND.WORK.value: "cleared"},
        ) == []
        assert case.credential_for(IND.WORK).status is S.MISSING_SEAL

    def test_wrong_id_compiles_to_one_subject_mismatch(self) -> None:
        case = CredentialCase(purpose=IND.TRAVEL, id_card=_id(S.WRONG_HOLDER))
        id_card = case.packet_manager.get_slot(CREDENTIAL_ID_SLOT)[0]

        defects = derive_defects(case.packet_manager, LOCAL_RULES)

        assert id_card.status is S.VALID
        assert id_card.subject_id != case.packet_manager.bearer_id
        assert [(defect.kind, defect.failure_class, defect.source_id) for defect in defects] == [
            (CredentialDefectKind.SUBJECT_MISMATCH, FailureClass.CRIME, id_card.uid),
        ]

    def test_wrong_permit_compiles_to_a_document_subject_mismatch(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK,
            id_card=_id(S.VALID),
            packet=[_permit(IND.WORK, holder_matches=False)],
        )
        id_card = case.packet_manager.get_slot(CREDENTIAL_ID_SLOT)[0]
        permit = case.packet_manager.get_slot(CREDENTIAL_PACKET_SLOT)[0]

        defects = derive_defects(case.packet_manager, LOCAL_RULES)

        assert permit.subject_id != id_card.subject_id
        assert [(defect.kind, defect.failure_class, defect.source_id) for defect in defects] == [
            (CredentialDefectKind.SUBJECT_MISMATCH, FailureClass.CRIME, permit.uid),
        ]

    def test_missing_id_does_not_manufacture_a_subject_mismatch(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK,
            id_card=None,
            packet=[_permit(IND.WORK, holder_matches=False)],
        )

        defects = derive_defects(case.packet_manager, LOCAL_RULES)

        assert [defect.kind for defect in defects] == [CredentialDefectKind.MISSING_EVIDENCE]


class TestAnonymousAndId:
    def test_anonymous_purpose_passes_without_documents(self) -> None:
        case = CredentialCase(purpose=IND.EMIGRATE)  # ANONYMOUS locally
        assert _derive(case) is D.PASS

    def test_with_id_valid_passes(self) -> None:
        case = CredentialCase(purpose=IND.TRAVEL, id_card=_id(S.VALID))
        assert _derive(case) is D.PASS

    def test_with_id_missing_denies(self) -> None:
        case = CredentialCase(purpose=IND.TRAVEL, id_card=None)
        assert _derive(case) is D.DENY

    def test_with_id_expired_denies(self) -> None:
        case = CredentialCase(purpose=IND.TRAVEL, id_card=_id(S.EXPIRED))
        assert _derive(case) is D.DENY

    def test_with_id_fake_arrests(self) -> None:
        case = CredentialCase(purpose=IND.TRAVEL, id_card=_id(S.WRONG_HOLDER))
        assert _derive(case) is D.ARREST


class TestPermit:
    def test_valid_permit_and_id_passes(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK, id_card=_id(S.VALID), packet=[_permit(IND.WORK)]
        )
        assert _derive(case) is D.PASS

    def test_missing_permit_denies(self) -> None:
        case = CredentialCase(purpose=IND.WORK, id_card=_id(S.VALID), packet=[])
        assert _derive(case) is D.DENY

    def test_missing_seal_permit_denies(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK, id_card=_id(S.VALID), packet=[_permit(IND.WORK, S.MISSING_SEAL)]
        )
        assert _derive(case) is D.DENY

    def test_forged_permit_arrests(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK, id_card=_id(S.VALID), packet=[_permit(IND.WORK, S.FORGED)]
        )
        assert _derive(case) is D.ARREST

    def test_permit_holder_mismatch_arrests(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK,
            id_card=_id(S.VALID),
            packet=[_permit(IND.WORK, S.VALID, holder_matches=False)],
        )
        assert _derive(case) is D.ARREST


class TestTwoErrorSurfaces:
    """The permit document and the id linkage are independent error surfaces."""

    def test_valid_permit_but_fake_id_arrests(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK, id_card=_id(S.WRONG_HOLDER), packet=[_permit(IND.WORK)]
        )
        assert _derive(case) is D.ARREST

    def test_forged_permit_but_valid_id_arrests(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK, id_card=_id(S.VALID), packet=[_permit(IND.WORK, S.FORGED)]
        )
        assert _derive(case) is D.ARREST


class TestSeverityAndForbidden:
    def test_severity_takes_the_worst(self) -> None:
        # A mitigatable permit (deny) plus concealed contraband (arrest) -> arrest.
        case = CredentialCase(
            purpose=IND.WORK,
            id_card=_id(S.VALID),
            packet=[_permit(IND.WORK, S.MISSING_SEAL)],
            possessions=[ContrabandItem(indication=IND.WEAPON, concealed=True)],
        )
        assert _derive(case) is D.ARREST

    def test_forbidden_purpose_denies(self) -> None:
        rules = Restrictions.from_map({Region.LOCAL: {IND.WORK: L.FORBIDDEN}})
        case = CredentialCase(purpose=IND.WORK, id_card=_id(S.VALID))
        assert derive_disposition(case.packet_manager, rules) is D.DENY


class TestContraband:
    def test_concealed_contraband_arrests(self) -> None:
        case = CredentialCase(
            purpose=IND.TRAVEL,
            id_card=_id(S.VALID),
            possessions=[ContrabandItem(indication=IND.DRUGS, concealed=True)],
        )
        assert _derive(case) is D.ARREST

    def test_declared_forbidden_contraband_denies(self) -> None:
        case = CredentialCase(
            purpose=IND.TRAVEL,
            id_card=_id(S.VALID),
            possessions=[ContrabandItem(indication=IND.DRUGS, concealed=False)],
        )
        assert _derive(case) is D.DENY

    def test_declared_permitted_contraband_with_permit_passes(self) -> None:
        case = CredentialCase(
            purpose=IND.TRAVEL,
            id_card=_id(S.VALID),
            packet=[_permit(IND.WEAPON)],
            possessions=[ContrabandItem(indication=IND.WEAPON, concealed=False)],
        )
        assert _derive(case) is D.PASS


class TestRegionalSelection:
    def test_same_purpose_differs_by_region(self) -> None:
        # Work is permit-gated locally but forbidden from the hostile west.
        local = CredentialCase(
            region=Region.LOCAL, purpose=IND.WORK, id_card=_id(S.VALID), packet=[_permit(IND.WORK)]
        )
        hostile = CredentialCase(
            region=Region.FOREIGN_WEST, purpose=IND.WORK, id_card=_id(S.VALID), packet=[_permit(IND.WORK)]
        )
        assert derive_disposition(local.packet_manager, DEFAULT_RESTRICTIONS) is D.PASS
        assert derive_disposition(hostile.packet_manager, DEFAULT_RESTRICTIONS) is D.DENY


class TestExpectedDispositionWiring:
    def test_derives_when_no_authored_override(self) -> None:
        case = CredentialCase(purpose=IND.WORK, id_card=_id(S.VALID), packet=[_permit(IND.WORK, S.FORGED)])
        game = CredentialsGame(roster=[case], restriction_map=LOCAL_RULES)
        assert game.expected_disposition(case) is D.ARREST

    def test_authored_override_wins_over_derivation(self) -> None:
        # Would derive ARREST, but the author pins PASS.
        case = CredentialCase(
            purpose=IND.WORK,
            id_card=_id(S.VALID),
            packet=[_permit(IND.WORK, S.FORGED)],
            correct_disposition=D.PASS,
        )
        game = CredentialsGame(roster=[case], restriction_map=LOCAL_RULES)
        assert game.expected_disposition(case) is D.PASS
