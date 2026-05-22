"""Tests for rules-based disposition derivation (Phase A.1)."""

from __future__ import annotations

from tangl.mechanics.games import (
    ContrabandItem,
    CredentialCase,
    CredentialDisposition,
    CredentialStatus,
    CredentialToken,
    CredentialsGame,
    DEFAULT_RESTRICTIONS,
    Indication,
    Region,
    Restrictions,
    RestrictionLevel,
    derive_disposition,
)

D = CredentialDisposition
S = CredentialStatus
I = Indication
L = RestrictionLevel

# A compact local rule set used across the matrix tests.
LOCAL_RULES = Restrictions.from_map(
    {
        Region.LOCAL: {
            I.TRAVEL: L.WITH_ID,
            I.WORK: L.WITH_PERMIT,
            I.EMIGRATE: L.ANONYMOUS,
            I.WEAPON: L.WITH_PERMIT,
            I.DRUGS: L.FORBIDDEN,
            I.SECRETS: L.FORBIDDEN,
        }
    }
)


def _id(status: S) -> CredentialToken:
    return CredentialToken(indication=I.TRAVEL, status=status)


def _permit(indication: I, status: S = S.VALID, holder_matches: bool = True) -> CredentialToken:
    return CredentialToken(
        indication=indication, status=status, requires_id=True, holder_matches=holder_matches
    )


def _derive(case: CredentialCase) -> CredentialDisposition:
    return derive_disposition(case, LOCAL_RULES)


class TestAnonymousAndId:
    def test_anonymous_purpose_passes_without_documents(self) -> None:
        case = CredentialCase(purpose=I.EMIGRATE)  # ANONYMOUS locally
        assert _derive(case) is D.PASS

    def test_with_id_valid_passes(self) -> None:
        case = CredentialCase(purpose=I.TRAVEL, id_card=_id(S.VALID))
        assert _derive(case) is D.PASS

    def test_with_id_missing_denies(self) -> None:
        case = CredentialCase(purpose=I.TRAVEL, id_card=None)
        assert _derive(case) is D.DENY

    def test_with_id_expired_denies(self) -> None:
        case = CredentialCase(purpose=I.TRAVEL, id_card=_id(S.EXPIRED))
        assert _derive(case) is D.DENY

    def test_with_id_fake_arrests(self) -> None:
        case = CredentialCase(purpose=I.TRAVEL, id_card=_id(S.WRONG_HOLDER))
        assert _derive(case) is D.ARREST


class TestPermit:
    def test_valid_permit_and_id_passes(self) -> None:
        case = CredentialCase(
            purpose=I.WORK, id_card=_id(S.VALID), packet=[_permit(I.WORK)]
        )
        assert _derive(case) is D.PASS

    def test_missing_permit_denies(self) -> None:
        case = CredentialCase(purpose=I.WORK, id_card=_id(S.VALID), packet=[])
        assert _derive(case) is D.DENY

    def test_missing_seal_permit_denies(self) -> None:
        case = CredentialCase(
            purpose=I.WORK, id_card=_id(S.VALID), packet=[_permit(I.WORK, S.MISSING_SEAL)]
        )
        assert _derive(case) is D.DENY

    def test_forged_permit_arrests(self) -> None:
        case = CredentialCase(
            purpose=I.WORK, id_card=_id(S.VALID), packet=[_permit(I.WORK, S.FORGED)]
        )
        assert _derive(case) is D.ARREST

    def test_permit_holder_mismatch_arrests(self) -> None:
        case = CredentialCase(
            purpose=I.WORK,
            id_card=_id(S.VALID),
            packet=[_permit(I.WORK, S.VALID, holder_matches=False)],
        )
        assert _derive(case) is D.ARREST


class TestTwoErrorSurfaces:
    """The permit document and the id linkage are independent error surfaces."""

    def test_valid_permit_but_fake_id_arrests(self) -> None:
        case = CredentialCase(
            purpose=I.WORK, id_card=_id(S.WRONG_HOLDER), packet=[_permit(I.WORK)]
        )
        assert _derive(case) is D.ARREST

    def test_forged_permit_but_valid_id_arrests(self) -> None:
        case = CredentialCase(
            purpose=I.WORK, id_card=_id(S.VALID), packet=[_permit(I.WORK, S.FORGED)]
        )
        assert _derive(case) is D.ARREST


class TestSeverityAndForbidden:
    def test_severity_takes_the_worst(self) -> None:
        # A mitigatable permit (deny) plus concealed contraband (arrest) -> arrest.
        case = CredentialCase(
            purpose=I.WORK,
            id_card=_id(S.VALID),
            packet=[_permit(I.WORK, S.MISSING_SEAL)],
            possessions=[ContrabandItem(indication=I.WEAPON, concealed=True)],
        )
        assert _derive(case) is D.ARREST

    def test_forbidden_purpose_denies(self) -> None:
        rules = Restrictions.from_map({Region.LOCAL: {I.WORK: L.FORBIDDEN}})
        case = CredentialCase(purpose=I.WORK, id_card=_id(S.VALID))
        assert derive_disposition(case, rules) is D.DENY


class TestContraband:
    def test_concealed_contraband_arrests(self) -> None:
        case = CredentialCase(
            purpose=I.TRAVEL,
            id_card=_id(S.VALID),
            possessions=[ContrabandItem(indication=I.DRUGS, concealed=True)],
        )
        assert _derive(case) is D.ARREST

    def test_declared_forbidden_contraband_denies(self) -> None:
        case = CredentialCase(
            purpose=I.TRAVEL,
            id_card=_id(S.VALID),
            possessions=[ContrabandItem(indication=I.DRUGS, concealed=False)],
        )
        assert _derive(case) is D.DENY

    def test_declared_permitted_contraband_with_permit_passes(self) -> None:
        case = CredentialCase(
            purpose=I.TRAVEL,
            id_card=_id(S.VALID),
            packet=[_permit(I.WEAPON)],
            possessions=[ContrabandItem(indication=I.WEAPON, concealed=False)],
        )
        assert _derive(case) is D.PASS


class TestRegionalSelection:
    def test_same_purpose_differs_by_region(self) -> None:
        # Work is permit-gated locally but forbidden from the hostile west.
        local = CredentialCase(
            region=Region.LOCAL, purpose=I.WORK, id_card=_id(S.VALID), packet=[_permit(I.WORK)]
        )
        hostile = CredentialCase(
            region=Region.FOREIGN_WEST, purpose=I.WORK, id_card=_id(S.VALID), packet=[_permit(I.WORK)]
        )
        assert derive_disposition(local, DEFAULT_RESTRICTIONS) is D.PASS
        assert derive_disposition(hostile, DEFAULT_RESTRICTIONS) is D.DENY


class TestExpectedDispositionWiring:
    def test_derives_when_no_authored_override(self) -> None:
        case = CredentialCase(purpose=I.WORK, id_card=_id(S.VALID), packet=[_permit(I.WORK, S.FORGED)])
        game = CredentialsGame(roster=[case], restriction_map=LOCAL_RULES)
        assert game.expected_disposition(case) is D.ARREST

    def test_authored_override_wins_over_derivation(self) -> None:
        # Would derive ARREST, but the author pins PASS.
        case = CredentialCase(
            purpose=I.WORK,
            id_card=_id(S.VALID),
            packet=[_permit(I.WORK, S.FORGED)],
            correct_disposition=D.PASS,
        )
        game = CredentialsGame(roster=[case], restriction_map=LOCAL_RULES)
        assert game.expected_disposition(case) is D.PASS
