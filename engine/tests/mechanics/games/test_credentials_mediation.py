"""Tests for Phase B.1 mediation moves (request_document / verify_id / request_search)."""

from __future__ import annotations

from tangl.mechanics.games import (
    ContrabandItem,
    CredentialDisposition,
    CredentialStatus,
    CredentialToken,
    CredentialsGame,
    CredentialsGameHandler,
    Indication,
    Region,
    Restrictions,
    RestrictionLevel,
)
from engine.tests.mechanics.games.credentials_helpers import make_credential_case as CredentialCase

D = CredentialDisposition
S = CredentialStatus
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


def _id(status: S = S.VALID) -> CredentialToken:
    return CredentialToken(indication=IND.TRAVEL, status=status)


def _permit(indication: IND, status: S = S.VALID) -> CredentialToken:
    return CredentialToken(indication=indication, status=status, requires_id=True)


def _game(*cases: CredentialCase, **overrides) -> tuple[CredentialsGame, CredentialsGameHandler]:
    game = CredentialsGame(roster=list(cases), restriction_map=RULES, **overrides)
    handler = CredentialsGameHandler()
    handler.setup(game)
    return game, handler


def _move_kinds(handler: CredentialsGameHandler, game: CredentialsGame) -> set[str]:
    return {m.kind for m in handler.get_available_moves(game)}


class TestMediationAvailability:
    def test_mediation_moves_gated_on_packet_stage(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK, id_card=_id(), packet=[_permit(IND.WORK, S.MISSING_SEAL)]
        )
        game, handler = _game(case)
        # documents stage: only inspect moves available.
        assert _move_kinds(handler, game) == {"inspect"}

        handler.receive_move(game, ("inspect", "passport"))
        # packet stage: inspect (remaining) + decide + mediation kinds appear.
        kinds = _move_kinds(handler, game)
        assert {"decide", "request_document", "verify_id", "request_search"}.issubset(kinds)

    def test_request_document_offered_for_all_present_permits(self) -> None:
        # Disclosure discipline: the menu must NOT reveal which permits are
        # flawed. request_document is offered for every presented permit
        # (valid, mitigatable, or forged) -- you can't tell the dud from the
        # useful one until you commit it.
        case = CredentialCase(
            purpose=IND.WORK,
            id_card=_id(),
            packet=[
                _permit(IND.WORK, S.MISSING_SEAL),
                _permit(IND.WEAPON, S.FORGED),
            ],
        )
        game, handler = _game(case)
        handler.receive_move(game, ("inspect", "passport"))

        request_targets = {
            m.target for m in handler.get_available_moves(game) if m.kind == "request_document"
        }
        assert request_targets == {IND.WORK.value, IND.WEAPON.value}

    def test_verify_id_skipped_without_id(self) -> None:
        # No id presented at all -- a *visible* absence, not hidden validity --
        # so the move is meaningless and absent. (This reveals nothing the
        # client can't already see in the packet.)
        case = CredentialCase(purpose=IND.TRAVEL, id_card=None)
        case.presented_documents = {"baggage": "An empty case."}
        game, handler = _game(case)
        handler.receive_move(game, ("inspect", "baggage"))

        assert "verify_id" not in _move_kinds(handler, game)

    def test_verify_id_offered_regardless_of_hidden_id_status(self) -> None:
        # An expired id is mitigatably invalid, but the menu must not leak that:
        # verify_id is offered the same as for a valid id.
        case = CredentialCase(purpose=IND.TRAVEL, id_card=_id(S.EXPIRED))
        game, handler = _game(case)
        handler.receive_move(game, ("inspect", "passport"))

        assert "verify_id" in _move_kinds(handler, game)

    def test_request_document_on_a_crime_records_without_clearing(self) -> None:
        # Requesting reissue of a forged permit discloses (via the outcome) that
        # it won't hold up, but never upgrades the disposition.
        case = CredentialCase(
            purpose=IND.WORK, id_card=_id(), packet=[_permit(IND.WORK, S.FORGED)]
        )
        game, handler = _game(case)
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("request_document", IND.WORK.value))

        assert game.finding_status[IND.WORK.value] == "confirmed"
        assert game.expected_disposition(case) is D.ARREST

    def test_each_mediation_move_offered_once_per_case(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK, id_card=_id(), packet=[_permit(IND.WORK, S.MISSING_SEAL)]
        )
        game, handler = _game(case)
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("verify_id", ""))

        # After running verify_id, it's recorded in finding_status and not offered again.
        assert "verify_id" not in _move_kinds(handler, game)


