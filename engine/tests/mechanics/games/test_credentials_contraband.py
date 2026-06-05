"""Tests for Phase B.2 contraband mediation (disclosure / relinquish / search).

The model (CREDENTIALS_LOOP_DESIGN.md B.2): contraband is what must be declared;
concealment is itself the violation. request_disclosure rescues (declare ->
assess as declared); request_search forecloses (concealment stands).
"""

from __future__ import annotations

from tangl.mechanics.games import (
    ContrabandItem,
    CredentialCase,
    CredentialDisposition,
    CredentialStatus,
    CredentialToken,
    CredentialsGame,
    CredentialsGameHandler,
    Indication,
    Region,
    Restrictions,
    RestrictionLevel,
    derive_disposition,
)

D = CredentialDisposition
S = CredentialStatus
IND = Indication
L = RestrictionLevel

# weapon = permit-required, secrets = declaration-only, drugs = forbidden.
RULES = Restrictions.from_map(
    {
        Region.LOCAL: {
            IND.TRAVEL: L.WITH_ID,
            IND.WEAPON: L.WITH_PERMIT,
            IND.SECRETS: L.ANONYMOUS,
            IND.DRUGS: L.FORBIDDEN,
        }
    }
)


def _id(status: S = S.VALID) -> CredentialToken:
    return CredentialToken(indication=IND.TRAVEL, status=status)


def _permit(indication: IND, status: S = S.VALID) -> CredentialToken:
    return CredentialToken(indication=indication, status=status, requires_id=True)


def _case(*possessions: ContrabandItem, packet: list | None = None) -> CredentialCase:
    return CredentialCase(
        purpose=IND.TRAVEL,
        presented_documents={"passport": "An id."},
        id_card=_id(),
        packet=packet or [],
        possessions=list(possessions),
    )


def _derive(case: CredentialCase, fs: dict | None = None) -> CredentialDisposition:
    return derive_disposition(case, RULES, fs)


class TestContrabandDerivation:
    """The graduated declared/concealed x level matrix (no mediation)."""

    def test_declared_declaration_only_allows(self) -> None:
        assert _derive(_case(ContrabandItem(indication=IND.SECRETS))) is D.PASS

    def test_concealed_declaration_only_denies(self) -> None:
        assert _derive(_case(ContrabandItem(indication=IND.SECRETS, concealed=True))) is D.DENY

    def test_declared_permitted_with_permit_allows(self) -> None:
        case = _case(ContrabandItem(indication=IND.WEAPON), packet=[_permit(IND.WEAPON)])
        assert _derive(case) is D.PASS

    def test_declared_permitted_without_permit_denies(self) -> None:
        assert _derive(_case(ContrabandItem(indication=IND.WEAPON))) is D.DENY

    def test_concealed_permitted_without_permit_arrests(self) -> None:
        # Classic smuggling: hidden weapon, no permit.
        assert _derive(_case(ContrabandItem(indication=IND.WEAPON, concealed=True))) is D.ARREST

    def test_concealed_permitted_with_valid_permit_denies(self) -> None:
        # Had the permit but concealed the weapon -> deny (Q1), not arrest.
        case = _case(ContrabandItem(indication=IND.WEAPON, concealed=True), packet=[_permit(IND.WEAPON)])
        assert _derive(case) is D.DENY

    def test_declared_forbidden_denies(self) -> None:
        assert _derive(_case(ContrabandItem(indication=IND.DRUGS))) is D.DENY

    def test_concealed_forbidden_arrests(self) -> None:
        assert _derive(_case(ContrabandItem(indication=IND.DRUGS, concealed=True))) is D.ARREST


class TestDisclosureRescuesSearchForecloses:
    def test_disclosure_rescues_concealed_permitted(self) -> None:
        case = _case(ContrabandItem(indication=IND.WEAPON, concealed=True), packet=[_permit(IND.WEAPON)])
        assert _derive(case) is D.DENY  # concealed, undiscovered
        assert _derive(case, {"disclosure": "declared"}) is D.PASS  # declared -> permitted

    def test_search_does_not_rescue_concealed_permitted(self) -> None:
        case = _case(ContrabandItem(indication=IND.WEAPON, concealed=True), packet=[_permit(IND.WEAPON)])
        # Searching reveals but forecloses the benign explanation -> still deny.
        assert _derive(case, {"search": "confirmed"}) is D.DENY

    def test_disclosure_downgrades_smuggled_forbidden_to_deny(self) -> None:
        case = _case(ContrabandItem(indication=IND.DRUGS, concealed=True))
        assert _derive(case) is D.ARREST  # smuggling forbidden goods
        assert _derive(case, {"disclosure": "declared"}) is D.DENY  # honesty mitigates

    def test_relinquish_clears_declared_contraband(self) -> None:
        case = _case(ContrabandItem(indication=IND.DRUGS))  # declared forbidden -> deny
        assert _derive(case) is D.DENY
        assert _derive(case, {"relinquish": "yielded"}) is D.PASS

    def test_disclose_then_relinquish_clears_smuggled_goods(self) -> None:
        case = _case(ContrabandItem(indication=IND.DRUGS, concealed=True))
        fs = {"disclosure": "declared", "relinquish": "yielded"}
        assert _derive(case, fs) is D.PASS


