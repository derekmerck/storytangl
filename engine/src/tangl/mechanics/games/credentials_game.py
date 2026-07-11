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
from typing import TYPE_CHECKING, ClassVar, Protocol

from pydantic import Field, PrivateAttr

if TYPE_CHECKING:
    from .credentials_roster import ScenarioOffer

from tangl.core import BaseFragment
from tangl.core.bases import BaseModelPlus, Unstructurable
from tangl.journal.intent import PieceConstraints, PiecesAccepts, PickAccepts
from tangl.journal.fragments import (
    ContentFragment,
    GroupFragment,
    KvFragment,
    KvRow,
    PieceFragment,
    PresentationHints,
)
from tangl.mechanics.credentials.assembly import (
    CredentialPacketManager as AssemblyCredentialPacketManager,
    materialize_packet,
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
from .enums import GamePhase, GameResult, RoundResult
from .game import Game
from .picking_game import PickingGame, PickingGameHandler, PickingMove


# Fixed namespace so a candidate / packet / document gets a stable fragment uid
# across rounds: the client fragment registry then updates pieces in place
# rather than treating each round's re-emission as new. The game uid is folded
# into the seed so distinct credentials blocks in one journal (e.g. a scheduled
# and a randomized shift) never collide on a shared global fragment id.
_PIECE_NS = uuid.UUID("b7c3f6e2-1d4a-4c9b-9f2e-7a6d5c4b3a21")
_DOCUMENT_SELECTOR_TARGET = "__document_piece__"


def _piece_uid(game_uid: uuid.UUID, case_index: int, key: str) -> uuid.UUID:
    return uuid.uuid5(_PIECE_NS, f"credentials:{game_uid}:{case_index}:{key}")


def _document_piece_id(case_index: int, label: str) -> str:
    return f"{case_index}:{label}"


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


class CredentialPacketProtocol(Protocol):
    """Discovery surface used by disposition derivation.

    Why
    ---
    Disposition rules should depend on what a packet can answer, not on how a
    candidate case stores its fields.

    Key Features
    ------------
    - exposes declared region and purpose
    - exposes bearer-id status and credentials by indication
    - exposes contraband and all presented credentials for severity checks

    API
    ---
    Implement the methods below; callers should not inspect concrete storage.

    Notes
    -----
    This is the compatibility seam between the v1 ``CredentialCase`` shape and
    future credential-packet managers.

    See also
    --------
    ``CredentialPacketManager`` and ``derive_disposition``.
    """

    def get_region(self) -> Region: ...

    def get_purpose(self) -> Indication: ...

    def id_status(self) -> CredentialStatus | None: ...

    def credential_for(self, indication: Indication) -> CredentialToken | None: ...

    def get_contraband(self) -> list[ContrabandItem]: ...

    def all_credentials(self) -> list[CredentialToken]: ...


class CredentialPacketManager(BaseModelPlus):
    """A candidate's credential packet, separated from case presentation.

    Why
    ---
    Credentials need the same owner-bound manager vocabulary as outfits and
    vehicles, but the live game still carries flat packet fields on
    ``CredentialCase``.

    Key Features
    ------------
    - carries declared region, purpose, bearer id, credentials, and possessions
    - exposes the packet discovery API used by disposition derivation
    - stays value-object based; no graph-token migration is implied

    API
    ---
    Use ``get_region``, ``get_purpose``, ``id_status``, ``credential_for``,
    ``get_contraband``, and ``all_credentials``.

    Notes
    -----
    ``CredentialCase.to_packet_manager`` is the compatibility bridge for current
    game data.

    See also
    --------
    ``CredentialPacketProtocol`` and ``CredentialCase``.
    """

    region: Region = Region.LOCAL
    purpose: Indication = Indication.TRAVEL
    id_card: CredentialToken | None = None
    credentials: list[CredentialToken] = Field(default_factory=list)
    possessions: list[ContrabandItem] = Field(default_factory=list)

    def get_region(self) -> Region:
        return self.region

    def get_purpose(self) -> Indication:
        return self.purpose

    def id_status(self) -> CredentialStatus | None:
        """Status of the bearer id, or ``None`` if no id was presented."""

        return self.id_card.status if self.id_card is not None else None

    def credential_for(self, indication: Indication) -> CredentialToken | None:
        """The presented credential satisfying ``indication``, if any."""

        return next((c for c in self.credentials if c.indication is indication), None)

    def get_contraband(self) -> list[ContrabandItem]:
        return list(self.possessions)

    def all_credentials(self) -> list[CredentialToken]:
        if self.id_card is None:
            return list(self.credentials)
        return [self.id_card, *self.credentials]


class CredentialCase(Unstructurable):
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
    packet_manager: AssemblyCredentialPacketManager | None = Field(
        default=None,
        json_schema_extra={"include": True, "unstructurable": True},
    )

    # Authored override; None means "derive from the rules".
    correct_disposition: CredentialDisposition | None = None

    # --- Phase C seams (context overrides / haggling) -----------------------
    whitelist: bool = False
    blacklist: bool = False
    bribe_offer: int = 0

    # ----- Discovery API ----------------------------------------------------
    # The only surface the game loop and derive_disposition may use to ask the
    # packet about its content, declared intent, and validity.

    def bind_packet_manager_owner(self, owner: object) -> None:
        """Bind any owned assembly packet manager to its graph registry anchor."""

        if self.packet_manager is not None:
            self.packet_manager.bind_owner(owner)

    def materialize_packet_manager(self, owner: object) -> None:
        """Replace this factory-shaped packet with its graph-owned assembly form."""

        if self.packet_manager is not None:
            self.packet_manager.bind_owner(owner)
            return
        self.packet_manager = materialize_packet(
            owner=owner,
            region=self.region,
            purpose=self.purpose,
            id_card=self.id_card,
            credentials=self.packet,
            possessions=self.possessions,
            label_prefix=self.candidate_name,
        )
        self.id_card = None
        self.packet = []
        self.possessions = []

    def to_packet_manager(self) -> CredentialPacketProtocol:
        if self.packet_manager is not None:
            return self.packet_manager
        return CredentialPacketManager(
            region=self.region,
            purpose=self.purpose,
            id_card=self.id_card,
            credentials=list(self.packet),
            possessions=list(self.possessions),
        )

    def get_region(self) -> Region:
        if self.packet_manager is not None:
            return self.packet_manager.get_region()
        return self.region

    def get_purpose(self) -> Indication:
        if self.packet_manager is not None:
            return self.packet_manager.get_purpose()
        return self.purpose

    def id_status(self) -> CredentialStatus | None:
        """Status of the bearer id, or ``None`` if no id was presented."""

        id_card = self.id_credential()
        return id_card.status if id_card is not None else None

    def id_credential(self) -> CredentialToken | None:
        """Project the bearer id without exposing packet storage."""

        if self.packet_manager is not None:
            return self.packet_manager.id_credential()
        return self.id_card

    def credential_for(self, indication: Indication) -> CredentialToken | None:
        """The presented credential satisfying ``indication``, if any."""

        if self.packet_manager is not None:
            return self.packet_manager.credential_for(indication)
        return next((c for c in self.packet if c.indication is indication), None)

    def get_contraband(self) -> list[ContrabandItem]:
        if self.packet_manager is not None:
            return self.packet_manager.get_contraband()
        return list(self.possessions)

    def all_credentials(self) -> list[CredentialToken]:
        if self.packet_manager is not None:
            return self.packet_manager.all_credentials()
        if self.id_card is None:
            return list(self.packet)
        return [self.id_card, *self.packet]

    def document_credentials(self) -> list[CredentialToken]:
        """Project visible non-id documents without exposing packet storage."""

        if self.packet_manager is not None:
            return self.packet_manager.document_credentials()
        return list(self.packet)


class CredentialCaseResult(BaseModelPlus):
    """Auditable record of one dispositioned candidate."""

    candidate_name: str
    chosen_disposition: CredentialDisposition
    expected_disposition: CredentialDisposition
    correct: bool
    penalty: int = 0
    # True when the call was correct but unbacked by surfaced evidence and the
    # no_evidence_penalty toggle was on (the "justify your disposition" tax fired).
    unjustified: bool = False
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


# Graduated scoring: the cost of the chosen call given the correct one, over the
# ordered allow -> deny -> arrest axis. One step off costs 2; two steps off
# (allow <-> arrest) costs 5; correct costs 0. Arrest-when-wrong is always the
# heavy 5, so the heavy hammer is appropriately high-stakes and deny is the
# low-variance hedge for ambiguous calls. Penalties accumulate to a per-shift
# failure threshold (the Papers Please citation model).
# (The "+1 right-but-unjustified" evidence tax lands with the justification model
# in B.3, where behavioral evidence -- a declined search, a bribe attempt --
# also counts as justification.)
# String-keyed (disposition .value) so it is a plain JSON-serializable structure
# a world can override per rule set. The default is the standard rule-of-law
# matrix; a regime could supply, e.g., {"arrest": {"pass": 5, "deny": 5,
# "arrest": 0}} to make any non-arrest a hard failure.
DISPOSITION_PENALTY: dict[str, dict[str, int]] = {
    "pass": {"pass": 0, "deny": 2, "arrest": 5},
    "deny": {"pass": 2, "deny": 0, "arrest": 5},
    "arrest": {"pass": 5, "deny": 2, "arrest": 0},
}


def default_penalty_matrix() -> dict[str, dict[str, int]]:
    """A fresh copy of the standard penalty matrix (for per-game defaults)."""

    return {expected: dict(row) for expected, row in DISPOSITION_PENALTY.items()}


def disposition_penalty(
    expected: CredentialDisposition,
    chosen: CredentialDisposition,
    matrix: dict[str, dict[str, int]] | None = None,
) -> int:
    """Penalty for choosing ``chosen`` when ``expected`` was correct, under
    ``matrix`` (the standard matrix by default).

    A custom matrix may be *partial* -- a regime can override just the rows/cells
    that differ from the standard (e.g. only the ``"arrest"`` row) and any missing
    expected-row or chosen-cell falls back to the standard matrix.
    """

    m = matrix or DISPOSITION_PENALTY
    row = m.get(expected.value, DISPOSITION_PENALTY[expected.value])
    return row.get(chosen.value, DISPOSITION_PENALTY[expected.value][chosen.value])


class Finding:
    """finding_status *values* (Phase B mediation outcomes). Plain-string
    constants (not an Enum) so finding_status stays a JSON-serializable
    ``dict[str, str]`` for the VM value_hash and round-trips through persistence."""

    CLEARED = "cleared"      # a mitigatable problem was found and repaired
    VERIFIED = "verified"    # checked and sound -- no adverse evidence
    CONFIRMED = "confirmed"  # an adverse fact confirmed (crime / concealment)
    DECLARED = "declared"    # contraband voluntarily disclosed
    TOO_LATE = "too_late"    # disclosure after a confirming search; no rescue
    YIELDED = "yielded"      # contraband surrendered


class FindingKey:
    """finding_status *keys* with a fixed name (the others are an indication
    value -- a permit keyed by the good it covers)."""

    ID = "id"
    SEARCH = "search"
    DISCLOSURE = "disclosure"
    RELINQUISH = "relinquish"


class ContrabandClass:
    """How a contraband indication's restriction level is handled (B.2)."""

    CRIMINAL = "criminal"
    FORBIDDEN = "forbidden"
    CREDENTIALED = "credentialed"  # needs a valid permit and/or bearer id
    DECLARATION_ONLY = "declaration_only"


# finding_status values that represent *surfaced* evidence -- an investigation
# that turned a problem up (CONFIRMED), repaired a mitigatable one (CLEARED), or
# recovered contraband (YIELDED). A plain VERIFIED (checked, sound) is not adverse
# evidence, so it is excluded. Behavioral evidence (a declined search, a bribe
# attempt) extends this set in Phase B.3.
_EVIDENCE_FINDINGS = frozenset({Finding.CONFIRMED, Finding.CLEARED, Finding.YIELDED})


# Time cost of each action, in shift-budget units. Cheap probes (a glance at a
# document, a date/seal check) cost 1; verifying an id or requesting a reissue
# costs 2; a search is expensive at 3. Decisions cost too: passing or denying is
# quick, but an arrest takes longer (escort/paperwork) -- which also reinforces
# the penalty matrix's "don't reach for arrest idly". Costs are fixed defaults
# for now; the per-shift time_budget is the tuning knob.
_MOVE_TIME_COST: dict[str, int] = {
    "inspect": 1,
    "request_document": 2,
    "verify_id": 2,
    "request_search": 3,
    "request_disclosure": 1,
    "request_relinquish": 1,
}
_DECISION_TIME_COST: dict[CredentialDisposition, int] = {
    CredentialDisposition.PASS: 1,
    CredentialDisposition.DENY: 1,
    CredentialDisposition.ARREST: 3,
}


def move_time_cost(move: PickingMove) -> int:
    """Time cost of one move (see ``_MOVE_TIME_COST`` / ``_DECISION_TIME_COST``)."""

    if move.kind == "decide":
        return _DECISION_TIME_COST.get(CredentialDisposition(move.target), 1)
    return _MOVE_TIME_COST.get(move.kind, 1)


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
    if finding_status and finding_status.get(token.indication.value) == Finding.CLEARED:
        return CredentialDisposition.PASS
    return CredentialDisposition.DENY


def _assess_id(
    packet: CredentialPacketProtocol,
    finding_status: dict[str, str] | None = None,
) -> CredentialDisposition:
    status = packet.id_status()
    if status is None:
        return CredentialDisposition.DENY  # missing id -> produce it (mitigatable)
    if status.is_valid:
        return CredentialDisposition.PASS
    if status.is_crime:
        return CredentialDisposition.ARREST  # fake / wrong-holder id
    # Mitigatable id (expired / bad date): cleared by future id-mediation.
    if finding_status and finding_status.get(FindingKey.ID) == Finding.CLEARED:
        return CredentialDisposition.PASS
    return CredentialDisposition.DENY


def _assess_requirement(
    packet: CredentialPacketProtocol,
    indication: Indication,
    level: RestrictionLevel,
    finding_status: dict[str, str] | None = None,
) -> CredentialDisposition:
    """Assess one indication against its required level (the two error surfaces)."""

    worst = CredentialDisposition.PASS
    if level.requires_permit:
        permit = packet.credential_for(indication)
        worst = _worse(worst, _assess_credential(permit, finding_status))
        if permit is not None and not permit.holder_matches:
            worst = _worse(worst, CredentialDisposition.ARREST)  # permit/id mismatch
    if level.requires_id:
        worst = _worse(worst, _assess_id(packet, finding_status))
    return worst


def _contraband_class(level: RestrictionLevel) -> str:
    """Classify a contraband indication's rule (Phase B.2)."""

    if level is RestrictionLevel.CRIMINAL:
        return ContrabandClass.CRIMINAL  # per-se crime; possession arrests, no rescue
    if level is RestrictionLevel.FORBIDDEN:
        return ContrabandClass.FORBIDDEN
    if level.requires_permit or level.requires_id:
        # Needs a valid permit and/or bearer id: route through _assess_requirement
        # so the id is actually checked (a WITH_ID good is not merely declarable).
        return ContrabandClass.CREDENTIALED
    return ContrabandClass.DECLARATION_ONLY  # anonymous level: allowed once declared


def _assess_contraband(
    packet: CredentialPacketProtocol,
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
    if cls == ContrabandClass.CRIMINAL:
        # Per-se crime: mere possession is the offense. Declaring or surrendering
        # it does not rescue (you cannot relinquish your way out of trafficking).
        # A permissive regime that tolerates the good simply maps it below
        # CRIMINAL. (A privileged-origin whitelist exemption is a Phase C overlay
        # applied above derive_disposition, not here.)
        return CredentialDisposition.ARREST
    # disclosure declares all concealed goods; a bare un-concealed item is
    # already declared. The contraband's permit (when one is required) lives in
    # the packet keyed by indication, so its standing is assessed by
    # _assess_requirement -- the same machinery as a purpose permit.
    declared = (not item.concealed) or fs.get(FindingKey.DISCLOSURE) == Finding.DECLARED

    if declared:
        if fs.get(FindingKey.RELINQUISH) == Finding.YIELDED:
            return CredentialDisposition.PASS  # voluntarily surrendered
        if cls == ContrabandClass.FORBIDDEN:
            return CredentialDisposition.DENY  # declared forbidden -> relinquish/deny
        if cls == ContrabandClass.CREDENTIALED:
            return _assess_requirement(packet, item.indication, level, fs)
        return CredentialDisposition.PASS  # declaration-only, declared -> allow

    # Concealed and not disclosed: concealment is the violation.
    if cls == ContrabandClass.FORBIDDEN:
        return CredentialDisposition.ARREST  # smuggling forbidden goods
    if cls == ContrabandClass.DECLARATION_ONLY:
        return CredentialDisposition.DENY  # concealed declarable goods
    # credentialed (permit and/or id required), concealed:
    if _assess_requirement(packet, item.indication, level, fs) is CredentialDisposition.PASS:
        return CredentialDisposition.DENY  # had a valid credential but concealed it (Q1)
    return CredentialDisposition.ARREST  # smuggling un-credentialed goods


def derive_disposition(
    packet: CredentialPacketProtocol,
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

    region = packet.get_region()
    worst = CredentialDisposition.PASS

    purpose = packet.get_purpose()
    level = restrictions.level_for(region, purpose, RestrictionLevel.ANONYMOUS)
    if level is RestrictionLevel.CRIMINAL:
        # The stated purpose is itself a crime (RestrictionLevel is shared by
        # purpose and contraband rules) -- e.g. an authored {WORK: CRIMINAL} regime.
        worst = _worse(worst, CredentialDisposition.ARREST)
    elif level is RestrictionLevel.FORBIDDEN:
        worst = _worse(worst, CredentialDisposition.DENY)  # purpose not allowed
    else:
        worst = _worse(worst, _assess_requirement(packet, purpose, level, finding_status))

    for item in packet.get_contraband():
        level = restrictions.level_for(region, item.indication, RestrictionLevel.FORBIDDEN)
        worst = _worse(worst, _assess_contraband(packet, item, level, finding_status))

    # Presenting a forged / fake document is a crime in itself, regardless of
    # whether the document was required -- handing over a fake id unasked still
    # arrests. (A merely *invalid* document -- expired, unsealed -- with nothing
    # to back is moot, since its status is not a crime.)
    for token in packet.all_credentials():
        if token.status.is_crime:
            worst = _worse(worst, CredentialDisposition.ARREST)

    return worst


class CredentialsGame(PickingGame):
    """A checkpoint shift: a roster of candidates inspected one at a time."""

    # --- Shift configuration (authored; never reset between candidates) ------
    roster: list[CredentialCase] = Field(
        default_factory=_default_roster,
        json_schema_extra={"include": True, "unstructurable": True},
    )
    # Optional lazy roster: when set, candidates are sampled offers materialized
    # on arrival (Phase A.3), and `offers` is the source of truth instead of
    # `roster`. See credentials_roster.py.
    offers: list["ScenarioOffer"] = Field(
        default_factory=list,
        json_schema_extra={"include": True, "unstructurable": True},
    )
    allow_arrest: bool = True
    # The shift is lost when accumulated penalty exceeds this. 0 is the strict
    # default (any wrong call ends the shift); a world raises it for a more
    # forgiving day. Penalty = decision penalties + overtime.
    penalty_threshold: int = 0
    # Scoring is per rule set. The penalty matrix (keyed by disposition value)
    # is overridable so a regime can score differently -- e.g. "arrest everyone,
    # any non-arrest fails". no_evidence_penalty is the toggle for the "justify
    # your disposition" tax: when > 0, a *correct* deny/arrest that is not backed
    # by a revealed finding costs that much (off by default; a decree regime that
    # needs no evidence leaves it at 0).
    penalty_matrix: dict[str, dict[str, int]] = Field(
        default_factory=default_penalty_matrix
    )
    no_evidence_penalty: int = 0
    # Soft attention/time budget. None disables time pressure (the default).
    # When set, every probe and decision costs time (see _MOVE_TIME_COST); time
    # spent over the budget converts to penalty at overtime_penalty_rate. Going
    # thorough costs time; going fast risks wrong calls.
    time_budget: int | None = None
    overtime_penalty_rate: int = 1
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
    # Shift-level time spent on probes and decisions (not per-case; reset only on
    # setup). Compared against time_budget for the overtime penalty.
    time_spent: int = Field(
        default=0,
        json_schema_extra={"reset_field": True},
    )
    # Mediation outcomes for the active case (Phase B.1): keys are an
    # indication's value (a permit) or a fixed ``FindingKey`` (id / search /
    # disclosure / relinquish); values are ``Finding`` constants. Kept as plain
    # ``dict[str, str]`` so it stays JSON-serializable for the VM value_hash.
    # Reset by advance_case so each candidate starts with a clean slate.
    finding_status: dict[str, str] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )
    # Lazy cache of materialized offers (cleared on setup; rebuilt on arrival).
    materialized: list[CredentialCase] = Field(
        default_factory=list,
        json_schema_extra={
            "include": True,
            "reset_field": True,
            "unstructurable": True,
        },
    )
    _component_manager_owner: object | None = PrivateAttr(default=None)

    def bind_component_managers(self, owner: object) -> None:
        """Bind assembly packet managers in already materialized cases to ``owner``."""

        self._component_manager_owner = owner
        for case in self.roster:
            case.bind_packet_manager_owner(owner)
        for case in self.materialized:
            case.materialize_packet_manager(owner)
        for offer in self.offers:
            if offer.pinned_case is not None:
                offer.pinned_case.bind_packet_manager_owner(owner)

    @property
    def has_component_manager_owner(self) -> bool:
        """Whether sampled cases can materialize into graph credential components."""

        return self._component_manager_owner is not None

    def prepare_active_case(self) -> CredentialCase:
        """Materialize the arriving sampled case at setup or UPDATE time."""

        if not self.offers:
            return self.roster[self.case_index]
        from .credentials_roster import materialize

        while len(self.materialized) <= self.case_index:
            offer = self.offers[len(self.materialized)]
            self.materialized.append(materialize(offer, self.restriction_map))
        case = self.materialized[self.case_index]
        if self.has_component_manager_owner:
            case.materialize_packet_manager(self._component_manager_owner)
        return case

    # ----- active case access ----------------------------------------------
    def _total_cases(self) -> int:
        """Number of candidates this shift: sampled offers if any, else roster."""

        return len(self.offers) if self.offers else len(self.roster)

    @property
    def active_case(self) -> CredentialCase:
        if not self.offers:
            return self.roster[self.case_index]
        if len(self.materialized) <= self.case_index:
            if (
                self.has_component_manager_owner
                and self.phase is GamePhase.READY
            ):
                raise RuntimeError("Sampled credential cases must be prepared before PLANNING")
            return self.prepare_active_case()
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
    def decision_penalty(self) -> int:
        """Accumulated per-case decision penalty across the shift so far."""

        return sum(result.penalty for result in self.case_results)

    @property
    def overtime(self) -> int:
        """Time spent over the budget (0 when no budget is set)."""

        if self.time_budget is None:
            return 0
        return max(0, self.time_spent - self.time_budget)

    @property
    def overtime_penalty(self) -> int:
        return self.overtime * self.overtime_penalty_rate

    @property
    def total_penalty(self) -> int:
        """Decision penalties plus the overtime penalty, against which the
        shift's failure threshold is judged."""

        return self.decision_penalty + self.overtime_penalty

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

        Never touches roster, rules, threshold, score, or
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
        if self.has_component_manager_owner and not self.shift_complete:
            self.prepare_active_case()

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
                "credential_total_penalty": self.total_penalty,
                "credential_decision_penalty": self.decision_penalty,
                "credential_penalty_threshold": self.penalty_threshold,
                "credential_no_evidence_penalty": self.no_evidence_penalty,
                "credential_time_budget": self.time_budget,
                "credential_time_spent": self.time_spent,
                "credential_overtime": self.overtime,
                "credential_shift_complete": self.shift_complete,
            }
        )
        return namespace


