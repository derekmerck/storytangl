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
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, ClassVar, Literal, Self

from pydantic import Field, PrivateAttr, model_validator

if TYPE_CHECKING:
    from .credentials_roster import ScenarioOffer

from tangl.core import BaseFragment, TokenCatalog
from tangl.core.bases import BaseModelPlus, Unstructurable
from tangl.journal.intent import PieceConstraints, PiecesAccepts, PickAccepts
from tangl.journal.fragments import (
    ContentFragment,
    GroupFragment,
    KvFragment,
    KvRow,
    MediaFragment,
    PieceFragment,
    PresentationHints,
)
from tangl.media.media_creators.composition_forge.composition_inputs import (
    CompositionInputUnavailable,
    resolve_composition_inputs,
)
from tangl.media.media_creators.composition_forge.composition_spec import CompositionSpec
from tangl.media.media_creators.media_spec import MediaSpec
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.mechanics.credentials.assembly import (
    CREDENTIAL_ID_SLOT,
    CREDENTIAL_PACKET_SLOT,
    CREDENTIAL_UNPRESENTED_SLOT,
    CredentialComponent,
    CredentialDefinition,
    CredentialPacketManager as AssemblyCredentialPacketManager,
    default_credential_catalog,
    materialize_packet,
)
from tangl.mechanics.credentials import (
    DEFAULT_RESTRICTIONS,
    ContrabandItem,
    CredentialAttestationObservation,
    CredentialCardProjection,
    CredentialDefect,
    CredentialDefectKind,
    CredentialStatus,
    CredentialToken,
    CredentialValidityObservation,
    CredentialVisibleObservation,
    FailureClass,
    IndicationId,
    OriginId,
    Indication,
    Region,
    Restrictions,
    RestrictionLevel,
    credential_card_composition_spec,
    credential_card_portrait_spec,
    credential_card_text_spec,
)
from tangl.mechanics.transaction import (
    AssetMoveCommitment,
    ComponentSlotAssetHolder,
    TransactionOffer,
)
from tangl.prose import TextRenderSession
from tangl.story.presentation import render_text_as
from tangl.vm.ctx import VmPhaseCtx
from tangl.vm.provision.resolver import Resolver
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


def _card_media_dep_uid(
    game_uid: uuid.UUID,
    case_index: int,
    component_id: uuid.UUID,
    role: str,
) -> uuid.UUID:
    """Return the stable dependency ID for one credential-card media role."""
    return _piece_uid(game_uid, case_index, f"card-dependency:{component_id}:{role}")


def _document_piece_id(case_index: int, label: str) -> str:
    return f"{case_index}:{label}"


def _component_piece_id(case_index: int, component_id: uuid.UUID) -> str:
    return f"{case_index}:component:{component_id}"


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


@dataclass(frozen=True)
class _CredentialDocumentRender:
    """Local render input for one canonical credential component."""

    component: CredentialComponent
    label: str
    base_description: str
    complete_replacement: str | None
    visible_observations: tuple[CredentialVisibleObservation, ...]


class CredentialDisposition(Enum):
    """Terminal disposition for a single candidate."""

    PASS = "pass"
    DENY = "deny"
    ARREST = "arrest"


CredentialsMove = PickingMove