class TestContrabandMoves:
    def _game(self, *possessions, packet=None):
        game = CredentialsGame(roster=[_case(*possessions, packet=packet)], restriction_map=RULES)
        handler = CredentialsGameHandler()
        handler.setup(game)
        handler.receive_move(game, ("inspect", "passport"))  # reach packet stage
        return game, handler

    def _kinds(self, handler, game):
        return {m.kind for m in handler.get_available_moves(game)}

    def test_disclosure_always_offered_relinquish_gated_on_declared(self) -> None:
        # Concealed-only: disclosure offered, relinquish not (nothing declared yet).
        game, handler = self._game(ContrabandItem(indication=IND.WEAPON, concealed=True))
        kinds = self._kinds(handler, game)
        assert "request_disclosure" in kinds
        assert "request_relinquish" not in kinds

    def test_relinquish_offered_after_disclosure(self) -> None:
        game, handler = self._game(ContrabandItem(indication=IND.WEAPON, concealed=True))
        handler.receive_move(game, ("request_disclosure", ""))
        # Disclosure declared the concealed weapon -> relinquish now offered.
        assert "request_relinquish" in self._kinds(handler, game)

    def test_relinquish_offered_for_declared_contraband(self) -> None:
        game, handler = self._game(ContrabandItem(indication=IND.DRUGS))  # declared
        assert "request_relinquish" in self._kinds(handler, game)

    def test_disclosure_move_rescues_to_pass(self) -> None:
        game, handler = self._game(
            ContrabandItem(indication=IND.WEAPON, concealed=True), packet=[_permit(IND.WEAPON)]
        )
        assert game.expected_disposition(game.active_case) is D.DENY
        handler.receive_move(game, ("request_disclosure", ""))
        assert game.finding_status["disclosure"] == "declared"
        assert game.expected_disposition(game.active_case) is D.PASS

    def test_relinquish_move_clears(self) -> None:
        game, handler = self._game(ContrabandItem(indication=IND.DRUGS))
        handler.receive_move(game, ("request_relinquish", ""))
        assert game.finding_status["relinquish"] == "yielded"
        assert game.expected_disposition(game.active_case) is D.PASS

    def test_search_then_disclosure_does_not_rescue(self) -> None:
        # Search forecloses: once a search confirms concealment, a later
        # disclosure is too late and cannot rescue the concealed-permitted item.
        game, handler = self._game(
            ContrabandItem(indication=IND.WEAPON, concealed=True), packet=[_permit(IND.WEAPON)]
        )
        handler.receive_move(game, ("request_search", ""))
        assert game.expected_disposition(game.active_case) is D.DENY
        handler.receive_move(game, ("request_disclosure", ""))
        assert game.finding_status["disclosure"] == "too_late"
        assert game.expected_disposition(game.active_case) is D.DENY  # not rescued

    def test_disclosure_then_search_still_rescues(self) -> None:
        # Voluntary disclosure before searching rescues; a subsequent search
        # only confirms what was already declared.
        game, handler = self._game(
            ContrabandItem(indication=IND.WEAPON, concealed=True), packet=[_permit(IND.WEAPON)]
        )
        handler.receive_move(game, ("request_disclosure", ""))
        assert game.expected_disposition(game.active_case) is D.PASS
        handler.receive_move(game, ("request_search", ""))
        assert game.finding_status["disclosure"] == "declared"
        assert game.expected_disposition(game.active_case) is D.PASS  # still rescued

    def test_disclosure_with_nothing_to_declare_is_clean(self) -> None:
        game, handler = self._game()  # no contraband
        result = handler.receive_move(game, ("request_disclosure", ""))
        assert result.name == "CONTINUE"
        assert game.finding_status["disclosure"] == "declared"
        # A clean candidate still derives PASS.
        assert game.expected_disposition(game.active_case) is D.PASS


