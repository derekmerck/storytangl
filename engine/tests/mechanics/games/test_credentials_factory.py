"""Tests for the procedural candidate factory (Phase A.2)."""

from __future__ import annotations

import random

import pytest

from tangl.mechanics.credentials import (
    CredentialToken,
    materialize_packet,
)
from tangl.mechanics.games import (
    CredentialCase,
    CredentialDefectKind,
    CredentialDisposition,
    CredentialStatus,
    FailureClass,
    FailureMode,
    Indication,
    Region,
    Restrictions,
    RestrictionLevel,
    applicable_modes,
    build_valid,
    degrade,
    derive_defects,
    derive_disposition,
    make_case,
    render_narrative,
    sample_failure_mode,
)

D = CredentialDisposition
IND = Indication
L = RestrictionLevel

RULES = Restrictions.from_map(
    {
        Region.LOCAL: {
            IND.TRAVEL: L.WITH_ID,
            IND.WORK: L.WITH_PERMIT,
            IND.WEAPON: L.WITH_PERMIT,
            IND.DRUGS: L.FORBIDDEN,
        }
    }
)

EXPECTED_CLASS_DISPOSITION = {
    FailureClass.MITIGATABLE: D.DENY,
    FailureClass.CRIME: D.ARREST,
}

EXPECTED_DEFECT_KIND = {
    FailureMode.MISSING_PERMIT: CredentialDefectKind.MISSING_EVIDENCE,
    FailureMode.UNSEALED_PERMIT: CredentialDefectKind.INVALID_EVIDENCE,
    FailureMode.FORGED_PERMIT: CredentialDefectKind.FRAUDULENT_EVIDENCE,
    FailureMode.WRONG_HOLDER_PERMIT: CredentialDefectKind.SUBJECT_MISMATCH,
    FailureMode.MISSING_ID: CredentialDefectKind.MISSING_EVIDENCE,
    FailureMode.EXPIRED_ID: CredentialDefectKind.INVALID_EVIDENCE,
    FailureMode.FAKE_ID: CredentialDefectKind.SUBJECT_MISMATCH,
    FailureMode.UNPERMITTED_CONTRABAND: CredentialDefectKind.UNAUTHORIZED_POSSESSION,
    FailureMode.CONCEALED_CONTRABAND: CredentialDefectKind.UNDECLARED_POSSESSION,
}


def _derive(case: CredentialCase) -> CredentialDisposition:
    return derive_disposition(case.packet_manager, RULES)


class TestBuildValid:
    def test_work_candidate_passes(self) -> None:
        assert _derive(build_valid(Region.LOCAL, IND.WORK, RULES)) is D.PASS

    def test_travel_candidate_passes(self) -> None:
        assert _derive(build_valid(Region.LOCAL, IND.TRAVEL, RULES)) is D.PASS

    def test_with_permittable_contraband_passes(self) -> None:
        case = build_valid(Region.LOCAL, IND.WORK, RULES, contraband=[IND.WEAPON])
        assert _derive(case) is D.PASS

    def test_rejects_forbidden_contraband(self) -> None:
        # Drugs are forbidden locally: no valid packet can carry them.
        with pytest.raises(ValueError):
            build_valid(Region.LOCAL, IND.TRAVEL, RULES, contraband=[IND.DRUGS])


class TestRoundTripInvariant:
    """degrade(build_valid(...), mode) derives to the mode's class disposition."""

    @pytest.mark.parametrize("mode", list(FailureMode))
    def test_single_mode_derives_to_its_class(self, mode: FailureMode) -> None:
        # Use a WORK candidate so permit and id surfaces both exist.
        case = make_case(Region.LOCAL, IND.WORK, RULES, failure_modes=[mode])
        assert _derive(case) is EXPECTED_CLASS_DISPOSITION[mode.failure_class]
        assert EXPECTED_DEFECT_KIND[mode] in {
            defect.kind for defect in derive_defects(case.packet_manager, RULES)
        }

    def test_composition_takes_the_worst(self) -> None:
        # A mitigatable permit flaw plus a smuggling crime -> arrest.
        case = make_case(
            Region.LOCAL,
            IND.WORK,
            RULES,
            failure_modes=[FailureMode.UNSEALED_PERMIT, FailureMode.CONCEALED_CONTRABAND],
        )
        assert _derive(case) is D.ARREST


class TestGeneratedPresentation:
    def test_concealed_contraband_is_not_rendered_as_declared(self) -> None:
        case = make_case(
            Region.LOCAL,
            IND.WORK,
            RULES,
            failure_modes=[FailureMode.CONCEALED_CONTRABAND],
        )

        assert "declared weapon" not in case.presented_documents

    def test_optional_visible_invalid_document_keeps_its_finding(self) -> None:
        case = CredentialCase(
            packet_manager=materialize_packet(
                owner=object(),
                region=Region.LOCAL,
                purpose=IND.TRAVEL,
                id_card=CredentialToken(indication=IND.TRAVEL),
                credentials=[
                    CredentialToken(
                        indication=IND.WEAPON,
                        status=CredentialStatus.EXPIRED,
                        requires_id=True,
                    )
                ],
                possessions=[],
                label_prefix="Traveler",
            )
        )

        render_narrative(case, derive_defects(case.packet_manager, RULES))

        assert _derive(case) is D.PASS
        assert case.hidden_facts["weapon permit"] == "The credential has expired."


class TestApplicability:
    def test_work_candidate_exposes_permit_and_id_modes(self) -> None:
        modes = applicable_modes(build_valid(Region.LOCAL, IND.WORK, RULES))
        assert FailureMode.FORGED_PERMIT in modes
        assert FailureMode.FAKE_ID in modes

    def test_travel_candidate_has_no_permit_modes(self) -> None:
        # Travel is id-only locally: no permit exists to forge.
        modes = applicable_modes(build_valid(Region.LOCAL, IND.TRAVEL, RULES))
        assert FailureMode.FORGED_PERMIT not in modes
        assert FailureMode.MISSING_PERMIT not in modes
        assert FailureMode.FAKE_ID in modes

    def test_filter_by_class(self) -> None:
        case = build_valid(Region.LOCAL, IND.WORK, RULES)
        crimes = applicable_modes(case, FailureClass.CRIME)
        assert crimes
        assert all(m.failure_class is FailureClass.CRIME for m in crimes)


class TestSampling:
    @pytest.mark.parametrize("failure_class", [FailureClass.MITIGATABLE, FailureClass.CRIME])
    def test_sampled_mode_derives_to_target_class(self, failure_class: FailureClass) -> None:
        rng = random.Random(1234)
        for _ in range(20):
            case = build_valid(Region.LOCAL, IND.WORK, RULES)
            mode = sample_failure_mode(case, failure_class, rng)
            assert mode is not None
            assert mode.failure_class is failure_class
            degrade(case, [mode])
            assert _derive(case) is EXPECTED_CLASS_DISPOSITION[failure_class]
