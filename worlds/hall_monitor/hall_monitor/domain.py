from __future__ import annotations

from typing import ClassVar, Literal
from uuid import UUID

from pydantic import Field, model_validator

from tangl.core import Selector
from tangl.core.bases import BaseModelPlus
from tangl.journal.fragments import ContentFragment
from tangl.mechanics.credentials import (
    CREDENTIAL_ID_SLOT,
    CREDENTIAL_PACKET_SLOT,
    CredentialComponent,
    CredentialDefinition,
    CredentialStatus,
    FailureMode,
    Restrictions,
    RestrictionLevel,
)
from tangl.mechanics.assembly import ComponentManager, Slot
from tangl.mechanics.presence.look import HairColor, HasSimpleLook
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.credentials_game import (
    CredentialCase,
    CredentialCaseResult,
    CredentialDisposition,
    CredentialPresentationProfile,
    CredentialsMove,
    CredentialsGame,
    CredentialsGameHandler,
)
from tangl.mechanics.games.enums import RoundResult
from tangl.mechanics.transaction import (
    AssetMoveCommitment,
    CallbackCommitment,
    ComponentSlotAssetHolder,
    TransactionOffer,
    TransactionReceipt,
)
from tangl.mechanics.games.credentials_roster import (
    ScenarioOffer,
    ShiftSpec,
    generate_roster,
)
from tangl.story import Action, Block, on_journal
from tangl.story.presentation import render_text_as
from tangl.vm import on_provision, on_update
from tangl.vm.ctx import VmPhaseCtx


HALL_RULES = {
    "upper": {
        "academic": RestrictionLevel.WITH_PERMIT,
        "activity": RestrictionLevel.WITH_PERMIT,
        "off_campus": RestrictionLevel.WITH_PERMIT,
        "uniform": RestrictionLevel.WITH_ID,
        "medicine": RestrictionLevel.WITH_PERMIT,
        "records": RestrictionLevel.WITH_PERMIT,
    },
    "lower": {
        "academic": RestrictionLevel.WITH_PERMIT,
        "activity": RestrictionLevel.WITH_PERMIT,
        "off_campus": RestrictionLevel.WITH_PERMIT,
        "uniform": RestrictionLevel.WITH_PERMIT,
        "medicine": RestrictionLevel.WITH_PERMIT,
        "records": RestrictionLevel.WITH_PERMIT,
    },
    "exchange": {
        "academic": RestrictionLevel.WITH_PERMIT,
        "activity": RestrictionLevel.WITH_PERMIT,
        "off_campus": RestrictionLevel.WITH_PERMIT,
        "uniform": RestrictionLevel.WITH_PERMIT,
        "medicine": RestrictionLevel.WITH_PERMIT,
        "records": RestrictionLevel.WITH_PERMIT,
    },
}

HALL_PRESENTATION = CredentialPresentationProfile(
    indication_labels={
        "academic": "academic",
        "activity": "activity",
        "off_campus": "off-campus",
        "uniform": "uniform",
        "medicine": "medicine",
        "records": "records",
    },
    document_labels={
        "academic": "hall pass",
        "activity": "activity pass",
        "off_campus": "off-campus pass",
        "uniform": "uniform waiver",
        "medicine": "doctor's note",
        "records": "office pass",
    },
    identity_label="student ID",
    identity_description="A laminated student identification card.",
    document_description="{document}.",
    ordinary_attestation_template=(
        "The {issuer_group} signature appears in blue ink."
    ),
    missing_attestation_template="The {issuer_group} signature line is blank.",
    alternate_attestation_template=(
        "The {issuer_group} signature is written in a heavy, unfamiliar hand."
    ),
    ordinary_validity_template="The pass is marked “Valid for this period.”",
    unusual_date_validity_template="The period box is marked “Period 9.”",
    past_validity_template="The pass is marked “Valid for last period.”",
    possession_description="A student openly declares {indication}.",
    status_text={
        CredentialStatus.MISSING_SEAL: "The required teacher signature is missing.",
        CredentialStatus.BAD_DATE: "The date on the pass is wrong.",
        CredentialStatus.EXPIRED: "The pass has expired.",
        CredentialStatus.FORGED: "The teacher signature is forged.",
        CredentialStatus.WRONG_HOLDER: "The student ID does not match this document.",
    },
    holder_mismatch_text="The student ID does not match this pass.",
    packet_inconsistency_text="The student's papers do not satisfy the hall rules.",
    move_labels={"request_document": "Ask for a corrected {document}"},
    decision_labels={
        "pass": "Allow onward",
        "deny": "Send back to class",
        "arrest": "Send to the office",
    },
    journal_text={
        "request_document": "You ask for a corrected {document}.",
        "request_document_cleared": "A teacher-signed replacement is produced.",
        "request_document_verified": "The student presents the same sound pass.",
        "request_document_confirmed": "No valid school document is forthcoming.",
        "request_document_not_applicable": "There is no school pass to correct.",
    },
)

