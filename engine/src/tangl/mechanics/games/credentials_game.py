"""
Credential checkpoint shift built on the inspect-and-commit picking loop.

A single :class:`CredentialsGame` hosts a *roster* of candidates. Each candidate
is evaluated through the same staged virtual subloop -- inspect documents,
review the packet, then choose a disposition -- and the shift ends only when the
final candidate has been dispositioned. This is the "one outer game with staged
virtual subgames" shape recommended in ``CREDENTIALS_LOOP_DESIGN.md``: no nested
game blocks and no extra story edges. The loop lives inside the game; the hosting
:class:`~tangl.mechanics.games.has_game.HasGame` block re-provisions moves for the
next candidate after every disposition until the game reports terminal.
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from pydantic import Field

if TYPE_CHECKING:
    from .credentials_roster import ScenarioOffer

from tangl.core.bases import BaseModelPlus
from tangl.journal.fragments import ContentFragment

from .credentials_enums import (
    DEFAULT_RESTRICTIONS,
    ContrabandItem,
    CredentialStatus,
    CredentialToken,
    Indication,
    Region,
    Restrictions,
    RestrictionLevel,
)
from .enums import GameResult, RoundResult
from .game import Game
from .picking_game import PickingGame, PickingGameHandler, PickingMove


class CredentialDisposition(Enum):
    """Terminal disposition for a single candidate."""

    PASS = "pass"
    DENY = "deny"
    ARREST = "arrest"


CredentialsMove = PickingMove


class CredentialCase(BaseModelPlus):
    """One candidate, with an opaque credential packet behind a discovery API.

    The narrative strings (``presented_documents`` / ``hidden_facts`` /
    ``packet_hidden_facts``) drive the v1 inspect loop. The *structured truth*
    (``region`` / ``purpose`` / ``id_card`` / ``packet`` / ``possessions``) is
    what :func:`derive_disposition` reads -- but only through the discovery
    methods below, never by reaching into the fields. That keeps the internal
    representation swappable (flat tokens today; a Singleton catalog with media
    later, see ``CREDENTIALS_LOOP_DESIGN.md`` A.6) behind one stable surface.

    ``correct_disposition`` is an optional authored *override*: when set it wins,
    otherwise the disposition is derived from the rules.
    """

    candidate_name: str = "Traveler"

    # --- Narrative surface for the (v1) inspect loop -------------------------
    required_documents: list[str] = Field(
        default_factory=lambda: ["passport", "travel permit"]
    )
    presented_documents: dict[str, str] = Field(
        default_factory=lambda: {
            "passport": "A worn passport with a blurred seal.",
            "travel permit": "A permit stamped for this week.",
            "baggage": "A lacquered case with a stubborn clasp.",
        }
    )
    hidden_facts: dict[str, str] = Field(
        default_factory=lambda: {
            "passport": "The seal impression is wrong for this border.",
        }
    )
    packet_hidden_facts: dict[str, str] = Field(
        default_factory=lambda: {
            "packet consistency": "The packet does not satisfy the checkpoint rules as presented.",
        }
    )

    # --- Structured truth (read only via the discovery API below) ------------
    region: Region = Region.LOCAL
    purpose: Indication = Indication.TRAVEL
    id_card: CredentialToken | None = None
    packet: list[CredentialToken] = Field(default_factory=list)
    possessions: list[ContrabandItem] = Field(default_factory=list)

    # Authored override; None means "derive from the rules".
    correct_disposition: CredentialDisposition | None = None

    # --- Phase C seams (context overrides / haggling) -----------------------
    whitelist: bool = False
    blacklist: bool = False
    bribe_offer: int = 0

    # ----- Discovery API ----------------------------------------------------
    # The only surface the game loop and derive_disposition may use to ask the
    # packet about its content, declared intent, and validity.

    def get_region(self) -> Region:
        return self.region

    def get_purpose(self) -> Indication:
        return self.purpose

    def id_status(self) -> CredentialStatus | None:
        """Status of the bearer id, or ``None`` if no id was presented."""

        return self.id_card.status if self.id_card is not None else None

    def credential_for(self, indication: Indication) -> CredentialToken | None:
        """The presented credential satisfying ``indication``, if any."""

        return next((c for c in self.packet if c.indication is indication), None)

    def get_contraband(self) -> list[ContrabandItem]:
        return list(self.possessions)


class CredentialCaseResult(BaseModelPlus):
    """Auditable record of one dispositioned candidate."""

    candidate_name: str
    chosen_disposition: CredentialDisposition
    expected_disposition: CredentialDisposition
    correct: bool
    discovered_findings: dict[str, str] = Field(default_factory=dict)
    packet_findings: dict[str, str] = Field(default_factory=dict)


def _default_roster() -> list[CredentialCase]:
    """A two-candidate shift so a bare game is playable and demonstrable."""

    return [
        CredentialCase(correct_disposition=CredentialDisposition.DENY),
        CredentialCase(
            candidate_name="Tomas Vey",
            presented_documents={
                "passport": "A crisp passport, its seal sharp and current.",
                "travel permit": "A permit stamped for this very week.",
            },
            hidden_facts={},
            packet_hidden_facts={},
            correct_disposition=CredentialDisposition.PASS,
        ),
    ]


# --- Disposition derivation (reads cases only via the discovery API) --------

_DISPOSITION_SEVERITY: dict[CredentialDisposition, int] = {
    CredentialDisposition.PASS: 0,
    CredentialDisposition.DENY: 1,
    CredentialDisposition.ARREST: 2,
}


def _worse(a: CredentialDisposition, b: CredentialDisposition) -> CredentialDisposition:
    return a if _DISPOSITION_SEVERITY[a] >= _DISPOSITION_SEVERITY[b] else b


def _assess_credential(token: CredentialToken | None) -> CredentialDisposition:
    if token is None:
        return CredentialDisposition.DENY  # missing -> produce it (mitigatable)
    if token.status.is_valid:
        return CredentialDisposition.PASS
    if token.status.is_crime:
        return CredentialDisposition.ARREST  # forged
    return CredentialDisposition.DENY  # missing seal / bad date / expired


def _assess_id(case: CredentialCase) -> CredentialDisposition:
    status = case.id_status()
    if status is None:
        return CredentialDisposition.DENY  # missing id -> produce it (mitigatable)
    if status.is_valid:
        return CredentialDisposition.PASS
    if status.is_crime:
        return CredentialDisposition.ARREST  # fake / wrong-holder id
    return CredentialDisposition.DENY


def _assess_requirement(
    case: CredentialCase,
    indication: Indication,
    level: RestrictionLevel,
) -> CredentialDisposition:
    """Assess one indication against its required level (the two error surfaces)."""

    worst = CredentialDisposition.PASS
    if level.requires_permit:
        permit = case.credential_for(indication)
        worst = _worse(worst, _assess_credential(permit))
        if permit is not None and not permit.holder_matches:
            worst = _worse(worst, CredentialDisposition.ARREST)  # permit/id mismatch
    if level.requires_id:
        worst = _worse(worst, _assess_id(case))
    return worst


def _assess_contraband(
    case: CredentialCase,
    item: ContrabandItem,
    level: RestrictionLevel,
) -> CredentialDisposition:
    if item.concealed:
        return CredentialDisposition.ARREST  # concealment is a crime
    if level is RestrictionLevel.FORBIDDEN:
        return CredentialDisposition.DENY  # declared but forbidden -> relinquish
    return _assess_requirement(case, item.indication, level)


def derive_disposition(
    case: CredentialCase,
    restrictions: Restrictions,
) -> CredentialDisposition:
    """Derive the correct disposition from the rules and the candidate's packet.

    Reads the candidate only through its discovery API, so the packet's internal
    representation stays opaque. Returns the most-severe applicable outcome
    (ARREST > DENY > PASS).
    """

    region = case.get_region()
    worst = CredentialDisposition.PASS

    purpose = case.get_purpose()
    level = restrictions.level_for(region, purpose, RestrictionLevel.ANONYMOUS)
    if level is RestrictionLevel.FORBIDDEN:
        worst = _worse(worst, CredentialDisposition.DENY)  # purpose not allowed
    else:
        worst = _worse(worst, _assess_requirement(case, purpose, level))

    for item in case.get_contraband():
        level = restrictions.level_for(region, item.indication, RestrictionLevel.FORBIDDEN)
        worst = _worse(worst, _assess_contraband(case, item, level))

    return worst


class CredentialsGame(PickingGame):
    """A checkpoint shift: a roster of candidates inspected one at a time."""

    # --- Shift configuration (authored; never reset between candidates) ------
    roster: list[CredentialCase] = Field(default_factory=_default_roster)
    # Optional lazy roster: when set, candidates are sampled offers materialized
    # on arrival (Phase A.3), and `offers` is the source of truth instead of
    # `roster`. See credentials_roster.py.
    offers: list["ScenarioOffer"] = Field(default_factory=list)
    checkpoint_rules: list[str] = Field(
        default_factory=lambda: [
            "Travelers need a valid passport.",
            "This route also requires a travel permit.",
        ]
    )
    allow_arrest: bool = True
    # ``None`` means "every candidate must be correct" (the strict default).
    pass_threshold: int | None = None
    # The day's rules. Cases derive their disposition against this unless they
    # carry an authored ``correct_disposition`` override.
    restriction_map: Restrictions = Field(
        default_factory=lambda: DEFAULT_RESTRICTIONS.model_copy(deep=True)
    )

    # --- Per-case working state (reset by advance_case) ----------------------
    case_index: int = Field(default=0, json_schema_extra={"reset_field": True})
    current_stage: str = Field(
        default="documents",
        json_schema_extra={"reset_field": True},
    )
    inspected_packet_targets: list[str] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )
    packet_findings: dict[str, str] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )

    # --- Shift-level outcome state (reset only on full setup) ----------------
    case_results: list[CredentialCaseResult] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )
    shift_complete: bool = Field(
        default=False,
        json_schema_extra={"reset_field": True},
    )
    # Lazy cache of materialized offers (cleared on setup; rebuilt on arrival).
    materialized: list[CredentialCase] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )

    # ----- active case access ----------------------------------------------
    def _total_cases(self) -> int:
        """Number of candidates this shift: sampled offers if any, else roster."""

        return len(self.offers) if self.offers else len(self.roster)

    @property
    def active_case(self) -> CredentialCase:
        if not self.offers:
            return self.roster[self.case_index]
        # Lazy: materialize each offer's packet only when the candidate arrives.
        from .credentials_roster import materialize

        while len(self.materialized) <= self.case_index:
            offer = self.offers[len(self.materialized)]
            self.materialized.append(materialize(offer, self.restriction_map))
        return self.materialized[self.case_index]

    @property
    def candidate_name(self) -> str:
        return self.active_case.candidate_name

    @property
    def presented_documents(self) -> dict[str, str]:
        return self.active_case.presented_documents

    @property
    def packet_hidden_facts(self) -> dict[str, str]:
        return self.active_case.packet_hidden_facts

    @property
    def required_documents(self) -> list[str]:
        return self.active_case.required_documents

    @property
    def hidden_findings(self) -> dict[str, str]:
        return self.active_case.hidden_facts

    @property
    def inspected_documents(self) -> list[str]:
        return [t for t in self.inspected_targets if t in self.presented_documents]

    @property
    def discovered_findings(self) -> dict[str, str]:
        return self.revealed_findings

    @property
    def disposition(self) -> CredentialDisposition | None:
        """The disposition committed for the *current* case, or ``None``.

        Per-case, not game-terminal: ``advance_case`` clears it so the next
        candidate starts undecided.
        """

        if self.committed_decision is None:
            return None
        return CredentialDisposition(self.committed_decision)

    @property
    def correct_count(self) -> int:
        return sum(1 for result in self.case_results if result.correct)

    @property
    def required_correct(self) -> int:
        if self.pass_threshold is not None:
            return self.pass_threshold
        return self._total_cases()

    # ----- picking-kernel surface (reads the active case) -------------------
    def get_visible_items(self) -> list[str]:
        return list(self.presented_documents)

    def get_inspect_targets(self) -> list[str]:
        return list(self.presented_documents)

    def get_hidden_facts(self) -> dict[str, str]:
        return dict(self.hidden_findings)

    def get_decision_targets(self) -> list[str]:
        if self.current_stage == "documents":
            return []
        options = [
            CredentialDisposition.PASS.value,
            CredentialDisposition.DENY.value,
        ]
        if self.allow_arrest:
            options.append(CredentialDisposition.ARREST.value)
        return options

    # ----- disposition policy ----------------------------------------------
    def expected_disposition(self, case: CredentialCase) -> CredentialDisposition:
        """Resolve the correct disposition for ``case``.

        Context overrides (whitelist/blacklist) win first; then an authored
        ``correct_disposition`` override if present; otherwise the disposition is
        derived from the day's rules via :func:`derive_disposition`.
        """

        if case.whitelist:
            return CredentialDisposition.PASS
        if case.blacklist:
            return (
                CredentialDisposition.ARREST
                if self.allow_arrest
                else CredentialDisposition.DENY
            )
        if case.correct_disposition is not None:
            return case.correct_disposition
        return derive_disposition(case, self.restriction_map)

    # ----- roster advancement ----------------------------------------------
    def advance_case(self) -> None:
        """Reset per-case working state and step to the next candidate.

        Never touches roster, checkpoint rules, threshold, score, or
        ``case_results``. Sets ``shift_complete`` instead of letting
        ``case_index`` run past the roster, so
        :meth:`CredentialsGameHandler.evaluate` owns shift terminality.
        """

        if self.case_index + 1 < self._total_cases():
            self.case_index += 1
        else:
            self.shift_complete = True

        self.current_stage = "documents"
        self.inspected_targets = []
        self.revealed_findings = {}
        self.inspected_packet_targets = []
        self.packet_findings = {}
        self.committed_decision = None

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        namespace.update(
            {
                # Active candidate / case progress
                "credential_candidate_name": self.candidate_name,
                "credential_required_documents": list(self.required_documents),
                "credential_inspected_documents": list(self.inspected_documents),
                "credential_discovered_findings": dict(self.discovered_findings),
                "credential_num_findings": len(self.discovered_findings),
                "credential_stage": self.current_stage,
                "credential_packet_findings": dict(self.packet_findings),
                "credential_num_packet_findings": len(self.packet_findings),
                "credential_checkpoint_rules": list(self.checkpoint_rules),
                "credential_allow_arrest": self.allow_arrest,
                "credential_disposition": (
                    self.disposition.value if self.disposition is not None else None
                ),
                # Shift / roster progress
                "credential_case_index": self.case_index,
                "credential_case_number": self.case_index + 1,
                "credential_roster_size": self._total_cases(),
                "credential_cases_remaining": self._total_cases() - len(self.case_results),
                "credential_correct_count": self.correct_count,
                "credential_shift_score": dict(self.score),
                "credential_shift_complete": self.shift_complete,
            }
        )
        return namespace


class CredentialsGameHandler(PickingGameHandler[CredentialsGame]):
    """Handler for an inspect-and-dispose checkpoint shift."""

    game_cls: ClassVar[type[Game]] = CredentialsGame

    def get_available_inspect_targets(self, game: CredentialsGame) -> list[str]:
        case = game.active_case
        targets = [
            name for name in case.presented_documents if name not in game.inspected_documents
        ]
        if game.current_stage != "documents":
            targets.extend(
                target
                for target in case.packet_hidden_facts
                if target not in game.inspected_packet_targets
            )
        return targets

    def get_move_label(self, game: CredentialsGame, move: CredentialsMove) -> str:
        if move.kind == "inspect":
            if move.target in game.active_case.packet_hidden_facts:
                return f"Review {move.target}"
            return f"Inspect {move.target}"
        return f"Choose {move.target}"

    def resolve_inspection(
        self,
        game: CredentialsGame,
        target: str,
        detail: dict[str, object],
    ) -> RoundResult:
        case = game.active_case

        if target in case.packet_hidden_facts:
            game.inspected_packet_targets.append(target)
            finding = self._packet_finding(game, target)
            if finding is not None:
                game.packet_findings[target] = finding
                detail["finding"] = finding
                detail["outcome"] = "packet_finding"
            else:
                detail["finding"] = "The packet still hangs together under current scrutiny."
                detail["outcome"] = "packet_clear"
            game.current_stage = "packet"
            return RoundResult.CONTINUE

        finding = case.hidden_facts.get(target)
        if finding is not None:
            game.revealed_findings[target] = finding
            detail["finding"] = finding
            detail["outcome"] = "finding"
        else:
            detail["finding"] = "It looks in order."
            detail["outcome"] = "clear"
        game.current_stage = "packet"
        return RoundResult.CONTINUE

    def resolve_decision(
        self,
        game: CredentialsGame,
        target: str,
        detail: dict[str, object],
    ) -> RoundResult:
        case = game.active_case
        chosen = CredentialDisposition(target)
        expected = game.expected_disposition(case)
        correct = chosen == expected

        game.case_results.append(
            CredentialCaseResult(
                candidate_name=case.candidate_name,
                chosen_disposition=chosen,
                expected_disposition=expected,
                correct=correct,
                discovered_findings=dict(game.revealed_findings),
                packet_findings=dict(game.packet_findings),
            )
        )

        detail["candidate"] = case.candidate_name
        detail["credential_stage"] = game.current_stage
        if correct:
            game.score["player"] = game.score.get("player", 0) + 1
            detail["outcome"] = "correct_disposition"
        else:
            game.score["opponent"] = game.score.get("opponent", 0) + 1
            detail["outcome"] = "wrong_disposition"
            detail["correct_disposition"] = expected.value

        round_result = RoundResult.WIN if correct else RoundResult.LOSE
        game.advance_case()
        return round_result

    def evaluate(self, game: CredentialsGame) -> GameResult:
        """Own shift terminality: in process until the final candidate is decided."""

        if not game.shift_complete:
            return GameResult.IN_PROCESS
        if game.correct_count >= game.required_correct:
            return GameResult.WIN
        return GameResult.LOSE

    def build_round_notes(
        self,
        game: CredentialsGame,
        player_move: CredentialsMove,
        opponent_move: CredentialsMove | None,
        round_result: RoundResult,
    ) -> dict[str, object] | None:
        detail = dict(super().build_round_notes(game, player_move, opponent_move, round_result) or {})
        detail["discovered_findings"] = dict(game.revealed_findings)
        detail["packet_findings"] = dict(game.packet_findings)
        detail.setdefault("credential_stage", game.current_stage)
        detail["case_index"] = game.case_index
        detail["correct_count"] = game.correct_count
        detail["shift_complete"] = game.shift_complete
        return detail

    def get_journal_fragments(self, game: CredentialsGame) -> list[ContentFragment] | None:
        last_round = game.last_round
        if last_round is None:
            return []

        action = last_round.player_move.kind
        target = last_round.player_move.target
        notes = last_round.notes or {}

        if action == "inspect":
            if str(notes.get("outcome", "")).startswith("packet"):
                return [
                    ContentFragment(content=f"You review {target}."),
                    ContentFragment(content=str(notes.get("finding", "No new contradiction appears."))),
                ]
            return [
                ContentFragment(content=f"You inspect the {target}."),
                ContentFragment(content=str(notes.get("finding", "Nothing new emerges."))),
            ]

        candidate = notes.get("candidate", "the traveler")
        if last_round.result == RoundResult.WIN:
            outcome_line = f"{candidate} absorbs the ruling without protest."
        else:
            outcome_line = (
                f"The room turns uneasy. The right call for {candidate} was "
                f"{notes.get('correct_disposition', 'a different ruling')}."
            )

        fragments = [
            ContentFragment(content=f"You choose to {target}."),
            ContentFragment(content=outcome_line),
        ]
        if game.shift_complete:
            fragments.append(
                ContentFragment(
                    content=(
                        f"Shift complete: {game.correct_count} of {len(game.roster)} "
                        "calls correct."
                    )
                )
            )
        else:
            fragments.append(
                ContentFragment(content="The next traveler steps up to the counter.")
            )
        return fragments

    def _packet_finding(self, game: CredentialsGame, target: str) -> str | None:
        case = game.active_case
        if target not in case.packet_hidden_facts:
            return None
        if case.whitelist:
            return "The whitelist seal overrides the usual packet mismatch."
        if case.blacklist:
            return "The packet matches a standing blacklist notice at this checkpoint."
        if case.bribe_offer > 0:
            return (
                f"The packet comes with a quiet offer of {case.bribe_offer} in side payment. "
                f"{case.packet_hidden_facts[target]}"
            )
        return case.packet_hidden_facts[target]
