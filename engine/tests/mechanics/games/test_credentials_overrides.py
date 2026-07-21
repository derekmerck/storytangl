"""Phase C: whitelist / blacklist identity overrides.

The override is *data*, not a subsystem: `whitelist`/`blacklist` flags on the case
feed `expected_disposition` (whitelist clamps down to PASS, blacklist clamps up to
ARREST), layered above `derive_disposition`. These tests pin the compositions with
the layers added since the override was first wired -- the CRIMINAL contraband
tier and the no_evidence_penalty tax -- and show that the **overt vs shadow
blacklist** distinction is the existing tax toggle, not new code:

  * overt blacklist (arrest by name) -- the name is authorization; tax off.
  * shadow blacklist (arrest *with reason*) -- tax on, so a bare name-arrest of a
    clean candidate reads as unjustified, which is the pressure to manufacture
    cover (the deferred planting malfeasance layer).
"""

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
    derive_disposition,
)
from engine.tests.mechanics.games.credentials_helpers import make_credential_case as CredentialCase

D = CredentialDisposition
S = CredentialStatus
IND = Indication
L = RestrictionLevel

RULES = Restrictions.from_map(
    {Region.LOCAL: {IND.TRAVEL: L.WITH_ID, IND.DRUGS: L.CRIMINAL}}
)


# --------------------------------------------------------------------------- #
# fixtures / helpers
# --------------------------------------------------------------------------- #
def _id(status: S = S.VALID) -> CredentialToken:
    return CredentialToken(indication=IND.TRAVEL, status=status)


def _clean(**kw) -> CredentialCase:
    return CredentialCase(
        purpose=IND.TRAVEL,
        presented_documents={"passport": "An id."},
        id_card=_id(),
        **kw,
    )


def _smuggler(**kw) -> CredentialCase:
    # Carries concealed criminal goods -> derives ARREST on its own.
    return CredentialCase(
        purpose=IND.TRAVEL,
        presented_documents={"passport": "An id."},
        id_card=_id(),
        possessions=[ContrabandItem(indication=IND.DRUGS, concealed=True)],
        **kw,
    )


def _game(
    case: CredentialCase, **kw
) -> tuple[CredentialsGame, CredentialsGameHandler]:
    game = CredentialsGame(roster=[case], restriction_map=RULES, **kw)
    handler = CredentialsGameHandler()
    handler.setup(game)
    return game, handler


# --------------------------------------------------------------------------- #
# test classes
# --------------------------------------------------------------------------- #
class TestWhitelist:
    def test_whitelist_clamps_a_criminal_packet_to_pass(self) -> None:
        # The sponsored-carrier exemption: even per-se-criminal goods are waved
        # through (the whitelist overlay sits above derive_disposition).
        case = _smuggler(whitelist=True)
        assert derive_disposition(case.packet_manager, RULES) is D.ARREST  # the packet is criminal
        game, _ = _game(case)
        assert game.expected_disposition(case) is D.PASS  # ...but sponsored -> pass

    def test_whitelisted_pass_is_never_taxed(self) -> None:
        game, handler = _game(_smuggler(whitelist=True), no_evidence_penalty=1)
        handler.receive_move(game, ("decide", "pass"))
        result = game.case_results[-1]
        assert result.correct is True
        assert result.unjustified is False
        assert result.penalty == 0


class TestBlacklist:
    def test_blacklist_escalates_a_clean_packet_to_arrest(self) -> None:
        case = _clean(blacklist=True)
        assert derive_disposition(case.packet_manager, RULES) is D.PASS  # nothing wrong
        game, _ = _game(case)
        assert game.expected_disposition(case) is D.ARREST  # ...but wanted -> arrest

    def test_blacklist_without_arrest_falls_back_to_deny(self) -> None:
        game, _ = _game(_clean(blacklist=True), allow_arrest=False)
        assert game.expected_disposition(game.active_case) is D.DENY


class TestOvertVsShadowBlacklist:
    """Same blacklisted clean candidate; the regime's tax toggle is the only
    difference between an overt and a shadow blacklist."""

    def test_overt_blacklist_arrest_is_free(self) -> None:
        # Tax off: the name on the list is authorization enough.
        game, handler = _game(_clean(blacklist=True), no_evidence_penalty=0)
        handler.receive_move(game, ("decide", "arrest"))
        result = game.case_results[-1]
        assert result.correct is True
        assert result.unjustified is False
        assert result.penalty == 0

    def test_shadow_blacklist_arrest_is_taxed(self) -> None:
        # Tax on: a clean candidate has no surfaced or self-evident grounds, so a
        # bare name-arrest is unjustified -- the pressure to manufacture cover.
        game, handler = _game(_clean(blacklist=True), no_evidence_penalty=1)
        handler.receive_move(game, ("decide", "arrest"))
        result = game.case_results[-1]
        assert result.correct is True
        assert result.unjustified is True
        assert result.penalty == 1