_HALL_FAILURES = (
    FailureMode.MISSING_PERMIT,
    FailureMode.UNSEALED_PERMIT,
    FailureMode.FORGED_PERMIT,
    FailureMode.WRONG_HOLDER_PERMIT,
    FailureMode.MISSING_ID,
    FailureMode.EXPIRED_ID,
    FailureMode.FAKE_ID,
)
_MEDIA_WITNESS_CASE_INDEX = 1
_WAIVER_CASE_INDEX = 0
HALL_DESK_CUSTODY_SLOT = "retained_documents"


def _special_student() -> ScenarioOffer:
    """Return the recurring lower-school medical-pass case for every shift."""

    return ScenarioOffer(
        target_disposition=CredentialDisposition.DENY,
        candidate_name="Mira Quill",
        region="lower",
        purpose="medicine",
        failure_modes=[FailureMode.MISSING_PERMIT],
        presented_documents_override={
            "student ID": "A laminated lower-school student identification card.",
        },
        packet_hidden_facts_override={
            "packet consistency": "The student's papers do not satisfy the hall rules.",
        },
    )


def _media_witness_student() -> ScenarioOffer:
    """Return the fixed visual subject-mismatch encounter for this world."""

    return ScenarioOffer(
        target_disposition=CredentialDisposition.ARREST,
        candidate_name="Rowan Vale",
        region="lower",
        purpose="medicine",
        failure_modes=[FailureMode.FAKE_ID],
    )


def _waiver_student() -> ScenarioOffer:
    """Return the earlier incomplete waiver that Hall Monitor may retain."""

    return ScenarioOffer(
        target_disposition=CredentialDisposition.DENY,
        candidate_name="Tess Alder",
        region="lower",
        purpose="medicine",
        failure_modes=[FailureMode.UNSEALED_PERMIT],
        presented_documents_override={
            "student ID": "A laminated lower-school student identification card.",
            "doctor's note": "A nurse waiver awaiting its completed signature.",
        },
    )


def _hall_offers(
    *,
    encounters: int,
    disposition_distribution: dict[CredentialDisposition, float],
    seed: int,
) -> list[ScenarioOffer]:
    """Generate one configured school shift through the shared roster funnel."""

    pinned = [_waiver_student(), _media_witness_student(), _special_student()]
    if encounters <= len(pinned):
        return pinned[:encounters]
    sampled = generate_roster(
        ShiftSpec(
            rules=Restrictions.from_map(HALL_RULES),
            encounters=encounters - len(pinned),
            origin_distribution={"upper": 0.4, "lower": 0.4, "exchange": 0.2},
            disposition_distribution=disposition_distribution,
            purpose_pool=("academic", "activity", "off_campus"),
            allowed_failure_modes=_HALL_FAILURES,
            seed=seed,
        )
    )
    return [*pinned, *sampled]


def _is_document(component: CredentialComponent) -> bool:
    return component.document_kind == "document"


class HallMonitorDeskCustodyManager(ComponentManager[CredentialComponent]):
    """Hall Monitor's durable desk custody for retained credential documents.

    Why
    ---
    The retained waiver remains a graph-owned credential component while it is
    no longer in its first candidate's packet.
    """

    slots: ClassVar[dict[str, Slot]] = {
        HALL_DESK_CUSTODY_SLOT: Slot.for_predicate(
            HALL_DESK_CUSTODY_SLOT,
            _is_document,
            max_count=100,
        ),
    }


