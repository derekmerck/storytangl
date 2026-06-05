"""Tests for per-rule-set scoring configuration (CREDENTIALS_LOOP_DESIGN.md
"Engine review" §2): the penalty matrix is a per-game knob, and the
no_evidence_penalty toggle taxes correct-but-unbacked rejections.

Two regimes exercise the generality:
  * a rule-of-law gate that wants dispositions justified by evidence; and
  * a decree regime ("arrest everyone, any non-arrest fails") whose penalty
    matrix makes deny/pass hard failures and leaves the evidence toggle off.
"""

from __future__ import annotations

from tangl.mechanics.games import (
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
    default_penalty_matrix,
    disposition_penalty,
)

D = CredentialDisposition
S = CredentialStatus
IND = Indication
L = RestrictionLevel

RULES = Restrictions.from_map(
    {Region.LOCAL: {IND.TRAVEL: L.WITH_ID, IND.WEAPON: L.WITH_PERMIT}}
)


def _id(status: S = S.VALID) -> CredentialToken:
    return CredentialToken(indication=IND.TRAVEL, status=status)


def _clean_case(name: str = "Ada") -> CredentialCase:
    return CredentialCase(
        candidate_name=name,
        purpose=IND.TRAVEL,
        presented_documents={"passport": "An id."},
        id_card=_id(),
        packet=[],
    )


def _bad_id_case(name: str = "Boris") -> CredentialCase:
    # Expired id -> WITH_ID requirement unmet -> expected DENY. The expiry is a
    # hidden fact, so inspecting the passport surfaces the evidence for the deny.
    return CredentialCase(
        candidate_name=name,
        purpose=IND.TRAVEL,
        presented_documents={"passport": "A worn id."},
        hidden_facts={"passport": "The expiry date has slipped past."},
        id_card=_id(S.EXPIRED),
        packet=[],
    )


def _game(roster, **overrides):
    game = CredentialsGame(roster=roster, restriction_map=RULES, **overrides)
    handler = CredentialsGameHandler()
    handler.setup(game)
    return game, handler


def _decide(handler, game, call: str) -> None:
    handler.receive_move(game, ("decide", call))


# --------------------------------------------------------------------------- #
# default matrix as a per-game field
# --------------------------------------------------------------------------- #
class TestDefaultMatrix:
    def test_default_matrix_is_the_standard(self) -> None:
        game = CredentialsGame()
        assert game.penalty_matrix == default_penalty_matrix()
        assert game.penalty_matrix["pass"]["arrest"] == 5
        assert game.penalty_matrix["deny"]["pass"] == 2

    def test_default_factory_is_not_shared(self) -> None:
        a = CredentialsGame()
        b = CredentialsGame()
        a.penalty_matrix["pass"]["deny"] = 99
        assert b.penalty_matrix["pass"]["deny"] == 2  # independent copies

    def test_helper_accepts_an_explicit_matrix(self) -> None:
        decree = {"arrest": {"pass": 5, "deny": 5, "arrest": 0}}
        assert disposition_penalty(D.ARREST, D.DENY, decree) == 5
        # default unchanged
        assert disposition_penalty(D.ARREST, D.DENY) == 2


# --------------------------------------------------------------------------- #
# a decree regime overrides the matrix
# --------------------------------------------------------------------------- #
class TestDecreeRegime:
    """'Arrest everyone, any non-arrest is a failure.'"""

    DECREE = {
        "pass": {"pass": 0, "deny": 2, "arrest": 5},
        "deny": {"pass": 2, "deny": 0, "arrest": 5},
        # under decree a non-arrest is a hard failure, not a mild hedge
        "arrest": {"pass": 5, "deny": 5, "arrest": 0},
    }

    def test_non_arrest_is_a_hard_failure(self) -> None:
        # A candidate whose expected call is ARREST, denied -> decree penalty 5.
        case = _bad_id_case()
        case.correct_disposition = D.ARREST  # the regime's expectation
        game, handler = _game([case], penalty_matrix=self.DECREE, penalty_threshold=0)
        _decide(handler, game, "deny")
        assert game.case_results[-1].penalty == 5
        assert game.result.name == "LOSE"

    def test_arrest_is_clean_under_decree(self) -> None:
        case = _bad_id_case()
        case.correct_disposition = D.ARREST
        game, handler = _game([case], penalty_matrix=self.DECREE)
        _decide(handler, game, "arrest")
        assert game.case_results[-1].penalty == 0
        assert game.result.name == "WIN"

    def test_decree_leaves_no_evidence_toggle_off(self) -> None:
        # Arresting-by-decree needs no evidence; the toggle defaults to 0 so an
        # unbacked correct arrest is not taxed.
        case = _bad_id_case()
        case.correct_disposition = D.ARREST
        game, handler = _game([case], penalty_matrix=self.DECREE)
        _decide(handler, game, "arrest")  # no inspection at all
        assert game.case_results[-1].unjustified is False
        assert game.case_results[-1].penalty == 0


# --------------------------------------------------------------------------- #
# no_evidence_penalty toggle
# --------------------------------------------------------------------------- #
class TestEvidenceTax:
    def test_off_by_default(self) -> None:
        game, handler = _game([_bad_id_case()])
        assert game.no_evidence_penalty == 0
        _decide(handler, game, "deny")  # correct, but no inspection
        assert game.case_results[-1].penalty == 0
        assert game.case_results[-1].unjustified is False

    def test_correct_unbacked_deny_is_taxed(self) -> None:
        game, handler = _game([_bad_id_case()], no_evidence_penalty=1, penalty_threshold=0)
        _decide(handler, game, "deny")  # correct call, no evidence surfaced
        result = game.case_results[-1]
        assert result.correct is True
        assert result.unjustified is True
        assert result.penalty == 1
        assert game.result.name == "LOSE"  # tax pushed over the strict threshold

    def test_backed_deny_is_not_taxed(self) -> None:
        game, handler = _game([_bad_id_case()], no_evidence_penalty=1)
        handler.receive_move(game, ("inspect", "passport"))  # surfaces the expiry
        _decide(handler, game, "deny")
        result = game.case_results[-1]
        assert result.unjustified is False
        assert result.penalty == 0
        assert game.result.name == "WIN"

    def test_correct_pass_is_never_taxed(self) -> None:
        # Waving a clean candidate through needs no evidence -- only rejections do.
        game, handler = _game([_clean_case()], no_evidence_penalty=1)
        _decide(handler, game, "pass")
        result = game.case_results[-1]
        assert result.unjustified is False
        assert result.penalty == 0

    def test_wrong_call_is_not_double_charged(self) -> None:
        # A wrong call already carries matrix penalty; the evidence tax only fires
        # on correct (penalty == 0) rejections, so a wrong deny is unaffected.
        game, handler = _game([_clean_case()], no_evidence_penalty=1)
        _decide(handler, game, "deny")  # expected PASS -> wrong
        result = game.case_results[-1]
        assert result.correct is False
        assert result.unjustified is False
        assert result.penalty == 2  # pure matrix penalty, no +tax

    def test_tax_rate_scales(self) -> None:
        game, handler = _game([_bad_id_case()], no_evidence_penalty=3, penalty_threshold=10)
        _decide(handler, game, "deny")
        assert game.case_results[-1].penalty == 3

    def test_namespace_exposes_toggle(self) -> None:
        game, _ = _game([_clean_case()], no_evidence_penalty=2)
        assert game.to_namespace()["credential_no_evidence_penalty"] == 2