class CredentialCase(Unstructurable):
    """One candidate, with its credential truth in a required packet manager.

    The narrative strings (``presented_documents`` / ``hidden_facts`` /
    ``packet_hidden_facts``) drive the v1 inspect loop. The *structured truth*
    (region, purpose, id card, documents, and possessions) lives in the required
    ``packet_manager``; :func:`derive_disposition` reads it through that
    owner-bound manager, never from the case directly.

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

    # --- Structured truth -----------------------------------------------------
    packet_manager: AssemblyCredentialPacketManager = Field(
        json_schema_extra={"include": True, "unstructurable": True},
    )
    prior_case_results: list["CredentialCaseResult"] = Field(
        default_factory=list,
        json_schema_extra={"include": True},
    )

    # Authored override; None means "derive from the rules".
    correct_disposition: CredentialDisposition | None = None

    # --- Phase C seams (context overrides / haggling) -----------------------
    whitelist: bool = False
    blacklist: bool = False
    bribe_offer: int = 0
    id_request_response: Literal["comply", "refuse"] = "comply"

    # ----- Discovery API ----------------------------------------------------
    # The only surface the game loop and derive_disposition may use to ask the
    # packet about its content, declared intent, and validity.

    def bind_packet_manager_owner(self, owner: object) -> None:
        """Bind the owned assembly packet manager to its graph registry anchor."""

        self.packet_manager.bind_owner(owner)

    def get_region(self) -> OriginId:
        return self.packet_manager.get_region()

    def get_purpose(self) -> IndicationId:
        return self.packet_manager.get_purpose()

    def id_status(self) -> CredentialStatus | None:
        """Status of the bearer id, or ``None`` if no id was presented."""

        id_card = self.id_credential()
        return id_card.status if id_card is not None else None

    def id_credential(self) -> CredentialToken | None:
        """Project the bearer id without exposing packet storage."""

        return self.packet_manager.id_credential()

    def credential_for(self, indication: IndicationId) -> CredentialToken | None:
        """The presented credential satisfying ``indication``, if any."""

        return self.packet_manager.credential_for(indication)

    def get_contraband(self) -> list[ContrabandItem]:
        return self.packet_manager.get_contraband()

    def all_credentials(self) -> list[CredentialToken]:
        return self.packet_manager.all_credentials()

    def document_credentials(self) -> list[CredentialToken]:
        """Project visible non-id documents without exposing packet storage."""

        return self.packet_manager.document_credentials()


class CredentialCaseResult(BaseModelPlus):
    """Auditable record of one dispositioned candidate."""

    case_index: int
    bearer_id: uuid.UUID
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


CredentialCase.model_rebuild(_types_namespace={"CredentialCaseResult": CredentialCaseResult})


def _default_roster() -> list[CredentialCase]:
    """A two-candidate shift so a bare game is playable and demonstrable."""

    return [
        CredentialCase(
            presented_documents={
                "passport": "A worn passport with a blurred seal.",
                "travel permit": "A permit stamped for this week.",
            },
            packet_manager=materialize_packet(
                owner=object(),
                region=Region.LOCAL,
                purpose=Indication.TRAVEL,
                id_card=CredentialToken(
                    indication=Indication.TRAVEL,
                    status=CredentialStatus.MISSING_SEAL,
                ),
                credentials=[CredentialToken(indication=Indication.TRAVEL)],
                possessions=[],
                label_prefix="Traveler",
            ),
            correct_disposition=CredentialDisposition.DENY,
        ),
        CredentialCase(
            candidate_name="Tomas Vey",
            presented_documents={
                "passport": "A crisp passport, its seal sharp and current.",
                "travel permit": "A permit stamped for this very week.",
            },
            hidden_facts={},
            packet_hidden_facts={},
            packet_manager=materialize_packet(
                owner=object(),
                region=Region.LOCAL,
                purpose=Indication.TRAVEL,
                id_card=CredentialToken(indication=Indication.TRAVEL),
                credentials=[CredentialToken(indication=Indication.TRAVEL)],
                possessions=[],
                label_prefix="Tomas Vey",
            ),
            correct_disposition=CredentialDisposition.PASS,
        ),
    ]


# --- Disposition derivation (reads cases only via the discovery API) --------

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
    REFUSED = "refused"      # candidate declined a requested response


class FindingKey:
    """finding_status *keys* with a fixed name (the others are an indication
    value -- a permit keyed by the good it covers)."""

    ID = "id"
    SEARCH = "search"
    DISCLOSURE = "disclosure"
    RELINQUISH = "relinquish"


# finding_status values that represent *surfaced* evidence -- an investigation
# that turned a problem up (CONFIRMED), repaired a mitigatable one (CLEARED), or
# recovered contraband (YIELDED). A plain VERIFIED (checked, sound) is not adverse
# evidence, so it is excluded. Behavioral evidence (a declined search, a bribe
# attempt) extends this set in Phase B.3.
_EVIDENCE_FINDINGS = frozenset(
    {Finding.CONFIRMED, Finding.CLEARED, Finding.YIELDED, Finding.REFUSED}
)


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


def _id_component(packet: AssemblyCredentialPacketManager) -> CredentialComponent | None:
    components = packet.get_slot(CREDENTIAL_ID_SLOT)
    return components[0] if components else None


def _permit_component(
    packet: AssemblyCredentialPacketManager,
    indication: IndicationId,
) -> CredentialComponent | None:
    return next(
        (
            component
            for component in packet.get_slot(CREDENTIAL_PACKET_SLOT)
            if component.indication == indication
        ),
        None,
    )


def _document_defect(
    component: CredentialComponent,
    *,
    subject: Literal["identity", "authorization"],
    indication: IndicationId,
    expected_subject_id: uuid.UUID | None,
    cleared: bool,
    invalid_kind: CredentialDefectKind,
    invalid_subject: Literal["identity", "authorization", "possession"],
) -> CredentialDefect | None:
    """Classify a supplied document once; missing documents are caller-owned."""

    if component.status is CredentialStatus.FORGED:
        return CredentialDefect(
            kind=CredentialDefectKind.FRAUDULENT_EVIDENCE,
            failure_class=FailureClass.CRIME,
            subject=subject,
            indication=indication,
            source_id=component.uid,
            cause=component.status,
        )
    if expected_subject_id is not None and component.subject_id != expected_subject_id:
        return CredentialDefect(
            kind=CredentialDefectKind.SUBJECT_MISMATCH,
            failure_class=FailureClass.CRIME,
            subject=subject,
            indication=indication,
            source_id=component.uid,
        )
    if component.status.is_valid or cleared:
        return None
    return CredentialDefect(
        kind=invalid_kind,
        failure_class=FailureClass.MITIGATABLE,
        subject=invalid_subject,
        indication=indication,
        source_id=component.uid,
        cause=component.status,
    )


def _requirement_defects(
    packet: AssemblyCredentialPacketManager,
    indication: IndicationId,
    level: RestrictionLevel,
    finding_status: dict[str, str],
    *,
    missing_kind: CredentialDefectKind = CredentialDefectKind.MISSING_EVIDENCE,
    invalid_kind: CredentialDefectKind = CredentialDefectKind.INVALID_EVIDENCE,
    missing_subject: Literal["identity", "authorization", "possession"] | None = None,
) -> list[CredentialDefect]:
    """Derive defects for one authorization requirement without choosing a result."""

    defects: list[CredentialDefect] = []
    id_card = _id_component(packet)
    if level.requires_permit:
        permit = _permit_component(packet, indication)
        if permit is None:
            defects.append(
                CredentialDefect(
                    kind=missing_kind,
                    failure_class=FailureClass.MITIGATABLE,
                    subject=missing_subject or "authorization",
                    indication=indication,
                )
            )
        else:
            defect = _document_defect(
                permit,
                subject="authorization",
                indication=indication,
                expected_subject_id=(id_card.subject_id if id_card is not None else None),
                cleared=finding_status.get(indication) == Finding.CLEARED,
                invalid_kind=invalid_kind,
                invalid_subject=missing_subject or "authorization",
            )
            if defect is not None:
                defects.append(defect)
    if level.requires_id:
        if id_card is None:
            defects.append(
                CredentialDefect(
                    kind=missing_kind,
                    failure_class=FailureClass.MITIGATABLE,
                    subject=missing_subject or "identity",
                    indication=indication,
                )
            )
        else:
            defect = _document_defect(
                id_card,
                subject="identity",
                indication=indication,
                expected_subject_id=packet.bearer_id,
                cleared=finding_status.get(FindingKey.ID) == Finding.CLEARED,
                invalid_kind=invalid_kind,
                invalid_subject=missing_subject or "identity",
            )
            if defect is not None:
                defects.append(defect)
    return defects


def _append_once(defects: list[CredentialDefect], defect: CredentialDefect) -> None:
    """Keep one observation per semantic source and kind."""

    if not any(
        existing.kind is defect.kind
        and existing.source_id == defect.source_id
        and existing.indication == defect.indication
        for existing in defects
    ):
        defects.append(defect)


def derive_defects(
    packet: AssemblyCredentialPacketManager,
    restrictions: Restrictions,
    finding_status: dict[str, str] | None = None,
) -> list[CredentialDefect]:
    """Return the mediated semantic defects in ``packet`` under ``restrictions``.

    The returned observations are transient assessment output. ``finding_status``
    changes only remediable observations; it never becomes a credential defect or
    substitutes discovered evidence for the packet's own state.
    """

    finding_status = finding_status or {}
    defects: list[CredentialDefect] = []
    region = packet.get_region()
    purpose = packet.get_purpose()
    purpose_level = restrictions.level_for(region, purpose, RestrictionLevel.ANONYMOUS)

    if purpose_level is RestrictionLevel.CRIMINAL:
        defects.append(
            CredentialDefect(
                kind=CredentialDefectKind.CRIMINAL_INTENT,
                failure_class=FailureClass.CRIME,
                subject="intent",
                indication=purpose,
            )
        )
    elif purpose_level is RestrictionLevel.FORBIDDEN:
        defects.append(
            CredentialDefect(
                kind=CredentialDefectKind.PROHIBITED_INTENT,
                failure_class=FailureClass.MITIGATABLE,
                subject="intent",
                indication=purpose,
            )
        )
    else:
        defects.extend(
            _requirement_defects(packet, purpose, purpose_level, finding_status)
        )

    for item in packet.get_contraband():
        level = restrictions.level_for(region, item.indication, RestrictionLevel.FORBIDDEN)
        if level is RestrictionLevel.CRIMINAL:
            defects.append(
                CredentialDefect(
                    kind=CredentialDefectKind.CRIMINAL_POSSESSION,
                    failure_class=FailureClass.CRIME,
                    subject="possession",
                    indication=item.indication,
                )
            )
            continue

        declared = (
            not item.concealed
            or finding_status.get(FindingKey.DISCLOSURE) == Finding.DECLARED
        )
        if declared and finding_status.get(FindingKey.RELINQUISH) == Finding.YIELDED:
            continue
        if level is RestrictionLevel.FORBIDDEN:
            defects.append(
                CredentialDefect(
                    kind=(
                        CredentialDefectKind.UNAUTHORIZED_POSSESSION
                        if declared
                        else CredentialDefectKind.UNDECLARED_POSSESSION
                    ),
                    failure_class=(
                        FailureClass.MITIGATABLE if declared else FailureClass.CRIME
                    ),
                    subject="possession",
                    indication=item.indication,
                )
            )
            continue
        if not level.requires_permit and not level.requires_id:
            if not declared:
                defects.append(
                    CredentialDefect(
                        kind=CredentialDefectKind.UNDECLARED_POSSESSION,
                        failure_class=FailureClass.MITIGATABLE,
                        subject="possession",
                        indication=item.indication,
                    )
                )
            continue

        requirement_defects = _requirement_defects(
            packet,
            item.indication,
            level,
            finding_status,
            missing_kind=CredentialDefectKind.UNAUTHORIZED_POSSESSION,
            invalid_kind=CredentialDefectKind.UNAUTHORIZED_POSSESSION,
            missing_subject="possession",
        )
        if declared:
            defects.extend(requirement_defects)
            continue
        for defect in requirement_defects:
            if defect.failure_class is FailureClass.CRIME:
                _append_once(defects, defect)
        defects.append(
            CredentialDefect(
                kind=CredentialDefectKind.UNDECLARED_POSSESSION,
                failure_class=(
                    FailureClass.CRIME if requirement_defects else FailureClass.MITIGATABLE
                ),
                subject="possession",
                indication=item.indication,
            )
        )

    # A forged document is criminal even when the day's rules did not require it.
    for component, subject in [
        *[(component, "identity") for component in packet.get_slot(CREDENTIAL_ID_SLOT)],
        *[
            (component, "authorization")
            for component in packet.get_slot(CREDENTIAL_PACKET_SLOT)
        ],
    ]:
        if component.status is CredentialStatus.FORGED:
            defect = _document_defect(
                component,
                subject=subject,
                indication=component.indication,
                expected_subject_id=None,
                cleared=False,
                invalid_kind=CredentialDefectKind.INVALID_EVIDENCE,
                invalid_subject=subject,
            )
            if defect is not None:
                _append_once(defects, defect)

    return defects


def derive_disposition(
    packet: AssemblyCredentialPacketManager,
    restrictions: Restrictions,
    finding_status: dict[str, str] | None = None,
) -> CredentialDisposition:
    """Fold structured defects into the three available checkpoint outcomes."""

    defects = derive_defects(packet, restrictions, finding_status)
    if any(defect.failure_class is FailureClass.CRIME for defect in defects):
        return CredentialDisposition.ARREST
    return CredentialDisposition.DENY if defects else CredentialDisposition.PASS


class CredentialPresentationProfile(BaseModelPlus):
    """Authored wording for the existing credential mediation grammar."""

    indication_labels: dict[IndicationId, str] = Field(default_factory=dict)
    document_labels: dict[IndicationId, str] = Field(default_factory=dict)
    identity_label: str = "passport"
    identity_description: str = "An identity document."
    document_description: str = "A {document}."
    ordinary_attestation_template: str = (
        "A round blue {issuer_group} seal is impressed beside the bearer line."
    )
    missing_attestation_template: str = "The {issuer_group} seal space is blank."
    alternate_attestation_template: str = (
        "An over-bright {issuer_group} seal sits beside the bearer line."
    )
    ordinary_validity_template: str = (
        "The validity line reads “Valid through the current entry period.”"
    )
    unusual_date_validity_template: str = "The issue line reads “32 September.”"
    past_validity_template: str = (
        "The validity line reads “Valid through the previous entry period.”"
    )
    possession_description: str = "Openly declared {indication}."
    candidate_arrival_template: str = (
        "{{ candidate_name }}{% set description = render_as(candidate, 'presence_description') %}"
        "{% if description %}, {{ description }}{% endif %} steps forward."
    )
    packet_presentation_template: str = (
        "They present their documents: "
        "{{ render_as(packet, 'inspection_description', "
        "bindings={'document_replacements': document_replacements, "
        "'document_bases': document_bases, "
        "'document_observations': document_observations}) }}"
    )
    status_text: dict[CredentialStatus, str] = Field(
        default_factory=lambda: {
            CredentialStatus.MISSING_SEAL: "The issuing seal is missing.",
            CredentialStatus.BAD_DATE: "The issue date is wrong.",
            CredentialStatus.EXPIRED: "The credential has expired.",
            CredentialStatus.FORGED: "The seal is a forgery.",
            CredentialStatus.WRONG_HOLDER: "The holder does not match this document.",
        }
    )
    identity_mismatch_text: str = "The identity document does not name this bearer."
    holder_mismatch_text: str = "The permit's holder does not match the bearer id."
    packet_inconsistency_text: str = (
        "The packet does not satisfy the checkpoint rules as presented."
    )
    move_labels: dict[str, str] = Field(
        default_factory=lambda: {
            "request_document": "Request reissue of {document}",
        }
    )
    decision_labels: dict[str, str] = Field(default_factory=dict)
    journal_text: dict[str, str] = Field(
        default_factory=lambda: {
            "request_document": "You request a reissue of the {document}.",
            "request_document_cleared": "The candidate produces a corrected copy.",
            "request_document_verified": "The candidate re-presents the same sound permit.",
            "request_document_confirmed": "No valid copy is forthcoming; the permit will not hold up.",
            "request_document_not_applicable": "There is nothing to reissue.",
        }
    )

    @model_validator(mode="after")
    def validate_status_text(self) -> Self:
        """Require authored profiles to name every invalid credential status."""

        missing = [
            status.value
            for status in CredentialStatus
            if not status.is_valid and status not in self.status_text
        ]
        if missing:
            raise ValueError(
                "status_text must define every invalid credential status; "
                f"missing: {', '.join(missing)}"
            )
        return self

    def document_label(
        self,
        indication: IndicationId,
        component: CredentialComponent | None = None,
    ) -> str:
        if indication in self.document_labels:
            return self.document_labels[indication]
        if component is not None and component.reference_singleton.name is not None:
            return component.reference_singleton.name
        return f"{self.indication_labels.get(indication, indication)} permit"

    def format(self, template: str, *, document: str, indication: IndicationId) -> str:
        return template.format(
            document=document,
            indication=self.indication_labels.get(indication, indication),
        )

    def attestation_observations(
        self,
        component: CredentialComponent,
        *,
        reissued: bool = False,
    ) -> tuple[CredentialAttestationObservation, ...]:
        """Project the visible issuer attestation without interpreting it."""

        if component.issuer_group is None:
            return ()
        template = self.ordinary_attestation_template
        if component.status is CredentialStatus.MISSING_SEAL and not reissued:
            template = self.missing_attestation_template
        elif component.status is CredentialStatus.FORGED:
            template = self.alternate_attestation_template
        return (
            CredentialAttestationObservation(
                content=template.format(
                    issuer_group=component.issuer_group.replace("_", " "),
                )
            ),
        )

    def validity_observations(
        self,
        component: CredentialComponent,
        *,
        reissued: bool = False,
    ) -> tuple[CredentialValidityObservation, ...]:
        """Project visible date wording without evaluating the credential."""

        if component.valid_period is None:
            return ()
        template = self.ordinary_validity_template
        if component.status is CredentialStatus.BAD_DATE and not reissued:
            template = self.unusual_date_validity_template
        elif component.status is CredentialStatus.EXPIRED and not reissued:
            template = self.past_validity_template
        return (
            CredentialValidityObservation(
                content=template.format(
                    valid_period=component.valid_period,
                    issuer_group=(component.issuer_group or "").replace("_", " "),
                )
            ),
        )

    def render_case(
        self,
        case: CredentialCase,
        defects: list[CredentialDefect],
    ) -> CredentialCase:
        """Project packet documents and defects into compatibility inspection text.

        Defects choose the policy-relevant finding text. A visible document still
        renders its raw status when that status is moot under the current rules;
        presentation does not promote that observation into a disposition defect.
        """

        documents: dict[str, str] = {}
        findings: dict[str, str] = {}
        defects_by_source = {
            defect.source_id: defect for defect in defects if defect.source_id is not None
        }

        id_card = _id_component(case.packet_manager)
        if id_card is not None:
            documents[self.identity_label] = self.identity_description
            defect = defects_by_source.get(id_card.uid)
            if defect is not None and defect.cause is not None:
                findings[self.identity_label] = self.status_text[defect.cause]
            elif defect is not None and defect.kind is CredentialDefectKind.SUBJECT_MISMATCH:
                findings[self.identity_label] = self.identity_mismatch_text
            elif not id_card.status.is_valid:
                findings[self.identity_label] = self.status_text[id_card.status]

        for component in case.packet_manager.get_slot(CREDENTIAL_PACKET_SLOT):
            document = self.document_label(component.indication, component)
            documents[document] = self.document_description.format(document=document)
            defect = defects_by_source.get(component.uid)
            if defect is not None and defect.cause is not None:
                findings[document] = self.status_text[defect.cause]
            elif defect is not None and defect.kind is CredentialDefectKind.SUBJECT_MISMATCH:
                findings[document] = self.holder_mismatch_text
            elif not component.status.is_valid:
                findings[document] = self.status_text[component.status]

        for item in case.get_contraband():
            if item.concealed:
                continue
            indication = self.indication_labels.get(item.indication, item.indication)
            documents[f"declared {indication}"] = self.possession_description.format(
                indication=indication,
            )

        case.presented_documents = documents
        case.hidden_facts = findings
        case.packet_hidden_facts = (
            {"packet consistency": self.packet_inconsistency_text} if findings else {}
        )
        return case


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
    catalog_ref: str | None = None
    presentation: CredentialPresentationProfile = Field(default_factory=CredentialPresentationProfile)

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
    # Frontier-materialized offers persist through accepted-entry setup. PLANNING
    # prepares the current and sequential candidate before that game is entered.
    materialized: list[CredentialCase] = Field(
        default_factory=list,
        json_schema_extra={
            "include": True,
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
            case.bind_packet_manager_owner(owner)

    def _credential_catalog(self, owner: object) -> TokenCatalog[CredentialDefinition]:
        if self.catalog_ref is None:
            return default_credential_catalog()
        graph = owner.graph
        world = graph.factory
        assert world is not None
        catalogs = [
            catalog
            for catalog in world.get_token_catalogs(caller=owner, graph=graph)
            if catalog.label == self.catalog_ref and catalog.has_kind(CredentialDefinition)
        ]
        if len(catalogs) != 1:
            raise ValueError(
                f"World '{world.label}' exposes {len(catalogs)} credential catalogs "
                f"named '{self.catalog_ref}'."
            )
        return catalogs[0]

    @property
    def has_component_manager_owner(self) -> bool:
        """Whether sampled cases can materialize into graph credential components."""

        return self._component_manager_owner is not None

    def prepare_case(self, case_index: int) -> CredentialCase:
        """Materialize one sequential case without making it active."""

        if not self.offers:
            return self.roster[case_index]
        from .credentials_roster import materialize

        while len(self.materialized) <= case_index:
            offer = self.offers[len(self.materialized)]
            self.materialized.append(
                materialize(
                    offer,
                    self.restriction_map,
                    owner=self._component_manager_owner or object(),
                    catalog=(
                        self._credential_catalog(self._component_manager_owner)
                        if self._component_manager_owner is not None
                        else None
                    ),
                    narrative_renderer=self.presentation.render_case,
                )
            )
        return self.materialized[case_index]

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
            return self.prepare_case(self.case_index)
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
        return derive_disposition(case.packet_manager, self.restriction_map, self.finding_status)

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

        if self.shift_complete:
            self.current_stage = "packet"
        elif not self.offers or len(self.materialized) > self.case_index:
            self.current_stage = "documents" if self.presented_documents else "packet"
        else:
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
                # Graph-bound context for recursive document presentation.
                "packet": self.active_case.packet_manager,
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
        """Prepare graph-owned offers, without sampling an unresolved lazy roster."""

        if game.has_component_manager_owner and game.offers:
            case = game.prepare_case(game.case_index)
            if not case.presented_documents:
                game.current_stage = "packet"
        elif not game.offers and not game.presented_documents:
            game.current_stage = "packet"

    def provision_presentation(self, game: CredentialsGame, *, ctx: VmPhaseCtx) -> None:
        """Prepare the current and sequential successor card frontiers."""
        if game.shift_complete or ctx.cursor is None:
            return

        indices = [game.case_index]
        if game.case_index + 1 < game._total_cases():
            indices.append(game.case_index + 1)
        for case_index in indices:
            case = game.prepare_case(case_index)
            if case_index == game.case_index and not case.presented_documents:
                game.current_stage = "packet"
            self._provision_case_presentation(
                game,
                case=case,
                case_index=case_index,
                ctx=ctx,
            )

    def _provision_case_presentation(
        self,
        game: CredentialsGame,
        *,
        case: CredentialCase,
        case_index: int,
        ctx: VmPhaseCtx,
    ) -> None:
        """Provision one already-prepared case without changing active state."""
        for projection in self.credential_card_projections(game, case=case):
            component = next(
                component
                for component in case.packet_manager.document_components()
                if component.uid == projection.component_id
            )
            subject = case.packet_manager.resolve_subject(projection.subject_id)
            portrait = self._card_media_dependency(
                game,
                component=component,
                case_index=case_index,
                role="portrait",
                spec=credential_card_portrait_spec(projection, subject),
                ctx=ctx,
            )
            text = self._card_media_dependency(
                game,
                component=component,
                case_index=case_index,
                role="printable_text",
                spec=credential_card_text_spec(projection),
                ctx=ctx,
            )
            resolver = Resolver.from_ctx(ctx)
            for dependency in (portrait, text):
                if not dependency.render_ready:
                    resolver.resolve_dependency(dependency, _ctx=ctx)
            if not portrait.render_ready or not text.render_ready:
                continue

            portrait_rit = portrait.provider
            text_rit = text.provider
            if not isinstance(portrait_rit, MediaRIT) or not isinstance(text_rit, MediaRIT):
                continue
            if portrait_rit.get_content_hash() is None or text_rit.get_content_hash() is None:
                continue

            card = self._card_media_dependency(
                game,
                component=component,
                case_index=case_index,
                role="card",
                spec=credential_card_composition_spec(
                    portrait_rit=portrait_rit,
                    text_rit=text_rit,
                ),
                ctx=ctx,
            )
            if not card.render_ready:
                resolver.resolve_dependency(card, _ctx=ctx)

    @staticmethod
    def _card_media_dependency(
        game: CredentialsGame,
        *,
        component: CredentialComponent,
        case_index: int,
        role: str,
        spec: MediaSpec,
        ctx: VmPhaseCtx,
    ) -> MediaDep:
        """Return one stable, graph-owned media dependency for a card role."""
        dependency_id = _card_media_dep_uid(
            game.uid,
            case_index,
            component.uid,
            role,
        )
        existing = ctx.graph.get(dependency_id)
        if existing is not None:
            assert isinstance(existing, MediaDep)
            return existing
        dependency = MediaDep(
            uid=dependency_id,
            registry=ctx.graph,
            predecessor_id=ctx.cursor_id,
            media_spec=spec,
            media_role="credential_card",
            label=f"credential-card-{role}",
        )
        ctx.graph.add(dependency, _ctx=ctx)
        return dependency

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
        # request_document: offer for every contributing permit not yet requested.
        for indication in self._request_document_indications(case):
            key = str(indication)
            if key in game.finding_status:
                continue
            moves.append(CredentialsMove(kind="request_document", target=key))
        # verify_id: offer whenever an id is presented and not yet verified.
        if case.id_status() is not None and FindingKey.ID not in game.finding_status:
            moves.append(CredentialsMove(kind="verify_id", target=""))
        if self._id_required_and_absent(game) and FindingKey.ID not in game.finding_status:
            moves.append(CredentialsMove(kind="request_id", target=""))
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

    @staticmethod
    def _id_required_and_absent(game: CredentialsGame) -> bool:
        """Whether visible packet state lacks an ID required by today's rules."""

        level = game.restriction_map.level_for(
            game.active_case.get_region(),
            game.active_case.get_purpose(),
            RestrictionLevel.ANONYMOUS,
        )
        return level.requires_id and game.active_case.id_status() is None

    @staticmethod
    def _request_document_indications(case: CredentialCase) -> list[IndicationId]:
        """Return visible document indications that semantically offer reissue."""

        return [
            component.indication
            for component in CredentialsGameHandler._request_document_components(
                case.packet_manager
            )
        ]

    @staticmethod
    def _request_document_components(
        manager: AssemblyCredentialPacketManager,
    ) -> list[CredentialComponent]:
        """Return the first packet component contributing each request target."""

        components_by_id = {
            str(component.uid): component
            for component in manager.get_slot(CREDENTIAL_PACKET_SLOT)
        }
        components: list[CredentialComponent] = []
        indications: set[IndicationId] = set()
        for facet in manager.component_facets(
            channel="choice",
            facet_type="giver",
        ):
            if (
                facet.payload != "request_document"
                or facet.subject_id != CREDENTIAL_PACKET_SLOT
            ):
                continue
            assert facet.source_id is not None
            component = components_by_id[facet.source_id]
            if component.indication not in indications:
                components.append(component)
                indications.add(component.indication)
        return components

    @staticmethod
    def _request_document_component(
        case: CredentialCase,
        indication: IndicationId,
    ) -> CredentialComponent | None:
        return next(
            (
                component
                for component in CredentialsGameHandler._request_document_components(
                    case.packet_manager
                )
                if component.indication == indication
            ),
            None,
        )

    @staticmethod
    def _request_document_label(game: CredentialsGame, indication: IndicationId) -> str:
        component = CredentialsGameHandler._request_document_component(
            game.active_case,
            indication,
        )
        return game.presentation.document_label(indication, component)

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
            return game.presentation.format(
                game.presentation.move_labels["request_document"],
                document=self._request_document_label(game, move.target),
                indication=move.target,
            )
        if move.kind == "verify_id":
            return "Verify identity"
        if move.kind == "request_id":
            return "Request ID"
        if move.kind == "request_search":
            return "Request search"
        if move.kind == "request_disclosure":
            return "Ask for anything to declare"
        if move.kind == "request_relinquish":
            return "Have the contraband surrendered"
        if move.kind == "decide":
            return game.presentation.decision_labels.get(
                move.target,
                f"Choose {move.target}",
            )
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
        inspect_targets = {
            target
            for target in self.get_available_inspect_targets(game)
            if target in game.presented_documents
        }
        target_by_piece_id = {
            _document_piece_id(game.case_index, target): target
            for target in inspect_targets
        }
        component_documents = self._document_components(game)
        label_counts = Counter(document.label for document in component_documents)
        for document in component_documents:
            if (
                label_counts[document.label] <= 1
                or document.label not in inspect_targets
            ):
                continue
            target_by_piece_id.pop(_document_piece_id(game.case_index, document.label), None)
            target_by_piece_id[
                _component_piece_id(game.case_index, document.component.uid)
            ] = document.label
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
                case_index=game.case_index,
                bearer_id=case.packet_manager.bearer_id,
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
        if kind == "request_id":
            return self._resolve_request_id(game, detail)
        if kind == "request_search":
            return self._resolve_request_search(game, detail)
        if kind == "request_disclosure":
            return self._resolve_request_disclosure(game, detail)
        if kind == "request_relinquish":
            return self._resolve_request_relinquish(game, detail)
        return super().resolve_move_kind(kind, game, player_move, detail)

    def _resolve_request_id(
        self,
        game: CredentialsGame,
        detail: dict[str, object],
    ) -> RoundResult:
        """Request one native but currently unpresented identity component."""

        if not self._id_required_and_absent(game):
            detail["outcome"] = "id_request_not_applicable"
            return RoundResult.CONTINUE
        case = game.active_case
        manager = case.packet_manager
        id_components = manager.get_slot(CREDENTIAL_UNPRESENTED_SLOT)
        id_card = next((item for item in id_components if item.document_kind == "id"), None)
        if case.id_request_response == "comply" and id_card is not None:
            TransactionOffer(
                label="present id",
                commitments=[
                    AssetMoveCommitment(
                        giver=ComponentSlotAssetHolder(manager, CREDENTIAL_UNPRESENTED_SLOT),
                        receiver=ComponentSlotAssetHolder(manager, CREDENTIAL_ID_SLOT),
                        asset=id_card,
                        label="present id",
                    ),
                ],
            ).accept()
            game.finding_status[FindingKey.ID] = Finding.CLEARED
            detail["outcome"] = "id_request_complied"
            detail["component_id"] = str(id_card.uid)
            game.presentation.render_case(
                case,
                derive_defects(manager, game.restriction_map, game.finding_status),
            )
        else:
            game.finding_status[FindingKey.ID] = Finding.REFUSED
            detail["outcome"] = "id_request_refused"
        return RoundResult.CONTINUE

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
        indication = indication_value
        if indication not in self._request_document_indications(game.active_case):
            detail["outcome"] = "request_document_not_applicable"
            detail["target_indication"] = indication_value
            return RoundResult.CONTINUE

        permit = self._request_document_component(game.active_case, indication)
        if permit is None:  # off-menu safety; receive_move does not validate
            detail["outcome"] = "request_document_not_applicable"
            detail["target_indication"] = indication_value
            return RoundResult.CONTINUE

        id_card = _id_component(game.active_case.packet_manager)
        defect = _document_defect(
            permit,
            subject="authorization",
            indication=indication,
            expected_subject_id=(id_card.subject_id if id_card is not None else None),
            cleared=game.finding_status.get(indication) == Finding.CLEARED,
            invalid_kind=CredentialDefectKind.INVALID_EVIDENCE,
            invalid_subject="authorization",
        )
        if defect is not None and defect.failure_class is FailureClass.CRIME:
            game.finding_status[indication_value] = Finding.CONFIRMED
            detail["outcome"] = "request_document_confirmed"
        elif defect is not None:
            game.finding_status[indication_value] = Finding.CLEARED
            detail["outcome"] = "request_document_cleared"
        else:
            game.finding_status[indication_value] = Finding.VERIFIED
            detail["outcome"] = "request_document_verified"
        detail["target_indication"] = indication_value
        return RoundResult.CONTINUE

    def _resolve_verify_id(
        self,
        game: CredentialsGame,
        detail: dict[str, object],
    ) -> RoundResult:
        # verify_id answers only "does the id match the bearer?". It discloses a
        # subject mismatch (a crime) but never mechanically repairs a stale id --
        # an expired or mis-dated id stays a deny until a future id-reissue move
        # (B.2). So it records VERIFIED / CONFIRMED, never CLEARED.
        id_card = _id_component(game.active_case.packet_manager)
        if id_card is None:  # off-menu safety; the menu offers this only with an id
            detail["outcome"] = "id_verified_not_applicable"
            return RoundResult.CONTINUE
        mismatch = any(
            defect.kind is CredentialDefectKind.SUBJECT_MISMATCH
            and defect.source_id == id_card.uid
            for defect in derive_defects(
                game.active_case.packet_manager,
                game.restriction_map,
                game.finding_status,
            )
        )
        if mismatch:
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
            detail["concealed"] = [str(item.indication) for item in concealed]
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
            detail["declared"] = [str(item.indication) for item in concealed]
        else:
            game.finding_status[FindingKey.DISCLOSURE] = Finding.DECLARED
            if concealed:
                detail["outcome"] = "disclosure_declared"
                detail["declared"] = [str(item.indication) for item in concealed]
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

    def get_journal_fragments(
        self,
        game: CredentialsGame,
        *,
        ctx: VmPhaseCtx | None = None,
    ) -> list[BaseFragment] | None:
        last_round = game.last_round
        if last_round is None:
            if game.shift_complete:
                return []
            return [
                *self._arrival_fragments(game, ctx=ctx),
                *self._candidate_fragments(game, ctx=ctx),
            ]

        move = self._normalize_move(last_round.player_move)
        prose = self._prose_fragments(game, last_round, move.kind, move.target, last_round.notes or {})

        if not game.shift_complete and move.kind == "decide":
            return [
                *prose,
                *self._arrival_fragments(game, ctx=ctx),
                *self._candidate_fragments(game, ctx=ctx),
            ]

        fragments: list[BaseFragment] = []
        # Structured candidate / packet view (Bridge.1). Skip once the shift is
        # over -- there is no next candidate to present.
        if not game.shift_complete:
            fragments.extend(self._candidate_fragments(game, ctx=ctx))
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
            outcome_key = str(outcome)
            line = game.presentation.journal_text.get(
                outcome_key,
                game.presentation.journal_text["request_document_not_applicable"],
            )
            document = self._request_document_label(game, target)
            return [
                ContentFragment(
                    content=game.presentation.format(
                        game.presentation.journal_text["request_document"],
                        document=document,
                        indication=target,
                    )
                ),
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
        if action == "request_id":
            if notes.get("outcome") == "id_request_complied":
                line = "The candidate produces their identification."
            elif notes.get("outcome") == "id_request_refused":
                line = "The candidate does not produce identification."
            else:
                line = "There is no identification to request."
            return [
                ContentFragment(content="You request the candidate's identification."),
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
        return fragments

    # ----- Bridge.1: structured (typed) fragment projection ----------------

    def _arrival_fragments(
        self,
        game: CredentialsGame,
        *,
        ctx: VmPhaseCtx | None,
    ) -> list[ContentFragment]:
        """Render the current candidate and packet once on arrival."""

        if ctx is None:
            return []

        case = game.active_case
        packet = case.packet_manager
        candidate = packet.resolve_subject(packet.bearer_id)
        session = TextRenderSession(ctx=ctx, text_resolver=render_text_as)
        bindings = {
            "candidate_name": case.candidate_name,
            "candidate": candidate,
            "packet": packet,
            **self._document_bindings(game),
        }
        return [
            ContentFragment(
                content=render_text_as(
                    candidate,
                    "arrival_description",
                    ctx=ctx,
                    session=session,
                    content=game.presentation.candidate_arrival_template,
                    bindings=bindings,
                ),
                source_id=candidate.uid,
            ),
            ContentFragment(
                content=render_text_as(
                    packet,
                    "packet_presentation",
                    ctx=ctx,
                    session=session,
                    content=game.presentation.packet_presentation_template,
                    bindings=bindings,
                ),
                source_id=ctx.cursor.uid,
            ),
        ]

    def _component_label(
        self,
        game: CredentialsGame,
        component: CredentialComponent,
    ) -> str:
        """Return the scenario-facing label for one packet component."""

        if component.document_kind == "id":
            return game.presentation.identity_label
        return game.presentation.document_label(component.indication, component)

    def _document_components(
        self,
        game: CredentialsGame,
        *,
        case: CredentialCase | None = None,
    ) -> list[_CredentialDocumentRender]:
        """Pair canonical components with their profile base and visible parts."""

        case = case or game.active_case
        is_active_case = case is game.active_case
        documents: list[_CredentialDocumentRender] = []
        for component in case.packet_manager.document_components():
            label = self._component_label(game, component)
            base_description = (
                game.presentation.identity_description
                if component.document_kind == "id"
                else game.presentation.format(
                    game.presentation.document_description,
                    document=label,
                    indication=component.indication,
                )
            )
            presented_description = case.presented_documents.get(label)
            complete_replacement = (
                presented_description
                if presented_description != base_description
                else None
            )
            reissued_component = self._request_document_component(
                case,
                component.indication,
            )
            reissued = (
                is_active_case
                and reissued_component is not None
                and component.uid == reissued_component.uid
                and game.finding_status.get(component.indication) == Finding.CLEARED
            )
            documents.append(
                _CredentialDocumentRender(
                    component=component,
                    label=label,
                    base_description=base_description,
                    complete_replacement=complete_replacement,
                    visible_observations=(
                        ()
                        if complete_replacement is not None
                        else (
                            game.presentation.attestation_observations(
                                component,
                                reissued=reissued,
                            )
                            + game.presentation.validity_observations(
                                component,
                                reissued=reissued,
                            )
                        )
                    ),
                )
            )
        return documents

    def credential_card_projections(
        self,
        game: CredentialsGame,
        *,
        case: CredentialCase | None = None,
    ) -> list[CredentialCardProjection]:
        """Project one case's canonical ID documents for future card media."""
        case = case or game.active_case
        return [
            CredentialCardProjection(
                component_id=document.component.uid,
                subject_id=document.component.subject_id,
                document_kind=document.component.document_kind,
                document_label=document.label,
                bearer_label=case.candidate_name,
                visible_parts=document.visible_observations,
            )
            for document in self._document_components(game, case=case)
            if (
                document.component.document_kind == "id"
                and document.complete_replacement is None
            )
        ]

    def _document_bindings(self, game: CredentialsGame) -> dict[str, object]:
        """Return the explicit per-component bindings for recursive packet text."""

        documents = self._document_components(game)
        return {
            "document_replacements": {
                document.component.uid: document.complete_replacement
                for document in documents
                if document.complete_replacement is not None
            },
            "document_bases": {
                document.component.uid: document.base_description
                for document in documents
            },
            "document_observations": {
                document.component.uid: document.visible_observations
                for document in documents
            },
        }

    @staticmethod
    def _fallback_document_description(
        component: CredentialComponent,
    ) -> str:
        """Keep direct callers useful when no live rendering context exists."""

        if component.reference_singleton.name is not None:
            return component.reference_singleton.name
        if component.document_kind == "id":
            return "identity document"
        return f"{component.indication} document"

    def _candidate_fragments(
        self,
        game: CredentialsGame,
        *,
        ctx: VmPhaseCtx | None = None,
    ) -> list[BaseFragment]:
        """Project the active candidate + packet zone + document pieces.

        Deterministic uids (per game + case index) let the client update these
        pieces in place across rounds rather than re-creating them each turn.
        """

        case = game.active_case
        idx = game.case_index
        packet_uid = _piece_uid(game.uid, idx, "packet")
        candidate_properties: dict[str, object] = {
            "declared_purpose": str(case.get_purpose()),
            "declared_region": str(case.get_region()),
        }
        if case.packet_manager.has_resolved_subject(case.packet_manager.bearer_id):
            bearer = case.packet_manager.resolve_subject(case.packet_manager.bearer_id)
            candidate_properties["look_media_payload"] = bearer.adapt_look_media_spec(
                media_role="candidate"
            )
            if ctx is not None:
                candidate_properties["look_description"] = render_text_as(
                    bearer,
                    "presence_description",
                    ctx=ctx,
                )

        candidate = PieceFragment(
            uid=_piece_uid(game.uid, idx, "candidate"),
            piece_id=f"candidate-{idx}",
            piece_kind="candidate",
            content=case.candidate_name,
            properties=candidate_properties,
            hints=PresentationHints(label_text=case.candidate_name),
        )

        doc_uids: list[uuid.UUID] = []
        doc_pieces: list[BaseFragment] = []
        component_labels: set[str] = set()
        component_documents = self._document_components(game)
        card_projections = {
            projection.component_id: projection
            for projection in self.credential_card_projections(game)
        }
        label_counts = Counter(
            document.label for document in component_documents
        )
        for document in component_documents:
            component = document.component
            label = document.label
            component_labels.add(label)
            description = (
                render_text_as(
                    component,
                    "document_description",
                    ctx=ctx,
                    content=document.complete_replacement,
                    bindings={
                        "packet": case.packet_manager,
                        "base_description": document.base_description,
                        "visible_observations": document.visible_observations,
                    },
                )
                if ctx is not None
                else document.complete_replacement
                or "; ".join(
                    [self._fallback_document_description(component)]
                    + [
                        observation.content
                        for observation in document.visible_observations
                    ]
                )
            )
            doc_uid = _piece_uid(game.uid, idx, f"doc:{component.uid}")
            doc_uids.append(doc_uid)
            properties: dict[str, object] = {
                "component_id": component.uid,
                "visible_parts": [
                    observation.model_dump() for observation in document.visible_observations
                ],
            }
            if (
                component.document_kind == "id"
                and case.packet_manager.has_resolved_subject(component.subject_id)
            ):
                subject = case.packet_manager.resolve_subject(component.subject_id)
                properties["look_media_payload"] = subject.adapt_look_media_spec(
                    media_role="id_photo"
                )
                if ctx is not None:
                    properties["look_description"] = render_text_as(
                        subject,
                        "presence_description",
                        ctx=ctx,
                    )
            doc_pieces.append(
                PieceFragment(
                    uid=doc_uid,
                    piece_id=(
                        _component_piece_id(idx, component.uid)
                        if label_counts[label] > 1
                        else _document_piece_id(idx, label)
                    ),
                    piece_kind=_document_kind(label),
                    content=description,
                    zone_ref=packet_uid,
                    properties=properties,
                    hints=PresentationHints(label_text=label),
                )
            )
            projection = card_projections.get(component.uid)
            if projection is not None:
                doc_pieces.extend(
                    self._card_media_fragments(
                        game,
                        projection=projection,
                        document_piece_id=doc_uid,
                        ctx=ctx,
                    )
                )

        for label, description in case.presented_documents.items():
            if label in component_labels:
                continue
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

    @staticmethod
    def _card_media_fragments(
        game: CredentialsGame,
        *,
        projection: CredentialCardProjection,
        document_piece_id: uuid.UUID,
        ctx: VmPhaseCtx | None,
    ) -> list[BaseFragment]:
        """Project one resolved card RIT beside its canonical document piece."""
        if ctx is None:
            return []
        dependency = ctx.graph.get(
            _card_media_dep_uid(
                game.uid,
                game.case_index,
                projection.component_id,
                "card",
            )
        )
        if not isinstance(dependency, MediaDep) or not dependency.render_ready:
            return []
        card = dependency.provider
        spec = dependency.requirement.media_spec
        if not isinstance(card, MediaRIT) or not isinstance(spec, CompositionSpec):
            return []
        try:
            resolve_composition_inputs(spec, graph=ctx.graph)
        except CompositionInputUnavailable:
            return []

        media_uid = _piece_uid(
            game.uid,
            game.case_index,
            f"card-media:{projection.component_id}",
        )
        return [
            MediaFragment(
                uid=media_uid,
                source_id=projection.component_id,
                media_role="credential_card",
                content=card,
                content_format="rit",
                content_type=card.data_type,
                scope="story",
            ),
            GroupFragment(
                uid=_piece_uid(
                    game.uid,
                    game.case_index,
                    f"piece-media:{projection.component_id}",
                ),
                group_type="piece_media",
                member_ids=[document_piece_id, media_uid],
            ),
        ]

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