class HallMonitorCredentialsGame(CredentialsGame):
    """School-specific credentials shift with the bounded school catalog."""

    restriction_map: Restrictions = Field(
        default_factory=lambda: Restrictions.from_map(HALL_RULES)
    )
    catalog_ref: str = "school"
    presentation: CredentialPresentationProfile = Field(
        default_factory=lambda: HALL_PRESENTATION.model_copy(deep=True)
    )
    desk_custody: HallMonitorDeskCustodyManager = Field(
        default_factory=HallMonitorDeskCustodyManager,
        json_schema_extra={"include": True, "unstructurable": True},
    )
    transaction_receipts: list[TransactionReceipt] = Field(
        default_factory=list,
        json_schema_extra={"include": True},
    )
    waiver_case_index: int = _WAIVER_CASE_INDEX
    inhaler_case_index: int = 2
    waiver_reissue_authorized: bool = True

    def bind_component_managers(self, owner: object) -> None:
        """Bind both candidate packets and the world-owned custody manager."""

        super().bind_component_managers(owner)
        self.desk_custody.bind_owner(owner)

    def prepare_case(self, case_index: int) -> CredentialCase:
        """Materialize the world-owned visual mismatch with distinct live looks."""

        case = super().prepare_case(case_index)
        if case_index != _MEDIA_WITNESS_CASE_INDEX:
            return case

        bearer = case.packet_manager.resolve_subject(case.packet_manager.bearer_id)
        id_card = case.packet_manager.get_slot(CREDENTIAL_ID_SLOT)[0]
        id_subject = case.packet_manager.resolve_subject(id_card.subject_id)
        if id_subject.uid == bearer.uid:
            raise ValueError("Hall Monitor media witness requires a mismatched ID subject")
        bearer.look.hair_color = HairColor.RED
        id_subject.look.hair_color = HairColor.BLONDE
        return case


class HallMonitorCredentialsHandler(CredentialsGameHandler):
    """Add Hall Monitor's narrow custody and authorized-reissue actions.

    Why
    ---
    The world owns when a visible document may be retained and reissued; the
    shared credential game continues to own evaluation and scoring.
    """

    def get_available_moves(self, game: HallMonitorCredentialsGame) -> list[CredentialsMove]:
        moves = super().get_available_moves(game)
        if game.current_stage == "documents":
            return moves

        if game.case_index == game.waiver_case_index:
            for component in game.active_case.packet_manager.get_slot(CREDENTIAL_PACKET_SLOT):
                if component.indication == "medicine":
                    moves.append(
                        CredentialsMove(kind="retain_waiver", target=str(component.uid))
                    )
        elif game.case_index == game.inhaler_case_index and game.waiver_reissue_authorized:
            for component in game.desk_custody.get_slot(HALL_DESK_CUSTODY_SLOT):
                if component.indication == "medicine":
                    moves.append(
                        CredentialsMove(kind="reissue_waiver", target=str(component.uid))
                    )
        return moves

    def get_move_label(self, game: HallMonitorCredentialsGame, move: CredentialsMove) -> str:
        if move.kind == "retain_waiver":
            return "Retain the medical waiver"
        if move.kind == "reissue_waiver":
            return "Complete and issue the medical waiver"
        return super().get_move_label(game, move)

    def resolve_move_kind(
        self,
        kind: str,
        game: HallMonitorCredentialsGame,
        player_move: CredentialsMove,
        detail: dict[str, object],
    ) -> RoundResult:
        if kind == "retain_waiver":
            return self._retain_waiver(game, player_move.target, detail)
        if kind == "reissue_waiver":
            return self._reissue_waiver(game, player_move.target, detail)
        return super().resolve_move_kind(kind, game, player_move, detail)

    @staticmethod
    def _active_waiver(
        game: HallMonitorCredentialsGame,
        component_id: str,
    ) -> CredentialComponent | None:
        return next(
            (
                component
                for component in game.active_case.packet_manager.get_slot(CREDENTIAL_PACKET_SLOT)
                if str(component.uid) == component_id and component.indication == "medicine"
            ),
            None,
        )

    def _retain_waiver(
        self,
        game: HallMonitorCredentialsGame,
        component_id: str,
        detail: dict[str, object],
    ) -> RoundResult:
        if game.case_index != game.waiver_case_index:
            raise ValueError("Medical waiver retention is not available for this candidate")
        component = self._active_waiver(game, component_id)
        if component is None:
            raise ValueError("The submitted waiver is not visible in this packet")
        offer = TransactionOffer(
            label="retain medical waiver",
            commitments=[
                AssetMoveCommitment(
                    giver=ComponentSlotAssetHolder(
                        game.active_case.packet_manager,
                        CREDENTIAL_PACKET_SLOT,
                    ),
                    receiver=ComponentSlotAssetHolder(
                        game.desk_custody,
                        HALL_DESK_CUSTODY_SLOT,
                    ),
                    asset=component,
                    label="retain medical waiver",
                ),
            ],
        )
        receipt = offer.accept()
        game.transaction_receipts.append(receipt)
        detail["outcome"] = "waiver_retained"
        detail["component_id"] = component.uid
        return RoundResult.CONTINUE

    def _reissue_waiver(
        self,
        game: HallMonitorCredentialsGame,
        component_id: str,
        detail: dict[str, object],
    ) -> RoundResult:
        if game.case_index != game.inhaler_case_index or not game.waiver_reissue_authorized:
            raise ValueError("Medical waiver reissue is not authorized here")
        component = next(
            (
                item
                for item in game.desk_custody.get_slot(HALL_DESK_CUSTODY_SLOT)
                if str(item.uid) == component_id and item.indication == "medicine"
            ),
            None,
        )
        if component is None:
            raise ValueError("The submitted waiver is not in desk custody")
        packet = game.active_case.packet_manager
        id_card = packet.get_slot(CREDENTIAL_ID_SLOT)[0]
        original_status = component.status
        original_subject_id = component.subject_id

        def apply_completion() -> None:
            component.status = CredentialStatus.VALID
            component.subject_id = id_card.subject_id

        def undo_completion() -> None:
            component.status = original_status
            component.subject_id = original_subject_id

        offer = TransactionOffer(
            label="complete medical waiver",
            commitments=[
                CallbackCommitment(
                    label="complete medical waiver",
                    apply=apply_completion,
                    undo=undo_completion,
                ),
                AssetMoveCommitment(
                    giver=ComponentSlotAssetHolder(game.desk_custody, HALL_DESK_CUSTODY_SLOT),
                    receiver=ComponentSlotAssetHolder(
                        game.active_case.packet_manager,
                        CREDENTIAL_PACKET_SLOT,
                    ),
                    asset=component,
                    label="issue medical waiver",
                ),
            ],
        )
        receipt = offer.accept()
        game.transaction_receipts.append(receipt)
        detail["outcome"] = "waiver_reissued"
        detail["component_id"] = component.uid
        return RoundResult.CONTINUE

    def _prose_fragments(
        self,
        game: HallMonitorCredentialsGame,
        last_round: object,
        action: str,
        target: str,
        notes: dict[str, object],
    ) -> list[ContentFragment]:
        if action == "retain_waiver":
            return [ContentFragment(content="You retain the medical waiver at the hall desk.")]
        if action == "reissue_waiver":
            return [ContentFragment(content="You complete and issue the medical waiver.")]
        return super()._prose_fragments(game, last_round, action, target, notes)