class TestMediationEffects:
    def test_request_document_clears_mitigatable_finding(self) -> None:
        case = CredentialCase(
            purpose=IND.WORK, id_card=_id(), packet=[_permit(IND.WORK, S.MISSING_SEAL)]
        )
        game, handler = _game(case)
        # Before mediation: derives DENY.
        assert game.expected_disposition(case) is D.DENY

        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("request_document", IND.WORK.value))

        assert game.finding_status[IND.WORK.value] == "cleared"
        # After mediation: derives PASS.
        assert game.expected_disposition(case) is D.PASS

    def test_verify_id_verifies_a_valid_id(self) -> None:
        case = CredentialCase(purpose=IND.TRAVEL, id_card=_id(S.VALID))
        game, handler = _game(case)
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("verify_id", ""))

        # "verified", not "cleared": verifying the holder does not repair docs.
        assert game.finding_status["id"] == "verified"
        assert game.expected_disposition(case) is D.PASS  # unchanged but audited

    def test_verify_id_does_not_repair_an_expired_id(self) -> None:
        # verify_id confirms the holder matches, but the id is still expired:
        # the disposition stays DENY (id-reissue is B.2).
        case = CredentialCase(purpose=IND.TRAVEL, id_card=_id(S.EXPIRED))
        game, handler = _game(case)
        assert game.expected_disposition(case) is D.DENY

        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("verify_id", ""))

        assert game.finding_status["id"] == "verified"
        assert game.expected_disposition(case) is D.DENY  # holder ok, still expired

    def test_verify_id_confirms_a_fake_id(self) -> None:
        case = CredentialCase(purpose=IND.TRAVEL, id_card=_id(S.WRONG_HOLDER))
        game, handler = _game(case)
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("verify_id", ""))

        assert game.finding_status["id"] == "confirmed"
        assert game.expected_disposition(case) is D.ARREST  # unchanged, still arrest

    def test_request_search_finds_concealed_contraband(self) -> None:
        case = CredentialCase(
            purpose=IND.TRAVEL,
            id_card=_id(),
            possessions=[ContrabandItem(indication=IND.WEAPON, concealed=True)],
        )
        case.presented_documents = {"passport": "An identity document."}
        game, handler = _game(case)
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("request_search", ""))

        assert game.finding_status["search"] == "confirmed"
        # Concealment is already ARREST; mediation confirms in the audit.
        assert game.expected_disposition(case) is D.ARREST

    def test_request_search_clean_when_no_concealment(self) -> None:
        case = CredentialCase(purpose=IND.TRAVEL, id_card=_id())
        game, handler = _game(case)
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("request_search", ""))

        assert game.finding_status["search"] == "cleared"
        assert game.expected_disposition(case) is D.PASS

class TestMediationLifecycle:
    def test_finding_status_resets_on_advance_case(self) -> None:
        # case 0 mediated (cleared), then dispositioned -> case 1 starts fresh.
        case0 = CredentialCase(
            purpose=IND.WORK, id_card=_id(), packet=[_permit(IND.WORK, S.MISSING_SEAL)]
        )
        case1 = CredentialCase(purpose=IND.TRAVEL, id_card=_id(S.VALID))
        game, handler = _game(case0, case1)

        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("request_document", IND.WORK.value))
        handler.receive_move(game, ("decide", "pass"))  # cleared -> PASS

        assert game.case_index == 1
        assert game.finding_status == {}  # reset for the next candidate

    def test_inspect_and_decide_still_work_unchanged(self) -> None:
        # Regression: the picking kernel's inspect/decide path is unaffected.
        case = CredentialCase(
            purpose=IND.WORK, id_card=_id(), packet=[_permit(IND.WORK, S.MISSING_SEAL)]
        )
        # Author the answer so we exercise the decide path without going via derive.
        case.correct_disposition = D.DENY
        game, handler = _game(case)

        handler.receive_move(game, ("inspect", "passport"))
        result = handler.receive_move(game, ("decide", "deny"))

        assert result.name == "WIN"
        assert game.shift_complete
