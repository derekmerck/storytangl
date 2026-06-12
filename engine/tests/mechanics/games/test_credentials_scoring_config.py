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
    default_penalty_matrix,
    disposition_penalty,
)

D = CredentialDisposition
S = CredentialStatus
IND = Indication
L = RestrictionLevel

RULES = Restrictions.from_map(
    {
        Region.LOCAL: {
            IND.TRAVEL: L.WITH_ID,
            IND.WEAPON: L.WITH_PERMIT,
            IND.DRUGS: L.FORBIDDEN,
            IND.WORK: L.FORBIDDEN,  # the purpose itself is disallowed today
        }
    }
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


def _missing_id_case(name: str = "Cleo") -> CredentialCase:
    # WITH_ID purpose but no id at all -> expected DENY; the absence is visible.
    return CredentialCase(
        candidate_name=name,
        purpose=IND.TRAVEL,
        presented_documents={"passport": "(none presented)"},
        id_card=None,
        packet=[],
    )


def _forbidden_purpose_case(name: str = "Eve") -> CredentialCase:
    # Valid id, but the stated purpose (WORK) is forbidden today -> expected DENY;
    # the purpose itself is the visible ground, nothing to inspect.
    return CredentialCase(
        candidate_name=name,
        purpose=IND.WORK,
        presented_documents={"passport": "An id."},
        id_card=_id(),
        packet=[],
    )


def _declared_drugs_case(name: str = "Dmitri") -> CredentialCase:
    # Openly carried (non-concealed) forbidden goods -> expected DENY; visible.
    return CredentialCase(
        candidate_name=name,
        purpose=IND.TRAVEL,
        presented_documents={"passport": "An id."},
        id_card=_id(),
        packet=[],
        possessions=[ContrabandItem(indication=IND.DRUGS)],
    )


def _game(
    roster: list[CredentialCase], **overrides: object
) -> tuple[CredentialsGame, CredentialsGameHandler]:
    game = CredentialsGame(roster=roster, restriction_map=RULES, **overrides)
    handler = CredentialsGameHandler()
    handler.setup(game)
    return game, handler


def _decide(handler: CredentialsGameHandler, game: CredentialsGame, call: str) -> None:
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
def _decree_matrix() -> dict[str, dict[str, int]]:
    """A fresh 'arrest everyone' matrix: a non-arrest is a hard failure."""

    return {
        "pass": {"pass": 0, "deny": 2, "arrest": 5},
        "deny": {"pass": 2, "deny": 0, "arrest": 5},
        # under decree a non-arrest is a hard failure, not a mild hedge
        "arrest": {"pass": 5, "deny": 5, "arrest": 0},
    }


class TestDecreeRegime:
    """'Arrest everyone, any non-arrest is a failure.'"""

    def test_non_arrest_is_a_hard_failure(self) -> None:
        # A candidate whose expected call is ARREST, denied -> decree penalty 5.
        case = _bad_id_case()
        case.correct_disposition = D.ARREST  # the regime's expectation
        game, handler = _game([case], penalty_matrix=_decree_matrix(), penalty_threshold=0)
        _decide(handler, game, "deny")
        assert game.case_results[-1].penalty == 5
        assert game.result.name == "LOSE"

    def test_arrest_is_clean_under_decree(self) -> None:
        case = _bad_id_case()
        case.correct_disposition = D.ARREST
        game, handler = _game([case], penalty_matrix=_decree_matrix())
        _decide(handler, game, "arrest")
        assert game.case_results[-1].penalty == 0
        assert game.result.name == "WIN"

    def test_decree_leaves_no_evidence_toggle_off(self) -> None:
        # Arresting-by-decree needs no evidence; the toggle defaults to 0 so an
        # unbacked correct arrest is not taxed.
        case = _bad_id_case()
        case.correct_disposition = D.ARREST
        game, handler = _game([case], penalty_matrix=_decree_matrix())
        _decide(handler, game, "arrest")  # no inspection at all
        assert game.case_results[-1].unjustified is False
        assert game.case_results[-1].penalty == 0

    def test_partial_matrix_overrides_only_named_cells(self) -> None:
        # A regime can supply just the row it wants to change; missing rows/cells
        # fall back to the standard matrix.
        partial = {"arrest": {"pass": 5, "deny": 5, "arrest": 0}}
        case = _bad_id_case()
        case.correct_disposition = D.ARREST
        game, handler = _game([case], penalty_matrix=partial)
        _decide(handler, game, "deny")  # overridden cell -> 5
        assert game.case_results[-1].penalty == 5

    def test_partial_matrix_falls_back_for_unspecified_rows(self) -> None:
        # The "deny" row is unspecified, so a wrong call against a should-deny
        # candidate uses the standard penalty (deny->arrest = 5).
        partial = {"arrest": {"pass": 5, "deny": 5, "arrest": 0}}
        game, handler = _game([_bad_id_case()], penalty_matrix=partial)  # expected DENY
        _decide(handler, game, "arrest")
        assert game.case_results[-1].penalty == 5  # standard deny->arrest


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
        # on *correct* rejections, so a wrong deny is unaffected.
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


class TestEvidenceTaxEdgeCases:
    """Special-handling cases for what counts as evidence."""

    def test_clean_search_does_not_count_as_evidence(self) -> None:
        # A clean search turned nothing up; it must not suppress the tax on an
        # unrelated unsurfaced issue (the expired id).
        game, handler = _game([_bad_id_case()], no_evidence_penalty=1)
        handler.receive_move(game, ("request_search", ""))  # clean -> "cleared"
        assert game.finding_status.get("search") == "cleared"
        _decide(handler, game, "deny")
        assert game.case_results[-1].unjustified is True
        assert game.case_results[-1].penalty == 1

    def test_missing_required_credential_is_self_evident(self) -> None:
        # No id presented for a WITH_ID purpose: the absence is visible, so a deny
        # is justified without any inspection -- not taxed.
        game, handler = _game([_missing_id_case()], no_evidence_penalty=1)
        _decide(handler, game, "deny")
        result = game.case_results[-1]
        assert result.correct is True
        assert result.unjustified is False
        assert result.penalty == 0

    def test_forbidden_purpose_is_self_evident(self) -> None:
        # The stated purpose is disallowed today; denying needs no inspection.
        game, handler = _game([_forbidden_purpose_case()], no_evidence_penalty=1)
        assert game.expected_disposition(game.active_case) is D.DENY
        _decide(handler, game, "deny")
        result = game.case_results[-1]
        assert result.correct is True
        assert result.unjustified is False
        assert result.penalty == 0

    def test_openly_declared_forbidden_contraband_is_self_evident(self) -> None:
        # Visibly-carried forbidden goods justify a deny on their face -- not taxed.
        game, handler = _game([_declared_drugs_case()], no_evidence_penalty=1)
        assert game.expected_disposition(game.active_case) is D.DENY
        _decide(handler, game, "deny")
        result = game.case_results[-1]
        assert result.unjustified is False
        assert result.penalty == 0

    def test_concealed_contraband_is_not_self_evident(self) -> None:
        # A *concealed* item is hidden: denying without searching is unjustified.
        case = _declared_drugs_case()
        case.possessions = [ContrabandItem(indication=IND.DRUGS, concealed=True)]
        game, handler = _game([case], no_evidence_penalty=1)
        assert game.expected_disposition(game.active_case) is D.ARREST  # smuggling
        _decide(handler, game, "arrest")  # correct, but blind
        assert game.case_results[-1].unjustified is True

    def test_tax_keys_off_correct_not_zero_penalty(self) -> None:
        # A lenient matrix tolerates a deny of a clean candidate at zero cost. The
        # call is *wrong* (expected PASS), so the evidence tax must not fire even
        # though the matrix penalty is 0.
        lenient = {"pass": {"pass": 0, "deny": 0, "arrest": 5}}
        game, handler = _game([_clean_case()], penalty_matrix=lenient, no_evidence_penalty=1)
        _decide(handler, game, "deny")  # expected PASS -> wrong, but tolerated
        result = game.case_results[-1]
        assert result.correct is False
        assert result.unjustified is False
        assert result.penalty == 0  # tolerated, and not taxed
