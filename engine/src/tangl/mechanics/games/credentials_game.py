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

import uuid
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from pydantic import Field

if TYPE_CHECKING:
    from .credentials_roster import ScenarioOffer

from tangl.core import BaseFragment
from tangl.core.bases import BaseModelPlus
from tangl.journal.fragments import (
    ContentFragment,
    GroupFragment,
    KvFragment,
    KvRow,
    PieceFragment,
    PresentationHints,
)

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


# Fixed namespace so a candidate / packet / document gets a stable fragment uid
# across rounds: the client fragment registry then updates pieces in place
# rather than treating each round's re-emission as new. The game uid is folded
# into the seed so distinct credentials blocks in one journal (e.g. a scheduled
# and a randomized shift) never collide on a shared global fragment id.
_PIECE_NS = uuid.UUID("b7c3f6e2-1d4a-4c9b-9f2e-7a6d5c4b3a21")


def _piece_uid(game_uid: uuid.UUID, case_index: int, key: str) -> uuid.UUID:
    return uuid.uuid5(_PIECE_NS, f"credentials:{game_uid}:{case_index}:{key}")


def _document_kind(label: str) -> str:
    """Best-effort document classification for piece styling.

    Specific document nouns first; a whole-word ``id`` / ``identity`` check last
    so substrings like "valid"/"residence" don't masquerade as id cards.
    """

    low = label.lower()
    words = set(low.split())
    if "permit" in low:
        return "permit"
    if "ticket" in low:
        return "ticket"
    if "passport" in low or "identity" in low or {"id", "ids"} & words:
        return "id_card"
    return "document"


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


def _assess_credential(
    token: CredentialToken | None,
    finding_status: dict[str, str] | None = None,
) -> CredentialDisposition:
    if token is None:
        return CredentialDisposition.DENY  # missing -> produce it (mitigatable)
    if token.status.is_valid:
        return CredentialDisposition.PASS
    if token.status.is_crime:
        return CredentialDisposition.ARREST  # forged; crimes not mediatable in B.1
    # Mitigatable (missing seal / bad date / expired): Phase B.1 mediation can
    # clear it via ``request_document``; check the per-case finding_status.
    if finding_status and finding_status.get(token.indication.value) == "cleared":
        return CredentialDisposition.PASS
    return CredentialDisposition.DENY


def _assess_id(
    case: CredentialCase,
    finding_status: dict[str, str] | None = None,
) -> CredentialDisposition:
    status = case.id_status()
    if status is None:
        return CredentialDisposition.DENY  # missing id -> produce it (mitigatable)
    if status.is_valid:
        return CredentialDisposition.PASS
    if status.is_crime:
        return CredentialDisposition.ARREST  # fake / wrong-holder id
    # Mitigatable id (expired / bad date): cleared by future id-mediation.
    if finding_status and finding_status.get("id") == "cleared":
        return CredentialDisposition.PASS
    return CredentialDisposition.DENY


def _assess_requirement(
    case: CredentialCase,
    indication: Indication,
    level: RestrictionLevel,
    finding_status: dict[str, str] | None = None,
) -> CredentialDisposition:
    """Assess one indication against its required level (the two error surfaces)."""

    worst = CredentialDisposition.PASS
    if level.requires_permit:
        permit = case.credential_for(indication)
        worst = _worse(worst, _assess_credential(permit, finding_status))
        if permit is not None and not permit.holder_matches:
            worst = _worse(worst, CredentialDisposition.ARREST)  # permit/id mismatch
    if level.requires_id:
        worst = _worse(worst, _assess_id(case, finding_status))
    return worst


def _contraband_class(level: RestrictionLevel) -> str:
    """Classify a contraband indication's rule (Phase B.2)."""

    if level is RestrictionLevel.FORBIDDEN:
        return "forbidden"
    if level.requires_permit:
        return "permit_required"
    return "declaration_only"  # allowed if declared (anonymous / id level)