class HallMonitorConsequence(BaseModelPlus):
    """World-authored later fate for one completed Hall Monitor case.

    Why
    ---
    Credentials records the mechanical receipt. Hall Monitor owns the meaning
    and the later narration of that receipt.
    """

    source_case_index: int
    bearer_id: UUID
    outcome: Literal["inhaler_withheld", "inhaler_allowed"]


class HallMonitorBlock(HasGame, Block):
    """Script-configured Hall Monitor scenario instance."""

    encounters: int = 5
    disposition_distribution: dict[CredentialDisposition, float] = Field(
        default_factory=lambda: {
            CredentialDisposition.PASS: 0.5,
            CredentialDisposition.DENY: 0.3,
            CredentialDisposition.ARREST: 0.2,
        }
    )
    seed: int = 20260719
    inhaler_case_index: int = 2
    consequences: list[HallMonitorConsequence] = Field(
        default_factory=list,
        json_schema_extra={"include": True},
    )

    _game_class = HallMonitorCredentialsGame
    _game_handler_class = HallMonitorCredentialsHandler

    @model_validator(mode="after")
    def _configure_game(self) -> HallMonitorBlock:
        if self.game_state is None:
            self.game_state = HallMonitorCredentialsGame(
                roster=[],
                inhaler_case_index=self.inhaler_case_index,
                offers=_hall_offers(
                    encounters=self.encounters,
                    disposition_distribution=self.disposition_distribution,
                    seed=self.seed,
                )
            )
        return self


class HallMonitorConsequenceBlock(Block):
    """Later attendance-note beat that reveals a recorded Hall Monitor fate.

    Why
    ---
    A completed credential disposition is a mechanical receipt. This ordinary
    later block makes any Hall Monitor interpretation visible without granting
    it same-turn frontier or namespace visibility.
    """

    source_block_label: str = "morning_shift"
    return_block_label: str = "returning_student"


class HallMonitorReturnBlock(HasGame, Block):
    """One pre-authored return encounter prepared from the attendance note.

    Why
    ---
    The node is ordinary authored topology. Its game is configured only after
    the first case receipt exists, during the predecessor's PLANNING pass.
    """

    _game_class = HallMonitorCredentialsGame
    _game_handler_class = CredentialsGameHandler