class CredentialsGameHandler(PickingGameHandler[CredentialsGame]):
    """Handler for an inspect-and-dispose checkpoint shift."""

    game_cls: ClassVar[type[Game]] = CredentialsGame

    def on_setup(self, game: CredentialsGame) -> None:
        """Prepare the first sampled packet before move provisioning begins."""

        if game.has_component_manager_owner and game.offers:
            game.prepare_active_case()

    def resolve_round(self, game, player_move, opponent_move):
        # Charge the move's time cost to the shift budget before resolving it.
        # Soft budget: actions are never blocked; overtime converts to penalty.
        game.time_spent += move_time_cost(self._normalize_move(player_move))
        return super().resolve_round(game, player_move, opponent_move)

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
        for token in case.document_credentials():
            key = token.indication.value
            if key in game.finding_status:
                continue
            moves.append(CredentialsMove(kind="request_document", target=key))
        # verify_id: offer whenever an id is presented and not yet verified.
        if case.id_status() is not None and FindingKey.ID not in game.finding_status:
            moves.append(CredentialsMove(kind="verify_id", target=""))
        # request_search: single move, once per case.
        if FindingKey.SEARCH not in game.finding_status:
            moves.append(CredentialsMove(kind="request_search", target=""))
        # request_disclosure (B.2): "anything to declare?" -- always offerable
        # (asking reveals nothing the menu shouldn't), once per case.
        if FindingKey.DISCLOSURE not in game.finding_status:
            moves.append(CredentialsMove(kind="request_disclosure", target=""))
        # request_relinquish (B.2): offer when the candidate has *declared*
        # contraband to surrender (visible, or disclosed via request_disclosure).
        if FindingKey.RELINQUISH not in game.finding_status and self._has_declared_contraband(game):
            moves.append(CredentialsMove(kind="request_relinquish", target=""))
        return moves

    def get_provisioned_moves(self, game: CredentialsGame) -> list[CredentialsMove]:
        moves = list(self.get_available_moves(game))
        document_moves = [
            move
            for move in moves
            if move.kind == "inspect" and move.target in game.presented_documents
        ]
        moves = [
            move
            for move in moves
            if move.kind != "inspect" or move.target not in game.presented_documents
        ]
        if document_moves:
            moves.insert(
                0,
                CredentialsMove(kind="inspect", target=_DOCUMENT_SELECTOR_TARGET),
            )
        return moves

    @staticmethod
    def _has_declared_contraband(game: CredentialsGame) -> bool:
        disclosed = game.finding_status.get(FindingKey.DISCLOSURE) == Finding.DECLARED
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
            if move.target == _DOCUMENT_SELECTOR_TARGET:
                return "Inspect a document"
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

    def get_move_accepts(
        self,
        game: CredentialsGame,
        move: CredentialsMove,
    ) -> PiecesAccepts | PickAccepts:
        if move.kind == "inspect" and move.target == _DOCUMENT_SELECTOR_TARGET:
            return PiecesAccepts(
                constraints=PieceConstraints(
                    target_zone_ref=str(
                        _piece_uid(game.uid, game.case_index, "packet"),
                    ),
                ),
            )
        return PickAccepts()

    def resolve_move_payload(
        self,
        game: CredentialsGame,
        move: CredentialsMove,
        payload: dict[str, object],
    ) -> CredentialsMove:
        move = self._normalize_move(move)
        if move.kind != "inspect" or move.target != _DOCUMENT_SELECTOR_TARGET:
            return move

        piece_ids = payload.get("piece_ids")
        if not isinstance(piece_ids, list) or len(piece_ids) != 1:
            raise ValueError("Inspect a document requires exactly one piece_id")

        selected_piece_id = piece_ids[0]
        if not isinstance(selected_piece_id, str):
            raise ValueError("Document piece_id must be a string")
        target_by_piece_id = {
            _document_piece_id(game.case_index, target): target
            for target in self.get_available_inspect_targets(game)
            if target in game.presented_documents
        }
        target = target_by_piece_id.get(selected_piece_id)
        if target is None:
            raise ValueError(f"Document piece is not inspectable: {selected_piece_id}")
        return CredentialsMove(kind="inspect", target=target)

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

    def _rejection_is_justified(self, game: CredentialsGame) -> bool:
        """Whether a deny/arrest on the active case is backed by evidence -- either
        surfaced by the player's investigation or self-evidently visible. Backs the
        no_evidence_penalty toggle (only an *unjustified* correct rejection is
        taxed), and errs toward "justified" so the tax never punishes a fair call.
        """

        return self._has_surfaced_evidence(game) or self._has_visible_grounds(game)

    def _has_surfaced_evidence(self, game: CredentialsGame) -> bool:
        """Adverse evidence the player turned up: a revealed document/packet
        finding, an adverse finding_status, or a logged declaration of contraband
        actually present.
        """

        if game.revealed_findings or game.packet_findings:
            return True
        fs = game.finding_status
        for key, value in fs.items():
            if value not in _EVIDENCE_FINDINGS:
                continue
            # A *clean* search (SEARCH: CLEARED) turned nothing up -- it is not
            # adverse evidence and must not suppress the tax on an unrelated
            # unsurfaced issue.
            if key == FindingKey.SEARCH and value == Finding.CLEARED:
                continue
            return True
        # A logged disclosure counts only when there was something to declare.
        if (
            fs.get(FindingKey.DISCLOSURE) in (Finding.DECLARED, Finding.TOO_LATE)
            and game.active_case.get_contraband()
        ):
            return True
        return False

    def _has_visible_grounds(self, game: CredentialsGame) -> bool:
        """Self-evident grounds for a rejection -- facts visible without any
        investigation: a credential the purpose plainly requires but the packet
        does not hold, or openly (non-concealed) contraband that is forbidden or
        plainly missing its permit. A concealed item is *not* self-evident, and a
        declared declaration-only item is allowed (not grounds), so neither counts.
        """

        case = game.active_case
        rules = game.restriction_map
        region = case.get_region()

        purpose = case.get_purpose()
        plevel = rules.level_for(region, purpose, RestrictionLevel.ANONYMOUS)
        if plevel in (RestrictionLevel.CRIMINAL, RestrictionLevel.FORBIDDEN):
            return True  # the stated purpose is itself criminal/disallowed -- self-evident
        if plevel.requires_id and case.id_status() is None:
            return True
        if plevel.requires_permit and case.credential_for(purpose) is None:
            return True

        for item in case.get_contraband():
            if item.concealed:
                continue  # a hidden item's grounds are not self-evident
            clevel = rules.level_for(region, item.indication, RestrictionLevel.FORBIDDEN)
            if clevel in (RestrictionLevel.CRIMINAL, RestrictionLevel.FORBIDDEN):
                return True  # openly criminal / forbidden goods
            if clevel.requires_permit and case.credential_for(item.indication) is None:
                return True  # visible item, plainly missing its permit
        return False

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
        # Scoring is per rule set: the penalty matrix is the game's, not a global.
        penalty = disposition_penalty(expected, chosen, game.penalty_matrix)

        # The "justify your disposition" tax (opt-in, off by default): a *correct*
        # rejection that is backed by neither surfaced nor self-evident evidence
        # still costs no_evidence_penalty. Keyed off ``correct`` (not penalty == 0)
        # so a custom matrix that tolerates a non-expected call at zero cost is not
        # mistaken for a correct one. A decree regime that needs no evidence leaves
        # the toggle at 0; a rule-of-law regime sets it to make profiling cost.
        unjustified = (
            correct
            and game.no_evidence_penalty > 0
            and chosen in (CredentialDisposition.DENY, CredentialDisposition.ARREST)
            and not self._rejection_is_justified(game)
        )
        if unjustified:
            penalty += game.no_evidence_penalty

        game.case_results.append(
            CredentialCaseResult(
                candidate_name=case.candidate_name,
                chosen_disposition=chosen,
                expected_disposition=expected,
                correct=correct,
                penalty=penalty,
                unjustified=unjustified,
                discovered_findings=dict(game.revealed_findings),
                packet_findings=dict(game.packet_findings),
            )
        )

        detail["candidate"] = case.candidate_name
        detail["credential_stage"] = game.current_stage
        detail["penalty"] = penalty
        if unjustified:
            detail["unjustified"] = True
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
        permit = game.active_case.credential_for(Indication(indication_value))
        if permit is None:  # off-menu safety; receive_move does not validate
            detail["outcome"] = "request_document_not_applicable"
            detail["target_indication"] = indication_value
            return RoundResult.CONTINUE

        if permit.status.is_crime:
            game.finding_status[indication_value] = Finding.CONFIRMED
            detail["outcome"] = "request_document_confirmed"
        elif permit.status.is_valid:
            game.finding_status[indication_value] = Finding.VERIFIED
            detail["outcome"] = "request_document_verified"
        else:
            game.finding_status[indication_value] = Finding.CLEARED
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
        # (B.2). So it records VERIFIED / CONFIRMED, never CLEARED.
        status = game.active_case.id_status()
        if status is None:  # off-menu safety; the menu offers this only with an id
            detail["outcome"] = "id_verified_not_applicable"
            return RoundResult.CONTINUE
        if status is CredentialStatus.WRONG_HOLDER:
            game.finding_status[FindingKey.ID] = Finding.CONFIRMED
            detail["outcome"] = "id_verified_problem"
        else:
            game.finding_status[FindingKey.ID] = Finding.VERIFIED
            detail["outcome"] = "id_verified_clean"
        return RoundResult.CONTINUE

    def _resolve_request_search(
        self,
        game: CredentialsGame,
        detail: dict[str, object],
    ) -> RoundResult:
        concealed = [item for item in game.active_case.get_contraband() if item.concealed]
        if concealed:
            game.finding_status[FindingKey.SEARCH] = Finding.CONFIRMED
            detail["outcome"] = "search_found_concealment"
            detail["concealed"] = [item.indication.value for item in concealed]
        else:
            game.finding_status[FindingKey.SEARCH] = Finding.CLEARED
            detail["outcome"] = "search_clean"
        return RoundResult.CONTINUE

    def _resolve_request_disclosure(
        self,
        game: CredentialsGame,
        detail: dict[str, object],
    ) -> RoundResult:
        # "Anything to declare?" -- a compliant candidate (B.2 assumes compliance;
        # lying is B.3) declares any concealed contraband. *Voluntary* disclosure
        # rescues concealed-but-permitted goods to the declared assessment (the
        # "oops" path). But search forecloses: once a search has already
        # confirmed concealment, a later disclosure is too late to rescue -- it
        # records "too_late" (which derive does not treat as declared) rather
        # than "declared".
        concealed = [item for item in game.active_case.get_contraband() if item.concealed]
        if concealed and game.finding_status.get(FindingKey.SEARCH) == Finding.CONFIRMED:
            game.finding_status[FindingKey.DISCLOSURE] = Finding.TOO_LATE
            detail["outcome"] = "disclosure_too_late"
            detail["declared"] = [item.indication.value for item in concealed]
        else:
            game.finding_status[FindingKey.DISCLOSURE] = Finding.DECLARED
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
        # Off-menu safety: with nothing declared to surrender, record nothing --
        # else a spurious YIELDED would count as surfaced evidence and suppress
        # the no_evidence_penalty on an unrelated rejection.
        if not self._has_declared_contraband(game):
            detail["outcome"] = "request_relinquish_not_applicable"
            return RoundResult.CONTINUE
        game.finding_status[FindingKey.RELINQUISH] = Finding.YIELDED
        detail["outcome"] = "relinquished"
        return RoundResult.CONTINUE

    # ----- lifecycle / projection ------------------------------------------

    def evaluate(self, game: CredentialsGame) -> GameResult:
        """Own shift terminality: in process until the final candidate is decided,
        then win if accumulated penalty stayed within the threshold."""

        if not game.shift_complete:
            return GameResult.IN_PROCESS
        if game.total_penalty <= game.penalty_threshold:
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
            return [] if game.shift_complete else self._candidate_fragments(game)

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
            elif outcome == "id_verified_not_applicable":
                line = "There is no id to verify."
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
            outcome = notes.get("outcome")
            items = notes.get("declared") or []
            what = ", ".join(items) if items else "something"
            if outcome == "disclosure_declared":
                line = f"The candidate hesitates, then sets out {what}."
            elif outcome == "disclosure_too_late":
                line = f"Too late -- the {what} you already turned up is on the counter between you."
            else:
                line = "The candidate has nothing to declare."
            return [
                ContentFragment(content="You ask whether there is anything to declare."),
                ContentFragment(content=line),
            ]
        if action == "request_relinquish":
            if notes.get("outcome") == "request_relinquish_not_applicable":
                return [
                    ContentFragment(
                        content="You look for contraband to have surrendered, but there is none."
                    ),
                ]
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
            piece_kind="candidate",
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
                    piece_id=_document_piece_id(idx, label),
                    piece_kind=_document_kind(label),
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