def _assess_contraband(
    case: CredentialCase,
    item: ContrabandItem,
    level: RestrictionLevel,
    finding_status: dict[str, str] | None = None,
) -> CredentialDisposition:
    """Assess one contraband item under the declaration-is-the-requirement model.

    Contraband is, by definition, what must be declared; concealing any of it is
    itself the violation. ``request_disclosure`` rescues (the candidate declares,
    so it is assessed as declared); ``request_search`` only reveals it (the
    concealment stands). See ``CREDENTIALS_LOOP_DESIGN.md`` B.2.
    """

    fs = finding_status or {}
    cls = _contraband_class(level)
    # disclosure declares all concealed goods; a bare un-concealed item is
    # already declared. The contraband's permit (when one is required) lives in
    # the packet keyed by indication, so its standing is assessed by
    # _assess_requirement -- the same machinery as a purpose permit.
    declared = (not item.concealed) or fs.get("disclosure") == "declared"

    if declared:
        if fs.get("relinquish") == "yielded":
            return CredentialDisposition.PASS  # voluntarily surrendered
        if cls == "forbidden":
            return CredentialDisposition.DENY  # declared forbidden -> relinquish/deny
        if cls == "permit_required":
            return _assess_requirement(case, item.indication, level, fs)
        return CredentialDisposition.PASS  # declaration-only, declared -> allow

    # Concealed and not disclosed: concealment is the violation.
    if cls == "forbidden":
        return CredentialDisposition.ARREST  # smuggling forbidden goods
    if cls == "declaration_only":
        return CredentialDisposition.DENY  # concealed declarable goods
    # permit-required, concealed:
    if _assess_requirement(case, item.indication, level, fs) is CredentialDisposition.PASS:
        return CredentialDisposition.DENY  # had a valid permit but concealed it (Q1)
    return CredentialDisposition.ARREST  # smuggling unpermitted goods