@on_update(wants_caller_kind=HallMonitorBlock, wants_exact_kind=False)
def record_hall_monitor_consequence(
    *,
    caller: HallMonitorBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Record Mira's later outcome after the credentials disposition commits."""

    game = caller.game
    if not game.case_results:
        return None
    result = game.case_results[-1]
    if result.case_index != caller.inhaler_case_index:
        return None
    if any(fact.source_case_index == result.case_index for fact in caller.consequences):
        return None

    if result.chosen_disposition is CredentialDisposition.DENY:
        outcome: Literal["inhaler_withheld", "inhaler_allowed"] = "inhaler_withheld"
    elif result.chosen_disposition is CredentialDisposition.PASS:
        outcome = "inhaler_allowed"
    else:
        return None

    caller.consequences.append(
        HallMonitorConsequence(
            source_case_index=result.case_index,
            bearer_id=result.bearer_id,
            outcome=outcome,
        )
    )
    return None


@on_provision(wants_caller_kind=HallMonitorConsequenceBlock, wants_exact_kind=False)
def prepare_hall_monitor_return(
    *,
    caller: HallMonitorConsequenceBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Configure the authored return before its successor is presented."""

    source = caller.graph.find_one(Selector(label=caller.source_block_label))
    return_block = caller.graph.find_one(Selector(label=caller.return_block_label))
    if not isinstance(source, HallMonitorBlock) or not isinstance(
        return_block,
        HallMonitorReturnBlock,
    ):
        raise LookupError("Hall Monitor return topology is incomplete")
    if not source.consequences:
        return None

    consequence = source.consequences[-1]
    if return_block.game_state is None:
        prior_result = source.game.case_results[consequence.source_case_index]
        if prior_result.bearer_id != consequence.bearer_id:
            raise ValueError("Hall Monitor consequence does not match its source receipt")
        return_block.game_state = HallMonitorCredentialsGame(
            roster=[],
            offers=[
                ScenarioOffer(
                    target_disposition=CredentialDisposition.PASS,
                    region="lower",
                    purpose="medicine",
                    candidate_name="Returning student",
                    bearer_id=consequence.bearer_id,
                    prior_case_results=[prior_result],
                    presented_documents_override={
                        "student ID": "A current student identification card.",
                        "doctor's note": "A fresh nurse-signed note for an inhaler.",
                    },
                )
            ]
        )
    if not any(
        caller.edges_out(Selector(has_kind=Action, successor_id=return_block.uid)),
    ):
        Action(
            registry=caller.graph,
            predecessor_id=caller.uid,
            successor_id=return_block.uid,
            text="Meet the returning student",
            tags={"dynamic", "hall_monitor_return"},
        )
    return None


@on_journal(wants_caller_kind=HallMonitorConsequenceBlock, wants_exact_kind=False)
def render_hall_monitor_consequence(
    *,
    caller: HallMonitorConsequenceBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> ContentFragment | None:
    """Reveal recorded Hall Monitor consequences only at the later note beat."""

    source = caller.graph.find_one(Selector(label=caller.source_block_label))
    if not isinstance(source, HallMonitorBlock) or not source.consequences:
        return None
    consequence = source.consequences[-1]
    bearer = caller.graph.get(consequence.bearer_id)
    if not isinstance(bearer, HasSimpleLook):
        raise LookupError(f"Hall Monitor bearer {consequence.bearer_id} is not present")
    name = bearer.get_label()
    presence = render_text_as(bearer, "presence_description", ctx=ctx)
    subject = f"{name}, {presence}," if presence else name
    if consequence.outcome == "inhaler_withheld":
        content = (
            f"{subject} was sent back to class. Their inhaler remained at the "
            "hall desk while the nurse's unsigned note was checked."
        )
    else:
        content = f"{subject} reached the nurse's office with their inhaler."
    return ContentFragment(
        content=content,
        source_id=consequence.bearer_id,
        tags={"hall_monitor_consequence"},
    )


@on_journal(wants_caller_kind=HallMonitorReturnBlock, wants_exact_kind=False)
def render_hall_monitor_return(
    *,
    caller: HallMonitorReturnBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> ContentFragment | None:
    """Recognize the returning bearer through their live presence projection."""

    game = caller.game
    if game.history or not game.active_case.prior_case_results:
        return None
    prior_result = game.active_case.prior_case_results[0]
    bearer = game.active_case.packet_manager.resolve_subject(prior_result.bearer_id)
    name = bearer.get_label()
    presence = render_text_as(bearer, "presence_description", ctx=ctx)
    subject = f"{name}, {presence}," if presence else name
    return ContentFragment(
        content=(
            f"{subject} returns after this morning's decision with a fresh nurse-signed note."
        ),
        source_id=bearer.uid,
        tags={"hall_monitor_return"},
    )


HallMonitorBlock.model_rebuild(_types_namespace={"UUID": UUID})