class TestForgedDocumentIsAlwaysACrime:
    def test_forged_unused_permit_arrests(self) -> None:
        # A forged weapon permit with no weapon -> arrest (presenting a fake is
        # criminal on its own), even though the contraband is absent.
        case = _case(packet=[_permit(IND.WEAPON, S.FORGED)])
        assert _derive(case) is D.ARREST

    def test_invalid_unused_permit_is_moot(self) -> None:
        # An expired weapon permit with no weapon -> allow (just remit it for
        # renewal); a merely-invalid unused permit is not a crime.
        case = _case(packet=[_permit(IND.WEAPON, S.EXPIRED)])
        assert _derive(case) is D.PASS


# drugs as a per-se crime in THIS regime; a permissive regime maps it lower.
CRIMINAL_RULES = Restrictions.from_map(
    {Region.LOCAL: {IND.TRAVEL: L.WITH_ID, IND.DRUGS: L.CRIMINAL}}
)


def _derive_crim(case: CredentialCase, fs: dict | None = None) -> CredentialDisposition:
    return derive_disposition(case, CRIMINAL_RULES, fs)


class TestCriminalContrabandTier:
    """A CRIMINAL good is a per-se crime: possession arrests, no rescue (B.2.1)."""

    def test_declared_criminal_arrests(self) -> None:
        assert _derive_crim(_case(ContrabandItem(indication=IND.DRUGS))) is D.ARREST

    def test_concealed_criminal_arrests(self) -> None:
        case = _case(ContrabandItem(indication=IND.DRUGS, concealed=True))
        assert _derive_crim(case) is D.ARREST

    def test_relinquish_does_not_rescue_criminal(self) -> None:
        case = _case(ContrabandItem(indication=IND.DRUGS))  # declared
        assert _derive_crim(case, {"relinquish": "yielded"}) is D.ARREST

    def test_disclose_and_relinquish_do_not_rescue_smuggled_criminal(self) -> None:
        case = _case(ContrabandItem(indication=IND.DRUGS, concealed=True))
        fs = {"disclosure": "declared", "relinquish": "yielded"}
        assert _derive_crim(case, fs) is D.ARREST

    def test_per_rule_set_contrast(self) -> None:
        # Same declared good: relinquishable to PASS under FORBIDDEN (module RULES),
        # but a per-se arrest under CRIMINAL -- the criminality is regime data.
        case = _case(ContrabandItem(indication=IND.DRUGS))
        assert _derive(case, {"relinquish": "yielded"}) is D.PASS
        assert _derive_crim(case, {"relinquish": "yielded"}) is D.ARREST


class TestCriminalSelfEvidence:
    """How the criminal tier interacts with the no_evidence_penalty tax."""

    def _game(self, *possessions):
        game = CredentialsGame(
            roster=[_case(*possessions)],
            restriction_map=CRIMINAL_RULES,
            no_evidence_penalty=1,
        )
        handler = CredentialsGameHandler()
        handler.setup(game)
        return game, handler

    def test_visible_criminal_is_self_evident_arrest(self) -> None:
        # Openly carried criminal goods justify an arrest on their face.
        game, handler = self._game(ContrabandItem(indication=IND.DRUGS))
        assert game.expected_disposition(game.active_case) is D.ARREST
        handler.receive_move(game, ("decide", "arrest"))
        result = game.case_results[-1]
        assert result.unjustified is False
        assert result.penalty == 0

    def test_concealed_criminal_blind_arrest_is_taxed(self) -> None:
        # Smuggled criminal goods are hidden: arresting without searching is a
        # blind (if correct) call, so the tax fires.
        game, handler = self._game(ContrabandItem(indication=IND.DRUGS, concealed=True))
        assert game.expected_disposition(game.active_case) is D.ARREST
        handler.receive_move(game, ("decide", "arrest"))  # no search
        assert game.case_results[-1].unjustified is True

    def test_concealed_criminal_after_search_is_justified(self) -> None:
        game, handler = self._game(ContrabandItem(indication=IND.DRUGS, concealed=True))
        handler.receive_move(game, ("request_search", ""))  # confirms concealment
        handler.receive_move(game, ("decide", "arrest"))
        result = game.case_results[-1]
        assert result.unjustified is False
        assert result.penalty == 0