def derive_disposition(
    case: CredentialCase,
    restrictions: Restrictions,
    finding_status: dict[str, str] | None = None,
) -> CredentialDisposition:
    """Derive the correct disposition from the rules and the candidate's packet.

    Reads the candidate only through its discovery API, so the packet's internal
    representation stays opaque. Returns the most-severe applicable outcome
    (ARREST > DENY > PASS). If ``finding_status`` is given (Phase B.1 mediation
    outcomes for the active case), cleared mitigatable findings contribute PASS
    instead of DENY.
    """

    region = case.get_region()
    worst = CredentialDisposition.PASS

    purpose = case.get_purpose()
    level = restrictions.level_for(region, purpose, RestrictionLevel.ANONYMOUS)
    if level is RestrictionLevel.FORBIDDEN:
        worst = _worse(worst, CredentialDisposition.DENY)  # purpose not allowed
    else:
        worst = _worse(worst, _assess_requirement(case, purpose, level, finding_status))

    for item in case.get_contraband():
        level = restrictions.level_for(region, item.indication, RestrictionLevel.FORBIDDEN)
        worst = _worse(worst, _assess_contraband(case, item, level, finding_status))

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
    # Mediation outcomes for the active case (Phase B.1): keys are an
    # indication's value (a permit), or "id", or "search". Values are
    # "cleared" / "confirmed". Reset by advance_case so each candidate starts
    # with a clean slate.
    finding_status: dict[str, str] = Field(
        default_factory=dict,
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
        return derive_disposition(case, self.restriction_map, self.finding_status)

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
        self.finding_status = {}

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

    def get_available_moves(self, game: CredentialsGame) -> list[CredentialsMove]:
        """Inspect + decide + (Phase B.1) mediation moves.

        Mediation moves are gated on the packet stage, same as decisions: the
        player inspects at least one document before mediating or deciding.
        """

        moves = list(super().get_available_moves(game))
        if game.current_stage == "documents":
            return moves

        case = game.active_case
        # Mediation availability is gated on *visible* state only -- which
        # documents the candidate presented -- never on hidden validity. The
        # menu must not let a client read backend logic off it: a useful
        # mediation is indistinguishable from a dud until it is committed. (The
        # outcome is disclosed by running the move, not by its presence.)
        #
        # request_document: offer for every presented permit not yet requested.
        for token in case.packet:
            key = token.indication.value
            if key in game.finding_status:
                continue
            moves.append(CredentialsMove(kind="request_document", target=key))
        # verify_id: offer whenever an id is presented and not yet verified.
        if case.id_card is not None and "id" not in game.finding_status:
            moves.append(CredentialsMove(kind="verify_id", target=""))
        # request_search: single move, once per case.
        if "search" not in game.finding_status:
            moves.append(CredentialsMove(kind="request_search", target=""))
        # request_disclosure (B.2): "anything to declare?" -- always offerable
        # (asking reveals nothing the menu shouldn't), once per case.
        if "disclosure" not in game.finding_status:
            moves.append(CredentialsMove(kind="request_disclosure", target=""))
        # request_relinquish (B.2): offer when the candidate has *declared*
        # contraband to surrender (visible, or disclosed via request_disclosure).
        if "relinquish" not in game.finding_status and self._has_declared_contraband(game):
            moves.append(CredentialsMove(kind="request_relinquish", target=""))
        return moves

    @staticmethod
    def _has_declared_contraband(game: CredentialsGame) -> bool:
        disclosed = game.finding_status.get("disclosure") == "declared"
        return any(
            (not item.concealed) or disclosed for item in game.active_case.get_contraband()
        )

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
        if move.kind == "request_document":
            return f"Request reissue of {move.target} permit"
        if move.kind == "verify_id":
            return "Verify identity"
        if move.kind == "request_search":
            return "Request search"
        if move.kind == "request_disclosure":
            return "Ask for anything to declare"
        if move.kind == "request_relinquish":
            return "Have the contraband surrendered"
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

    # ----- Phase B.1 mediation moves ---------------------------------------

    def resolve_move_kind(
        self,
        kind: str,
        game: CredentialsGame,
        player_move: CredentialsMove,
        detail: dict[str, object],
    ) -> RoundResult:
        if kind == "request_document":
            return self._resolve_request_document(game, player_move.target, detail)
        if kind == "verify_id":
            return self._resolve_verify_id(game, detail)
        if kind == "request_search":
            return self._resolve_request_search(game, detail)
        if kind == "request_disclosure":
            return self._resolve_request_disclosure(game, detail)
        if kind == "request_relinquish":
            return self._resolve_request_relinquish(game, detail)
        return super().resolve_move_kind(kind, game, player_move, detail)

    def _resolve_request_document(
        self,
        game: CredentialsGame,
        indication_value: str,
        detail: dict[str, object],
    ) -> RoundResult:
        # The outcome -- not the move's availability -- is what discloses the
        # permit's standing. Requesting a reissue:
        #   mitigatable -> the candidate produces a corrected copy ("cleared");
        #   valid       -> they re-present the same sound permit ("verified");
        #   crime        -> the forgery cannot be reissued; it stands ("confirmed").
        # Only a cleared mitigatable finding upgrades derive_disposition.
        permit = next(
            (t for t in game.active_case.packet if t.indication.value == indication_value),
            None,
        )
        if permit is None:  # off-menu safety; receive_move does not validate
            detail["outcome"] = "request_document_not_applicable"
            detail["target_indication"] = indication_value
            return RoundResult.CONTINUE

        if permit.status.is_crime:
            game.finding_status[indication_value] = "confirmed"
            detail["outcome"] = "request_document_confirmed"
        elif permit.status.is_valid:
            game.finding_status[indication_value] = "verified"
            detail["outcome"] = "request_document_verified"
        else:
            game.finding_status[indication_value] = "cleared"
            detail["outcome"] = "request_document_cleared"
        detail["target_indication"] = indication_value
        return RoundResult.CONTINUE

    def _resolve_verify_id(
        self,
        game: CredentialsGame,
        detail: dict[str, object],
    ) -> RoundResult:
        # verify_id answers only "does the id match the bearer?". It discloses a
        # holder mismatch (a crime) but never mechanically repairs a stale id --
        # an expired or mis-dated id stays a deny until a future id-reissue move
        # (B.2). So it records "verified" / "confirmed", never "cleared".
        status = game.active_case.id_status()
        if status is CredentialStatus.WRONG_HOLDER:
            game.finding_status["id"] = "confirmed"
            detail["outcome"] = "id_verified_problem"
        else:
            game.finding_status["id"] = "verified"
            detail["outcome"] = "id_verified_clean"
        return RoundResult.CONTINUE

    def _resolve_request_search(
        self,
        game: CredentialsGame,
        detail: dict[str, object],
    ) -> RoundResult:
        concealed = [item for item in game.active_case.get_contraband() if item.concealed]
        if concealed:
            game.finding_status["search"] = "confirmed"
            detail["outcome"] = "search_found_concealment"
            detail["concealed"] = [item.indication.value for item in concealed]
        else:
            game.finding_status["search"] = "cleared"
            detail["outcome"] = "search_clean"
        return RoundResult.CONTINUE

    def _resolve_request_disclosure(
        self,
        game: CredentialsGame,
        detail: dict[str, object],
    ) -> RoundResult:
        # "Anything to declare?" -- a compliant candidate (B.2 assumes compliance;
        # lying is B.3) declares any concealed contraband. Declaring rescues
        # concealed-but-permitted goods to the declared assessment (the "oops"
        # path); contrast request_search, which only reveals and forecloses.
        game.finding_status["disclosure"] = "declared"
        concealed = [item for item in game.active_case.get_contraband() if item.concealed]
        if concealed:
            detail["outcome"] = "disclosure_declared"
            detail["declared"] = [item.indication.value for item in concealed]
        else:
            detail["outcome"] = "disclosure_nothing"
        return RoundResult.CONTINUE

    def _resolve_request_relinquish(
        self,
        game: CredentialsGame,
        detail: dict[str, object],
    ) -> RoundResult:
        # The candidate surrenders declared contraband, clearing the violation.
        game.finding_status["relinquish"] = "yielded"
        detail["outcome"] = "relinquished"
        return RoundResult.CONTINUE

    # ----- lifecycle / projection ------------------------------------------

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
        # A decision runs advance_case(), which resets the per-case working state,
        # so read the just-decided case's findings/index from its recorded result
        # rather than the (already reset) live game state.
        if detail.get("action") == "decide" and game.case_results:
            last = game.case_results[-1]
            detail["discovered_findings"] = dict(last.discovered_findings)
            detail["packet_findings"] = dict(last.packet_findings)
            detail["case_index"] = len(game.case_results) - 1
        else:
            detail["discovered_findings"] = dict(game.revealed_findings)
            detail["packet_findings"] = dict(game.packet_findings)
            detail["case_index"] = game.case_index
        detail.setdefault("credential_stage", game.current_stage)
        detail["correct_count"] = game.correct_count
        detail["shift_complete"] = game.shift_complete
        return detail

    def get_journal_fragments(self, game: CredentialsGame) -> list[BaseFragment] | None:
        last_round = game.last_round
        if last_round is None:
            return []

        move = self._normalize_move(last_round.player_move)
        prose = self._prose_fragments(game, last_round, move.kind, move.target, last_round.notes or {})

        fragments: list[BaseFragment] = []
        # Structured candidate / packet view (Bridge.1). Skip once the shift is
        # over -- there is no next candidate to present. On a non-final decision
        # this is the *arriving* candidate, which lands alongside the
        # "next traveler steps up" prose.
        if not game.shift_complete:
            fragments.extend(self._candidate_fragments(game))
        # Findings table for the active case; present on inspect / mediation
        # rounds, empty after a decision resets the working state.
        findings = self._findings_fragment(game)
        if findings is not None:
            fragments.append(findings)
        fragments.extend(prose)
        return fragments

    def _prose_fragments(
        self,
        game: CredentialsGame,
        last_round,
        action: str,
        target: str,
        notes: dict,
    ) -> list[ContentFragment]:
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

        if action == "request_document":
            outcome = notes.get("outcome")
            if outcome == "request_document_cleared":
                line = "The candidate produces a corrected copy."
            elif outcome == "request_document_verified":
                line = "The candidate re-presents the same sound permit."
            elif outcome == "request_document_confirmed":
                line = "No valid copy is forthcoming; the permit will not hold up."
            else:
                line = "There is nothing to reissue."
            return [
                ContentFragment(content=f"You request a reissue of the {target} permit."),
                ContentFragment(content=line),
            ]
        if action == "verify_id":
            outcome = notes.get("outcome")
            if outcome == "id_verified_problem":
                line = "The id does not match the bearer."
            else:
                line = "The id matches the bearer."
            return [
                ContentFragment(content="You verify the bearer's identity."),
                ContentFragment(content=line),
            ]
        if action == "request_search":
            if notes.get("outcome") == "search_found_concealment":
                items = notes.get("concealed") or []
                what = ", ".join(items) if items else "contraband"
                line = f"You uncover concealed {what}."
            else:
                line = "The search turns up nothing concealed."
            return [
                ContentFragment(content="You request a search."),
                ContentFragment(content=line),
            ]
        if action == "request_disclosure":
            if notes.get("outcome") == "disclosure_declared":
                items = notes.get("declared") or []
                what = ", ".join(items) if items else "something"
                line = f"The candidate hesitates, then sets out {what}."
            else:
                line = "The candidate has nothing to declare."
            return [
                ContentFragment(content="You ask whether there is anything to declare."),
                ContentFragment(content=line),
            ]
        if action == "request_relinquish":
            return [
                ContentFragment(content="You direct the candidate to surrender the contraband."),
                ContentFragment(content="They hand it over and step back, lighter."),
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
                        f"Shift complete: {game.correct_count} of {game._total_cases()} "
                        "calls correct."
                    )
                )
            )
        else:
            fragments.append(
                ContentFragment(content="The next traveler steps up to the counter.")
            )
        return fragments

    # ----- Bridge.1: structured (typed) fragment projection ----------------

    def _candidate_fragments(self, game: CredentialsGame) -> list[BaseFragment]:
        """Project the active candidate + packet zone + document pieces.

        Deterministic uids (per game + case index) let the client update these
        pieces in place across rounds rather than re-creating them each turn.
        """

        case = game.active_case
        idx = game.case_index
        packet_uid = _piece_uid(game.uid, idx, "packet")

        candidate = PieceFragment(
            uid=_piece_uid(game.uid, idx, "candidate"),
            piece_id=f"candidate-{idx}",
            kind="candidate",
            content=case.candidate_name,
            properties={
                "declared_purpose": case.get_purpose().value,
                "declared_region": case.get_region().value,
            },
            hints=PresentationHints(label_text=case.candidate_name),
        )

        doc_uids: list[uuid.UUID] = []
        doc_pieces: list[BaseFragment] = []
        for label, description in case.presented_documents.items():
            doc_uid = _piece_uid(game.uid, idx, f"doc:{label}")
            doc_uids.append(doc_uid)
            doc_pieces.append(
                PieceFragment(
                    uid=doc_uid,
                    piece_id=f"{idx}:{label}",
                    kind=_document_kind(label),
                    content=description,
                    zone_ref=packet_uid,
                    hints=PresentationHints(label_text=label),
                )
            )

        packet = GroupFragment(
            uid=packet_uid,
            group_type="zone",
            member_ids=doc_uids,
            zone_role="packet",
            hints=PresentationHints(label_text="Credentials packet"),
        )
        return [candidate, packet, *doc_pieces]

    def _findings_fragment(self, game: CredentialsGame) -> KvFragment | None:
        """Project revealed document/packet findings as a KvFragment.

        Discloses only what the player has already surfaced through inspection
        (no leaking of unrevealed truth). Document findings are flagged
        ``warn``; packet-level contradictions are ``danger``.
        """

        rows: list[KvRow] = []
        for target, finding in game.revealed_findings.items():
            rows.append(KvRow(key=target, value=finding, emphasis="warn"))
        for target, finding in game.packet_findings.items():
            rows.append(KvRow(key=target, value=finding, emphasis="danger"))
        if not rows:
            return None
        return KvFragment(content=rows)

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
